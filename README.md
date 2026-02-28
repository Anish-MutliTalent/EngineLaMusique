# 🎸 Engine La Musique

A **procedural, generative music engine** built entirely in Python. No samples, no WAV files — every sound is synthesized in real-time using pure DSP.

Engine La Musique simulates a full band with drums, bass, rhythm, lead, pads, and arpeggios across **4 distinct styles** — all driven by smart music theory and a live conductor system.

## ✨ Features

- **4 Styles**: Rock, Pop, EDM, Classical — each with unique instrument voicings and arrangements
- **Generative Music Theory**: Automatic chord progressions, scale mapping, and voice leading
- **Synthesized Instruments**:
  - 🎸 Guitar — Karplus-Strong string synthesis with strumming, palm mutes, and distortion
  - 🥁 Drums — Procedurally synthesized kick, snare, hi-hats, and toms
  - 🎹 Synth — Subtractive synthesis for bass, pads, arps, and piano
- **Effects Chain**: Distortion, Delay, Reverb, Chorus — all real-time
- **Smart Conductor**: Manages tension, intensity, chord progressions, and layer activation
- **Musical Outro**: 3-phase ending with ritardando, cadential progression, and smooth fade
- **Live Control**: Change style, key, tempo, effects, and layers in real-time via CLI

## 📦 Installation

```bash
pip install engine-la-musique
```

Or install from source:

```bash
git clone https://github.com/anish/engine-la-musique.git
cd engine-la-musique
pip install -e .
```

### Dependencies

- `numpy` — DSP and audio math
- `pyaudio` — Real-time audio output
- `scipy` (optional) — Better guitar cabinet simulation filters

## 🚀 Quick Start

### As a CLI

```bash
engine-la-musique
```

Or run directly:

```bash
python -m EngineLaMusique.main
```

### As a Library

```python
from EngineLaMusique import Conductor, AudioEngine

conductor = Conductor()
conductor.apply_style('classical')
conductor.set_param('key', 'D maj')
conductor.set_param('bpm', 90)
conductor.start()

engine = AudioEngine(conductor)
engine.start()  # Starts playing in a thread
```

## 🎛️ CLI Commands

Once the engine is running, control it in real-time:

| Command | Description |
|---------|-------------|
| `start` | Start the engine |
| `outro` | Trigger musical ending sequence |
| `style <name>` | Switch style: `rock`, `pop`, `edm`, `classical` |
| `intensity <0-100>` | Set performance intensity |
| `bpm <value>` | Set tempo |
| `key <Note> [maj/min]` | Change key (e.g., `key G# min`) |
| `section <name>` | Switch section: `intro`, `verse`, `chorus`, `build`, `break` |
| `layer <name> <on/off>` | Toggle layers: `kick`, `snare`, `bass`, `rhythm`, `lead`, etc. |
| `dist <0-100>` | Set distortion % |
| `delay <0-100>` | Set delay mix % |
| `reverb <0-100>` | Set reverb mix % |
| `chorus <0-100>` | Set chorus mix % |
| `sustain <0-100>` | Set note sustain (0=staccato, 100=legato) |
| `status` | Show current state |
| `quit` | Exit |

## 🏗️ Architecture

```
EngineLaMusique/
├── main.py           # CLI interface
├── conductor.py      # The brain — state, chords, intensity, outro logic
├── audio_engine.py   # The heart — renders audio beat-by-beat
├── music_theory.py   # Scales, chords, progressions
├── instruments/
│   ├── guitar.py     # Karplus-Strong synthesis
│   ├── drums.py      # Procedural drum synthesis
│   └── synthesizer.py # Waveform generation, ADSR, piano
└── effects/
    └── __init__.py   # Distortion, delay, reverb, chorus
```

- **Conductor**: Decides chords, manages global state (intensity, style, layers), drives the outro sequence
- **AudioEngine**: Renders audio beat-by-beat, mixing all active layers per style
- **Instruments**: Pure Python DSP — no external samples

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
