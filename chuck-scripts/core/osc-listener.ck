// osc-listener.ck — receives OSC from Python and stores values by source name.
// Infrastructure only: no routing or DSP logic here.
//
// Address namespace (category = first path segment):
//   /landmarks/<type>/<side>/<finger>   f f f   e.g. /landmarks/hand/right/index
//   /slider/<module>/<name>             f       e.g. /slider/theremin/vibrato
//   /trigger/<name>                     (future, discrete — not handled here yet)
//
// Values land in the Landmarks store (landmarks.ck, loaded first):
//   landmarks -> key "<side>_<finger>_<axis>"   (e.g. right_index_y)
//   sliders   -> key "<module>.<name>"          (e.g. theremin.vibrato)
//
// One loop handles every source via OscIn.listenAll(); adding a finger, a
// slider, or a whole module needs no new code unless it's a new *category*.

OscIn oin;
OscMsg msg;
8000 => oin.port;
oin.listenAll();   // catch every address; we dispatch on the path ourselves

<<< "[osc-listener] listening on port", oin.port() >>>;

// Split an OSC address into its non-empty path segments.
// "/landmarks/hand/right/index" -> ["landmarks","hand","right","index"]
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
        if( seg.size() < 1 ) continue;

        if( seg[0] == "landmarks" )
        {
            // Key is prefixed with the landmark type (hand_, pose_, face_).
            if( seg.size() < 2 ) continue;
            seg[1] => string type;   // hand | pose | face

            if( type == "hand" )
            {
                // /landmarks/hand/<side>/<finger> (x y z) -> hand_<side>_<finger>_<axis>
                if( seg.size() < 4 || msg.numArgs() < 3 ) continue;
                "hand_" + seg[2] + "_" + seg[3] => string base;
                Landmarks.set( base + "_x", msg.getFloat(0) );
                Landmarks.set( base + "_y", msg.getFloat(1) );
                Landmarks.set( base + "_z", msg.getFloat(2) );
            }
            // future: /landmarks/pose/<name> -> pose_<name>_<axis>
            //         /landmarks/face/<name> -> face_<name>_<axis>
        }
        else if( seg[0] == "slider" )
        {
            // /slider/<module>/<name> carrying one float
            if( seg.size() < 3 || msg.numArgs() < 1 ) continue;
            seg[1] + "." + seg[2] => string key;     // "<module>.<name>"
            Landmarks.set( key, msg.getFloat(0) );
        }
        // else: unknown / future category (e.g. /trigger/...) — ignored for now
    }
}
