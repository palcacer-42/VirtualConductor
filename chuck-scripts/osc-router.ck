// osc-router.ck — Single OSC listener. Writes incoming hand data to globals.
// All DSP scripts read from these globals instead of owning their own OscRecv.

global float g_right_x;
global float g_right_y;
global float g_right_z;
global float g_left_x;
global float g_left_y;
global float g_left_z;

// Neutral starting position (center of frame)
0.5 => g_right_x; 0.5 => g_right_y; 0.0 => g_right_z;
0.5 => g_left_x;  0.5 => g_left_y;  0.0 => g_left_z;

OscRecv recv;
8000 => recv.port;
recv.listen();

recv.event("/right-hand/index, f f f") @=> OscEvent rightHand;
recv.event("/left-hand/index, f f f")  @=> OscEvent leftHand;

<<< "[osc-router] Listening on port 8000..." >>>;

fun void routeRight() {
    while(true) {
        rightHand => now;
        while(rightHand.nextMsg()) {
            rightHand.getFloat() => g_right_x;
            rightHand.getFloat() => g_right_y;
            rightHand.getFloat() => g_right_z;
        }
    }
}

fun void routeLeft() {
    while(true) {
        leftHand => now;
        while(leftHand.nextMsg()) {
            leftHand.getFloat() => g_left_x;
            leftHand.getFloat() => g_left_y;
            leftHand.getFloat() => g_left_z;
        }
    }
}

spork ~ routeRight();
spork ~ routeLeft();

while(true) { 1::second => now; }
