import pyaudio
import numpy as np
import threading
import queue
import time

from .conductor import Conductor
from .instruments.synthesizer import Synthesizer, Waveform
from .instruments.guitar import Guitar
from .instruments.drums import DrumMachine
from .effects import distortion, delay, reverb, chorus

class AudioEngine:
    def __init__(self, conductor: Conductor):
        self.conductor = conductor
        self.fs = 44100
        
        # Instruments
        self.synth = Synthesizer(self.fs)
        self.guitar = Guitar(self.fs)
        self.drums = DrumMachine(self.fs)
        
        # Audio Buffer Queue
        self.buffer_queue = queue.Queue(maxsize=2)
        self.running = True
        
        # Carry-over buffer for tails extending past beat
        self.carry_buffer = np.zeros(int(self.fs * 4.0))
        
        self.beat_count = 0
        
        # Lead state - start at center of scale
        self.last_lead_note_idx = 7  # Center of a ~14-note scale
        
    def _get_lead_scale(self):
        """Get scale notes for lead, shifted down to mid range (octave 3-4)."""
        raw = self.conductor.key.get_scale_notes(octaves=2)
        # Shift down one octave: divide all frequencies by 2
        # This puts C major from 261-932Hz down to 130-466Hz (C3-A#4)
        return [f / 2.0 for f in raw]
    
    def _pick_lead_note(self, scale, is_strong=False):
        """Pick next lead note with center bias.
        
        Melody gravitates toward the middle of the scale (indices 4-9).
        Occasionally ventures to extremes for variety.
        """
        center = len(scale) // 2  # Middle of the range
        idx = self.last_lead_note_idx
        
        # Clamp to valid range first
        idx = max(0, min(len(scale)-1, idx))
        
        # 70% chance: pull toward center (mid range focus)
        # 20% chance: free movement (stepwise)  
        # 10% chance: wider jump (occasional high/low)
        roll = np.random.random()
        
        if roll < 0.70:
            # Bias toward center - step toward middle
            if idx < center - 2:
                step = np.random.choice([1, 2])  # Move up toward center
            elif idx > center + 2:
                step = np.random.choice([-1, -2])  # Move down toward center
            else:
                # In the sweet spot - small movements
                step = np.random.choice([-1, 0, 1], p=[0.35, 0.2, 0.45])
        elif roll < 0.90:
            # Free stepwise
            step = np.random.choice([-2, -1, 1, 2], p=[0.15, 0.35, 0.35, 0.15])
        else:
            # Wide jump for variety
            step = np.random.choice([-4, -3, 3, 4], p=[0.2, 0.3, 0.3, 0.2])
        
        idx = max(0, min(len(scale)-1, idx + step))
        self.last_lead_note_idx = idx
        return scale[idx]
        
    def start(self):
        threading.Thread(target=self.producer_loop, daemon=True).start()
        
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paFloat32,
                        channels=1,
                        rate=self.fs,
                        output=True)
        print("Audio Engine Started.")
        
        while self.running:
            try:
                data = self.buffer_queue.get(timeout=1)
                stream.write(data)
            except queue.Empty:
                pass
            except KeyboardInterrupt:
                break
                
        stream.stop_stream()
        stream.close()
        p.terminate()

    def producer_loop(self):
        while self.running:
            if self.buffer_queue.full():
                time.sleep(0.05)
                continue
            beat_audio = self.render_next_beat()
            self.buffer_queue.put(beat_audio.astype(np.float32).tobytes())

    def mix_clip(self, buffer, clip, start_sample, volume=1.0):
        """Mixes a clip into the buffer at start_sample."""
        if len(clip) == 0: return
        clip = clip * volume
        end_sample = start_sample + len(clip)
        max_len = len(buffer)
        
        if start_sample < max_len:
            write_len = min(len(clip), max_len - start_sample)
            buffer[start_sample : start_sample + write_len] += clip[:write_len]
            if write_len < len(clip):
                remaining = clip[write_len:]
                if len(remaining) > len(self.carry_buffer):
                    self.carry_buffer = np.resize(self.carry_buffer, len(remaining) + 44100)
                self.carry_buffer[:len(remaining)] += remaining
        else:
            offset = start_sample - max_len
            if offset + len(clip) > len(self.carry_buffer):
                new_len = offset + len(clip) + 44100
                new_carry = np.zeros(new_len)
                new_carry[:len(self.carry_buffer)] = self.carry_buffer
                self.carry_buffer = new_carry
            self.carry_buffer[offset : offset + len(clip)] += clip

    # ========================================
    # DRUMS (shared across styles)
    # ========================================
    def render_drums(self, buffer, num_samples, pos, intensity):
        if self.conductor.layers['kick'].active:
            if pos == 0:
                self.mix_clip(buffer, self.drums.kick(), 0, 0.9)
            elif pos == 2 and intensity > 0.5:
                self.mix_clip(buffer, self.drums.kick(), 0, 0.9)
                
        if self.conductor.layers['snare'].active:
            if pos == 2:
                self.mix_clip(buffer, self.drums.snare(), 0, 0.8)
            if intensity > 0.6 and np.random.random() < 0.2:
                off = int(num_samples * 0.75)
                self.mix_clip(buffer, self.drums.snare() * 0.4, off, 0.4)
            # Tom fill every 16 beats
            if self.beat_count % 16 == 15 and intensity > 0.7:
                tom_hi = self.drums.tom(150, 0.1)
                tom_lo = self.drums.tom(100, 0.1)
                step = int(num_samples / 4)
                self.mix_clip(buffer, tom_hi, 0, 0.8)
                self.mix_clip(buffer, tom_hi, step, 0.7)
                self.mix_clip(buffer, tom_lo, step*2, 0.8)
                self.mix_clip(buffer, tom_lo, step*3, 0.7)

        if self.conductor.layers['hihat'].active:
            hh_vol = 0.4 + (intensity * 0.3)
            self.mix_clip(buffer, self.drums.hihat(open=False), 0, hh_vol)
            is_open = (intensity > 0.7 and pos == 3)
            self.mix_clip(buffer, self.drums.hihat(open=is_open), int(num_samples/2), hh_vol * 0.8)

    # ========================================
    # BASS (shared across styles)
    # ========================================
    def render_bass(self, buffer, num_samples, pos, beat_dur, root, intensity):
        if not self.conductor.layers['bass'].active:
            return
        freq = root / 2
        dur = beat_dur * 0.8
        if pos == 0:
            bass = self.synth.generate_wave(freq, dur, Waveform.SAW, 0.6)
            bass = self.synth.low_pass_filter(bass, 300 + intensity*200)
            bass = self.synth.apply_envelope(bass, 0.05, 0.2, 0.6, 0.2)
            self.mix_clip(buffer, bass, 0, 0.8)
        elif pos == 2 and intensity > 0.4:
            bass = self.synth.generate_wave(freq, dur/2, Waveform.SQUARE, 0.5)
            bass = self.synth.low_pass_filter(bass, 400)
            bass = self.synth.apply_envelope(bass, 0.03, 0.1, 0.0, 0.1)
            self.mix_clip(buffer, bass, int(num_samples/2), 0.7)

    # ========================================
    # PAD (shared)
    # ========================================
    def render_pad(self, buffer, num_samples, pos, beat_dur, chord):
        if not self.conductor.layers['pad'].active or pos != 0:
            return
        for idx, f in enumerate(chord):
            pad = self.synth.generate_wave(f, beat_dur * 4.0, Waveform.SAW, 0.12)
            pad = self.synth.low_pass_filter(pad, 600 + idx * 200)
            pad = self.synth.apply_envelope(pad, attack=0.8, sustain=0.8, release=1.0)
            pad2 = self.synth.generate_wave(f * 1.003, beat_dur * 4.0, Waveform.SAW, 0.12)
            pad2 = self.synth.low_pass_filter(pad2, 600)
            pad2 = self.synth.apply_envelope(pad2, attack=0.8, sustain=0.8, release=1.0)
            self.mix_clip(buffer, pad + pad2, 0, 0.6)

    # ========================================
    # ARPEGGIATOR (shared)
    # ========================================
    def render_arp(self, buffer, num_samples, beat_dur, chord):
        if not self.conductor.layers['arp'].active:
            return
        arp_speed = 4
        step = int(num_samples / arp_speed)
        for i in range(arp_speed):
            note_idx = (self.beat_count * arp_speed + i) % len(chord)
            freq = chord[note_idx] * 4
            arp_sig = self.synth.generate_wave(freq, 0.1, Waveform.SQUARE, 0.1)
            arp_sig = self.synth.apply_envelope(arp_sig, 0.005, 0.05, 0.0, 0.05)
            arp_sig = self.synth.low_pass_filter(arp_sig, 2000)
            self.mix_clip(buffer, arp_sig, step * i, 0.4)

    # ========================================
    # RISER (shared)
    # ========================================
    def render_riser(self, buffer, num_samples, beat_dur, intensity):
        if not self.conductor.layers['riser'].active:
            return
        loop_pos = self.beat_count % 16
        if loop_pos >= 12 and intensity > 0.4:
            sweep_progress = (loop_pos - 12) / 4.0
            riser_sig = self.synth.generate_wave(100, beat_dur, Waveform.NOISE, 0.15 * intensity)
            avg_f = 200 + (8000 * (sweep_progress + 0.125))
            riser_sig = self.synth.low_pass_filter(riser_sig, avg_f)
            self.mix_clip(buffer, riser_sig, 0, 0.4)

    # ========================================
    # STYLE: ROCK
    # ========================================
    def render_rock_lead(self, buffer, num_samples, beat_dur, pos, intensity, chord):
        """Rock lead: always on, distorted, faster at high intensity."""
        if not self.conductor.layers['lead'].active:
            return
        scale = self._get_lead_scale()
        dist_pct = self.conductor.distortion_pct
        dist_gain = dist_pct / 5.0
        sus = self.conductor.sustain_pct
        sustain_mult = 0.2 + (sus / 100.0) * 1.8
        
        is_strong = (pos % 2 == 0)
        freq = self._pick_lead_note(scale, is_strong)
        
        if intensity > 0.7:
            dur = beat_dur * 0.5 * sustain_mult
            
            lead1 = self.guitar.play_note(freq, dur, velocity=0.9, style='clean', sustain_pct=sus)
            if dist_pct > 0:
                lead1 = distortion(lead1, gain=dist_gain, mix=min(1.0, dist_pct/60.0))
            self.mix_clip(buffer, lead1, 0, 0.9)
            
            step2 = np.random.choice([-1, 1, 2])
            freq2 = self._pick_lead_note(scale)
            lead2 = self.guitar.play_note(freq2, dur, velocity=0.8, style='clean', sustain_pct=sus)
            if dist_pct > 0:
                lead2 = distortion(lead2, gain=dist_gain, mix=min(1.0, dist_pct/60.0))
            self.mix_clip(buffer, lead2, int(num_samples/2), 0.8)
        else:
            dur = beat_dur * sustain_mult
            lead_sig = self.guitar.play_note(freq, dur, velocity=0.8, style='clean', sustain_pct=sus)
            if dist_pct > 0:
                lead_sig = distortion(lead_sig, gain=dist_gain, mix=min(1.0, dist_pct/60.0))
            if self.conductor.delay_mix > 0:
                lead_sig = delay(lead_sig, self.fs, 350, 0.45, self.conductor.delay_mix)
            self.mix_clip(buffer, lead_sig, 0, 0.9)
        
        # Harmony voice
        if self.conductor.layers['harmony'].active:
            h_freq = self._pick_lead_note(scale)
            h_sig = self.guitar.play_note(h_freq, beat_dur * 0.8, velocity=0.5, style='crunch', sustain_pct=sus)
            self.mix_clip(buffer, h_sig, 0, 0.7)

    def render_rock_rhythm(self, buffer, num_samples, beat_dur, pos, intensity, chord):
        """Rock rhythm guitar: heavy power chords, palm mutes, double-tracked."""
        if not self.conductor.layers['rhythm'].active or intensity < 0.2:
            return
        dist_pct = self.conductor.distortion_pct
        sus = self.conductor.sustain_pct
        
        # Power chord frequencies (root, 5th, octave) - down an octave for weight
        gtr_chord = [chord[0], chord[0] * 1.5, chord[0] * 2.0]
        
        # Main chords: beats 1 and 3 always, 2 and 4 at higher intensity
        if pos == 0 or pos == 2:
            # Full power chord hit
            dur = beat_dur * (0.4 + (sus / 100.0) * 0.6)
            sig = self.guitar.play_chord(gtr_chord, dur, velocity=0.9, style='clean', strum_speed=0.01)
            if dist_pct > 5:
                sig = distortion(sig, gain=dist_pct / 7.0, mix=min(1.0, dist_pct / 40.0))
            self.mix_clip(buffer, sig, 0, 0.75)
            
            # Double-track: same chord slightly detuned for thickness
            gtr_chord2 = [f * 1.003 for f in gtr_chord]
            sig2 = self.guitar.play_chord(gtr_chord2, dur, velocity=0.7, style='clean', strum_speed=0.015)
            if dist_pct > 5:
                sig2 = distortion(sig2, gain=dist_pct / 7.0, mix=min(1.0, dist_pct / 40.0))
            self.mix_clip(buffer, sig2, 0, 0.4)
            
        elif intensity > 0.5:
            # Upbeat: shorter, punchier chord
            dur = beat_dur * 0.3
            sig = self.guitar.play_chord(gtr_chord, dur, velocity=0.6, style='clean', strum_speed=0.01)
            if dist_pct > 5:
                sig = distortion(sig, gain=dist_pct / 7.0, mix=min(1.0, dist_pct / 40.0))
            self.mix_clip(buffer, sig, 0, 0.55)
        
        # Palm-muted 8th notes at high intensity (chugging)
        if intensity > 0.7 and (pos == 1 or pos == 3):
            palm_freq = chord[0]  # Root note only, palm muted
            half = int(num_samples / 2)
            for sub_beat in range(2):
                pm = self.guitar.play_note(palm_freq, beat_dur * 0.15, velocity=0.5, style='clean', sustain_pct=10)
                if dist_pct > 5:
                    pm = distortion(pm, gain=dist_pct / 8.0, mix=min(1.0, dist_pct / 50.0))
                self.mix_clip(buffer, pm, sub_beat * half, 0.5)


    # ========================================
    # STYLE: POP
    # ========================================
    def render_pop_lead(self, buffer, num_samples, beat_dur, pos, intensity, chord):
        """Pop lead: punchy, clean guitar, catchy melodic phrases."""
        if not self.conductor.layers['lead'].active:
            return
        scale = self._get_lead_scale()
        freq = self._pick_lead_note(scale)
        sus = self.conductor.sustain_pct
        dur = beat_dur * (0.2 + (sus / 100.0) * 1.8)
        
        # Punchy: occasional octave jump for catchiness
        if np.random.random() < 0.15 and intensity > 0.5:
            freq = freq * 2  # Octave up pop hook
        
        lead_sig = self.guitar.play_note(freq, dur, velocity=0.8, style='clean', sustain_pct=sus)
        lead_sig = chorus(lead_sig, self.fs, mix=self.conductor.chorus_mix)
        if self.conductor.delay_mix > 0:
            lead_sig = delay(lead_sig, self.fs, 300, 0.35, self.conductor.delay_mix)
        self.mix_clip(buffer, lead_sig, 0, 0.8)
        
        # At high intensity: add a second punchy note (8th note)
        if intensity > 0.6 and np.random.random() < 0.6:
            freq2 = self._pick_lead_note(scale)
            dur2 = dur * 0.5
            lead2 = self.guitar.play_note(freq2, dur2, velocity=0.65, style='clean', sustain_pct=sus)
            lead2 = chorus(lead2, self.fs, mix=self.conductor.chorus_mix * 0.5)
            self.mix_clip(buffer, lead2, int(num_samples / 2), 0.6)

    def render_pop_rhythm(self, buffer, num_samples, beat_dur, pos, intensity, chord):
        """Pop rhythm: down-up strumming pattern, clean with chorus shimmer."""
        if not self.conductor.layers['rhythm'].active:
            return
        sus = self.conductor.sustain_pct
        gtr_chord = [f * 2 for f in chord]
        half = int(num_samples / 2)
        
        # Down-up strumming pattern
        # Downstroke: strong, slower strum
        down_vel = 0.8 if pos % 2 == 0 else 0.6  # Accent on 1 and 3
        down_dur = beat_dur * (0.3 + (sus / 100.0) * 0.4)
        down = self.guitar.play_chord(gtr_chord, down_dur, velocity=down_vel, style='clean', strum_speed=0.03)
        down = chorus(down, self.fs, mix=0.25)
        self.mix_clip(buffer, down, 0, 0.75)
        
        # Upstroke: lighter, faster strum on the "and" of each beat
        if intensity > 0.3:
            up_vel = 0.45
            up_dur = beat_dur * 0.25
            # Upstroke uses fewer strings (top 3 notes)
            up_chord = gtr_chord[-3:] if len(gtr_chord) >= 3 else gtr_chord
            up = self.guitar.play_chord(up_chord, up_dur, velocity=up_vel, style='clean', strum_speed=0.015)
            up = chorus(up, self.fs, mix=0.2)
            self.mix_clip(buffer, up, half, 0.55)


    # ========================================
    # STYLE: EDM
    # ========================================
    def render_edm_lead(self, buffer, num_samples, beat_dur, pos, intensity, chord):
        """EDM lead: synth-based, saw/square with filter sweeps."""
        if not self.conductor.layers['lead'].active:
            return
        scale = self._get_lead_scale()
        freq = self._pick_lead_note(scale)
        next_idx = self.last_lead_note_idx
        
        # EDM uses synth, not guitar
        waveform = Waveform.SAW if np.random.random() > 0.3 else Waveform.SQUARE
        
        if intensity > 0.7:
            # 16th notes: sustain controls each sub-note
            sub_sustain = 0.3 + (self.conductor.sustain_pct / 100.0) * 0.7
            note_dur = beat_dur / 4.0 * sub_sustain
            step_s = int(num_samples / 4)
            for i in range(4):
                n_idx = max(0, min(len(scale)-1, next_idx + np.random.choice([-1, 0, 1])))
                f = scale[n_idx]
                sig = self.synth.generate_wave(f * 2, note_dur, waveform, 0.4)
                sig = self.synth.apply_envelope(sig, 0.005, 0.05, 0.3, 0.05)
                cutoff = 800 + intensity * 4000
                sig = self.synth.low_pass_filter(sig, cutoff)
                self.mix_clip(buffer, sig, step_s * i, 0.7)
        else:
            dur = beat_dur * (0.3 + (self.conductor.sustain_pct / 100.0) * 1.2)
            sig = self.synth.generate_wave(freq * 2, dur, waveform, 0.4)
            sig = self.synth.apply_envelope(sig, 0.01, 0.1, 0.5, 0.2)
            sig = self.synth.low_pass_filter(sig, 2000 + intensity * 3000)
            sig = delay(sig, self.fs, 250, 0.4, self.conductor.delay_mix)
            self.mix_clip(buffer, sig, 0, 0.7)

    # ========================================
    # STYLE: CLASSICAL
    # ========================================
    def render_classical_lead(self, buffer, num_samples, beat_dur, pos, intensity, chord):
        """Classical: strings + Mozart piano + woodwind color. Dynamic rhythm."""
        if not self.conductor.layers['lead'].active:
            return
        scale = self._get_lead_scale()
        sus = self.conductor.sustain_pct
        
        # Generate a dynamic rhythm pattern for this beat
        rhythm = self._classical_rhythm_pattern(beat_dur, intensity)
        
        # 1. PIANO (Mozart-style, co-equal with strings)
        self._render_classical_piano(buffer, num_samples, beat_dur, pos, intensity, chord, scale, rhythm, sus)
        
        # 2. STRING SECTION
        self._render_classical_strings(buffer, num_samples, beat_dur, pos, intensity, chord, scale, rhythm, sus)
        
        # 3. WOODWIND (color, not every beat)
        if pos == 0 or (pos == 2 and intensity > 0.5):
            self._render_classical_woodwind(buffer, num_samples, beat_dur, chord, scale, sus)
    
    def _classical_rhythm_pattern(self, beat_dur, intensity):
        """Generate a dynamic sub-beat rhythm pattern.
        
        Returns list of (offset_fraction, duration_fraction) tuples.
        """
        roll = np.random.random()
        
        if intensity > 0.7:
            patterns = [
                [(0.0, 0.25), (0.25, 0.25), (0.5, 0.5)],                # 2 eighths + quarter
                [(0.0, 0.5), (0.5, 0.25), (0.75, 0.25)],                # quarter + 2 eighths
                [(0.0, 0.25), (0.25, 0.25), (0.5, 0.25), (0.75, 0.25)], # 4 eighths (running)
                [(0.0, 0.33), (0.33, 0.33), (0.66, 0.34)],              # triplet
                [(0.0, 0.75), (0.75, 0.25)],                              # dotted quarter + eighth
            ]
        elif intensity > 0.4:
            patterns = [
                [(0.0, 1.0)],                           # quarter
                [(0.0, 0.5), (0.5, 0.5)],               # 2 eighths
                [(0.0, 0.75), (0.75, 0.25)],             # dotted + short
                [(0.0, 1.2)],                            # legato
            ]
        else:
            patterns = [
                [(0.0, 1.5)],                            # half note
                [(0.0, 1.0)],                            # quarter
                [(0.0, 2.0)],                            # very sustained
                [],                                       # rest
            ]
        
        return patterns[int(roll * len(patterns)) % len(patterns)]
    
    def _pick_consonant_note(self, scale, chord):
        """Pick a note biased toward chord tones to avoid dissonance.
        
        60% chord tone, 40% free scale tone.
        """
        chord_indices = []
        for i, s_freq in enumerate(scale):
            for c_freq in chord:
                ratio = s_freq / c_freq if c_freq > 0 else 0
                if ratio > 0:
                    cents = abs(12 * np.log2(ratio))
                    octave_cents = cents % 12
                    if octave_cents < 0.5 or octave_cents > 11.5:
                        chord_indices.append(i)
                        break
        
        if np.random.random() < 0.60 and chord_indices:
            idx = max(0, min(len(scale)-1, self.last_lead_note_idx))
            nearest = min(chord_indices, key=lambda ci: abs(ci - idx))
            nearest = max(0, min(len(scale)-1, nearest + np.random.choice([-1, 0, 0, 1])))
            self.last_lead_note_idx = nearest
            return scale[nearest]
        else:
            return self._pick_lead_note(scale)
    
    def _render_classical_piano(self, buffer, num_samples, beat_dur, pos, intensity, chord, scale, rhythm, sus):
        """Mozart-style piano: running passages, arpeggiated figures, sustained chords."""
        if not rhythm:
            return
        
        for offset_frac, dur_frac in rhythm:
            start_sample = int(offset_frac * num_samples)
            note_dur = beat_dur * dur_frac * (0.5 + (sus / 100.0) * 0.8)
            
            freq = self._pick_consonant_note(scale, chord)
            piano_sig = self.synth.piano_note(freq, note_dur, velocity=0.75)
            
            # Beat 1: left hand plays chord underneath
            if pos == 0 and offset_frac == 0.0:
                for c_freq in chord[:3]:
                    lh = self.synth.piano_note(c_freq / 2, beat_dur * 1.5, velocity=0.45)
                    self.mix_clip(buffer, lh, start_sample, 0.4)
            
            # Occasional octave doubling
            if np.random.random() < 0.15 and intensity > 0.5:
                oct = self.synth.piano_note(freq * 2, note_dur * 0.7, velocity=0.35)
                end = min(len(piano_sig), len(oct))
                piano_sig[:end] += oct[:end]
            
            piano_sig = reverb(piano_sig, self.fs, decay=0.3, mix=0.25)
            self.mix_clip(buffer, piano_sig, start_sample, 0.7)
    
    def _render_classical_strings(self, buffer, num_samples, beat_dur, pos, intensity, chord, scale, rhythm, sus):
        """String section: sustained bowed tones."""
        if not rhythm:
            return
        
        offset_frac, dur_frac = rhythm[0]
        str_dur = beat_dur * max(dur_frac, 0.8) * (0.6 + (sus / 100.0) * 0.8)
        start_sample = int(offset_frac * num_samples)
        
        freq = self._pick_consonant_note(scale, chord)
        n_samp = int(self.fs * str_dur)
        if n_samp < 2:
            return
        t = np.linspace(0, str_dur, n_samp, endpoint=False)
        phase = np.cumsum(np.ones(n_samp) / self.fs)
        vibrato = 1 + 0.004 * np.sin(2 * np.pi * 5.5 * t)
        
        v1 = np.sin(2 * np.pi * freq * vibrato * phase)
        v1 = self.synth.apply_envelope(v1, attack=0.15, decay=0.1, sustain=0.85, release=0.25, duration=str_dur)
        
        v2 = np.sin(2 * np.pi * freq * 1.002 * vibrato * phase)
        v2 = self.synth.apply_envelope(v2, attack=0.2, decay=0.1, sustain=0.8, release=0.3, duration=str_dur)
        
        cello_vib = 1 + 0.003 * np.sin(2 * np.pi * 4.5 * t)
        cello = np.sin(2 * np.pi * (freq / 2) * cello_vib * phase)
        cello += 0.25 * np.sin(2 * np.pi * freq * cello_vib * phase)
        cello = self.synth.apply_envelope(cello, attack=0.25, decay=0.15, sustain=0.8, release=0.35, duration=str_dur)
        
        strings = v1 * 0.35 + v2 * 0.25 + cello * 0.3
        strings = reverb(strings, self.fs, decay=0.45, mix=0.35)
        self.mix_clip(buffer, strings, start_sample, 0.6)
        
        # String harmony
        h_freq = self._pick_consonant_note(scale, chord)
        h_v = np.sin(2 * np.pi * h_freq * vibrato * phase)
        h_v = self.synth.apply_envelope(h_v, attack=0.25, sustain=0.7, release=0.3, duration=str_dur)
        h_v *= 0.2
        h_v = reverb(h_v, self.fs, decay=0.4, mix=0.3)
        self.mix_clip(buffer, h_v, start_sample, 0.4)
    
    def _render_classical_woodwind(self, buffer, num_samples, beat_dur, chord, scale, sus):
        """Woodwind color: occasional oboe phrases."""
        dur = beat_dur * (0.6 + (sus / 100.0) * 0.6)
        n_samp = int(self.fs * dur)
        if n_samp < 2:
            return
        t = np.linspace(0, dur, n_samp, endpoint=False)
        phase = np.cumsum(np.ones(n_samp) / self.fs)
        
        freq = self._pick_consonant_note(scale, chord)
        
        ww = np.sin(2 * np.pi * freq * phase) * 0.6
        ww += np.sin(2 * np.pi * freq * 2 * phase) * 0.2
        ww += np.sin(2 * np.pi * freq * 3 * phase) * 0.1
        
        ww = self.synth.apply_envelope(ww, attack=0.12, decay=0.1, sustain=0.6, release=0.2, duration=dur)
        ww *= (1 + 0.004 * np.sin(2 * np.pi * 5.0 * t))
        ww = self.synth.low_pass_filter(ww, 3500)
        ww = reverb(ww, self.fs, decay=0.3, mix=0.25)
        self.mix_clip(buffer, ww, 0, 0.25)


    # ========================================
    # MAIN RENDER
    # ========================================
    def render_next_beat(self):
        # Handle Setup (Silence)
        if self.conductor.state == 'setup':
            time.sleep(0.05)  # Prevent busy loop
            return np.zeros(int(self.fs * 0.1), dtype=np.float32)
            
        # Handle Outro / Playing updates
        if self.conductor.state == 'outro':
            self.conductor.update()  # Update every beat for smooth ritardando
        elif self.beat_count % 4 == 0:
            self.conductor.update()
            
        # Handle Finished
        if self.conductor.state == 'finished':
            self.running = False
            return np.zeros(1024, dtype=np.float32)
            
        beat_dur = self.conductor.get_beat_duration()
        num_samples = int(self.fs * beat_dur)
        beat_buffer = np.zeros(num_samples)
        
        # Carry-over from previous beats
        if len(self.carry_buffer) > 0:
            overlap = min(len(self.carry_buffer), num_samples)
            beat_buffer[:overlap] += self.carry_buffer[:overlap]
            new_carry = np.zeros_like(self.carry_buffer)
            if len(self.carry_buffer) > num_samples:
                remaining = self.carry_buffer[num_samples:]
                new_carry[:len(remaining)] = remaining
            self.carry_buffer = new_carry
        
        intensity = self.conductor.intensity
        chord = self.conductor.current_chord
        root = chord[0]
        pos = self.beat_count % 4
        style = self.conductor.style
        is_outro = self.conductor.state == 'outro'
        outro_phase = self.conductor.outro_phase
        
        # ---- SHARED LAYERS ----
        self.render_drums(beat_buffer, num_samples, pos, intensity)
        self.render_bass(beat_buffer, num_samples, pos, beat_dur, root, intensity)
        self.render_riser(beat_buffer, num_samples, beat_dur, intensity)
        
        # ---- STYLE-SPECIFIC LAYERS ----
        if style == 'rock':
            self.render_pad(beat_buffer, num_samples, pos, beat_dur, chord)
            self.render_rock_rhythm(beat_buffer, num_samples, beat_dur, pos, intensity, chord)
            self.render_rock_lead(beat_buffer, num_samples, beat_dur, pos, intensity, chord)
            
        elif style == 'pop':
            self.render_pad(beat_buffer, num_samples, pos, beat_dur, chord)
            self.render_pop_rhythm(beat_buffer, num_samples, beat_dur, pos, intensity, chord)
            self.render_pop_lead(beat_buffer, num_samples, beat_dur, pos, intensity, chord)
            
        elif style == 'edm':
            self.render_pad(beat_buffer, num_samples, pos, beat_dur, chord)
            self.render_arp(beat_buffer, num_samples, beat_dur, chord)
            self.render_edm_lead(beat_buffer, num_samples, beat_dur, pos, intensity, chord)
            
        elif style == 'classical':
            self.render_pad(beat_buffer, num_samples, pos, beat_dur, chord)
            self.render_arp(beat_buffer, num_samples, beat_dur, chord)
            self.render_classical_lead(beat_buffer, num_samples, beat_dur, pos, intensity, chord)
        
        # ---- OUTRO: STYLE-SPECIFIC TOUCHES ----
        if is_outro and outro_phase == 'cadence':
            self._render_outro_cadence_flavor(beat_buffer, num_samples, beat_dur, chord, style)
        
        # Master FX chain
        # 1. Master reverb (boost during ring-out for natural tail)
        reverb_mix = self.conductor.reverb_mix
        if is_outro:
            if outro_phase == 'cadence':
                reverb_mix = min(1.0, reverb_mix + 0.15)
            elif outro_phase == 'ringout':
                reverb_mix = min(1.0, reverb_mix + 0.3)
        
        if reverb_mix > 0:
            beat_buffer = reverb(beat_buffer, self.fs,
                                decay=0.5 + reverb_mix * 0.4,
                                mix=reverb_mix)
        
        # 2. Soft limiter (gentle to avoid breaking/chipping with distortion)
        beat_buffer = np.tanh(beat_buffer * 0.85) * 0.9
        
        # 3. Outro master volume fade
        if is_outro:
            beat_buffer *= self.conductor.outro_volume_mult
        
        self.beat_count += 1
        return beat_buffer
    
    def _render_outro_cadence_flavor(self, buffer, num_samples, beat_dur, chord, style):
        """Add style-specific color during the cadence phase of the outro."""
        if style == 'classical':
            # String swell: sustained chord with crescendo-decrescendo shape
            n_samp = min(num_samples, int(self.fs * beat_dur * 1.5))
            if n_samp < 2:
                return
            t = np.linspace(0, beat_dur * 1.5, n_samp, endpoint=False)
            swell = np.zeros(n_samp)
            for f in chord[:3]:
                vibrato = 1 + 0.005 * np.sin(2 * np.pi * 5.0 * t)
                swell += np.sin(2 * np.pi * (f / 2) * vibrato * t) * 0.15
            # Swell envelope: crescendo then fade
            env = np.sin(np.linspace(0, np.pi, n_samp))
            swell *= env
            swell = reverb(swell, self.fs, decay=0.5, mix=0.4)
            self.mix_clip(buffer, swell, 0, 0.5)
            
        elif style == 'rock':
            # Final power chord ring with heavy delay tail
            gtr_chord = [chord[0], chord[0] * 1.5, chord[0] * 2.0]
            sig = self.guitar.play_chord(gtr_chord, beat_dur * 1.2, velocity=0.7,
                                         style='clean', strum_speed=0.02)
            sig = distortion(sig, gain=4.0, mix=0.5)
            sig = delay(sig, self.fs, 450, 0.5, 0.6)
            self.mix_clip(buffer, sig, 0, 0.5)
            
        elif style == 'pop':
            # Clean chord with chorus shimmer
            gtr_chord = [f * 2 for f in chord[:3]]
            sig = self.guitar.play_chord(gtr_chord, beat_dur * 1.0, velocity=0.5,
                                         style='clean', strum_speed=0.04)
            sig = chorus(sig, self.fs, mix=0.5)
            sig = delay(sig, self.fs, 350, 0.4, 0.4)
            self.mix_clip(buffer, sig, 0, 0.4)
            
        elif style == 'edm':
            # Filter sweep down on a pad chord
            for f in chord[:3]:
                pad = self.synth.generate_wave(f, beat_dur, Waveform.SAW, 0.15)
                # Sweep cutoff from high to low over the beat
                sweep_steps = 8
                step_size = len(pad) // sweep_steps
                for i in range(sweep_steps):
                    cutoff = 4000 - (i / sweep_steps) * 3500
                    start = i * step_size
                    end = min((i + 1) * step_size, len(pad))
                    if end > start:
                        chunk = pad[start:end]
                        pad[start:end] = self.synth.low_pass_filter(
                            chunk, max(200, cutoff)
                        )
                pad = self.synth.apply_envelope(pad, attack=0.3, sustain=0.6, release=0.5)
                self.mix_clip(buffer, pad, 0, 0.4)

