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

while( true ) { 1::second => now; }
