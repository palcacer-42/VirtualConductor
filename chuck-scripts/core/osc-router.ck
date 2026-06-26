// osc-router.ck — receives final parameter values from Python and writes them
// straight to the effect globals.
//
// Python owns all routing: it decides per param whether to use the slider or a
// landmark, resolves one value, and sends it on /param/<module>/<param>. ChucK
// does no routing or landmark handling — it just plays the value it's given.

// --- Effect parameter globals (modules read these; declared here too so they
// exist and sit at a neutral value before any module is added) ---
global float g_theremin_pitch;
global float g_theremin_volume;
global float g_synth_pitch;
global float g_synth_cutoff;

// input (input.ck) — shared input: monitor volume + source selection
global float g_input_volume;
global float g_input_source;   // 0 = fake-theorbo, 1 = mic

// burst-trigger — a momentary event, not a held value. Python sends a bang on
// /trigger/burst the instant the trigger fires (GUI button now, a MIDI pad
// later); burst-trigger.ck waits on this and fires one burst per signal. Being
// event-driven, it never rides the camera/GUI frame rate.
global Event g_burst_fire;

// aliased-shimmer — the "collect" gate. A held 0/1 state, not an event: Python
// sends 1 the instant the gate opens (GUI button pressed or a MIDI pad note-on)
// and 0 when it closes (button released / note-off), on /gate/collect. A float
// the module polls.
global float g_collect_gate;

// granulator — every param is a normalized 0..1 value; granulator.ck maps each
// into its [MIN, MAX] range.
global float g_granulator_grainsize;
global float g_granulator_density;
global float g_granulator_position;
global float g_granulator_posspray;
global float g_granulator_panspray;
global float g_granulator_octaveup;
global float g_granulator_octavedown;
global float g_granulator_pitchrange;
global float g_granulator_pitchprob;
global float g_granulator_finerange;
global float g_granulator_fineprob;
global float g_granulator_thresh;
global float g_granulator_attack;
global float g_granulator_release;
global float g_granulator_delayleft;
global float g_granulator_delayright;
global float g_granulator_feedback;
global float g_granulator_delaymix;
global float g_granulator_reverbmix;
global float g_granulator_mastervol;

0.5 => g_theremin_pitch;
0.5 => g_theremin_volume;
0.5 => g_synth_pitch;
0.5 => g_synth_cutoff;

0.5 => g_input_volume;
0.0 => g_input_source;   // 0 = fake-theorbo (default), 1 = mic

0.0 => g_collect_gate;   // gate closed at start

0.5 => g_granulator_grainsize;
0.5 => g_granulator_density;
0.5 => g_granulator_position;
0.5 => g_granulator_posspray;
0.5 => g_granulator_panspray;
0.5 => g_granulator_octaveup;
0.5 => g_granulator_octavedown;
0.5 => g_granulator_pitchrange;
0.5 => g_granulator_pitchprob;
0.5 => g_granulator_finerange;
0.5 => g_granulator_fineprob;
0.5 => g_granulator_thresh;
0.5 => g_granulator_attack;
0.5 => g_granulator_release;
0.5 => g_granulator_delayleft;
0.5 => g_granulator_delayright;
0.5 => g_granulator_feedback;
0.5 => g_granulator_delaymix;
0.5 => g_granulator_reverbmix;
0.5 => g_granulator_mastervol;

OscIn oin;
OscMsg msg;
8000 => oin.port;
oin.listenAll();   // catch every address; we dispatch on the path ourselves

<<< "[osc-router] listening on port", oin.port() >>>;

// Split an OSC address into its non-empty path segments.
// "/param/synth/pitch" -> ["param","synth","pitch"]
fun string[] segments( string addr )
{
    string out[0];
    addr => string rest;
    while( rest.length() > 0 )
    {
        rest.find( "/" ) => int i;
        if( i < 0 ) { out << rest; break; }   // last segment
        if( i > 0 ) out << rest.substring( 0, i );
        rest.substring( i + 1 ) => rest;
    }
    return out;
}

while( true )
{
    oin => now;
    while( oin.recv( msg ) )
    {
        segments( msg.address ) @=> string seg[];

        // /trigger/<name> — a bang (no args). A momentary event, handled before
        // the /param guard. Signal the matching module's wait-event.
        if( seg.size() >= 2 && seg[0] == "trigger" )
        {
            if( seg[1] == "burst" ) g_burst_fire.broadcast();
            continue;
        }

        // /gate/<name> — a held 0/1 state (button down/up or MIDI note on/off),
        // carrying one float. Handled before the /param guard.
        if( seg.size() >= 2 && seg[0] == "gate" && msg.numArgs() >= 1 )
        {
            if( seg[1] == "collect" ) msg.getFloat(0) => g_collect_gate;
            continue;
        }

        // /param/<module>/<param> carrying one float
        if( seg.size() < 3 || seg[0] != "param" || msg.numArgs() < 1 ) continue;

        seg[1] => string module;
        seg[2] => string param;
        msg.getFloat(0) => float v;

        if( module == "theremin" )
        {
            if( param == "pitch" )  v => g_theremin_pitch;
            else if( param == "volume" ) v => g_theremin_volume;
        }
        else if( module == "synth" )
        {
            if( param == "pitch" )  v => g_synth_pitch;
            else if( param == "cutoff" ) v => g_synth_cutoff;
        }
        else if( module == "input" )
        {
            if(      param == "volume" )  v => g_input_volume;
            else if( param == "source" )  v => g_input_source;
        }
        else if( module == "granulator" )
        {
            if(      param == "grainsize" )  v => g_granulator_grainsize;
            else if( param == "density" )    v => g_granulator_density;
            else if( param == "position" )   v => g_granulator_position;
            else if( param == "posspray" )   v => g_granulator_posspray;
            else if( param == "panspray" )   v => g_granulator_panspray;
            else if( param == "octaveup" )   v => g_granulator_octaveup;
            else if( param == "octavedown" ) v => g_granulator_octavedown;
            else if( param == "pitchrange" ) v => g_granulator_pitchrange;
            else if( param == "pitchprob" )  v => g_granulator_pitchprob;
            else if( param == "finerange" )  v => g_granulator_finerange;
            else if( param == "fineprob" )   v => g_granulator_fineprob;
            else if( param == "thresh" )     v => g_granulator_thresh;
            else if( param == "attack" )     v => g_granulator_attack;
            else if( param == "release" )    v => g_granulator_release;
            else if( param == "delayleft" )  v => g_granulator_delayleft;
            else if( param == "delayright" ) v => g_granulator_delayright;
            else if( param == "feedback" )   v => g_granulator_feedback;
            else if( param == "delaymix" )   v => g_granulator_delaymix;
            else if( param == "reverbmix" )  v => g_granulator_reverbmix;
            else if( param == "mastervol" )  v => g_granulator_mastervol;
        }
        // else: unknown module/param — ignored
    }
}
