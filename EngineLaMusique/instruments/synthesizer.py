import numpy as np
from enum import Enum

class Waveform(Enum):
    SINE = 0
    SAW = 1
    SQUARE = 2
    TRIANGLE = 3
    NOISE = 4

class Synthesizer:
    def __init__(self, sample_rate=44100):
        self.fs = sample_rate
        
    def generate_wave(self, freq, duration, waveform: Waveform = Waveform.SINE, amplitude=0.5):
        t = np.linspace(0, duration, int(self.fs * duration), endpoint=False)
        
        if waveform == Waveform.SINE:
            return amplitude * np.sin(2 * np.pi * freq * t)
        elif waveform == Waveform.SAW:
            return amplitude * (2 * (t * freq - np.floor(t * freq + 0.5)))
        elif waveform == Waveform.SQUARE:
            return amplitude * np.sign(np.sin(2 * np.pi * freq * t))
        elif waveform == Waveform.TRIANGLE:
            return amplitude * (2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1)
        elif waveform == Waveform.NOISE:
            return amplitude * (np.random.uniform(-1, 1, size=len(t)))
            
        return np.zeros_like(t)

    def apply_envelope(self, audio, attack=0.01, decay=0.1, sustain=0.7, release=0.2, duration=1.0):
        """Standard ADSR Envelope"""
        total_samples = len(audio)
        attack_samples = int(attack * self.fs)
        decay_samples = int(decay * self.fs)
        release_samples = int(release * self.fs)
        
        # Ensure envelope fits within duration
        sustain_samples = total_samples - (attack_samples + decay_samples + release_samples)
        if sustain_samples < 0:
            # Scale down proportionally if too short
            scale = total_samples / (attack_samples + decay_samples + release_samples)
            attack_samples = int(attack_samples * scale)
            decay_samples = int(decay_samples * scale)
            release_samples = int(release_samples * scale)
            sustain_samples = 0
            
        envelope = np.zeros(total_samples)
        
        # Attack
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Decay
        envelope[attack_samples:attack_samples+decay_samples] = \
            np.linspace(1, sustain, decay_samples)
            
        # Sustain
        if sustain_samples > 0:
            envelope[attack_samples+decay_samples : -release_samples] = sustain
            
        # Release
        envelope[-release_samples:] = np.linspace(sustain, 0, release_samples)
        
        return audio * envelope
        
    def low_pass_filter(self, audio, cutoff_freq):
        """Simple RC Low Pass Filter implementation"""
        dt = 1/self.fs
        rc = 1 / (2 * np.pi * cutoff_freq)
        alpha = dt / (rc + dt)
        
        filtered = np.zeros_like(audio)
        filtered[0] = audio[0]
        for i in range(1, len(audio)):
            filtered[i] = filtered[i-1] + (alpha * (audio[i] - filtered[i-1]))
            
        return filtered

    def piano_note(self, freq, duration, velocity=0.7):
        """Synthesize a piano-like note using multi-harmonic additive synthesis.
        
        Models hammered strings with percussive attack and frequency-dependent decay.
        Uses detuned pairs for the natural chorus of piano strings.
        """
        n_samples = int(self.fs * duration)
        if n_samples < 2:
            return np.zeros(2)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        
        # Piano harmonics with decreasing amplitude and faster decay for highs
        signal = np.zeros(n_samples)
        harmonics = [
            (1.0,   1.000, 0.60),  # fundamental
            (2.0,   0.500, 0.45),  # 2nd harmonic
            (3.0,   0.250, 0.35),  # 3rd
            (4.0,   0.150, 0.25),  # 4th
            (5.0,   0.080, 0.20),  # 5th
            (6.0,   0.040, 0.15),  # 6th
        ]
        
        for mult, amp, decay_rate in harmonics:
            h_freq = freq * mult
            if h_freq > 10000:  # Don't generate inaudible harmonics
                continue
            # Each harmonic has exponential decay (higher harmonics die faster)
            envelope = np.exp(-decay_rate * t / duration * 5)
            signal += amp * np.sin(2 * np.pi * h_freq * t) * envelope
        
        # Detuned pair for chorus effect (real pianos have 2-3 strings per note)
        for mult, amp, decay_rate in harmonics[:3]:  # Only first 3

            h_freq = freq * mult * 1.001  # Slight detune
            envelope = np.exp(-decay_rate * t / duration * 5)
            signal += amp * 0.3 * np.sin(2 * np.pi * h_freq * t) * envelope
        
        # Percussive attack: sharp transient
        attack_samples = min(int(0.008 * self.fs), n_samples)
        attack_env = np.ones(n_samples)
        attack_env[:attack_samples] = np.linspace(0, 1, attack_samples)
        signal = signal * attack_env
        
        # Normalize
        peak = np.max(np.abs(signal))
        if peak > 0:
            signal = signal / peak
        
        return signal * velocity

