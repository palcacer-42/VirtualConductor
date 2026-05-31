// synth.ck — Pure DSP. Reads hand position from globals set by osc-router.ck.
// Right hand Y = pitch, Left hand Y = filter cutoff.
// Run via launch-synth.ck, not directly.

global float g_synth_pitch;
global float g_synth_cutoff;

// ===== HELPERS =====
fun float mapRange(float value, float inMin, float inMax, float outMin, float outMax) {
    return outMin + (value - inMin) * (outMax - outMin) / (inMax - inMin);
}

fun float clamp(float value, float minVal, float maxVal) {
    if (value < minVal) return minVal;
    if (value > maxVal) return maxVal;
    return value;
}

fun float expMap(float value, float minVal, float maxVal) {
    return minVal * Math.pow(maxVal / minVal, value);
}

// ===== AUDIO SETUP =====
SawOsc saw => LPF filter => Gain master => dac;
440 => saw.freq;
0.5 => master.gain;
2000 => filter.freq;
2.0 => filter.Q;

// ===== SETTINGS =====
0.1 => float smoothing;
5::ms => dur updateRate;
200.0 => float minCutoff;
4000.0 => float maxCutoff;

<<< "[synth] Ready. Right hand = PITCH (200-800 Hz), Left hand = FILTER CUTOFF" >>>;

fun void interpolate() {
    440.0 => float currentFreq;
    2000.0 => float currentCutoff;

    while(true) {
        // Compute targets from globals each tick (0 -> min, 1 -> max; Python
        // already normalized and applied any axis inversion).
        200 + (g_synth_pitch * 600) => float targetFreq;
        expMap(g_synth_cutoff, minCutoff, maxCutoff) => float targetCutoff;

        // Smooth toward targets
        currentFreq + (targetFreq - currentFreq) * smoothing => currentFreq;
        currentFreq => saw.freq;

        currentCutoff + (targetCutoff - currentCutoff) * smoothing => currentCutoff;
        currentCutoff => filter.freq;

        updateRate => now;
    }
}

spork ~ interpolate();

while(true) { 1::second => now; }
