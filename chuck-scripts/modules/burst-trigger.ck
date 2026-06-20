// burst-test.ck
// SPACE = fire a short noise burst.
// Uses KBHit (terminal stdin) -- no /dev/input permissions needed.

// --- keyboard input ---
KBHit kb;
kb.on();

// --- mix bus (bursts patch into here) ---
Gain mix => dac;
0.5 => mix.gain;

// SPACE = ASCII 32
32 => int SPACE;

chout <= "\rSPACE = noise burst       ";
chout.flush();

while( true )
{
    kb => now;                  // wait for a key event
    while( kb.more() )
    {
        kb.getchar() => int key;
        if( key == SPACE )
            spork ~ burst();
    }
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
