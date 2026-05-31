"""
routing_config.py — Reads/writes the GUI's routing state.

Python owns all routing now: per param it holds the control mode (slider vs
landmark), the slider position, and the chosen landmark, and sends a single
resolved value to ChucK each frame over OSC. ChucK does no routing, so there are
no .cfg files to keep in sync — this module just persists the GUI state so the
app comes back the way the user left it.
"""

import json
import os

# Per-param routing state (mode + slider position + chosen landmark), persisted
# across sessions so the GUI restores exactly as the user left it.
STATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "routing_state.json"
)

DEFAULT_MODE = "slider"   # params start on the slider until the user ticks landmark
DEFAULT_SLIDER = 0.5      # neutral, matches the seeded landmark center
DEFAULT_EXP = False       # Exp curve is a feel knob, applied in Python to the
                          # final 0..1; off by default (linear)
DEFAULT_INVERT = True     # default landmarks are all _y (top-down in MediaPipe),
                          # so up=more needs the flip — on by default to match it
# Working range, measured on the invert-corrected signal: lo = the corrected
# value mapped to the param MINIMUM, hi = the value mapped to MAXIMUM (Set Min/
# Max are therefore always semantic). Full span by default (no calibration).
# Because captures live in the invert-corrected space, the range resets whenever
# invert is toggled.
DEFAULT_LO = 0.0
DEFAULT_HI = 1.0

# Params each module exposes, with the landmark each one defaults to.
MODULE_PARAMS = {
    "theremin": [("pitch", "hand_right_index_y"), ("volume", "hand_left_index_y")],
    "synth":    [("pitch", "hand_right_index_y"), ("cutoff", "hand_left_index_y")],
}

# All selectable landmarks — must match the table in landmarks.ck.
SIDES = ["right", "left"]
FINGERS = ["thumb", "index", "middle", "ring", "pinky"]
AXES = ["x", "y", "z"]
LANDMARKS = [f"hand_{s}_{f}_{a}" for s in SIDES for f in FINGERS for a in AXES]


def load_state():
    """Return {module: {param: {"mode", "slider", "landmark", "invert", "exp", "lo",
    "hi"}}}, filling defaults for any missing/invalid entry so the GUI always
    gets a complete, well-typed dict."""
    data = {}
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH) as f:
                data = json.load(f)
        except (ValueError, OSError):
            data = {}  # corrupt/unreadable -> fall back to defaults

    state = {}
    for module, params in MODULE_PARAMS.items():
        state[module] = {}
        for param, default_landmark in params:
            saved = data.get(module, {}).get(param, {})
            mode = saved.get("mode", DEFAULT_MODE)
            if mode not in ("slider", "landmark"):
                mode = DEFAULT_MODE
            try:
                slider = float(saved.get("slider", DEFAULT_SLIDER))
            except (TypeError, ValueError):
                slider = DEFAULT_SLIDER
            landmark = saved.get("landmark", default_landmark)
            if landmark not in LANDMARKS:
                landmark = default_landmark
            invert = bool(saved.get("invert", DEFAULT_INVERT))
            exp = bool(saved.get("exp", DEFAULT_EXP))
            try:
                lo = float(saved.get("lo", DEFAULT_LO))
            except (TypeError, ValueError):
                lo = DEFAULT_LO
            try:
                hi = float(saved.get("hi", DEFAULT_HI))
            except (TypeError, ValueError):
                hi = DEFAULT_HI
            state[module][param] = {
                "mode": mode, "slider": slider,
                "landmark": landmark, "invert": invert,
                "exp": exp, "lo": lo, "hi": hi,
            }
    return state


def save_state(state):
    """Persist {module: {param: {"mode", "slider", "landmark", "invert", "exp",
    "lo", "hi"}}}."""
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
