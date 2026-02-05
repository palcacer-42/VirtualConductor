// theremin.ck - Two-hand OSC Theremin
// Right hand index = pitch, Left hand index = volume
// Run: chuck theremin.ck

// ===== AUDIO SETUP =====
SinOsc s => Gain g => dac;
440 => s.freq;      // Starting frequency
0.5 => g.gain;      // Starting volume

// ===== OSC SETUP =====
OscRecv recv;
8000 => recv.port;
recv.listen();

// Create events for each hand
recv.event("/right-hand/index, f f f") @=> OscEvent rightHand;
recv.event("/left-hand/index, f f f") @=> OscEvent leftHand;

<<< "🎵 Two-Hand Theremin Ready!" >>>;
<<< "   Right hand = PITCH (200-800 Hz)" >>>;
<<< "   Left hand  = VOLUME" >>>;
<<< "   Listening on port 8000..." >>>;
<<< "   Press Ctrl+C to quit" >>>;

// ===== RIGHT HAND: Pitch Control =====
fun void pitchControl() {
    while(true) {
        rightHand => now;
        while(rightHand.nextMsg()) {
            rightHand.getFloat() => float x;
            rightHand.getFloat() => float y;
            rightHand.getFloat() => float z;
            
            // Map Y (0-1) to frequency (200-800 Hz)
            // Invert: hand up = high pitch
            200 + ((1.0 - y) * 600) => s.freq;
        }
    }
}

// ===== LEFT HAND: Volume Control =====
fun void volumeControl() {
    while(true) {
        leftHand => now;
        while(leftHand.nextMsg()) {
            leftHand.getFloat() => float x;
            leftHand.getFloat() => float y;
            leftHand.getFloat() => float z;
            
            // Map Y (0-1) to volume (0-1)
            // Invert: hand up = loud
            (1.0 - y) => g.gain;
        }
    }
}

// ===== START CONCURRENT SHREDS =====
spork ~ pitchControl();
spork ~ volumeControl();

// Keep main shred alive
while(true) {
    1::second => now;
}
