// landmarks.ck — name → value lookup for the landmark globals.
// Isolates the big translation table so osc-router.ck stays focused on routing.
// Must be loaded into the VM BEFORE osc-router.ck (see chuck_controller.py).

// --- Landmark globals (shared with osc-listener.ck, same VM globals) ---
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

// Turns a landmark name from a .cfg file into its live value.
// Unknown names return 0.5 (neutral / center of frame) so a typo stays safe.
public class Landmarks {
    fun static float value(string name) {
        if (name == "right_thumb_x")  return g_right_thumb_x;
        if (name == "right_thumb_y")  return g_right_thumb_y;
        if (name == "right_thumb_z")  return g_right_thumb_z;
        if (name == "right_index_x")  return g_right_index_x;
        if (name == "right_index_y")  return g_right_index_y;
        if (name == "right_index_z")  return g_right_index_z;
        if (name == "right_middle_x") return g_right_middle_x;
        if (name == "right_middle_y") return g_right_middle_y;
        if (name == "right_middle_z") return g_right_middle_z;
        if (name == "right_ring_x")   return g_right_ring_x;
        if (name == "right_ring_y")   return g_right_ring_y;
        if (name == "right_ring_z")   return g_right_ring_z;
        if (name == "right_pinky_x")  return g_right_pinky_x;
        if (name == "right_pinky_y")  return g_right_pinky_y;
        if (name == "right_pinky_z")  return g_right_pinky_z;

        if (name == "left_thumb_x")   return g_left_thumb_x;
        if (name == "left_thumb_y")   return g_left_thumb_y;
        if (name == "left_thumb_z")   return g_left_thumb_z;
        if (name == "left_index_x")   return g_left_index_x;
        if (name == "left_index_y")   return g_left_index_y;
        if (name == "left_index_z")   return g_left_index_z;
        if (name == "left_middle_x")  return g_left_middle_x;
        if (name == "left_middle_y")  return g_left_middle_y;
        if (name == "left_middle_z")  return g_left_middle_z;
        if (name == "left_ring_x")    return g_left_ring_x;
        if (name == "left_ring_y")    return g_left_ring_y;
        if (name == "left_ring_z")    return g_left_ring_z;
        if (name == "left_pinky_x")   return g_left_pinky_x;
        if (name == "left_pinky_y")   return g_left_pinky_y;
        if (name == "left_pinky_z")   return g_left_pinky_z;

        return 0.5;
    }
}

<<< "[landmarks] Lookup table ready." >>>;
