"""Smoke test: render 8 beats for each style and check output levels."""
import sys
sys.path.insert(0, r'd:\Python_Files\PycharmProjects\DynamicMusic')
import numpy as np
from EngineLaMusique.conductor import Conductor
from EngineLaMusique.audio_engine import AudioEngine

c = Conductor()
e = AudioEngine(c)

for style in ['rock', 'pop', 'edm', 'classical']:
    c.apply_style(style)
    c.intensity = 0.8
    e.beat_count = 0
    
    print(f"\n=== Style: {style.upper()} ===")
    total_energy = 0
    for beat in range(8):
        buf = e.render_next_beat()
        peak = np.max(np.abs(buf))
        rms = np.sqrt(np.mean(buf**2))
        total_energy += rms
        if beat < 2:
            print(f"  Beat {beat}: peak={peak:.4f}  rms={rms:.4f}  len={len(buf)}")
    avg_rms = total_energy / 8
    print(f"  Average RMS over 8 beats: {avg_rms:.4f}")
    if avg_rms < 0.01:
        print(f"  WARNING: {style} sounds nearly silent!")
    else:
        print(f"  OK - audible output confirmed")

print("\nDone.")
