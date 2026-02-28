import numpy as np
import pyaudio
import threading
import queue
import time


class ContinuousOrchestra:
    def __init__(self):
        self.intensity = 30
        self.fs = 44100
        self.running = True
        self.buffer_queue = queue.Queue(maxsize=3)

        # Musical DNA: Scale degrees for harmonic improvisation
        self.root_notes = [130.81, 103.83, 87.31, 98.00]  # Cm, Ab, Fm, G roots
        self.scale_intervals = [1.0, 1.122, 1.189, 1.335, 1.498, 1.682, 1.888]  # Minor scale ratios

        # Improvisation state
        self.current_root_idx = 0
        self.harmonic_tension = 0.0  # 0.0 = resolved, 1.0 = max tension
        self.phrase_position = 0
        self.last_melody_notes = []

        # Rhythm variation
        self.rhythmic_density = 0.5
        self.syncopation = 0.0

        # Timbre evolution
        self.brightness = 0.5
        self.chorus_spread = 0.002


conductor = ContinuousOrchestra()


def choose_next_chord(current_idx, tension, intensity):
    """Smart chord progression based on musical tension"""
    # Common progressions with tension values
    progressions = {
        0: [(1, 0.3), (2, 0.5), (3, 0.8)],  # Cm -> Ab(release), Fm(continue), G(tension)
        1: [(2, 0.4), (0, -0.3), (3, 0.6)],  # Ab -> Fm, Cm(resolve), G
        2: [(3, 0.7), (1, -0.2), (0, -0.4)],  # Fm -> G(tension), Ab, Cm(home)
        3: [(0, -0.5), (2, 0.2), (1, -0.1)]  # G -> Cm(resolve), Fm, Ab
    }

    options = progressions[current_idx]

    # Weight choices based on current tension and intensity
    if tension > 0.7 and np.random.rand() < 0.6:  # Seek resolution
        weights = [1.5 if t < 0 else 0.5 for _, t in options]
    elif tension < 0.3 and intensity > 60:  # Build tension
        weights = [1.5 if t > 0.4 else 0.5 for _, t in options]
    else:
        weights = [1.0 + np.random.rand() * 0.5 for _ in options]

    weights = np.array(weights) / sum(weights)
    choice_idx = np.random.choice(len(options), p=weights)
    next_chord, tension_change = options[choice_idx]

    return next_chord, max(0.0, min(1.0, tension + tension_change))


def generate_chord_voicing(root_freq, tension, intensity):
    """Creates unique chord voicings each time"""
    # Base triad with variations
    intervals = [1.0, 1.189, 1.498]  # Minor triad

    # Add tensions based on harmonic tension
    if tension > 0.5 and np.random.rand() < tension:
        intervals.append(1.888)  # Add 7th
    if tension > 0.7 and intensity > 70:
        intervals.append(2.245)  # Add 9th

    # Voice leading: sometimes invert the chord
    if np.random.rand() < 0.3:
        intervals = [i * 2 if i == min(intervals) else i for i in intervals]

    # Random octave doublings
    if intensity > 50 and np.random.rand() < 0.4:
        intervals.append(intervals[np.random.randint(len(intervals))] * 0.5)

    return [root_freq * i for i in intervals]


def improvise_melody(root_freq, scale_intervals, intensity, previous_notes):
    """Generate melodic phrases that evolve naturally"""
    phrase_length = np.random.randint(4, 12) if intensity > 60 else np.random.randint(2, 6)
    melody = []

    # Start from a scale degree (prefer stepwise motion from previous phrase)
    if previous_notes:
        last_interval = previous_notes[-1]
        # Find closest scale degree
        current_degree = min(range(len(scale_intervals)),
                             key=lambda i: abs(scale_intervals[i] - last_interval))
    else:
        current_degree = 0  # Start on root

    for _ in range(phrase_length):
        # Melodic motion: mostly stepwise, occasional leaps
        if np.random.rand() < 0.7:  # Stepwise
            step = np.random.choice([-1, 1, 2, -2], p=[0.3, 0.3, 0.2, 0.2])
            current_degree = (current_degree + step) % len(scale_intervals)
        else:  # Leap
            current_degree = np.random.randint(0, len(scale_intervals))

        # Octave selection based on intensity
        octave = 1.0
        if intensity > 70:
            octave = np.random.choice([1.0, 2.0, 0.5], p=[0.5, 0.3, 0.2])

        melody.append(scale_intervals[current_degree] * octave)

    return melody


