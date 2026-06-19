// modalbar-trigger-test.ck
// SPACE = strike a ModalBar (random pitch).  Number keys 0-8 = select preset.
// select param: h=stickHardness p=strikePosition v=velocity d=damp
//               f=vibratoFreq g=vibratoGain r=ratioSpray (preset->inharmonic)
// LEFT/RIGHT arrows = adjust the selected param.
// Per-shred voice model: each strike spawns its own ModalBar that rings out
// and is destroyed when the shred ends -- polyphony scales with note count.
// Uses KBHit (terminal stdin) -- no /dev/input permissions needed.

// --- keyboard input ---
KBHit kb;
kb.on();

// --- mix bus (voices patch into here) ---
Gain mix => dac;
0.5 => mix.gain;

// --- current voice settings (each new strike reads these at birth) ---
0 => int curPreset;             // 0 = Marimba
0.4 => float curStickHardness;  // soft-ish mallet
0.5 => float curStrikePosition; // hit the middle
0.8 => float curVelocity;       // how hard the strike
0.5 => float curDamp;           // damping (more = shorter ring)
6.0 => float curVibratoFreq;    // vibrato rate (Hz)
0.0 => float curVibratoGain;    // vibrato depth (off by default)
0.0 => float curRatioSpray;     // per-mode ratio perturbation (0 = pure preset)

// parameter bounds
0.0     => float STICK_HARDNESS_MIN;   1.0     => float STICK_HARDNESS_MAX;
0.0     => float STRIKE_POSITION_MIN;  1.0     => float STRIKE_POSITION_MAX;
0.3     => float VELOCITY_MIN;         1.0     => float VELOCITY_MAX;  // floor: always audible
0.0     => float DAMP_MIN;             1.0     => float DAMP_MAX;
0.0     => float VIBRATO_FREQ_MIN;     12.0    => float VIBRATO_FREQ_MAX;  // Hz
0.0     => float VIBRATO_GAIN_MIN;     1.0     => float VIBRATO_GAIN_MAX;
0.0     => float RATIO_SPRAY_MIN;      1.0     => float RATIO_SPRAY_MAX;

// preset names (index = preset number)
["Marimba","Vibraphone","Agogo","Wood1","Reso","Wood2","Beats","Two Fixed","Clump"] @=> string presetNames[];

// ModalBar has 4 resonant modes; we perturb their ratios for timbral variety
4 => int NMODES;

// which param the arrows control
"h" => string selected;    // h = stickHardness

// SPACE = ASCII 32 ; number keys '0'..'8' = ASCII 48..56 ; 'h' = 104
32 => int SPACE;

fun void printMenu()
{
    chout <= "\rpreset " <= curPreset <= " (" <= presetNames[curPreset] <= ")"
          <= "  |  h:hard=" <= (curStickHardness*100)$int
          <= "  p:pos=" <= (curStrikePosition*100)$int
          <= "  v:vel=" <= (curVelocity*100)$int
          <= "  d:damp=" <= (curDamp*100)$int
          <= "  f:vibF=" <= (curVibratoFreq$int) <= "Hz"
          <= "  g:vibG=" <= (curVibratoGain*100)$int
          <= "  r:ratio=" <= (curRatioSpray*100)$int
          <= "  [" <= selected <= "]"
          <= "  |  SPACE=strike  0-8=preset  LEFT/RIGHT=adjust       ";
    chout.flush();
}

// nudge the currently selected param by one step in direction dir (+1 / -1).
// each param has its own step size; result is clamped to its bounds.
fun void adjust( float dir )
{
    if( selected == "h" )
        Math.max( Math.min( curStickHardness + dir*0.05, STICK_HARDNESS_MAX ), STICK_HARDNESS_MIN ) => curStickHardness;
    if( selected == "p" )
        Math.max( Math.min( curStrikePosition + dir*0.05, STRIKE_POSITION_MAX ), STRIKE_POSITION_MIN ) => curStrikePosition;
    if( selected == "v" )
        Math.max( Math.min( curVelocity + dir*0.05, VELOCITY_MAX ), VELOCITY_MIN ) => curVelocity;
    if( selected == "d" )
        Math.max( Math.min( curDamp + dir*0.05, DAMP_MAX ), DAMP_MIN ) => curDamp;
    if( selected == "vf" )
        Math.max( Math.min( curVibratoFreq + dir*1.0, VIBRATO_FREQ_MAX ), VIBRATO_FREQ_MIN ) => curVibratoFreq;
    if( selected == "vg" )
        Math.max( Math.min( curVibratoGain + dir*0.05, VIBRATO_GAIN_MAX ), VIBRATO_GAIN_MIN ) => curVibratoGain;
    if( selected == "r" )
        Math.max( Math.min( curRatioSpray + dir*0.05, RATIO_SPRAY_MAX ), RATIO_SPRAY_MIN ) => curRatioSpray;
    printMenu();
}

