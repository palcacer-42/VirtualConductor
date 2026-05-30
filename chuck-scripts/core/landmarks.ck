// landmarks.ck — shared name->value store for all continuous OSC sources.
//
// Every continuous input (hand landmarks today; face/pose/GUI sliders later) is
// stored here under a string key, e.g. "right_index_y" or "theremin.vibrato".
// This is the single place that maps a name to a value: osc-listener.ck writes
// into it, osc-router.ck reads from it. Adding a new source costs no code here.
//
// MUST be loaded into the VM BEFORE osc-listener.ck and osc-router.ck
// (see chuck_controller.py) so the store exists before anyone touches it.

public class Landmarks {
    // The one shared store. 'static' => a single instance shared by every shred.
    static float store[];

    // Write a named value (called by the OSC listener as data arrives).
    fun static void set( string name, float value ) {
        value => Landmarks.store[name];
    }

    // Read a named value. Names never written read as 0.0 (e.g. a slider before
    // its first message, or a typo'd route) — safe, never throws once allocated.
    fun static float value( string name ) {
        return Landmarks.store[name];
    }
}

// --- Allocate the store, then seed hand landmarks to a neutral pose -----------
// Seeding keeps instruments centered instead of jumping before the first camera
// frame arrives. x/y center = 0.5; z (depth) neutral = 0.0.
new float[0] @=> Landmarks.store;

["right", "left"] @=> string sides[];
["thumb", "index", "middle", "ring", "pinky"] @=> string fingers[];
for( int s; s < sides.size(); s++ )
    for( int f; f < fingers.size(); f++ )
    {
        "hand_" + sides[s] + "_" + fingers[f] => string base;
        Landmarks.set( base + "_x", 0.5 );
        Landmarks.set( base + "_y", 0.5 );
        Landmarks.set( base + "_z", 0.0 );
    }

string seeded[0];
Landmarks.store.getKeys( seeded );
<<< "[landmarks] store ready;", seeded.size(), "keys seeded." >>>;
