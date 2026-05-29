"""
routing_config.py — Reads/writes the per-module ChucK routing .cfg files.

Format: one "param : landmark" per line. This is the Python side of the routing
system; it must stay in sync with chuck-scripts/core/osc-router.ck (parser +
defaults) and landmarks.ck (the set of valid landmark names).
"""

import os

CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "chuck-scripts", "config"
)

# Params each module exposes, with the default landmark used when an entry is
# missing. Must match the fallbacks in osc-router.ck.
MODULE_PARAMS = {
    "theremin": [("pitch", "right_index_y"), ("volume", "left_index_y")],
    "synth":    [("pitch", "right_index_y"), ("cutoff", "left_index_y")],
}

# All selectable landmarks — must match the table in landmarks.ck.
SIDES = ["right", "left"]
FINGERS = ["thumb", "index", "middle", "ring", "pinky"]
AXES = ["x", "y", "z"]
LANDMARKS = [f"{s}_{f}_{a}" for s in SIDES for f in FINGERS for a in AXES]


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
