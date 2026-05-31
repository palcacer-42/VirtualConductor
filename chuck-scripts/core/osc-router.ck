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

0.5 => g_theremin_pitch;
0.5 => g_theremin_volume;
0.5 => g_synth_pitch;
0.5 => g_synth_cutoff;

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
        // /param/<module>/<param> carrying one float
        segments( msg.address ) @=> string seg[];
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
        // else: unknown module/param — ignored
    }
}
