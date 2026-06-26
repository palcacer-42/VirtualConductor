// aliased-shimmer.ck — Pure DSP. Reads audio input from the shared g_mic bus
// set by core/input.ck. No output yet.

global Gain g_mic;

// "collect" gate from osc-router.ck: 1 while the gate is held open (GUI button
// pressed or a learned MIDI pad), 0 when released. No output uses it yet.
global float g_collect_gate;

<<< "[aliased-shimmer] Ready. Listening to g_mic (no output)." >>>;

// Poll the gate and log only when it flips, so the console shows each
// open/close edge rather than spamming every tick.
0 => int gateOpen;
while( true )
{
    (g_collect_gate > 0.5) => int nowOpen;
    if( nowOpen != gateOpen )
    {
        nowOpen => gateOpen;
        if( gateOpen ) <<< "[aliased-shimmer] gate ON" >>>;
        else           <<< "[aliased-shimmer] gate OFF" >>>;
    }
    5::ms => now;
}
