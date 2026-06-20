// burst-trigger.ck
// Fires a short noise burst on each /trigger/burst event from Python.
// Python sends the bang the instant the trigger fires (GUI button now, a MIDI
// pad later), so this stays decoupled from the camera/GUI frame rate.

// Shared trigger event — signalled by osc-router.ck when /trigger/burst arrives.
global Event g_burst_fire;

// --- mix bus (bursts patch into here) ---
Gain mix => dac;
0.5 => mix.gain;

while( true )
{
    g_burst_fire => now;        // wait for the next trigger
    spork ~ burst();
}

// one burst: white noise through a quick AR envelope, then the shred ends
// and the local ugens are disconnected + reclaimed automatically
fun void burst()
{
    Noise n => Envelope env => mix;
    0.3 => n.gain;
    0::ms => env.duration;
    1.0 => env.target;          // snap open (attack)
    2::ms => now;

    80::ms => env.duration;     // gentle decay
    0.0 => env.target;
    80::ms => now;
}
