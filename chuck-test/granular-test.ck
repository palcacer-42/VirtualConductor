// granular-test.ck
// Fake mic input: loops a WAV file continuously
// Replace SndBuf with adc when real mic is ready

SndBuf input => blackhole;
me.dir() + "/samples/tiorba.wav" => input.read;
1 => input.loop;
1.0 => input.rate;

// dynamics processor — reduces transients before recording into LiSa
// to bypass: replace 'limiter' with 'input' on the LiSa line below
input => Dyno limiter;
limiter.limit();

// circular buffer
// ** bypass limiter: change 'limiter =>' to 'input =>' on the next line **
limiter => LiSa2 grainBuffer => blackhole;
Gain masterL; Gain masterR;
grainBuffer.chan(0) => masterL => dac.left;
grainBuffer.chan(1) => masterR => dac.right;
1.0 => masterL.gain => masterR.gain;
4::second => grainBuffer.duration;
1 => grainBuffer.record;

// grain parameters
100::ms => dur grainSize;
10.0 => float density;
0.5 => float position;
0.1 => float posSpray;
0.3 => float panSpray;

// limiter parameters
5::ms   => dur   limiterAttack;
300::ms => dur   limiterRelease;
0.5     => float limiterThresh;

// parameter bounds
10::ms  => dur   GRAIN_SIZE_MIN;  500::ms => dur   GRAIN_SIZE_MAX;
5.0     => float DENSITY_MIN;     50.0    => float DENSITY_MAX;
0.0     => float POSITION_MIN;    1.0     => float POSITION_MAX;
0.0     => float POS_SPRAY_MIN;   0.5     => float POS_SPRAY_MAX;
1::ms   => dur   DYNO_ATTACK_MIN;  50::ms   => dur   DYNO_ATTACK_MAX;
50::ms  => dur   DYNO_RELEASE_MIN; 1000::ms => dur   DYNO_RELEASE_MAX;
0.1     => float DYNO_THRESH_MIN;  1.0      => float DYNO_THRESH_MAX;
0.0     => float MASTER_VOL_MIN;   2.0      => float MASTER_VOL_MAX;
0.0     => float PAN_SPRAY_MIN;    0.5      => float PAN_SPRAY_MAX;

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
fun void setDynoAttack(dur val) {
    Math.max(val/ms, DYNO_ATTACK_MIN/ms)::ms => val;
    Math.min(val/ms, DYNO_ATTACK_MAX/ms)::ms => limiterAttack;
    limiterAttack => limiter.attackTime;
}
fun void setDynoRelease(dur val) {
    Math.max(val/ms, DYNO_RELEASE_MIN/ms)::ms => val;
    Math.min(val/ms, DYNO_RELEASE_MAX/ms)::ms => limiterRelease;
    limiterRelease => limiter.releaseTime;
}
fun void setPanSpray(float val) {
    Math.max(Math.min(val, PAN_SPRAY_MAX), PAN_SPRAY_MIN) => panSpray;
}

fun void setMasterVol(float val) {
    Math.max(Math.min(val, MASTER_VOL_MAX), MASTER_VOL_MIN) => masterL.gain => masterR.gain;
}

fun void setDynoThresh(float val) {
    Math.max(Math.min(val, DYNO_THRESH_MAX), DYNO_THRESH_MIN) => limiterThresh;
    limiterThresh => limiter.thresh;
}

// grain function
fun void grain() {
    grainBuffer.getVoice() => int v;
    if( v == -1 ) return; // no voice available

    // position with spray
    position + Math.random2f(-posSpray, posSpray) => float pos;
    if( pos < 0.0 ) 0.0 => pos;
    if( pos > 1.0 ) 1.0 => pos;

    // Gaussian pan (sum of 3 uniforms ≈ bell curve), centered at 0.5
    (Math.random2f(-1.0, 1.0) + Math.random2f(-1.0, 1.0) + Math.random2f(-1.0, 1.0)) / 3.0 => float panPos;
    Math.max(0.0, Math.min(1.0, 0.5 + panPos * panSpray)) => panPos;
    grainBuffer.pan(v, panPos);

    grainBuffer.rate(v, 1.0);
    grainBuffer.playPos(v, pos * grainBuffer.duration());
    grainBuffer.voiceGain(v, 0.0); // bug1 fix: start silent before play
    grainBuffer.play(v, 1);

    // manual Hanning envelope — fine steps to avoid staircase zipper noise
    grainSize / 256 => dur stepSize;
    if( stepSize < 0.25::ms ) 0.25::ms => stepSize;
    (grainSize / stepSize) $ int => int steps;
    for( 0 => int i; i < steps; i++ ) {
        0.5 * (1.0 - Math.cos(2.0 * Math.PI * i / steps)) => float amp;
        grainBuffer.voiceGain(v, amp);
        stepSize => now;
    }

    grainBuffer.voiceGain(v, 0.0); // ensure silent before stopping
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
// t = limiter thresh, a = limiter attack, r = limiter release
// w = pan spray, v = master volume
// + / - to increase / decrease selected parameter
"g" => string selected;

fun void printControls() {
    chout <= "\r  g:" + (grainSize/ms) + "ms d:" + density + " p:" + position + " s:" + posSpray + " w:" + panSpray + " | t:" + limiterThresh + " a:" + (limiterAttack/ms) + "ms r:" + (limiterRelease/ms) + "ms | v:" + masterL.gain() + " [" + selected + "]       ";
    chout.flush();
}

fun void keyboard() {
    KBHit kb;
    kb.on();
    <<< "controls: g=grainSize d=density p=position s=posSpray t=limiterThresh a=limiterAttack r=limiterRelease v=masterVol  +/- to change" >>>;
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
            if( key == 116 ) { "t" => selected; printControls(); }
            if( key == 97  ) { "a" => selected; printControls(); }
            if( key == 114 ) { "r" => selected; printControls(); }
            if( key == 119 ) { "w" => selected; printControls(); } // w
            if( key == 118 ) { "v" => selected; printControls(); } // v

            // increase
            if( key == 43 ) {
                if( selected == "g" ) { setGrainSize(grainSize + 10::ms); }
                if( selected == "d" ) { setDensity(density + 1.0); }
                if( selected == "p" ) { setPosition(position + 0.05); }
                if( selected == "s" ) { setPosSpray(posSpray + 0.05); }
                if( selected == "t" ) { setDynoThresh(limiterThresh + 0.05); }
                if( selected == "a" ) { setDynoAttack(limiterAttack + 5::ms); }
                if( selected == "r" ) { setDynoRelease(limiterRelease + 50::ms); }
                if( selected == "w" ) { setPanSpray(panSpray + 0.05); }
                if( selected == "v" ) { setMasterVol(masterL.gain() + 0.05); }
                printControls();
            }

            // decrease
            if( key == 45 ) {
                if( selected == "g" ) { setGrainSize(grainSize - 10::ms); }
                if( selected == "d" ) { setDensity(density - 1.0); }
                if( selected == "p" ) { setPosition(position - 0.05); }
                if( selected == "s" ) { setPosSpray(posSpray - 0.05); }
                if( selected == "t" ) { setDynoThresh(limiterThresh - 0.05); }
                if( selected == "a" ) { setDynoAttack(limiterAttack - 5::ms); }
                if( selected == "r" ) { setDynoRelease(limiterRelease - 50::ms); }
                if( selected == "w" ) { setPanSpray(panSpray - 0.05); }
                if( selected == "v" ) { setMasterVol(masterL.gain() - 0.05); }
                printControls();
            }
        }
    }
}

spork ~ keyboard();

while( true ) { 1::second => now; }
