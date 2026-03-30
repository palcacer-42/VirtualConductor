// theremin.ck — Pure DSP. Reads hand position from globals set by osc-router.ck.
// Right hand Y = pitch, Left hand Y = volume.
// Run via launch-theremin.ck, not directly.

global float g_theremin_pitch;
global float g_theremin_volume;

// ===== AUDIO SETUP =====
SinOsc s => Gain g => dac;
440 => s.freq;
0.5 => g.gain;

// ===== VIBRATO =====
// Rate proportional to current frequency (ratio 1/60 → ~7 Hz at 440 Hz)
// Depth: ±0.5% of current frequency
SinOsc vibrato => blackhole;
0.015 => float vibratoDepthRatio;  // depth as fraction of freq
1.0 / 60.0 => float vibratoRateRatio;  // rate as fraction of freq

// ===== INTERPOLATION SETTINGS =====
0.1 => float smoothing;
5::ms => dur updateRate;

<<< "[theremin] Ready. Right hand = PITCH (200-800 Hz), Left hand = VOLUME" >>>;

fun void interpolate() {
    while(true) {
        // Compute targets from globals each tick
        200 + ((1.0 - g_theremin_pitch) * 600) => float targetFreq;
        (1.0 - g_theremin_volume) => float targetGain;

        // Smooth toward targets
        s.freq() + (targetFreq - s.freq()) * smoothing => float currentFreq;

        // Vibrato: rate and depth both scale with frequency
        currentFreq * vibratoRateRatio => vibrato.freq;
        currentFreq + (vibrato.last() * currentFreq * vibratoDepthRatio) => s.freq;

        g.gain() + (targetGain - g.gain()) * smoothing => g.gain;

        updateRate => now;
    }
}

spork ~ interpolate();

while(true) { 1::second => now; }
