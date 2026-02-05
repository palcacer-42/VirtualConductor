// synth.ck - Two-hand OSC Synth with Waveform Crossfade
// Right hand = pitch, Left hand = waveform (sine ↔ square)
// Run: chuck synth.ck

// ===== AUDIO SETUP =====
// Two oscillators mixed together
SinOsc sine => Gain sineGain => Gain master => dac;
SqrOsc sqr  => Gain sqrGain  => master;

// Starting values
440 => sine.freq;
440 => sqr.freq;
0.5 => master.gain;  // Overall volume
1.0 => sineGain.gain; // Start with sine
0.0 => sqrGain.gain;  // Square off

// ===== TARGET VALUES =====
440.0 => float targetFreq;
0.0 => float targetMix;  // 0 = sine, 1 = square

// ===== INTERPOLATION SETTINGS =====
0.1 => float smoothing;
5::ms => dur updateRate;

// ===== OSC SETUP =====
OscRecv recv;
8000 => recv.port;
recv.listen();

recv.event("/right-hand/index, f f f") @=> OscEvent rightHand;
recv.event("/left-hand/index, f f f") @=> OscEvent leftHand;

<<< "🎹 Two-Hand Synth Ready!" >>>;
<<< "   Right hand = PITCH (200-800 Hz)" >>>;
<<< "   Left hand  = WAVEFORM (down=sine, up=square)" >>>;
<<< "   Listening on port 8000..." >>>;

// ===== RIGHT HAND: Pitch =====
fun void pitchOSC() {
    while(true) {
        rightHand => now;
        while(rightHand.nextMsg()) {
            rightHand.getFloat() => float x;
            rightHand.getFloat() => float y;
            rightHand.getFloat() => float z;
            200 + ((1.0 - y) * 600) => targetFreq;
        }
    }
}

// ===== LEFT HAND: Waveform Mix =====
fun void waveformOSC() {
    while(true) {
        leftHand => now;
        while(leftHand.nextMsg()) {
            leftHand.getFloat() => float x;
            leftHand.getFloat() => float y;
            leftHand.getFloat() => float z;
            // Y=0 (hand up) = square, Y=1 (hand down) = sine
            // Invert: hand up = more square
            (1.0 - y) => targetMix;
        }
    }
}

// ===== INTERPOLATION =====
fun void interpolate() {
    0.0 => float currentMix;
    440.0 => float currentFreq;
    
    while(true) {
        // Smooth frequency
        currentFreq + (targetFreq - currentFreq) * smoothing => currentFreq;
        currentFreq => sine.freq;
        currentFreq => sqr.freq;
        
        // Smooth waveform mix
        currentMix + (targetMix - currentMix) * smoothing => currentMix;
        
        // Crossfade: sine decreases as square increases
        (1.0 - currentMix) => sineGain.gain;
        currentMix => sqrGain.gain;
        
        updateRate => now;
    }
}

// ===== START SHREDS =====
spork ~ pitchOSC();
spork ~ waveformOSC();
spork ~ interpolate();

while(true) {
    1::second => now;
}
