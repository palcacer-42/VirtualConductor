// osc-router.ck — Single OSC listener. Writes incoming hand data to globals.
// All DSP scripts read from semantic globals instead of owning their own OscRecv.

// --- Landmark globals (raw data from Python) ---
global float g_right_thumb_x;  global float g_right_thumb_y;  global float g_right_thumb_z;
global float g_right_index_x;  global float g_right_index_y;  global float g_right_index_z;
global float g_right_middle_x; global float g_right_middle_y; global float g_right_middle_z;
global float g_right_ring_x;   global float g_right_ring_y;   global float g_right_ring_z;
global float g_right_pinky_x;  global float g_right_pinky_y;  global float g_right_pinky_z;

global float g_left_thumb_x;   global float g_left_thumb_y;   global float g_left_thumb_z;
global float g_left_index_x;   global float g_left_index_y;   global float g_left_index_z;
global float g_left_middle_x;  global float g_left_middle_y;  global float g_left_middle_z;
global float g_left_ring_x;    global float g_left_ring_y;    global float g_left_ring_z;
global float g_left_pinky_x;   global float g_left_pinky_y;   global float g_left_pinky_z;

// --- Semantic globals (what effects actually read) ---
// Change the right-hand side here to reroute any effect parameter.
global float g_theremin_pitch;   // routed from: g_right_index_y
global float g_theremin_volume;  // routed from: g_left_index_y

global float g_synth_pitch;      // routed from: g_right_index_y
global float g_synth_cutoff;     // routed from: g_left_index_y

// Neutral starting position (center of frame)
0.5 => g_right_thumb_x;  0.5 => g_right_thumb_y;  0.0 => g_right_thumb_z;
0.5 => g_right_index_x;  0.5 => g_right_index_y;  0.0 => g_right_index_z;
0.5 => g_right_middle_x; 0.5 => g_right_middle_y; 0.0 => g_right_middle_z;
0.5 => g_right_ring_x;   0.5 => g_right_ring_y;   0.0 => g_right_ring_z;
0.5 => g_right_pinky_x;  0.5 => g_right_pinky_y;  0.0 => g_right_pinky_z;

0.5 => g_left_thumb_x;   0.5 => g_left_thumb_y;   0.0 => g_left_thumb_z;
0.5 => g_left_index_x;   0.5 => g_left_index_y;   0.0 => g_left_index_z;
0.5 => g_left_middle_x;  0.5 => g_left_middle_y;  0.0 => g_left_middle_z;
0.5 => g_left_ring_x;    0.5 => g_left_ring_y;    0.0 => g_left_ring_z;
0.5 => g_left_pinky_x;   0.5 => g_left_pinky_y;   0.0 => g_left_pinky_z;

OscRecv recv;
8000 => recv.port;
recv.listen();

recv.event("/right-hand/thumb, f f f")  @=> OscEvent rightThumb;
recv.event("/right-hand/index, f f f")  @=> OscEvent rightIndex;
recv.event("/right-hand/middle, f f f") @=> OscEvent rightMiddle;
recv.event("/right-hand/ring, f f f")   @=> OscEvent rightRing;
recv.event("/right-hand/pinky, f f f")  @=> OscEvent rightPinky;

recv.event("/left-hand/thumb, f f f")   @=> OscEvent leftThumb;
recv.event("/left-hand/index, f f f")   @=> OscEvent leftIndex;
recv.event("/left-hand/middle, f f f")  @=> OscEvent leftMiddle;
recv.event("/left-hand/ring, f f f")    @=> OscEvent leftRing;
recv.event("/left-hand/pinky, f f f")   @=> OscEvent leftPinky;

<<< "[osc-router] Listening on port 8000..." >>>;

// --- OSC receivers (active) ---
fun void routeRightIndex() {
    while(true) {
        rightIndex => now;
        while(rightIndex.nextMsg()) {
            rightIndex.getFloat() => g_right_index_x;
            rightIndex.getFloat() => g_right_index_y;
            rightIndex.getFloat() => g_right_index_z;
        }
    }
}
fun void routeLeftIndex() {
    while(true) {
        leftIndex => now;
        while(leftIndex.nextMsg()) {
            leftIndex.getFloat() => g_left_index_x;
            leftIndex.getFloat() => g_left_index_y;
            leftIndex.getFloat() => g_left_index_z;
        }
    }
}
spork ~ routeRightIndex();
spork ~ routeLeftIndex();

// --- OSC receivers (inactive — uncomment as effects need them) ---
// fun void routeRightThumb() {
//     while(true) {
//         rightThumb => now;
//         while(rightThumb.nextMsg()) {
//             rightThumb.getFloat() => g_right_thumb_x;
//             rightThumb.getFloat() => g_right_thumb_y;
//             rightThumb.getFloat() => g_right_thumb_z;
//         }
//     }
// }
// spork ~ routeRightThumb();

// --- Routing table (change here to remap effect parameters) ---
fun void updateRouting() {
    while(true) {
        g_right_index_y => g_theremin_pitch;
        g_left_index_y  => g_theremin_volume;

        g_right_index_y => g_synth_pitch;
        g_left_index_y  => g_synth_cutoff;

        1::ms => now;
    }
}
spork ~ updateRouting();

while(true) { 1::second => now; }
