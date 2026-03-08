# Granular Texture Effect — Implementation Notes

---

## Architecture (current)

```
SndBuf (tiorba.wav) → Gain inputGain → dac          (dry monitor, key i)
SndBuf → Dyno limiter → LiSa2 grainBuffer → blackhole (recording into buffer)

LiSa2.chan(0) → Gain masterL → dac.left              (granular out, key v)
LiSa2.chan(1) → Gain masterR → dac.right
```

> Replace `SndBuf` with `adc` for real mic when ready.

Three components:
1. **Circular buffer** — `LiSa2` continuously records live input (4 seconds)
2. **Scheduler** — decides *when* to fire a grain (Poisson process)
3. **Grain** — reads a window from the buffer, applies envelope, pans, pitches, outputs

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

**Important:** LiSa's built-in `rampUp`/`rampDown` is **linear**, which disturbs the grain spectrum and can cause artifacts. We apply the Hanning envelope **manually** inside the grain function.

**Bug fix:** envelope step size = `grainSize / 256` — prevents staircase zipper noise. Minimum step = 0.25ms.

**Bug fix:** `voiceGain(v, 0.0)` before `play(v, 1)` — prevents attack click.

---

## Stereo Panning — Per Voice

`LiSa2` supports per-voice stereo panning via `grainBuffer.pan(voice, value)` where `0.0` = full left, `0.5` = center, `1.0` = full right.

Each grain gets a **Gaussian random pan** (sum of 3 uniforms / 3 ≈ bell curve), centered at 0.5, scaled by `panSpray`. More grains cluster near center, fewer at edges — cohesive but wide stereo image.

**Important:** stereo master volume uses two separate `Gain` UGens (masterL/masterR) connected to `dac.left`/`dac.right`. A single mono `Gain` between `LiSa2` and `dac` would collapse stereo to mono.

---

## Pitch Shifting — Variable Playback Rate

Reading the buffer at `rate != 1.0` shifts pitch. Rate is exponential — semitones to rate:

```
rate = 2^(semitones / 12)
```

- `rate = 1.0` → original pitch
- `rate = 2.0` → octave up
- `rate = 0.5` → octave down

All pitch parameters accumulate into `totalSemitones` per grain, then one `Math.pow(2.0, totalSemitones / 12.0)` call sets the rate. Order inside grain():

1. **Octave jump** — mutually exclusive `if/else if`: octaveUp prob → +12st, octaveDown prob → -12st
2. **Pitch spray** — `pitchProb` dice roll → uniform random ±`pitchRange` semitones
3. **Fine detune** — `fineProb` dice roll → uniform random ±`fineRange` cents (×0.01 → semitones)

---

## Dynamics — Limiter

`Dyno limiter` inserted between `SndBuf` and `LiSa2` to tame input transients before recording into the buffer. Prevents loud attack clicks from dominating the grain cloud.

---

## Parameters

| Key | Parameter     | Description                                              | Range         |
|-----|---------------|----------------------------------------------------------|---------------|
| `g` | `grainSize`   | Length of each grain                                     | 10–500ms      |
| `d` | `density`     | Average grains per second                                | 5–50          |
| `p` | `position`    | Read position in buffer (0=oldest, 1=now)                | 0–1           |
| `s` | `posSpray`    | Random scatter around position                           | 0–0.5         |
| `w` | `panSpray`    | Stereo spread width (Gaussian)                           | 0–0.5         |
| `u` | `octaveUp`    | Probability grain jumps +1 octave                        | 0–1           |
| `o` | `octaveDown`  | Probability grain jumps -1 octave (else if octaveUp)     | 0–1           |
| `k` | `pitchRange`  | Max semitone deviation per grain                         | 0–12st        |
| `j` | `pitchProb`   | Probability pitch spray is applied                       | 0–1           |
| `f` | `fineRange`   | Max fine detune per grain                                | 0–100ct       |
| `e` | `fineProb`    | Probability fine detune is applied                       | 0–1           |
| `t` | `limiterThresh` | Dyno limiter threshold                                 | 0.1–1.0       |
| `a` | `limiterAttack` | Dyno limiter attack time                               | 1–50ms        |
| `r` | `limiterRelease` | Dyno limiter release time                             | 50–1000ms     |
| `i` | `inputGain`   | Dry input monitor volume                                 | 0–1           |
| `v` | `masterVol`   | Granular chain master volume                             | 0–2           |

---

## The Cloud Recipe

Three things together:
1. **High density** (many overlapping grains)
2. **High posSpray** (grains read from scattered buffer positions)
3. **Small pitchSpray / fineSpray** (subtle random pitch per grain)

This is what Ableton Granulator Cloud Mode and Mutable Clouds do.

---

## Grain Types (from Bencina)

- **Tapped Delay Line** — read from live input buffer (what we're doing)
- **Stored Sample** — read from a pre-recorded file
- **Synthetic** — oscillator-based grain (no buffer needed)

---

## Still TODO

- `freeze` — toggle `grainBuffer.record(0/1)`, key `z` (f is taken by fineRange)
- Dry/wet mix — blend input vs granular output
- Reverb — on granular output only (`LiSa2 → NRev → dac`), keep input dry
- Replace `SndBuf` with `adc` for real mic input
