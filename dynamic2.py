import numpy as np
import pyaudio
import threading
import time


# --- THE CONDUCTOR'S STATE ---
class Conductor:
    def __init__(self):
        self.intensity = 30  # Start ambient
        self.running = True
        self.fs = 44100
        self.current_key = "C"

    def get_scale(self):
        # Bach-style: Low intensity = Major (Joy), High = Minor (Drama/Power)
        if self.intensity < 60:
            return [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88]  # C Major
        else:
            return [293.66, 329.63, 349.23, 392.00, 440.00, 466.16, 523.25]  # D Minor


conductor = Conductor()


def get_wave(freq, duration, type='sine'):
    t = np.linspace(0, duration, int(conductor.fs * duration), endpoint=False)
    if type == 'ethereal':
        # Double Oscillator Detune
        return np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * (freq * 1.006) * t)
    return np.sin(2 * np.pi * freq * t)


def audio_thread():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=conductor.fs, output=True)

    prev_note = 261.63

    while conductor.running:
        current_intensity = conductor.intensity
        scale = conductor.get_scale()

        # 1. TEMPO LOGIC: High intensity = Faster movement
        beat_len = 2.0 if current_intensity < 50 else 1.0
        samples = np.zeros(int(conductor.fs * beat_len))
        t = np.linspace(0, beat_len, len(samples), endpoint=False)

        # 2. THE PEDAL BASS (The Foundation)
        root = scale[0]
        bass = 0.4 * get_wave(root / 2, beat_len, 'ethereal')
        samples += bass * (1 + (current_intensity / 100))

        # 3. HARMONIC CLIMAX (The Pads)
        intervals = [0, 2, 4]  # Root, 3rd, 5th
        for i in intervals:
            samples += 0.2 * get_wave(scale[i], beat_len, 'ethereal')

            # 4. STOCHASTIC MELODY (The "Bach" Walk) - FIXED
            if current_intensity > 50:
                sub_div = 4 if current_intensity < 80 else 8
                samples_per_sub = len(samples) // sub_div  # Integer division

                for s in range(sub_div):
                    start = s * samples_per_sub
                    # Ensure the last slice catches any remaining samples
                    end = (s + 1) * samples_per_sub if s < sub_div - 1 else len(samples)
                    actual_len = end - start

                    # Harmonic Walk
                    idx = scale.index(min(scale, key=lambda x: abs(x - prev_note)))
                    idx = np.clip(idx + np.random.choice([-1, 0, 1]), 0, len(scale) - 1)
                    note = scale[idx] * (2 if current_intensity > 75 else 1)

                    # Generate wave and envelope for the EXACT length of the slice
                    mel_t = np.linspace(0, actual_len / conductor.fs, actual_len, endpoint=False)
                    mel_wave = (np.sin(2 * np.pi * note * mel_t) +
                                0.3 * np.sin(2 * np.pi * note * 1.005 * mel_t))  # Detuned pair

                    # Exponential decay envelope (the "pluck")
                    mel_env = np.exp(-5 * np.linspace(0, 1, actual_len))

                    samples[start:end] += mel_wave * mel_env * (current_intensity / 180)
                    prev_note = note

        # 5. MASTERING: Tanh Saturation for "Analog" warmth
        samples = np.tanh(samples * 0.7)
        stream.write(samples.astype(np.float32).tobytes())

    stream.stop_stream()
    p.terminate()


# Start the music
t = threading.Thread(target=audio_thread)
t.start()

print("Type a number to change intensity, or 'q' to quit.")
try:
    while True:
        val = input("Set Intensity: ")
        if val.lower() == 'q':
            conductor.running = False
            break
        try:
            conductor.intensity = int(val)
        except:
            pass
except KeyboardInterrupt:
    conductor.running = False