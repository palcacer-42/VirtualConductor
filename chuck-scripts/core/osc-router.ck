// osc-router.ck — Maps landmark globals to effect parameter globals.
// Edit here to reroute any effect parameter. Never touch osc-listener.ck for this.

// --- Landmark globals (defined in osc-listener.ck) ---
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

// --- Effect parameter globals ---
global float g_theremin_pitch;   // routed from: g_right_index_y
global float g_theremin_volume;  // routed from: g_left_index_y

global float g_synth_pitch;      // routed from: g_right_index_y
global float g_synth_cutoff;     // routed from: g_left_index_y

<<< "[osc-router] Routing table active..." >>>;

fun void updateRouting() {
    while(true) {
        // --- Theremin ---
        g_right_index_y => g_theremin_pitch;
        g_left_index_y  => g_theremin_volume;

        // --- Synth ---
        g_right_index_y => g_synth_pitch;
        g_left_index_y  => g_synth_cutoff;

        1::ms => now;
    }
}
spork ~ updateRouting();

while(true) { 1::second => now; }
