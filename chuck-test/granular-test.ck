// granular-test.ck
// Fake mic input: loops a WAV file continuously
// Replace SndBuf with adc when real mic is ready

SndBuf input => dac;
me.dir() + "/samples/tiorba.wav" => input.read;
1 => input.loop;
1.0 => input.rate;

// circular buffer
input => LiSa grainBuffer => blackhole;
grainBuffer => dac;
4::second => grainBuffer.duration;
1 => grainBuffer.record;

// grain parameters
100::ms => dur grainSize;
10.0 => float density;
0.5 => float position;
0.1 => float posSpray;

// parameter bounds
10::ms  => dur   GRAIN_SIZE_MIN;  500::ms => dur   GRAIN_SIZE_MAX;
5.0     => float DENSITY_MIN;     50.0    => float DENSITY_MAX;
0.0     => float POSITION_MIN;    1.0     => float POSITION_MAX;
0.0     => float POS_SPRAY_MIN;   0.5     => float POS_SPRAY_MAX;

// setters — any UI layer should use these to enforce bounds
fun void setGrainSize(dur val) {
    Math.max(val/ms, GRAIN_SIZE_MIN/ms)::ms => val;
    Math.min(val/ms, GRAIN_SIZE_MAX/ms)::ms => grainSize;
}
fun void setDensity(float val) {
    Math.max(Math.min(val, DENSITY_MAX), DENSITY_MIN) => density;
}
fun void setPosition(float val) {
    Math.max(Math.min(val, POSITION_MAX), POSITION_MIN) => position;
}
fun void setPosSpray(float val) {
    Math.max(Math.min(val, POS_SPRAY_MAX), POS_SPRAY_MIN) => posSpray;
}

// grain function
fun void grain() {
    grainBuffer.getVoice() => int v;
    if( v == -1 ) return; // no voice available

    // position with spray
    position + Math.random2f(-posSpray, posSpray) => float pos;
    if( pos < 0.0 ) 0.0 => pos;
    if( pos > 1.0 ) 1.0 => pos;

    grainBuffer.rate(v, 1.0);
    grainBuffer.playPos(v, pos * grainBuffer.duration());
    grainBuffer.play(v, 1);

    // manual Hanning envelope
    1::ms => dur stepSize;
    (grainSize / stepSize) $ int => int steps;
    for( 0 => int i; i < steps; i++ ) {
        0.5 * (1.0 - Math.cos(2.0 * Math.PI * i / steps)) => float amp;
        grainBuffer.voiceGain(v, amp);
        stepSize => now;
    }

    grainBuffer.play(v, 0);
}

// grain spawner
fun void spawner() {
    while( true ) {
        // Poisson inter-onset time
        (-Math.log(Math.random2f(0.0001, 1.0)) / density)::second => now;
        spork ~ grain();
    }
}

spork ~ spawner();

// keyboard control
// g = grainSize, d = density, p = position, s = posSpray
// + / - to increase / decrease selected parameter
"g" => string selected;

fun void printControls() {
    chout <= "\r  g:" + (grainSize/ms) + "ms d:" + density + " p:" + position + " s:" + posSpray + " [" + selected + "]       ";
    chout.flush();
}

fun void keyboard() {
    KBHit kb;
    kb.on();
    <<< "controls: g=grainSize d=density p=position s=posSpray  +/- to change" >>>;
    printControls();

    while( true ) {
        kb => now;
        while( kb.more() ) {
            kb.getchar() => int key;

            // quit
            if( key == 113 ) { <<< "\nbye!" >>>; Machine.removeAllShreds(); }

            // select parameter
            if( key == 103 ) { "g" => selected; printControls(); }
            if( key == 100 ) { "d" => selected; printControls(); }
            if( key == 112 ) { "p" => selected; printControls(); }
            if( key == 115 ) { "s" => selected; printControls(); }

            // increase
            if( key == 43 ) {
                if( selected == "g" ) { setGrainSize(grainSize + 10::ms); }
                if( selected == "d" ) { setDensity(density + 1.0); }
                if( selected == "p" ) { setPosition(position + 0.05); }
                if( selected == "s" ) { setPosSpray(posSpray + 0.05); }
                printControls();
            }

            // decrease
            if( key == 45 ) {
                if( selected == "g" ) { setGrainSize(grainSize - 10::ms); }
                if( selected == "d" ) { setDensity(density - 1.0); }
                if( selected == "p" ) { setPosition(position - 0.05); }
                if( selected == "s" ) { setPosSpray(posSpray - 0.05); }
                printControls();
            }
        }
    }
}

spork ~ keyboard();

while( true ) { 1::second => now; }
