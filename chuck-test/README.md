# ChucK Test Programs

OSC-controlled audio experiments using hand tracking from the Virtual Conductor.

## Quick Start

```bash
# Terminal 1: Start the hand tracker
cd ~/Documents/CODE/kiko
./run_virtual_conductor.sh

# Terminal 2: Run a ChucK program
cd chuck-test
chuck theremin.ck   # or synth.ck
```

## Programs

### theremin.ck
**Two-hand theremin with smooth interpolation**
- **Right hand** → Pitch (200-800 Hz)
- **Left hand** → Volume (0-1)
- Uses exponential smoothing for natural glide

### synth.ck
**Classic subtractive synth (Saw + LPF)**
- **Right hand** → Pitch (200-800 Hz)
- **Left hand** → Filter cutoff (200-4000 Hz)
- Uses exponential mapping for perceptually-correct filter response

### osc_test.ck
**Debug tool** — prints all incoming OSC messages from the tracker.

---

## OSC Protocol

The Python tracker sends fingertip positions on **port 8000**:

| Address | Data |
|---------|------|
| `/left-hand/thumb` | `[x, y, z]` |
| `/left-hand/index` | `[x, y, z]` |
| `/left-hand/middle` | `[x, y, z]` |
| `/left-hand/ring` | `[x, y, z]` |
| `/left-hand/pinky` | `[x, y, z]` |
| `/right-hand/thumb` | `[x, y, z]` |
| `/right-hand/index` | `[x, y, z]` |
| `/right-hand/middle` | `[x, y, z]` |
| `/right-hand/ring` | `[x, y, z]` |
| `/right-hand/pinky` | `[x, y, z]` |

**Coordinate system:**
- `x`: 0.0 (left) → 1.0 (right)
- `y`: 0.0 (top) → 1.0 (bottom)
- `z`: depth (negative = closer to camera)

---

## Reusable Helper Functions

Located in `synth.ck`:

```chuck
// Linear mapping between ranges
fun float mapRange(float value, float inMin, float inMax, float outMin, float outMax)

// Clamp value to range
fun float clamp(float value, float minVal, float maxVal)

// Exponential mapping (for frequency/filter cutoff)
fun float expMap(float value, float minVal, float maxVal)

// Equal power crossfade (for mixing audio sources)
fun float equalPowerA(float mix)  // Returns gain for source A
fun float equalPowerB(float mix)  // Returns gain for source B
```

---

## Architecture

```
┌─────────────────┐    OSC (UDP:8000)    ┌─────────────┐
│  Python Tracker │ ──────────────────▶  │    ChucK    │
│  (MediaPipe)    │   /right-hand/index  │   (Audio)   │
└─────────────────┘      [x, y, z]       └─────────────┘
```