printMenu();

while( true )
{
    kb => now;                  // wait for a key event
    while( kb.more() )
    {
        kb.getchar() => int key;

        // SPACE -> spawn a voice at a random pitch, snapshotting current settings
        if( key == SPACE )
            spork ~ strikeModalBar( Math.random2f( 200.0, 800.0 ), curPreset,
                                    curStickHardness, curStrikePosition, curVelocity,
                                    curDamp, curVibratoFreq, curVibratoGain, curRatioSpray );

        // number keys 0-8 -> select preset
        if( key >= 48 && key <= 56 )
        {
            key - 48 => curPreset;
            printMenu();
        }

        // select param: h=stickHardness p=strikePosition v=velocity
        //               d=damp f=vibratoFreq g=vibratoGain
        if( key == 104 ) { "h"  => selected; printMenu(); }
        if( key == 112 ) { "p"  => selected; printMenu(); }
        if( key == 118 ) { "v"  => selected; printMenu(); }
        if( key == 100 ) { "d"  => selected; printMenu(); }
        if( key == 102 ) { "vf" => selected; printMenu(); }
        if( key == 103 ) { "vg" => selected; printMenu(); }
        if( key == 114 ) { "r"  => selected; printMenu(); }  // r = ratio spray

        // arrow keys arrive as escape sequence: 27 '[' (91) then 67=right / 68=left
        if( key == 27 && kb.more() )
        {
            kb.getchar() => int k2;
            if( k2 == 91 && kb.more() )
            {
                kb.getchar() => int k3;
                if( k3 == 67 ) adjust(  1.0 );  // right = increase
                if( k3 == 68 ) adjust( -1.0 );  // left  = decrease
            }
        }
    }
}

// one voice: build a ModalBar from the given properties, strike it, ring out,
// then the shred ends and the local bar is disconnected + reclaimed automatically
fun void strikeModalBar( float freq, int preset, float stickHardness,
                         float strikePosition, float velocity,
                         float damp, float vibratoFreq, float vibratoGain,
                         float ratioSpray )
{
    ModalBar bar => mix;
    preset => bar.preset;            // set preset first; the rest override it
    stickHardness => bar.stickHardness;
    strikePosition => bar.strikePosition;
    damp => bar.damp;
    vibratoFreq => bar.vibratoFreq;
    vibratoGain => bar.vibratoGain;

    // perturb each mode's ratio away from the preset:
    // 0 = pure preset (tonal) -> higher = detuned / inharmonic (bell, metallic)
    if( ratioSpray > 0.0 )
        for( 0 => int m; m < NMODES; m++ )
        {
            m => bar.mode;                  // select mode m
            bar.modeRatio() => float r;     // its preset ratio
            Math.max( 0.05, r * (1.0 + Math.random2f( -ratioSpray, ratioSpray )) ) => bar.modeRatio;
        }

    freq => bar.freq;

    velocity => bar.noteOn;  // velocity 0-1

    // hold the shred exactly as long as the bar is still ringing -- adapts to
    // any preset/decay, so we never clip the tail and never over-hold a dead voice
    0.0008  => float SILENCE;     // level below which we call it silent (~ -62 dB)
    10::second => dur MAX_RING;   // safety ceiling for a non-decaying resonance
    now => time start;

    30::ms => now;                // let the attack develop before we start watching
    while( now - start < MAX_RING )
    {
        if( peakOver( bar, 256 ) < SILENCE ) break;  // measure a short window
        20::ms => now;
    }
}

// peak absolute output of a ugen over the next nSamps samples
fun float peakOver( UGen u, int nSamps )
{
    0.0 => float peak;
    for( 0 => int i; i < nSamps; i++ )
    {
        Math.fabs( u.last() ) => float a;
        if( a > peak ) a => peak;
        1::samp => now;
    }
    return peak;
}
