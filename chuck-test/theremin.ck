// theremin.ck - OSC-controlled sine wave (like a theremin!)
// Receives right-hand thumb position from Virtual Conductor
// Run: chuck theremin.ck

// Sound setup
SinOsc s => dac;
0.5 => s.gain;
440 => s.freq;

// OSC setup
OscRecv recv;
8000 => recv.port;
recv.listen();

// Subscribe to index finger position
recv.event("/right-hand/index, f f f") @=> OscEvent indexEvent;

<<< "🎵 Theremin ready! Listening on port 8000" >>>;
<<< "   Move your right INDEX FINGER to control pitch" >>>;
<<< "   Press Ctrl+C to quit" >>>;

// Main loop
while(true) {
    // Wait for OSC message
    indexEvent => now;
    
    while(indexEvent.nextMsg()) {
        // Get x, y, z
        indexEvent.getFloat() => float x;
        indexEvent.getFloat() => float y;
        indexEvent.getFloat() => float z;
        
        // Map Y position (0-1) to frequency (200-800 Hz)
        // Y=0 is top of screen, Y=1 is bottom
        // Invert so raising thumb = higher pitch
        200 + ((1.0 - y) * 600) => s.freq;
        
        // Optional: print values
        // <<< "Thumb y:", y, "freq:", s.freq() >>>;
    }
}
