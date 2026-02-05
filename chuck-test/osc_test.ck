// osc_test.ck - Test OSC receiver for right hand fingertips
// Run: chuck osc_test.ck

OscIn oin;
OscMsg msg;
8000 => oin.port;  // Listen on port 8000

// Listen to all right-hand addresses
oin.addAddress("/right-hand/thumb");
oin.addAddress("/right-hand/index");
oin.addAddress("/right-hand/middle");
oin.addAddress("/right-hand/ring");
oin.addAddress("/right-hand/pinky");

<<< "Listening for OSC on port 8000..." >>>;
<<< "Run the Virtual Conductor in another terminal" >>>;
<<< "-------------------------------------------" >>>;

while(true) {
    oin => now;
    while(oin.recv(msg)) {
        // Get x, y, z values
        msg.getFloat(0) => float x;
        msg.getFloat(1) => float y;
        msg.getFloat(2) => float z;
        
        <<< msg.address, "x:", x, "y:", y, "z:", z >>>;
    }
}
