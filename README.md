# Virtual Conductor

Real-time face, hand, and pose tracking that drives sound synthesis — designed
for controlling music with body movement.

## How it works

A webcam feed is processed by **MediaPipe** (v0.10.32) to detect face landmarks,
hand landmarks, and body pose in real time. A **Dear ImGui** GUI shows the camera
feed with landmark overlays and the controls for routing and synthesis.

Sound is produced by **ChucK**, which the app launches and controls. The routing
between body movement and sound lives entirely in Python:

- For each instrument parameter, the GUI holds a **mode** — either a manual
  *slider* or a tracked *landmark* (e.g. right index fingertip height).
- Each frame, Python resolves every parameter to a single normalized `0..1`
  value and sends it over **OSC** as `/param/<module>/<param>`. ChucK just plays
  that value — it does no routing of its own.
- Momentary events (e.g. a noise burst) are sent as OSC triggers like
  `/trigger/burst`, decoupled from the frame rate.

**MIDI** is currently input-only infrastructure: the Configuration panel lets you
pick a connected MIDI device and watch its incoming messages in a monitor.
Messages aren't mapped to anything yet — that hook (`MidiListener.on_message`) is
where future control of ChucK triggers / parameters will plug in.

Optional **gesture recognition** (scikit-learn) classifies right-hand poses, with
sample collection and model training available from the GUI.

## Requirements

- Python 3.12
- A webcam
- [ChucK](https://chuck.stanford.edu/) installed and on your `PATH` (for audio)

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

MediaPipe model files (`face_landmarker.task`, `hand_landmarker.task`,
`pose_landmarker.task`) must be placed in the `models/` directory.

MIDI input uses the `python-rtmidi` backend (in `requirements.txt`), which wraps
the native MIDI API on macOS, Windows, and Linux.

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
tracker.py             — MediaPipe face/hand/pose tracking
gui.py                 — Dear ImGui interface + routing logic
routing_config.py      — Persisted GUI/routing state and config
osc_controller.py      — OSC client (sends resolved /param values to ChucK)
midi_input.py          — MIDI input listener (device selection + monitor)
chuck_controller.py    — Launches and controls the ChucK VM and effects
gesture_collector.py   — Records hand-gesture training samples
gesture_recognizer.py  — Trains and predicts hand gestures
chuck-scripts/         — ChucK synthesis modules and OSC router
models/                — MediaPipe model files
```
