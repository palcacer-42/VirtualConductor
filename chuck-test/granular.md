# Granular Texture Effect — Implementation Notes

---

## Architecture

```
adc → [circular buffer] ← write ptr (stops on freeze)
            ↓
      grain scheduler  (Poisson process at rate λ)
       ↓      ↓      ↓
     grain  grain  grain  → mix → dac
```

Three components:
1. **Circular buffer** — continuously records live input
2. **Scheduler** — decides *when* to fire a grain (Poisson)
3. **Grain** — reads a window from the buffer, applies envelope, outputs audio

---

## Grain Scheduling — Poisson Process

Grains are fired using a **Poisson process** with rate λ (grains/sec).
The time between grain onsets follows an **exponential distribution**:

```
inter_onset_time = -ln(rand) / λ
```

- `rand` = uniform random number in (0, 1)
- `λ` = density (e.g. 20 = 20 grains/sec)

This gives organic, non-mechanical timing — exactly what cloud effects use.
Higher λ = denser cloud. Typical range: 5–100 grains/sec.

---

## Grain Envelope — Raised Cosine (Hanning)

Each grain fades in and out to avoid clicks:

```
amp[i] = 0.5 * (1 - cos(2π * i / N))
```

`i` = sample index within grain, `N` = total grain length in samples.

This is the standard window for smooth, seamless grain blending.

---

## Pitch Shifting — Variable Playback Rate

Reading the buffer at `rate != 1.0` shifts pitch.
Requires **linear interpolation** for non-integer read positions:

```
readPtr += rate
i = floor(readPtr)
frac = readPtr - i
sample = buf[i] + frac * (buf[i+1] - buf[i])
```

- `rate = 1.0` → original pitch
- `rate = 2.0` → octave up
- `rate = 0.5` → octave down

---

## Parameters

| Parameter    | Description                                                  |
|--------------|--------------------------------------------------------------|
| `grainSize`  | Length of each grain in ms (20–300ms)                        |
| `density` λ  | Average grains per second — thickness of cloud               |
| `position`   | Where in the buffer to read (0 = oldest, 1 = now)            |
| `posSpray`   | Random scatter around position — smearing, diffusion         |
| `pitchShift` | Playback rate per grain                                      |
| `pitchSpray` | Random pitch deviation per grain — shimmer/chorus            |
| `freeze`     | Stops buffer writing — holds a frozen moment as texture      |

---

## The Cloud Recipe

Three things together:
1. **High density** (many overlapping grains)
2. **High posSpray** (grains read from scattered buffer positions)
3. **Small pitchSpray** (subtle random pitch per grain)

This is what Ableton Granulator Cloud Mode and Mutable Clouds do.

---

## Grain Types (from Bencina)

- **Tapped Delay Line** — read from live input buffer (what we want)
- **Stored Sample** — read from a pre-recorded file
- **Synthetic** — oscillator-based grain (no buffer needed)

---

## Build Steps

1. Circular buffer — write live input continuously, track write pointer
2. Single grain — read N samples from buffer at position, apply Hanning, mix to output
3. Scheduler — fire grains using Poisson inter-onset time (`-ln(rand)/λ`)
4. Randomize per grain — position += posSpray * rand, rate += pitchSpray * rand
5. Freeze — flag that stops the write pointer