def generate_voice(f, dur, intensity, brightness, chorus_spread):
    """Enhanced voice generation with timbral variation"""
    t = np.linspace(0, dur, int(44100 * dur), endpoint=False)
    sig = np.zeros_like(t)

    num_singers = 1 + int(intensity / 10)

    for i in range(num_singers):
        detune = 1.0 + (i * chorus_spread)

        # Fundamental
        sig += np.sin(2 * np.pi * f * detune * t)

        # Harmonics (vary with brightness)
        sig += (0.4 * brightness) * np.sin(2 * np.pi * f * 2.001 * detune * t)
        if brightness > 0.6:
            sig += (0.2 * (brightness - 0.6)) * np.sin(2 * np.pi * f * 3.002 * detune * t)

    # Dynamic envelope based on duration
    attack = min(0.1, dur * 0.2)
    release = min(0.15, dur * 0.3)
    attack_samples = int(len(t) * attack / dur)
    release_samples = int(len(t) * release / dur)

    env = np.ones_like(t)
    env[:attack_samples] = np.linspace(0, 1, attack_samples)
    env[-release_samples:] = np.linspace(1, 0, release_samples)

    return (sig / np.sqrt(num_singers)) * env


def producer_thread():
    """Generates continuously evolving music"""
    while conductor.running:
        inte = conductor.intensity

        # Choose next chord in progression
        conductor.current_root_idx, conductor.harmonic_tension = choose_next_chord(
            conductor.current_root_idx,
            conductor.harmonic_tension,
            inte
        )

        root = conductor.root_notes[conductor.current_root_idx]

        # Evolve timbre parameters
        conductor.brightness = 0.3 + (inte / 150) + np.random.rand() * 0.2
        conductor.chorus_spread = 0.001 + (inte / 20000) + np.random.rand() * 0.002

        # Variable bar duration for organic feel
        bar_dur = 2.0 + np.random.rand() * 0.4 - 0.2
        samples = np.zeros(int(44100 * bar_dur))

        # LAYER 1: Harmonic foundation with unique voicing
        chord = generate_chord_voicing(root, conductor.harmonic_tension, inte)

        for freq in chord:
            samples += generate_voice(freq, bar_dur, inte,
                                      conductor.brightness * 0.7,
                                      conductor.chorus_spread) * 0.04
            # Bass reinforcement
            if freq == min(chord):
                samples += generate_voice(freq / 2, bar_dur, inte * 0.6,
                                          0.3, conductor.chorus_spread * 0.5) * 0.06

        # LAYER 2: Improvised melodic line
        if inte > 40:
            melody = improvise_melody(root, conductor.scale_intervals,
                                      inte, conductor.last_melody_notes)
            conductor.last_melody_notes = melody[-3:]  # Remember for continuity

            # Rhythmic variation
            note_density = 6 if inte < 60 else (12 if inte < 80 else 20)
            note_dur = bar_dur / note_density

            for n, interval in enumerate(melody[:note_density]):
                # Syncopation: randomly delay some notes
                offset = 0
                if np.random.rand() < 0.2:
                    offset = int(44100 * note_dur * 0.1)

                start = int(n * 44100 * note_dur) + offset
                if start >= len(samples):
                    break

                note_freq = root * interval

                # FM synthesis for lead (varies by intensity)
                t_sub = np.linspace(0, note_dur, int(44100 * note_dur), endpoint=False)
                mod_depth = inte / 50 + np.random.rand() * 2
                mod = np.sin(2 * np.pi * note_freq * t_sub) * mod_depth

                lead = np.sin(2 * np.pi * note_freq * t_sub + mod)
                lead *= np.exp(-4 * t_sub / note_dur)  # Pluck envelope

                end = min(start + len(lead), len(samples))
                samples[start:end] += lead[:end - start] * (inte / 400)

        # LAYER 3: Atmospheric pad (occasionally)
        if inte > 60 and np.random.rand() < 0.3:
            pad_freq = root * np.random.choice([0.5, 1.0, 1.5])
            pad = generate_voice(pad_freq, bar_dur, inte * 0.8,
                                 0.8, conductor.chorus_spread * 3)
            samples += pad * 0.03

        # Dynamic saturation based on intensity
        saturation_amt = 0.5 + (inte / 150)
        samples = np.tanh(samples * saturation_amt)

        # Normalize with slight variation
        peak = np.max(np.abs(samples))
        if peak > 0:
            target_level = 0.6 + np.random.rand() * 0.1
            samples = samples * (target_level / peak)

        conductor.buffer_queue.put(samples.astype(np.float32).tobytes())
        conductor.phrase_position += 1


def consumer_thread():
    """Plays the pre-calculated music without interruption"""
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


# Start both threads
threading.Thread(target=producer_thread, daemon=True).start()
threading.Thread(target=consumer_thread, daemon=True).start()

print("🎼 Continuous Improvising Orchestra")
print("Controls:")
print("  - Enter intensity (0-100)")
print("  - Press Ctrl+C to exit")
print()

while True:
    try:
        val = input("Intensity: ")
        conductor.intensity = max(0, min(100, int(val)))
        print(f"→ Set to {conductor.intensity} (Tension: {conductor.harmonic_tension:.2f})")
    except KeyboardInterrupt:
        print("\n🎭 Ending performance...")
        conductor.running = False
        break
    except:
        print("⚠ Please enter a number (0-100)")