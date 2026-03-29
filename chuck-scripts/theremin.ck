// theremin.ck — Pure DSP. Reads hand position from globals set by osc-router.ck.
// Right hand Y = pitch, Left hand Y = volume.
// Run via launch-theremin.ck, not directly.

global float g_right_y;
global float g_left_y;

// ===== AUDIO SETUP =====
SinOsc s => Gain g => dac;
440 => s.freq;
0.5 => g.gain;

// ===== INTERPOLATION SETTINGS =====
0.1 => float smoothing;
5::ms => dur updateRate;

<<< "[theremin] Ready. Right hand = PITCH (200-800 Hz), Left hand = VOLUME" >>>;

fun void interpolate() {
    while(true) {
        // Compute targets from globals each tick
        200 + ((1.0 - g_right_y) * 600) => float targetFreq;
        (1.0 - g_left_y) => float targetGain;

        // Smooth toward targets
        s.freq() + (targetFreq - s.freq()) * smoothing => s.freq;
        g.gain() + (targetGain - g.gain()) * smoothing => g.gain;

        updateRate => now;
    }
}

spork ~ interpolate();

while(true) { 1::second => now; }
