# Virtual Conductor

Real-time face, hand, and pose tracking that sends MIDI and OSC messages — designed for controlling music and sound with body movement.

## How it works

A webcam feed is processed by **MediaPipe** (v0.10.32) to detect face landmarks, hand landmarks, and body pose in real time. Tracking data is sent out as:

- **MIDI** — Hand position mapped to configurable CC messages
- **OSC** — Fingertip coordinates sent as `/left-hand/{finger}` and `/right-hand/{finger}` vectors

The GUI (built with **Dear ImGui**) shows the camera feed with landmark overlays and provides controls for toggling trackers and assigning MIDI CCs.

## Requirements

- Python 3.12
- Webcam

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

MediaPipe model files (`face_landmarker.task`, `hand_landmarker.task`, `pose_landmarker.task`) must be placed in the `models/` directory.

## Run

```bash
python virtual-conductor.py
```

Or use the launcher script:

```bash
./run_virtual_conductor.sh
```

## Project structure

```
virtual-conductor.py   — Entry point and main loop
tracker.py             — MediaPipe tracking + MIDI/OSC output
gui.py                 — Dear ImGui interface
midi_controller.py     — MIDI output controller
osc_controller.py      — OSC output controller
models/                — MediaPipe model files
```
