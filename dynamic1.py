import numpy as np
import pyaudio
import random
import threading

# --- MUSICAL PARAMETERS ---
RATE = 44100
INTENSITY = 85  # 1-100: 1=Deep Bass, 50=Ethereal Pads, 100=Bach Grandeur
CHORD_PROGRESSION = [
    [130.81, 164.81, 196.00, 246.94],  # Cmaj7
    [174.61, 220.00, 261.63, 329.63],  # Fmaj7
    [146.83, 174.61, 220.00, 293.66],  # Dm7
    [196.00, 246.94, 293.66, 392.00]  # G7
]

def get_ethereal_string(f, t, intensity):
    detune = 0.005 * (intensity / 100)
    wave = np.sin(2 * np.pi * f * t) + np.sin(2 * np.pi * f * (1 + detune) * t)
    if intensity > 40:
        wave += 0.5 * np.sin(2 * np.pi * f * 2.001 * t)
    return wave

def get_envelope(length, attack=0.2, release=0.2):
    att_samples = int(length * attack)
    rel_samples = int(length * release)
    env = np.ones(length)
    env[:att_samples] = np.linspace(0, 1, att_samples)
    env[-rel_samples:] = np.linspace(1, 0, rel_samples)
    return env

def update_intensity():
    global INTENSITY
    while True:
        try:
            new_intensity = int(input("Enter new intensity (1-100): "))
            if 1 <= new_intensity <= 100:
                INTENSITY = new_intensity
                print(f"Intensity updated to {INTENSITY}")
            else:
                print("Please enter a value between 1 and 100.")
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 100.")

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, output=True)

print(f"Synthesizing at Intensity {INTENSITY}...")
step = 0

# Start a thread to listen for intensity changes
threading.Thread(target=update_intensity, daemon=True).start()

try:
    while True:
        chord = CHORD_PROGRESSION[step % 4]
        beat_dur = 2.0
        t = np.linspace(0, beat_dur, int(RATE * beat_dur), endpoint=False)
        master_buffer = np.zeros_like(t)

        master_buffer += 0.3 * np.sin(2 * np.pi * (chord[0] / 2) * t) * get_envelope(len(t), 0.1, 0.4)

        pad_vol = 0.2 if INTENSITY > 10 else 0
        for freq in chord:
            master_buffer += pad_vol * get_ethereal_string(freq, t, INTENSITY)

        if INTENSITY > 50:
            mel_vol = (INTENSITY - 50) / 150
            sub_beat_count = 8
            samples_per_sub = len(t) // sub_beat_count
            for i in range(sub_beat_count):
                mel_note = random.choice(chord) * (2 if i % 2 == 0 else 1.5)
                start, end = i * samples_per_sub, (i + 1) * samples_per_sub
                sub_t = t[start:end] - t[start]
                master_buffer[start:end] += mel_vol * get_ethereal_string(mel_note, sub_t, INTENSITY) * get_envelope(
                    len(sub_t), 0.2, 0.2)

        if INTENSITY > 80:
            kick_env = np.exp(-10 * t[:len(t) // 2])
            master_buffer[:len(t) // 2] += 0.4 * np.sin(2 * np.pi * 60 * np.exp(-20 * t[:len(t) // 2])) * kick_env

        master_buffer = np.tanh(master_buffer * 0.8)

        stream.write(master_buffer.astype(np.float32).tobytes())
        step += 1

except KeyboardInterrupt:
    stream.stop_stream()
    p.terminate()





















































































































































































































































































































































































































































































































































    r