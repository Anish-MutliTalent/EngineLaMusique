"""Quick test to see if the Guitar class produces audible output."""
import numpy as np
import pyaudio
import sys
sys.path.insert(0, r'd:\Python_Files\PycharmProjects\DynamicMusic')

from EngineLaMusique.instruments.guitar import Guitar

g = Guitar(44100)

# Test 1: Raw Karplus-Strong
print("=== Test 1: Raw Karplus-Strong at 440Hz ===")
raw = g.karplus_strong(440, 1.0)
print(f"  Length: {len(raw)}")
print(f"  Max: {np.max(np.abs(raw)):.6f}")
print(f"  Mean: {np.mean(np.abs(raw)):.6f}")
print(f"  Non-zero samples: {np.count_nonzero(raw)}")

# Test 2: play_note clean
print("\n=== Test 2: play_note(440, 1.0, style='clean') ===")
clean = g.play_note(440, 1.0, style='clean')
print(f"  Length: {len(clean)}")
print(f"  Max: {np.max(np.abs(clean)):.6f}")
print(f"  Mean: {np.mean(np.abs(clean)):.6f}")

# Test 3: play_note distorted
print("\n=== Test 3: play_note(440, 1.0, style='distorted') ===")
dist = g.play_note(440, 1.0, style='distorted')
print(f"  Length: {len(dist)}")
print(f"  Max: {np.max(np.abs(dist)):.6f}")
print(f"  Mean: {np.mean(np.abs(dist)):.6f}")

# Test 4: Play it through speakers
print("\n=== Playing raw KS tone (1 second) ===")
# Normalize to safe volume
if np.max(np.abs(raw)) > 0:
    audio = raw / np.max(np.abs(raw)) * 0.5
else:
    audio = raw
    print("WARNING: raw signal is completely silent!")

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paFloat32, channels=1, rate=44100, output=True)
stream.write(audio.astype(np.float32).tobytes())

print("=== Playing distorted note (1 second) ===")
if np.max(np.abs(dist)) > 0:
    audio2 = dist / np.max(np.abs(dist)) * 0.5
else:
    audio2 = dist
    print("WARNING: distorted signal is completely silent!")
stream.write(audio2.astype(np.float32).tobytes())

stream.stop_stream()
stream.close()
p.terminate()
print("\nDone.")
