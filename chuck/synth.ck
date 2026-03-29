// synth.ck - Classic Subtractive Synth (Saw + LPF)
// Right hand = pitch, Left hand = filter cutoff
// Run: chuck synth.ck

// ===== HELPER FUNCTIONS (reusable) =====

// Map value from one range to another
fun float mapRange(float value, float inMin, float inMax, float outMin, float outMax) {
    return outMin + (value - inMin) * (outMax - outMin) / (inMax - inMin);
}

// Clamp value to range
fun float clamp(float value, float minVal, float maxVal) {
    if (value < minVal) return minVal;
    if (value > maxVal) return maxVal;
    return value;
}

// Exponential mapping (for perceptually-correct frequency control)
// value: 0.0-1.0, returns value between minVal and maxVal on exponential curve
fun float expMap(float value, float minVal, float maxVal) {
    return minVal * Math.pow(maxVal/minVal, value);
}

// ===== AUDIO SETUP =====
// Classic subtractive: Oscillator -> Filter -> Output
SawOsc saw => LPF filter => Gain master => dac;

// Starting values
440 => saw.freq;
0.5 => master.gain;

// Filter settings
2000 => filter.freq;  // Cutoff frequency (Hz)
2.0 => filter.Q;      // Resonance (subtle)

// ===== TARGET VALUES =====
440.0 => float targetFreq;
2000.0 => float targetCutoff;

// Filter range (Hz)
200.0 => float minCutoff;
4000.0 => float maxCutoff;

// ===== INTERPOLATION SETTINGS =====
0.1 => float smoothing;
5::ms => dur updateRate;

// ===== OSC SETUP =====
OscRecv recv;
8000 => recv.port;
recv.listen();

recv.event("/right-hand/index, f f f") @=> OscEvent rightHand;
recv.event("/left-hand/index, f f f") @=> OscEvent leftHand;

<<< "🎹 Subtractive Synth Ready! (Saw + LPF)" >>>;
<<< "   Right hand = PITCH (200-800 Hz)" >>>;
<<< "   Left hand  = FILTER CUTOFF (200-4000 Hz)" >>>;
<<< "   Listening on port 8000..." >>>;

// ===== RIGHT HAND: Pitch =====
fun void pitchOSC() {
    while(true) {
        rightHand => now;
        while(rightHand.nextMsg()) {
            rightHand.getFloat() => float x;
            rightHand.getFloat() => float y;
            rightHand.getFloat() => float z;
            // Hand up = high pitch
            200 + ((1.0 - y) * 600) => targetFreq;
        }
    }
}

// ===== LEFT HAND: Filter Cutoff =====
fun void filterOSC() {
    while(true) {
        leftHand => now;
        while(leftHand.nextMsg()) {
            leftHand.getFloat() => float x;
            leftHand.getFloat() => float y;
            leftHand.getFloat() => float z;
            // Hand up = bright (high cutoff), Hand down = dark (low cutoff)
            // Exponential mapping for perceptually-correct response
            expMap(1.0 - y, minCutoff, maxCutoff) => targetCutoff;
        }
    }
}

// ===== INTERPOLATION =====
fun void interpolate() {
    440.0 => float currentFreq;
    2000.0 => float currentCutoff;
    
    while(true) {
        // Smooth frequency
        currentFreq + (targetFreq - currentFreq) * smoothing => currentFreq;
        currentFreq => saw.freq;
        
        // Smooth filter cutoff
        currentCutoff + (targetCutoff - currentCutoff) * smoothing => currentCutoff;
        currentCutoff => filter.freq;
        
        updateRate => now;
    }
}

// ===== START SHREDS =====
spork ~ pitchOSC();
spork ~ filterOSC();
spork ~ interpolate();

while(true) {
    1::second => now;
}
