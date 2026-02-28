import numpy as np
import pyaudio
import threading
import queue


class ContinuousOrchestra:
    def __init__(self):
        self.intensity = 30
        self.fs = 44100
        self.running = True
        self.buffer_queue = queue.Queue(maxsize=3)  # The "pre-calculated" shelf
        # Grandeur Progression: Cm -> Ab -> Fm -> G (Baroque/Epic)
        self.prog = [[130.81, 155.56, 196.00], [103.83, 130.81, 155.56],
                     [87.31, 103.83, 130.81], [98.00, 123.47, 146.83]]


conductor = ContinuousOrchestra()


def generate_voice(f, dur, intensity):
    t = np.linspace(0, dur, int(44100 * dur), endpoint=False)
    # Ethereal Chorus: Each "track" is a cluster of 5 detuned sines
    sig = np.zeros_like(t)
    num_singers = 1 + int(intensity / 10)
    for i in range(num_singers):
        detune = 1.0 + (i * 0.001)
        # Formant math: adding a second harmonic gives a "Vocal" quality
        sig += np.sin(2 * np.pi * f * detune * t)
        sig += 0.4 * np.sin(2 * np.pi * f * 2.001 * detune * t)

    # Smooth Attack/Release
    env = np.sin(np.pi * np.arange(len(t)) / len(t))
    return (sig / np.sqrt(num_singers)) * env


def producer_thread():
    """Calculates the music AHEAD of time so there are no pauses."""
    bar = 0
    last_intensity = conductor.intensity  # Track the last intensity value
    while conductor.running:
        # Check if intensity has changed
        if conductor.intensity != last_intensity:
            # Clear the queue except for 1 extra section
            while not conductor.buffer_queue.empty():
                try:
                    conductor.buffer_queue.get_nowait()
                except queue.Empty:
                    break
            last_intensity = conductor.intensity  # Update the last intensity value

        inte = conductor.intensity
        chord = conductor.prog[bar % 4]
        bar_dur = 2.0
        samples = np.zeros(int(44100 * bar_dur))

        # LAYER 1
        for freq in chord:
            samples += generate_voice(freq, bar_dur, inte) * 0.05
            samples += generate_voice(freq / 2, bar_dur, inte * 0.5) * 0.05

        # LAYER 2
        if inte > 50:
            sub_n = 8 if inte < 80 else 16
            sub_dur = bar_dur / sub_n
            for n in range(sub_n):
                start = int(n * 44100 * sub_dur)

                note = chord[n % 3] * (2 if n % 4 == 0 else 1.5)

                t_sub = np.linspace(0, sub_dur, int(44100 * sub_dur), endpoint=False)
                mod = np.sin(2 * np.pi * note * t_sub) * (inte / 40)
                lead = np.sin(2 * np.pi * note * t_sub + mod) * np.exp(-5 * t_sub / sub_dur)
                samples[start:start + len(lead)] += lead * (inte / 300)

        # Saturation
        samples = np.tanh(samples * (0.6 + inte / 100))

        # Queue
        if conductor.buffer_queue.qsize() < 2:  # Keep only 1 extra section
            conductor.buffer_queue.put(samples.astype(np.float32).tobytes())
        bar += 1


def consumer_thread():
    """Plays the pre-calculated music without interruption."""
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True)

    while conductor.running:
        try:
            data = conductor.buffer_queue.get(timeout=1)
            stream.write(data)
        except queue.Empty:
            continue

    stream.close()
    p.terminate()


threading.Thread(target=producer_thread, daemon=True).start()
threading.Thread(target=consumer_thread, daemon=True).start()

while True:
    try:
        val = input("Intensity: ")
        conductor.intensity = int(val)
    except:
        break