// theremin.ck - Two-hand OSC Theremin with Smooth Interpolation
// Right hand index = pitch, Left hand index = volume
// Run: chuck theremin.ck

// ===== AUDIO SETUP =====
SinOsc s => Gain g => dac;
440 => s.freq;      // Starting frequency
0.5 => g.gain;      // Starting volume

// ===== TARGET VALUES (updated by OSC) =====
440.0 => float targetFreq;
0.5 => float targetGain;

// ===== INTERPOLATION SETTINGS =====
0.1 => float smoothing;  // 0.01 = very smooth, 0.5 = fast response
5::ms => dur updateRate; // How often to interpolate

// ===== OSC SETUP =====
OscRecv recv;
8000 => recv.port;
recv.listen();

// Create events for each hand
recv.event("/right-hand/index, f f f") @=> OscEvent rightHand;
recv.event("/left-hand/index, f f f") @=> OscEvent leftHand;

<<< "🎵 Two-Hand Theremin Ready! (with smooth interpolation)" >>>;
<<< "   Right hand = PITCH (200-800 Hz)" >>>;
<<< "   Left hand  = VOLUME" >>>;
<<< "   Smoothing:", smoothing >>>;
<<< "   Listening on port 8000..." >>>;

// ===== RIGHT HAND: Update Target Pitch =====
fun void pitchOSC() {
    while(true) {
        rightHand => now;
        while(rightHand.nextMsg()) {
            rightHand.getFloat() => float x;
            rightHand.getFloat() => float y;
            rightHand.getFloat() => float z;
            
            // Set target (not applied directly)
            200 + ((1.0 - y) * 600) => targetFreq;
        }
    }
}

// ===== LEFT HAND: Update Target Volume =====
fun void volumeOSC() {
    while(true) {
        leftHand => now;
        while(leftHand.nextMsg()) {
            leftHand.getFloat() => float x;
            leftHand.getFloat() => float y;
            leftHand.getFloat() => float z;
            
            // Set target (not applied directly)
            (1.0 - y) => targetGain;
        }
    }
}

// ===== SMOOTH INTERPOLATION SHRED =====
fun void interpolate() {
    while(true) {
        // Glide frequency toward target
        s.freq() + (targetFreq - s.freq()) * smoothing => s.freq;
        
        // Glide volume toward target
        g.gain() + (targetGain - g.gain()) * smoothing => g.gain;
        
        // Wait before next update
        updateRate => now;
    }
}

// ===== START ALL SHREDS =====
spork ~ pitchOSC();
spork ~ volumeOSC();
spork ~ interpolate();

// Keep main shred alive
while(true) {
    1::second => now;
}
