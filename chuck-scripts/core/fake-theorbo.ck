// fake-theorbo.ck — shared audio input bus.
//
// Loops tiorba.wav as a stand-in for a live theorbo/mic, exposed on the global
// Gain g_mic. Modules tap g_mic instead of opening the file themselves, so the
// input source lives in exactly one place. When a real mic is available, replace
// the SndBuf line below with `adc => inGain;` and every module keeps working.
//
// Input level is controlled here (g_theorbo_inputgain, a slider in Python), so
// fx modules don't need their own input gain.

global Gain g_mic;
global float g_theorbo_inputgain;   // 0..1 from Python; 0.5 = unity

// g_mic => dac is the input monitor: you always hear the (gain-controlled)
// theorbo on VM start. Modules also tap g_mic, but only fake-theorbo sends the
// raw input to the output.
SndBuf input => Gain inGain => g_mic => dac;
me.dir() + "/../../chuck-test/samples/tiorba.wav" => input.read;
1 => input.loop;
1.0 => input.rate;

<<< "[fake-theorbo] looping tiorba.wav into g_mic" >>>;

// apply the input level continuously (0..1 -> 0..2 gain, 0.5 = unity)
while( true ) {
    g_theorbo_inputgain * 2.0 => inGain.gain;
    10::ms => now;
}
