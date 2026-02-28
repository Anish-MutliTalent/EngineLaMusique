import numpy as np

class DrumMachine:
    def __init__(self, sample_rate=44100):
        self.fs = sample_rate
        
    def kick(self, duration=0.3):
        t = np.linspace(0, duration, int(self.fs * duration), endpoint=False)
        # Pitch envelope: 150 -> 50 Hz
        freq = 150 * np.exp(-15 * t) + 50
        # Phase accumulator
        phase = np.cumsum(freq) / self.fs
        # Sine wave
        sig = np.sin(2 * np.pi * phase)
        # Amp envelope
        env = np.exp(-10 * t)
        
        # Click transient
        click = np.random.uniform(-1, 1, int(0.01 * self.fs))
        sig[:len(click)] += click * 0.5
        
        return sig * env
        
    def snare(self, duration=0.2):
        t = np.linspace(0, duration, int(self.fs * duration), endpoint=False)
        # Tonal component
        tone = np.sin(2 * np.pi * 180 * t) * np.exp(-15 * t)
        # Noise component (wires)
        noise_raw = np.random.uniform(-1, 1, len(t))
        # LPF the noise slightly
        noise_filtered = np.convolve(noise_raw, np.ones(5)/5.0, mode='same')
        noise = noise_filtered * np.exp(-20 * t)
        
        # Mix
        return (tone * 0.5 + noise * 0.8) * 0.8
        
    def hihat(self, duration=0.08, open=False):
        if open:
            duration = 0.3
            decay = 15
        else:
            decay = 80 # Very short
            
        t = np.linspace(0, duration, int(self.fs * duration), endpoint=False)
        noise = np.random.uniform(-1, 1, len(t))
        
        # Simple Highpass (subtract lowpass)
        # Averaging is lowpass
        low = np.convolve(noise, np.ones(8)/8.0, mode='same')
        high = noise - low
        
        env = np.exp(-decay * t)
        return high * env * 0.6
        
    def tom(self, freq=100, duration=0.3):
        t = np.linspace(0, duration, int(self.fs * duration), endpoint=False)
        # Pitch bend down
        pitch = freq * (1 + 0.5 * np.exp(-10*t))
        phase = np.cumsum(pitch) / self.fs
        sig = np.sin(2 * np.pi * phase)
        env = np.exp(-5 * t)
        return sig * env

