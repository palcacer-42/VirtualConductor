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

while( true ) { 1::second => now; }
