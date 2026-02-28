import numpy as np
import pyaudio
import threading
import random


class OrchestralConductor:
    def __init__(self):
        self.intensity = 40
        self.fs = 44100
        self.running = True
        #progression states
        self.scales = {
            "peace": [261.63, 293.66, 329.63, 392.00, 440.00],  # Pentatonic
            "grand": [261.63, 293.66, 311.13, 349.23, 392.00, 415.30, 466.16]  # C Minor
        }


conductor = OrchestralConductor()


def get_instrument(freq, dur, intensity):
    t = np.linspace(0, dur, int(conductor.fs * dur), endpoint=False)

    # 1. THE "HUMAN" JITTER
    # Real players are never perfectly on pitch. We add a 0.1Hz micro-vibrato
    vibrato = 1 + (0.002 * np.sin(2 * np.pi * 5 * t))

    # 2. PHASE MODULATION (Realistic Timbre)
    # This simulates the "bite" of a bow. Higher intensity = more overtones.
    mod_index = (intensity / 100) * 2
    modulator = np.sin(2 * np.pi * freq * vibrato * t)
    carrier = np.sin(2 * np.pi * freq * vibrato * t + mod_index * modulator)

    # 3. DYNAMIC ENVELOPE
    # Fast attack for "Grandeur", slow for "Dreamy"
    attack = 0.05 if intensity > 70 else 0.4
    env = np.ones_like(t)
    att_size = int(len(t) * attack)
    env[:att_size] = np.linspace(0, 1, att_size)
    env[-att_size:] = np.linspace(1, 0, att_size)

    return carrier * env


def audio_thread():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=conductor.fs, output=True)

    curr_note_idx = 0

    while conductor.running:
        inte = conductor.intensity
        scale = conductor.scales["grand"] if inte > 60 else conductor.scales["peace"]

        # Improvisation Logic: Variable note lengths (Phrasing)
        # Low intensity = Long, flowing notes. High = Short, urgent notes.
        phrase_length = 4 if inte < 40 else (8 if inte < 80 else 16)
        beat_dur = 4.0 / phrase_length

        samples = np.zeros(int(conductor.fs * beat_dur))

        # MELODY LAYER: Recursive "Smart" Choice
        # Rules: Don't jump more than 3 notes in the scale; 20% chance to hold
        jump = random.choice([-2, -1, 1, 2])
        curr_note_idx = (curr_note_idx + jump) % len(scale)
        freq = scale[curr_note_idx]

        # Octave switching for "Grandeur"
        if inte > 75 and random.random() > 0.7: freq *= 2

        # Generate Note
        samples += 0.4 * get_instrument(freq, beat_dur, inte)

        # HARMONY LAYER (Pads/Strings)
        # Deep pedal notes that change only every 4 beats
        if random.random() > 0.8:
            root = scale[0] / 2
            samples += 0.3 * get_instrument(root, beat_dur, inte * 0.5)

        # FINAL POLISH
        # Soft-clipping with a touch of "Air" (Noise floor)
        samples += np.random.normal(0, 0.002, len(samples))  # Subtle analog hiss
        samples = np.tanh(samples * 1.2)

        stream.write(samples.astype(np.float32).tobytes())

    stream.stop_stream()
    p.terminate()


t = threading.Thread(target=audio_thread, daemon=True)
t.start()

try:
    while True:
        val = input("Intensity: ")
        conductor.intensity = int(val)
except:
    conductor.running = False