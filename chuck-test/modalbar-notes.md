# ModalBar — quick reference

STK struck-bar instrument (modal synthesis: a bank of tuned, decaying
resonators). Chain it straight to the dac: `ModalBar bar => dac;`

## Presets — `.preset(int)` 0–8
| # | sound      |
|---|------------|
| 0 | Marimba    |
| 1 | Vibraphone |
| 2 | Agogo      |
| 3 | Wood1      |
| 4 | Reso       |
| 5 | Wood2      |
| 6 | Beats      |
| 7 | Two Fixed  |
| 8 | Clump      |

## Main playing controls
- `.noteOn(velocity)`   [0–1]  — strike the bar (use this on keypress)
- `.noteOff(velocity)`         — release / damp
- `.freq(Hz)`                  — pitch of the bar
- `.strikePosition(0–1)`       — WHERE you hit it; big timbral change (center vs edge)
- `.stickHardness(0–1)`        — soft mallet (mellow) → hard mallet (bright attack)

## Shaping / expression
- `.strike(0–1)`               — strike directly (alt to noteOn)
- `.damp(0–1)`                 — damping of resonators (how fast it rings out)
- `.vibratoFreq(Hz)` / `.vibratoGain(0–1)` — vibrato (musical on vibraphone)
- `.volume(0–1)`, `.masterGain(0–1)`, `.directGain(0–1)` — levels

## Per-mode sculpting (build a custom bar)
- `.mode(int)`          — select which mode to edit
- `.modeRatio(float)`   — freq ratio of that mode vs fundamental (inharmonicity)
- `.modeRadius(0–1)`    — resonance/decay of that mode (→1 = rings longer)
- `.modeGain(0–1)`      — loudness of that mode

Inheritance: ModalBar → StkInstrument → UGen → Object
Docs: https://chuck.stanford.edu/doc/program/ugen_stk.html

---

## Practical notes (from modalbar-trigger-test.ck)

### Control map (keyboard)
- SPACE = strike (random pitch 200–800 Hz, snapshots current settings)
- 0–8   = select preset
- select-a-param then LEFT/RIGHT arrows to adjust (granular-style):
  - h = stickHardness   p = strikePosition   v = velocity
  - d = damp            f = vibratoFreq (Hz)  g = vibratoGain
  - r = ratioSpray (preset -> inharmonic, see below)
- arrows arrive as escape seq: 27 91 67 (right) / 27 91 68 (left).
- `adjust(dir)` takes +1/-1; each param has its own step (0.05 for 0–1 params,
  1.0 for vibratoFreq Hz). Real units + per-param steps = granular convention.

### Parameter bounds convention (matches granular-test.ck)
- Paired `X_MIN` / `X_MAX` float constants in an aligned "parameter bounds" block.
- Clamp with `Math.max( Math.min(val, X_MAX), X_MIN )`.
- VELOCITY_MIN = 0.3 (floor so the softest strike is still audible). Max 1.0.

### Mode-ratio perturbation = the timbre/diversity engine
- A preset is just a saved set of per-mode {ratio, radius, gain}. ModalBar has
  NMODES = 4 modes. `mode(m)` selects a mode; `modeRatio()/modeRatio(v)` get/set
  its frequency ratio vs the fundamental.
- Pattern: load preset FIRST (it resets the modes), then perturb each mode's ratio:
  `r * (1 + random2f(-spray, spray))`, guarded `Math.max(0.05, ...)` so it never
  hits 0/negative. spray=0 -> pure preset (tonal); higher -> detuned/inharmonic
  (bell, metallic). Randomized per strike -> variety even at a fixed spray.
- Harmonic ratios (1,2,3,4) = tonal/pitched; non-integer = bell-like/clangorous.
- Keep presets as seeds; perturb on top — don't hand-build bars from scratch.
- TO VERIFY (not yet run): chuck-operator set form `m => bar.mode;` /
  `v => bar.modeRatio;`. If rejected, use call form `bar.mode(m)`.

### Original practical notes (from earlier trigger-test.ck)

### Per-shred voice model
- A struck bar rings + decays on its own after `noteOn` — no envelope needed.
- Best polyphony pattern: `spork ~ strikeModalBar(freq, preset, hardness, pos, vel)`.
  The `ModalBar` is created *inside* the function (patched to a `mix` bus), and
  is auto-disconnected + reclaimed when the shred ends. Voice count scales with
  the number of live shreds — perfect for "note count varies".
- GOTCHA: the local bar only lives as long as the shred. The function MUST hold
  time for the full ring-out before returning, or the tail gets cut (click).

### Ring time = voice lifetime, NOT an envelope
- The hold time after `noteOn` only keeps the voice alive; it doesn't shape sound.
  - Longer than the natural decay → no audible difference (just holds silence).
  - Shorter than the decay → truncates the tail (audible cut / click).
- Don't hardcode a duration. trigger-test watches the bar's own output
  (`bar.last()` peak over a short window) and ends the shred when it drops below
  ~0.0008 (≈ -62 dB), with a 10s safety ceiling. Adapts to ANY preset/decay,
  never clips, never over-holds. Tune the SILENCE threshold if tails end early/late.

### Decay length varies by preset
- Marimba / Agogo / Wood presets: short, dry (well under 1s).
- Vibraphone (1): the long one — can approach/exceed 2s. A fixed 2s would clip it.
  → another reason to use the dynamic silence-detection above.

### Reuse seam for the future pitch-detector → ModalBar
- `strikeModalBar(...)` takes ALL properties as arguments → no globals needed to
  reuse it. The pitch detector would just `spork ~ strikeModalBar(peakFreq, ...)`
  per detected peak (mirrors the 4-`SinOsc` array in pitch-detector-osc-test.ck).
- Make THAT path polyphonic; keep the manual keyboard test mono-per-strike.

### Globals vs setters
- Keyboard control state lives in `curPreset`, `curStickHardness`,
  `curStrikePosition`; each strike snapshots them at spawn time.
- No setters yet — there's only ONE writer (keyboard) and clamping is inline in
  `adjust()`. Add a `setX()` per param only when a SECOND writer appears (OSC /
  conductor sending live param changes), so the clamp lives in one place — same
  reason granular-test.ck has its setGrainSize/setDensity setters.
