import numpy as np

class Guitar:
    def __init__(self, fs=44100):
        self.fs = fs
        
    def karplus_strong(self, freq, duration, decay_factor=0.996):
        """Karplus-Strong string synthesis with frequency-compensated decay."""
        N = int(self.fs * duration)
        p = int(self.fs / freq)
        
        if p < 2:
            return np.zeros(N)
        
        # --- FREQUENCY COMPENSATION ---
        # The KS averaging filter runs (freq) times per second.
        # Higher freq = faster decay. Compensate aggressively.
        ref_freq = 130.0  # ~C3
        if freq > ref_freq:
            octaves_above = np.log2(freq / ref_freq)
            # Aggressive: +0.008 per octave above C3
            compensation = octaves_above * 0.008
            decay_factor = min(0.99999, decay_factor + compensation)
        
        # Initialize wavetable with noise burst
        wavetable = np.random.uniform(-1, 1, p)
        
        # Pre-filter: fewer passes for high notes (short buffers)
        # 3 passes on a 25-sample buffer destroys the signal
        num_smooth_passes = max(1, min(3, p // 30))
        for _ in range(num_smooth_passes):
            smoothed = np.zeros_like(wavetable)
            for i in range(len(wavetable)):
                smoothed[i] = 0.5 * (wavetable[i] + wavetable[(i - 1) % p])
            wavetable = smoothed
        
        # Output buffer
        output = np.zeros(N)
        
        buf = wavetable.copy()
        buf_idx = 0
        
        for n in range(N):
            output[n] = buf[buf_idx]
            
            prev_idx = (buf_idx - 1) % p
            new_val = decay_factor * 0.5 * (buf[buf_idx] + buf[prev_idx])
            
            buf[buf_idx] = new_val
            buf_idx = (buf_idx + 1) % p
        
        return output



    def cabinet_simulator(self, audio):
        """Simulates a Guitar Cabinet (bandpass 80-4500Hz)"""
        try:
            from scipy.signal import butter, lfilter
            # High Pass at 80Hz
            b_hp, a_hp = butter(2, 80 / (self.fs / 2), btype='high')
            audio = lfilter(b_hp, a_hp, audio)
            # Low Pass at 4500Hz
            b_lp, a_lp = butter(2, 4500 / (self.fs / 2), btype='low')
            audio = lfilter(b_lp, a_lp, audio)
            return audio
        except ImportError:
            # Fallback: simple moving average LPF
            kernel = np.ones(10) / 10.0
            return np.convolve(audio, kernel, mode='same')

    def apply_distortion(self, audio, gain=5.0):
        """Tube-amp style soft clipping + cabinet simulation."""
        # Drive stage
        driven = np.tanh(audio * gain)
        # Cabinet sim removes the harsh upper harmonics from clipping
        return self.cabinet_simulator(driven)

    def play_chord(self, freqs, duration, velocity=0.8, style='clean', strum_speed=0.03):
        """Simulates strumming a chord with staggered string onsets."""
        total_dur = duration + strum_speed * len(freqs)
        max_samples = int(self.fs * total_dur)
        mixed = np.zeros(max_samples)
        
        for i, f in enumerate(freqs):
            delay_samples = int(self.fs * (i * strum_speed))
            delay_samples = max(0, delay_samples)
            
            string_sig = self.karplus_strong(f, duration)
            
            end = min(delay_samples + len(string_sig), max_samples)
            write_len = end - delay_samples
            if write_len > 0:
                mixed[delay_samples:end] += string_sig[:write_len]
        
        # Normalize
        peak = np.max(np.abs(mixed))
        if peak > 0:
            mixed = mixed / peak
        
        mixed *= velocity
        
        if style == 'distorted':
            mixed = self.apply_distortion(mixed, gain=8.0)
        elif style == 'crunch':
            mixed = self.apply_distortion(mixed, gain=3.0)
        else:
            mixed = self.cabinet_simulator(mixed)
            
        return mixed

    def play_note(self, freq, duration, velocity=0.8, style='clean', sustain_pct=70):
        """Play a single guitar note.
        
        sustain_pct: 0-100.
          0   = very short, note dies quickly (decay=0.98)
          50  = normal pluck (decay=0.996)
          100 = infinite sustain, note never dies (decay=0.9999)
        """
        # Map sustain_pct to KS decay factor
        # 0% -> 0.98 (fast decay), 50% -> 0.996, 100% -> 0.9999 (infinite)
        s = max(0, min(100, sustain_pct)) / 100.0
        decay = 0.98 + s * 0.0199  # Range: 0.98 to 0.9999
        
        raw = self.karplus_strong(freq, duration, decay_factor=decay)
        
        # Normalize to unit amplitude before effects
        peak = np.max(np.abs(raw))
        if peak < 1e-6:
            return np.zeros_like(raw)
        raw = raw / peak
        
        if style == 'distorted':
            raw = self.apply_distortion(raw, gain=10.0)
        elif style == 'crunch':
            raw = self.apply_distortion(raw, gain=4.0)
        else:
            raw = self.cabinet_simulator(raw)
        
        return raw * velocity

