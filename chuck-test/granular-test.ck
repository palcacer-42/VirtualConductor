// granular-test.ck
// Fake mic input: loops a WAV file continuously
// Replace SndBuf with adc when real mic is ready

SndBuf input => dac;
me.dir() + "/samples/tiorba.wav" => input.read;
1 => input.loop;
1.0 => input.rate;

// circular buffer
input => LiSa grainBuffer => blackhole;
4::second => grainBuffer.duration;
1 => grainBuffer.record;

// grain parameters
100::ms => dur grainSize;
10.0 => float density;
0.5 => float position;
0.1 => float posSpray;

// grain spawner
fun void spawner() {
    while( true ) {
        // Poisson inter-onset time
        (-Math.log(Math.random2f(0.0001, 1.0)) / density)::second => now;
        <<< "grain fired at", now >>>;
    }
}

spork ~ spawner();

while( true ) { 1::second => now; }
