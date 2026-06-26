// aliased-shimmer.ck — a hold-to-record looper built on LiSa2 (live sampling).
// Audio input is the shared g_mic bus from core/input.ck.
//
// LiSa2 is the live-sampling buffer: it records live input into its own buffer
// and can play it back with per-voice rate / position / loop control, plus a
// clear() that empties it — the right tool for capturing g_mic and then
// manipulating the captured buffer in different ways. Stereo (LiSa2) so the
// playback can be spread/panned later, matching granulator.ck's output style.
//
// Behaviour, driven by the osc-router globals:
//   collect gate HELD  -> record g_mic into the buffer from the start
//   collect gate RELEASED -> stop recording, loop-play the recorded region
//   clear trigger      -> empty the buffer and stop playback

global Gain g_mic;

// "collect" gate from osc-router.ck: 1 while held (GUI button pressed or a
// learned MIDI pad), 0 when released. Held = record, released = loop-play.
global float g_aliased_shimmer_collect;

// "clear" trigger from osc-router.ck: a one-shot, delivered as a 0->1 edge. We
// detect the rise, act once, then reset it to 0 to consume it.
global int g_aliased_shimmer_clear;

// loop output volume: normalized 0..1, mapped into [0, MASTER_VOL_MAX] gain
// (0.5 -> unity), like granulator's mastervol.
global float g_aliased_shimmer_mastervol;

// ===== AUDIO SETUP =====
60::second => dur MAX_BUF;       // longest single hold-to-record we can capture (1 min)
50::ms => dur RAMP;              // record fade in/out — see recRamp below
0.0 => float MASTER_VOL_MIN;     // 0..1 mastervol maps into [MIN, MAX] gain
2.0 => float MASTER_VOL_MAX;     // (0.5 -> 1.0 unity), like granulator

// g_mic feeds LiSa2 as the record source; the buffer's main out goes to a sink
// (blackhole) and the audible signal comes from the per-channel playback taps,
// exactly like granulator.ck. A master gain sits before dac for headroom.
g_mic => LiSa2 buf => blackhole;
buf.duration( MAX_BUF );
buf.maxVoices( 1 );              // one playback voice for the loop
0 => buf.loopRec;                // recording stops at the buffer end, doesn't wrap
buf.recRamp( RAMP );             // fade the recording in/out so the captured
                                 // buffer starts and ends at zero — no click at
                                 // the loop seam where loopEnd wraps to loopStart

Gain masterL, masterR;
1.0 => masterL.gain => masterR.gain;
buf.chan(0) => masterL => dac.left;
buf.chan(1) => masterR => dac.right;

0 => buf.record;                 // start idle (not recording, not playing)

// map a normalized 0..1 into a float range, like granulator's mapF
fun float mapF(float g, float lo, float hi) { return lo + g * (hi - lo); }

// clamp into the gain range and apply to both master channels, like
// granulator's setMasterVol
fun void setMasterVol(float val) {
    Math.max(Math.min(val, MASTER_VOL_MAX), MASTER_VOL_MIN) => masterL.gain => masterR.gain;
}

// stop loop playback (used before recording over and on clear)
fun void stopPlayback() {
    buf.play( 0, 0 );
    buf.loop( 0, 0 );
}

// gate rising edge: begin a fresh recording from the buffer start
fun void startRecording() {
    stopPlayback();
    buf.recPos( 0::ms );             // record over from the start
    1 => buf.record;
}

// gate falling edge: stop recording, then loop-play what we captured
fun void startLoop() {
    0 => buf.record;
    RAMP => now;                     // let the record fade-out finish writing the
                                     // tail so recPos covers it (loopEnd at zero)
    buf.recPos() => dur recLen;      // how much we actually captured
    if( recLen <= 1::ms ) return;    // nothing meaningful recorded
    buf.loopStart( 0, 0::ms );
    buf.loopEnd( 0, recLen );
    buf.loop( 0, 1 );
    buf.rate( 0, 1.0 );
    buf.playPos( 0, 0::ms );
    buf.play( 0, 1 );
}

// clear trigger: stop everything and empty the buffer
fun void clearBuffer() {
    0 => buf.record;
    stopPlayback();
    buf.clear();
}

// ===== CONTROL LOOP =====
// Poll the gate for its edges and dispatch the looper actions. 5 ms is fine for
// hand/MIDI-driven control; recPos() gives the sample-accurate recorded length.
0 => int gateOpen;
while( true )
{
    // track the master volume each tick (normalized 0..1 -> clamped gain)
    setMasterVol( mapF(g_aliased_shimmer_mastervol, MASTER_VOL_MIN, MASTER_VOL_MAX) );

    (g_aliased_shimmer_collect > 0.5) => int nowOpen;
    if( nowOpen && !gateOpen ) startRecording();   // rising edge
    if( !nowOpen && gateOpen ) startLoop();         // falling edge
    nowOpen => gateOpen;

    // clear trigger: any pending 0->1 fires once, then we reset to consume it.
    if( g_aliased_shimmer_clear != 0 )
    {
        0 => g_aliased_shimmer_clear;
        clearBuffer();
    }

    5::ms => now;
}
