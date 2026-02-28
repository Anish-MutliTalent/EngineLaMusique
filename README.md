# Engine La Musique

[![PyPI version](https://img.shields.io/pypi/v/EngineLaMusique.svg)](https://pypi.org/project/EngineLaMusique/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A **procedural, generative music engine** built entirely in Python. No samples, no WAV files. Every sound is synthesized in real-time using pure math.

Engine La Musique simulates a full band/orchestra with drums, bass, rhythm, lead, pads, and arpeggios across **4 distinct styles** driven by smart music theory and a live conductor system.

## Features

- **4 Styles**: Rock, Pop, EDM, Classicaaa - each with unique instrument voicings and arrangements
- **Generative Music Theory**: Automatic chord progressions, scale mapping, and voice leading
- **Synthesized Instruments**:
  - 🎸 Guitar — Karplus-Strong string synthesis with strumming, palm mutes, and distortion
  - 🥁 Drums — Procedurally synthesized kick, snare, hi-hats, and toms
  - 🎹 Synth — Subtractive synthesis for bass, pads, arps, and piano
- **Effects Chain**: Distortion, Delay, Reverb, Chorus - all real-time
- **Smart Conductor**: Manages tension, intensity, chord progressions, and layer activation
- **Musical Outro**: 3-phase ending with ritardando, cadential progression (IV → ii → V7 → I), and smooth fade
- **Live Control**: Change style, key, tempo, effects, and layers in real-time via CLI

---

## 📦 Installation

### From PyPI

```bash
pip install EngineLaMusique
```

### From Source

```bash
git clone https://github.com/Anish-MutliTalent/EngineLaMusique.git
cd EngineLaMusique
pip install -e .
```

### Requirements

| Package | Required? | Purpose |
|---------|-----------|---------|
| `numpy` | ✅ Yes | DSP math — waveform generation, filtering, mixing |
| `pyaudio` | ✅ Yes | Real-time audio output via PortAudio |
| `scipy` | ⚡ Optional | Better guitar cabinet simulation (Butterworth filters). Install with `pip install EngineLaMusique[full]` |

> **Note on PyAudio**: On some systems, PyAudio requires PortAudio to be installed first.
> - **Windows**: `pip install pyaudio` usually works out of the box.
> - **macOS**: `brew install portaudio && pip install pyaudio`
> - **Linux (Debian/Ubuntu)**: `sudo apt install portaudio19-dev && pip install pyaudio`

---

## Quick Start

### As a CLI

```bash
EngineLaMusique
```

Or run directly:

```bash
python -m EngineLaMusique.main
```

This opens an interactive terminal where you type `start` to begin playing and control the engine with commands.

### As a Python Library

```python
from EngineLaMusique import Conductor, AudioEngine

# Configure the conductor
conductor = Conductor()
conductor.apply_style('rock')        # rock, pop, edm, classical
conductor.set_param('key', 'A min')  # Any key + maj/min
conductor.set_param('bpm', 120)
conductor.set_param('intensity', 80) # 0-100

# Start playing
conductor.start()
engine = AudioEngine(conductor)
engine.start()  # Blocks and plays audio

# To trigger an outro (from another thread):
# conductor.trigger_outro()
```

---

## 🎛️ CLI Commands

Once the engine is running, control it in real-time:

| Command | Description | Example |
|---------|-------------|---------|
| `start` | Start the engine | `start` |
| `outro` | Trigger the 3-phase ending sequence | `outro` |
| `style <name>` | Switch style | `style classical` |
| `intensity <0-100>` | Set performance intensity | `intensity 80` |
| `bpm <value>` | Set tempo | `bpm 140` |
| `key <Note> [maj/min]` | Change musical key | `key G# min` |
| `section <name>` | Switch section: `intro`, `verse`, `chorus`, `build`, `break` | `section chorus` |
| `layer <name> <on/off>` | Toggle layers: `kick`, `snare`, `bass`, `rhythm`, `lead`, `pad`, `arp`, `harmony`, `riser` | `layer arp on` |
| `dist <0-100>` | Set distortion % | `dist 70` |
| `delay <0-100>` | Set delay mix % | `delay 40` |
| `reverb <0-100>` | Set reverb mix % | `reverb 50` |
| `chorus <0-100>` | Set chorus mix % | `chorus 30` |
| `sustain <0-100>` | Set note sustain (0=staccato, 100=legato) | `sustain 85` |
| `status` | Show current engine state | `status` |
| `quit` | Stop and exit | `quit` |

---

## 🎵 Styles

Each style configures the instrument layers, effects, and voicings differently:

| Style | Instruments | Character |
|-------|------------|-----------|
| **Rock** | Distorted lead guitar, power chord rhythm, full drums | Heavy, driving, aggressive |
| **Pop** | Clean guitar with chorus, strumming rhythm, full drums | Bright, catchy, polished |
| **EDM** | Saw/square synth leads, filter sweeps, arpeggios | Electronic, pulsing, energetic |
| **Classical** | Piano (Mozart-style), string section, woodwinds, cello | Orchestral, dynamic, expressive |

---

## 🔊 Effects

All effects are implemented as pure Python DSP — no external plugins:

| Effect | Description |
|--------|-------------|
| **Distortion** | Multi-stage tube amp simulation with cabinet IR |
| **Delay** | Analog-style multi-tap delay with filtered feedback |
| **Reverb** | Large hall reverb with early reflections, comb filters, and allpass diffusers |
| **Chorus** | 4-voice chorus with independent LFOs per voice |

---

## � The Outro System

When you type `outro`, the engine doesn't just stop — it performs a musically expressive ending:

1. **Approach** — Gentle slowdown, IV → ii chord progression, drums and rhythm layers fade out one by one
2. **Cadence** — Stronger ritardando, V7 → I perfect authentic cadence (the classic resolution), only harmonic layers remain
3. **Ring-out** — Deep deceleration, holds the tonic chord, volume fades smoothly to silence

Each style adds its own flavor during the cadence: rock gets a power chord ring with delay, classical gets a string swell, pop gets chorus shimmer, and EDM gets a filter sweep down.

---

## �🏗️ Architecture

```
EngineLaMusique/
├── main.py           # CLI interface and command parsing
├── conductor.py      # The brain — state, chords, intensity, 3-phase outro
├── audio_engine.py   # The heart — renders audio beat-by-beat, mixes layers
├── music_theory.py   # Scales, keys, chords, progression generator
├── instruments/
│   ├── guitar.py     # Karplus-Strong string synthesis
│   ├── drums.py      # Procedural drum synthesis (kick, snare, hihat, tom)
│   └── synthesizer.py # Waveform generation, ADSR envelopes, piano synthesis
└── effects/
    └── __init__.py   # Distortion, delay, reverb, chorus DSP
```

| Component | Role |
|-----------|------|
| **Conductor** | Decides chords, manages global state (intensity, style, layers), drives the outro sequence |
| **AudioEngine** | Renders audio beat-by-beat, mixing all active instrument layers per style |
| **Instruments** | Pure Python DSP — Karplus-Strong strings, additive/subtractive synthesis, procedural drums |
| **Effects** | Real-time audio effects — distortion, delay, reverb, chorus |

---

## 🤝 Contributing

Contributions are welcome! Here are some areas that could use help:

- **New styles** (jazz, funk, ambient, lo-fi...)
- **New instruments** (brass, flute, organ...)
- **WAV/MP3 export** (render to file instead of just live playback)
- **MIDI support** (input/output)
- **Performance optimizations** (Cython/Numba for the reverb comb filters)

```bash
git clone https://github.com/Anish-MutliTalent/EngineLaMusique.git
cd EngineLaMusique
pip install -e ".[full]"
python -m EngineLaMusique.main
```

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
