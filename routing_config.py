"""
routing_config.py — Reads/writes the per-module ChucK routing .cfg files.

Format: one "param : landmark" per line. This is the Python side of the routing
system; it must stay in sync with chuck-scripts/core/osc-router.ck (parser +
defaults) and landmarks.ck (the set of valid landmark names).
"""

import json
import os

CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "chuck-scripts", "config"
)

# GUI-only state (control mode + slider position per param), persisted across
# sessions. The landmark choice is NOT here — that lives in the .cfg files which
# ChucK reads at startup. ChucK learns mode/slider live over OSC, so this file is
# purely so the GUI comes back the way the user left it.
STATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "routing_state.json"
)

DEFAULT_MODE = "slider"   # params start on the slider until the user ticks landmark
DEFAULT_SLIDER = 0.5      # neutral, matches the seeded landmark center

# Params each module exposes, with the default landmark used when an entry is
# missing. Must match the fallbacks in osc-router.ck.
MODULE_PARAMS = {
    "theremin": [("pitch", "hand_right_index_y"), ("volume", "hand_left_index_y")],
    "synth":    [("pitch", "hand_right_index_y"), ("cutoff", "hand_left_index_y")],
}

# All selectable landmarks — must match the table in landmarks.ck.
SIDES = ["right", "left"]
FINGERS = ["thumb", "index", "middle", "ring", "pinky"]
AXES = ["x", "y", "z"]
LANDMARKS = [f"hand_{s}_{f}_{a}" for s in SIDES for f in FINGERS for a in AXES]


def config_path(module):
    return os.path.join(CONFIG_DIR, f"{module}.cfg")


def load_routing(module):
    """Return {param: landmark}, falling back to defaults for missing entries."""
    routing = {param: default for param, default in MODULE_PARAMS[module]}
    path = config_path(module)
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if ":" not in line:
                    continue  # blank/comment/garbage line
                key, _, val = line.partition(":")
                key, val = key.strip(), val.strip()
                if key in routing and val:
                    routing[key] = val
    return routing


def save_routing(module, routing):
    """Write {param: landmark} to the module's .cfg, colon-aligned like the
    hand-edited files (e.g. 'pitch  : right_index_y')."""
    params = [param for param, _ in MODULE_PARAMS[module]]
    width = max(len(p) for p in params)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(config_path(module), "w") as f:
        for param in params:
            f.write(f"{param.ljust(width)} : {routing[param]}\n")


def load_state():
    """Return {module: {param: {"mode", "slider"}}}, filling defaults for any
    missing/invalid entry so the GUI always gets a complete, well-typed dict."""
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
        for param, _default in params:
            saved = data.get(module, {}).get(param, {})
            mode = saved.get("mode", DEFAULT_MODE)
            if mode not in ("slider", "landmark"):
                mode = DEFAULT_MODE
            try:
                slider = float(saved.get("slider", DEFAULT_SLIDER))
            except (TypeError, ValueError):
                slider = DEFAULT_SLIDER
            state[module][param] = {"mode": mode, "slider": slider}
    return state


def save_state(state):
    """Persist {module: {param: {"mode", "slider"}}} to routing_state.json."""
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
