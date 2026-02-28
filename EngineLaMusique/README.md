# Ultimate Dynamic Music Engine

A procedural, generative music engine built in Python. It simulates a band (Drums, Bass, Rhythm Guitar, Lead Guitar, Keys/Pad) with real-time control over intensity, key, and arrangement sections.

## Features

- **Generative Music Theory**: Automatic chord progressions and scale mapping.
- **Synthesized Instruments**:
  - **Guitar**: Karplus-Strong string synthesis with strumming and distortion.
  - **Drums**: Procedurally synthesized kick, snare, hi-hats.
  - **Synth**: Subtracting synthesis for bass, pads, and arps.
- **Effects**: Distortion, Delay, Reverb (simulated), Filters.
- **Smart Conductor**: Manages tension, intensity, and layer activation.

## How to Run

1. Ensure you have `numpy`, `scipy`, and `pyaudio` installed.
   ```bash
   pip install numpy scipy pyaudio
   ```
2. Run the engine from the project root:
   ```bash
   python -m UltimateEngine.main
   ```

## Controls

The engine accepts commands in the terminal while running:

- `intensity <0-100>`: Sets the performance intensity. Higher = more instruments, louder, more distortion.
- `bpm <value>`: Sets the tempo.
- `key <Note> [maj/min]`: Changes the key (e.g., `key G# min`, `key A maj`).
- `section <name>`: Instantly switches to a preset section:
  - `intro`: Soft, ambient.
  - `verse`: Groovy, moderate.
  - `chorus`: Full band, harmonized leads.
  - `build`: Rising tension, noise sweeps.
  - `break`: Minimal, atmospheric.
- `layer <name> <on/off>`: Toggle specific instruments (`kick`, `snare`, `bass`, `rhythm`, `lead`, `harmony`, `pad`, `arp`, `riser`).
- `quit`: Stop the engine.

## Architecture

- **Conductor**: The brain. Decides chords and manages global state.
- **AudioEngine**: The heart. Renders audio beat-by-beat, mixing instruments.
- **Instruments**: Pure Python DSP implementations.
