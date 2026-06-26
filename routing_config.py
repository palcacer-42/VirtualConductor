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

# All persisted runtime state lives in one config/ folder beside this module, so
# the project root stays clean as settings files accumulate.
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")


def _ensure_config_dir():
    """Create config/ on demand so the first save works on a fresh checkout."""
    os.makedirs(CONFIG_DIR, exist_ok=True)


# Per-param routing state (mode + slider position + chosen landmark), persisted
# across sessions so the GUI restores exactly as the user left it.
STATE_PATH = os.path.join(CONFIG_DIR, "routing_state.json")

# The input source ("fake-theorbo" or "mic") is a single setting, not a per-param
# value, so it persists in its own small file.
INPUT_SOURCE_PATH = os.path.join(CONFIG_DIR, "input_source.json")
INPUT_SOURCES = ["fake-theorbo", "mic"]
DEFAULT_INPUT_SOURCE = "fake-theorbo"

# All MIDI settings live together in one small file: the selected input device
# ("None" = listen to nothing) and the burst-trigger's learned control.
MIDI_CONFIG_PATH = os.path.join(CONFIG_DIR, "midi_config.json")
DEFAULT_MIDI_PORT = "None"

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
    # Input: the shared input source (always running). One param = the dry input
    # monitor volume; the source choice (fake-theorbo vs mic) persists separately.
    "input":    [("volume", "hand_left_index_y")],
    # Granulator: every param exposed. The landmark is only the default used if
    # the user switches that param to landmark mode — all start on the slider.
    "granulator": [
        # grain
        ("grainsize",  "hand_right_index_y"),
        ("density",    "hand_left_index_y"),
        ("position",   "hand_right_thumb_y"),
        ("posspray",   "hand_left_thumb_y"),
        ("panspray",   "hand_right_middle_y"),
        # pitch
        ("octaveup",   "hand_right_ring_y"),
        ("octavedown", "hand_left_ring_y"),
        ("pitchrange", "hand_right_pinky_y"),
        ("pitchprob",  "hand_left_pinky_y"),
        ("finerange",  "hand_right_middle_x"),
        ("fineprob",   "hand_left_middle_x"),
        # limiter
        ("thresh",     "hand_right_thumb_x"),
        ("attack",     "hand_left_thumb_x"),
        ("release",    "hand_right_index_x"),
        # delay
        ("delayleft",  "hand_left_index_x"),
        ("delayright", "hand_right_ring_x"),
        ("feedback",   "hand_left_ring_x"),
        ("delaymix",   "hand_right_pinky_x"),
        # reverb
        ("reverbmix",  "hand_left_pinky_x"),
        # output
        ("mastervol",  "hand_right_pinky_z"),
    ],
    # Aliased-shimmer: a looper with one routable param — the loop's output
    # volume. Collect/Clear are buttons (rendered separately), not params.
    "aliased-shimmer": [("mastervol", "hand_right_pinky_z")],
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
    _ensure_config_dir()
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def load_input_source():
    """Return the persisted input source ("fake-theorbo" or "mic"), defaulting to
    fake-theorbo if unset or invalid."""
    if os.path.exists(INPUT_SOURCE_PATH):
        try:
            with open(INPUT_SOURCE_PATH) as f:
                source = json.load(f).get("source")
            if source in INPUT_SOURCES:
                return source
        except (ValueError, OSError):
            pass
    return DEFAULT_INPUT_SOURCE


def save_input_source(source):
    """Persist the input source selection ("fake-theorbo" or "mic")."""
    _ensure_config_dir()
    with open(INPUT_SOURCE_PATH, "w") as f:
        json.dump({"source": source}, f, indent=2)


def _read_midi_config():
    """Whole midi_config.json as a dict (empty if missing/corrupt)."""
    if os.path.exists(MIDI_CONFIG_PATH):
        try:
            with open(MIDI_CONFIG_PATH) as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except (ValueError, OSError):
            pass
    return {}


def _write_midi_config(data):
    _ensure_config_dir()
    with open(MIDI_CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_midi_port():
    """Return the persisted MIDI input port name, or "None" if unset/invalid.
    The name isn't validated against connected devices here — the GUI checks it
    against the live port list before reopening (a saved device may be unplugged)."""
    port = _read_midi_config().get("port")
    return port if isinstance(port, str) else DEFAULT_MIDI_PORT


def save_midi_port(port):
    """Persist the selected MIDI input port name ("None" = listen to nothing),
    leaving the other MIDI settings in the file untouched."""
    data = _read_midi_config()
    data["port"] = port
    _write_midi_config(data)


def load_burst_binding():
    """Return the persisted burst-trigger MIDI binding as
    {"type": "note_on", "note": n} or {"type": "control_change", "control": n},
    or None if unset/invalid."""
    b = _read_midi_config().get("burst_binding")
    if isinstance(b, dict):
        if b.get("type") == "note_on" and isinstance(b.get("note"), int):
            return {"type": "note_on", "note": b["note"]}
        if b.get("type") == "control_change" and isinstance(b.get("control"), int):
            return {"type": "control_change", "control": b["control"]}
    return None


def save_burst_binding(binding):
    """Persist the burst-trigger MIDI binding (a dict), or None to clear it,
    leaving the other MIDI settings in the file untouched."""
    data = _read_midi_config()
    data["burst_binding"] = binding
    _write_midi_config(data)


def load_collect_binding():
    """Return the persisted aliased-shimmer "collect" gate MIDI binding as
    {"type": "note_on", "note": n} or {"type": "control_change", "control": n},
    or None if unset/invalid. The learned control gates the effect: note-on /
    cc>0 opens it, note-off / cc 0 closes it."""
    b = _read_midi_config().get("collect_binding")
    if isinstance(b, dict):
        if b.get("type") == "note_on" and isinstance(b.get("note"), int):
            return {"type": "note_on", "note": b["note"]}
        if b.get("type") == "control_change" and isinstance(b.get("control"), int):
            return {"type": "control_change", "control": b["control"]}
    return None


def save_collect_binding(binding):
    """Persist the "collect" gate MIDI binding (a dict), or None to clear it,
    leaving the other MIDI settings in the file untouched."""
    data = _read_midi_config()
    data["collect_binding"] = binding
    _write_midi_config(data)


def load_clear_binding():
    """Return the persisted aliased-shimmer "clear" trigger MIDI binding as
    {"type": "note_on", "note": n} or {"type": "control_change", "control": n},
    or None if unset/invalid. The learned control fires the clear on its onset,
    like the burst trigger."""
    b = _read_midi_config().get("clear_binding")
    if isinstance(b, dict):
        if b.get("type") == "note_on" and isinstance(b.get("note"), int):
            return {"type": "note_on", "note": b["note"]}
        if b.get("type") == "control_change" and isinstance(b.get("control"), int):
            return {"type": "control_change", "control": b["control"]}
    return None


def save_clear_binding(binding):
    """Persist the "clear" trigger MIDI binding (a dict), or None to clear it,
    leaving the other MIDI settings in the file untouched."""
    data = _read_midi_config()
    data["clear_binding"] = binding
    _write_midi_config(data)
