import numpy as np
import threading
import queue
from .music_theory import Key, ScaleType, ProgressionGenerator


class LayerState:
    def __init__(self, name, active=True, volume=0.8):
        self.name = name
        self.active = active
        self.volume = volume
        self.complexity = 0.5


class Conductor:
    def __init__(self):
        self.bpm = 110.0
        self.key = Key('C', ScaleType.MINOR)
        self.progression = ProgressionGenerator(self.key)
        
        self.current_chord = self.key.get_chord(1)
        
        # State Management
        self.state = 'setup'  # setup, playing, outro, finished
        self.outro_steps = 0
        
        # Outro: 3-phase system
        self.outro_phase = None        # 'approach', 'cadence', 'ringout'
        self.outro_volume_mult = 1.0   # Master fade: 1.0 → 0.0 over ring-out
        self._outro_entry_bpm = 110.0  # BPM when outro was triggered
        self._outro_entry_intensity = 0.5
        
        # Global Parameters
        self.intensity = 0.5
        self.tension = 0.0
        self.style = 'rock'  # 'rock', 'pop', 'edm', 'classical'
        
        # Effects parameters (higher defaults for prominence)
        self.distortion_pct = 60  # 0-100 (60 = heavy crunch)
        self.delay_mix = 0.4     # 0-1
        self.reverb_mix = 0.35   # 0-1
        self.chorus_mix = 0.3    # 0-1
        self.sustain_pct = 70    # 0-100 (note duration control)
        
        # Layers
        self.layers = {
            'kick': LayerState('kick', True, 0.9),
            'snare': LayerState('snare', True, 0.7),
            'hihat': LayerState('hihat', True, 0.5),
            'bass': LayerState('bass', True, 0.8),
            'rhythm': LayerState('rhythm', False, 0.6),
            'pad': LayerState('pad', True, 0.5),
            'arp': LayerState('arp', False, 0.6),
            'lead': LayerState('lead', True, 0.7),
            'harmony': LayerState('harmony', False, 0.6),
            'riser': LayerState('riser', True, 0.5),
        }
        
        # Snapshot of layer states before outro (for reference)
        self._pre_outro_layers = {}
        
        self.bar_count = 0
        self.lock = threading.Lock()
        
    def start(self):
        """Transition from setup to playing."""
        with self.lock:
            self.state = 'playing'
            self.bar_count = 0

    def trigger_outro(self):
        """Trigger the 3-phase outro sequence.
        
        Phase 1 — Approach (steps 0-3): Gentle slowdown, IV→ii progression,
            rhythmic layers thin out progressively.
        Phase 2 — Cadence (steps 4-7): Stronger ritardando, V7→I perfect
            authentic cadence, only harmonic layers remain.
        Phase 3 — Ring-out (steps 8-14): Deep ritardando, holds tonic,
            master volume fades smoothly to silence.
        """
        with self.lock:
            self.state = 'outro'
            self.outro_steps = 0
            self.outro_phase = 'approach'
            self.outro_volume_mult = 1.0
            self._outro_entry_bpm = self.bpm
            self._outro_entry_intensity = self.intensity
            
            # Snapshot current layer states
            self._pre_outro_layers = {
                k: v.active for k, v in self.layers.items()
            }
            
            # Disable riser immediately — it sounds wrong in an outro
            self.layers['riser'].active = False
            
            # Start the approach: subdominant (IV) chord
            self.current_chord = self.key.get_chord(4)
            
    def _update_outro(self):
        """Internal: advance the outro by one step (called with lock held)."""
        self.outro_steps += 1
        
        # ─── PHASE 1: APPROACH (steps 1-4) ───
        # Gentle slowdown, IV → ii, layers thin progressively
        if self.outro_steps <= 4:
            self.outro_phase = 'approach'
            
            # Gentle ritardando — barely noticeable at first
            self.bpm = max(30, self.bpm * 0.97)
            
            # Smooth intensity fade: entry → 0.35
            progress = self.outro_steps / 4.0
            self.intensity = self._outro_entry_intensity * (1.0 - progress * 0.6)
            
            # Chord progression within approach
            if self.outro_steps == 1:
                # IV — subdominant (already set in trigger_outro)
                pass
            elif self.outro_steps == 2:
                # Stay on IV — let it breathe
                pass
            elif self.outro_steps == 3:
                # ii — supertonic (subdominant preparation)
                self.current_chord = self.key.get_chord(2)
            elif self.outro_steps == 4:
                # Stay on ii — building anticipation for V
                pass
            
            # Progressive layer removal
            if self.outro_steps == 1:
                # Drop kick and hihat first — lighten the beat
                self.layers['kick'].active = False
                self.layers['hihat'].active = False
                self.layers['riser'].active = False
            elif self.outro_steps == 2:
                # Drop snare — rhythm fading
                self.layers['snare'].active = False
                self.layers['arp'].active = False
            elif self.outro_steps == 3:
                # Drop rhythm guitar — just harmonic foundation now
                self.layers['rhythm'].active = False
            elif self.outro_steps == 4:
                # Only harmonic layers remain
                self.layers['bass'].active = False
                self.layers['pad'].active = True
                self.layers['lead'].active = True
                self.layers['harmony'].active = True
                
        # ─── PHASE 2: CADENCE (steps 5-8) ───
        # Stronger ritardando, V7 → I perfect authentic cadence
        elif self.outro_steps <= 8:
            self.outro_phase = 'cadence'
            
            # Stronger ritardando
            self.bpm = max(25, self.bpm * 0.93)
            
            # Continue fading intensity
            cadence_progress = (self.outro_steps - 4) / 4.0
            self.intensity = max(0.1, 0.35 - cadence_progress * 0.15)
            
            if self.outro_steps == 5:
                # V7 — dominant seventh (maximum tension before resolution)
                self.current_chord = self.key.get_chord(5, add_7th=True)
            elif self.outro_steps == 6:
                # Stay on V7 — let the tension build
                pass
            elif self.outro_steps == 7:
                # I — RESOLUTION (the moment of arrival)
                self.current_chord = self.key.get_chord(1)
            elif self.outro_steps == 8:
                # Stay on I — savor the resolution
                pass
                
            # Keep only pad + lead during cadence, add harmony for body
            self.layers['pad'].active = True
            self.layers['lead'].active = True
            self.layers['harmony'].active = True
            
        # ─── PHASE 3: RING-OUT (steps 9-15) ───
        # Deep ritardando, hold tonic, master fade to silence
        elif self.outro_steps <= 15:
            self.outro_phase = 'ringout'
            
            # Deep ritardando — noticeable deceleration
            self.bpm = max(20, self.bpm * 0.88)
            
            # Hold on tonic (I)
            self.current_chord = self.key.get_chord(1)
            
            # Intensity dwindles
            self.intensity = max(0.05, 0.2 - (self.outro_steps - 8) * 0.025)
            
            # Master volume fade: smooth curve to silence
            ringout_progress = (self.outro_steps - 8) / 7.0  # 0.0 → 1.0
            # Use an exponential ease-out so the fade feels natural
            self.outro_volume_mult = max(0.0, (1.0 - ringout_progress) ** 1.5)
            
            # Thin layers during ring-out
            if self.outro_steps >= 11:
                self.layers['harmony'].active = False
            if self.outro_steps >= 13:
                self.layers['lead'].active = False
                # Only pad ringing out
                
        # ─── FINISHED ───
        else:
            self.outro_volume_mult = 0.0
            self.state = 'finished'
            return
            
    def update(self):
        """Called every measure (or beat in outro) to update state."""
        with self.lock:
            if self.state == 'outro':
                self._update_outro()

            elif self.state == 'playing':
                phrase_pos = self.bar_count % 4
                self.current_chord = self.progression.next_chord(
                    richness=0.3 + self.tension * 0.4,
                    position_in_phrase=phrase_pos
                )
                self.bar_count += 1

    def get_beat_duration(self):
        return 60.0 / self.bpm

    def apply_style(self, style):
        """Configure layers for a specific style."""
        with self.lock:
            self.style = style
            
            if style == 'rock':
                self.layers['kick'].active = True
                self.layers['snare'].active = True
                self.layers['hihat'].active = True
                self.layers['bass'].active = True
                self.layers['rhythm'].active = True
                self.layers['pad'].active = False
                self.layers['lead'].active = True
                self.layers['harmony'].active = False
                self.layers['arp'].active = False
                self.distortion_pct = 60
                self.delay_mix = 0.2
                self.reverb_mix = 0.15
                self.sustain_pct = 60
                
            elif style == 'pop':
                self.layers['kick'].active = True
                self.layers['snare'].active = True
                self.layers['hihat'].active = True
                self.layers['bass'].active = True
                self.layers['rhythm'].active = True
                self.layers['pad'].active = True
                self.layers['lead'].active = True
                self.layers['harmony'].active = False
                self.layers['arp'].active = False
                self.distortion_pct = 10
                self.delay_mix = 0.3
                self.reverb_mix = 0.25
                self.chorus_mix = 0.3
                self.sustain_pct = 70
                
            elif style == 'edm':
                self.layers['kick'].active = True
                self.layers['snare'].active = True
                self.layers['hihat'].active = True
                self.layers['bass'].active = True
                self.layers['rhythm'].active = False
                self.layers['pad'].active = True
                self.layers['lead'].active = True
                self.layers['harmony'].active = False
                self.layers['arp'].active = True
                self.layers['riser'].active = True
                self.distortion_pct = 0
                self.delay_mix = 0.4
                self.reverb_mix = 0.3
                self.sustain_pct = 50
                
            elif style == 'classical':
                self.layers['kick'].active = False
                self.layers['snare'].active = False
                self.layers['hihat'].active = False
                self.layers['bass'].active = True
                self.layers['rhythm'].active = False
                self.layers['pad'].active = True
                self.layers['lead'].active = True
                self.layers['harmony'].active = True
                self.layers['arp'].active = True
                self.layers['riser'].active = False
                self.distortion_pct = 0
                self.delay_mix = 0.15
                self.reverb_mix = 0.4
                self.chorus_mix = 0.2
                self.sustain_pct = 85

    def set_param(self, param, value):
        with self.lock:
            if param == 'bpm':
                self.bpm = float(value)
            elif param == 'intensity':
                self.intensity = float(value) / 100.0
            elif param == 'distortion':
                self.distortion_pct = max(0, min(100, int(value)))
            elif param == 'delay':
                self.delay_mix = float(value) / 100.0
            elif param == 'reverb':
                self.reverb_mix = float(value) / 100.0
            elif param == 'chorus':
                self.chorus_mix = float(value) / 100.0
            elif param == 'sustain':
                self.sustain_pct = max(0, min(100, int(value)))
            elif param == 'key':
                parts = value.split()
                root = parts[0]
                scale = ScaleType.MINOR
                if len(parts) > 1 and 'maj' in parts[1].lower():
                    scale = ScaleType.MAJOR
                self.key = Key(root, scale)
                self.progression = ProgressionGenerator(self.key)
