// granulator.ck — Pure DSP. Reads all params from globals set by osc-router.ck.
// Python sends each param normalized 0..1 on /param/granulator/<param>; this
// shred maps every 0..1 value into its [MIN, MAX] range. Run via the VM, not
// directly. (Replace SndBuf with adc when real mic is ready.)

SndBuf input => Gain inputGain => dac;
0.5 => inputGain.gain;
me.dir() + "/../../chuck-test/samples/tiorba.wav" => input.read;
1 => input.loop;
1.0 => input.rate;

// dynamics processor — reduces transients before recording into LiSa
// to bypass: replace 'limiter' with 'input' on the LiSa line below
input => Dyno limiter;
limiter.limit();

// circular buffer
// ** bypass limiter: change 'limiter =>' to 'input =>' on the next line **
limiter => LiSa2 grainBuffer => blackhole;
// ping pong delay (before master volume)
DelayL delL, delR;
1.05::second => delL.max;
1.05::second => delR.max;
300::ms => delL.delay;
400::ms => delR.delay;

// cross feedback: left output → right input, right output → left input
Gain xfbL, xfbR;
0.5 => xfbL.gain => xfbR.gain;

// dry/wet gains
Gain dryL, dryR, wetL, wetR;
1.0 => dryL.gain => dryR.gain;
0.0 => wetL.gain => wetR.gain;

// master
NRev reverbL, reverbR;
0.0 => reverbL.mix => reverbR.mix;

Gain masterL, masterR;
1.0 => masterL.gain => masterR.gain;

// dry path
grainBuffer.chan(0) => dryL => reverbL => masterL => dac.left;
grainBuffer.chan(1) => dryR => reverbR => masterR => dac.right;

// wet path: grainBuffer into delays
grainBuffer.chan(0) => delL;
grainBuffer.chan(1) => delR;

// cross feedback wiring
delL => xfbR => delR;
delR => xfbL => delL;

// wet output into reverb
delL => wetL => reverbL;
delR => wetR => reverbR;
4::second => grainBuffer.duration;
1 => grainBuffer.record;

// grain parameters
100::ms => dur grainSize;
10.0 => float density;
0.5 => float position;
0.1 => float posSpray;
0.3 => float panSpray;
300::ms => dur delayTimeL;
400::ms => dur delayTimeR;
0.5 => float delayFeedback;
0.0 => float delayMix;
0.0 => float reverbMix;
0.0 => float octaveUp;
0.0 => float octaveDown;
0.0 => float fineRange;
0.0 => float fineProb;
0.0 => float pitchRange;
0.0 => float pitchProb;

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
0.0     => float INPUT_GAIN_MIN;   1.0      => float INPUT_GAIN_MAX;
0.0     => float PAN_SPRAY_MIN;    0.5      => float PAN_SPRAY_MAX;
50::ms  => dur   DELAY_TIME_MIN;   1000::ms => dur   DELAY_TIME_MAX;
0.0     => float DELAY_FB_MIN;     0.95     => float DELAY_FB_MAX;
0.0     => float DELAY_MIX_MIN;    1.0      => float DELAY_MIX_MAX;
0.0     => float REVERB_MIX_MIN;   1.0      => float REVERB_MIX_MAX;
0.0     => float OCTAVE_UP_MIN;    1.0      => float OCTAVE_UP_MAX;
0.0     => float OCTAVE_DOWN_MIN;  1.0      => float OCTAVE_DOWN_MAX;
0.0     => float FINE_RANGE_MIN;   100.0    => float FINE_RANGE_MAX;
0.0     => float FINE_PROB_MIN;    1.0      => float FINE_PROB_MAX;
0.0     => float PITCH_RANGE_MIN;  12.0     => float PITCH_RANGE_MAX;
0.0     => float PITCH_PROB_MIN;   1.0      => float PITCH_PROB_MAX;

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

fun void setDelayTimeL(dur val) {
    Math.max(val/ms, DELAY_TIME_MIN/ms)::ms => val;
    Math.min(val/ms, DELAY_TIME_MAX/ms)::ms => delayTimeL;
    delayTimeL => delL.delay;
}
fun void setDelayTimeR(dur val) {
    Math.max(val/ms, DELAY_TIME_MIN/ms)::ms => val;
    Math.min(val/ms, DELAY_TIME_MAX/ms)::ms => delayTimeR;
    delayTimeR => delR.delay;
}
fun void setDelayFeedback(float val) {
    Math.max(Math.min(val, DELAY_FB_MAX), DELAY_FB_MIN) => delayFeedback;
    delayFeedback => xfbL.gain => xfbR.gain;
}
fun void setDelayMix(float val) {
    Math.max(Math.min(val, DELAY_MIX_MAX), DELAY_MIX_MIN) => delayMix;
    1.0 - delayMix => dryL.gain => dryR.gain;
    delayMix => wetL.gain => wetR.gain;
}

fun void setReverbMix(float val) {
    Math.max(Math.min(val, REVERB_MIX_MAX), REVERB_MIX_MIN) => reverbMix;
    reverbMix => reverbL.mix => reverbR.mix;
}

fun void setOctaveUp(float val) {
    Math.max(Math.min(val, OCTAVE_UP_MAX), OCTAVE_UP_MIN) => octaveUp;
}
fun void setOctaveDown(float val) {
    Math.max(Math.min(val, OCTAVE_DOWN_MAX), OCTAVE_DOWN_MIN) => octaveDown;
}
fun void setFineRange(float val) {
    Math.max(Math.min(val, FINE_RANGE_MAX), FINE_RANGE_MIN) => fineRange;
}
fun void setFineProb(float val) {
    Math.max(Math.min(val, FINE_PROB_MAX), FINE_PROB_MIN) => fineProb;
}
fun void setPitchRange(float val) {
    Math.max(Math.min(val, PITCH_RANGE_MAX), PITCH_RANGE_MIN) => pitchRange;
}
fun void setPitchProb(float val) {
    Math.max(Math.min(val, PITCH_PROB_MAX), PITCH_PROB_MIN) => pitchProb;
}

fun void setInputGain(float val) {
    Math.max(Math.min(val, INPUT_GAIN_MAX), INPUT_GAIN_MIN) => inputGain.gain;
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

    // linear pan: uniform random within spray range
    Math.random2f(0.5 - panSpray, 0.5 + panSpray) => float panPos;
    Math.max(0.0, Math.min(1.0, panPos)) => panPos;
    grainBuffer.pan(v, panPos);

    // pitch: accumulate semitones from all pitch parameters
    0.0 => float totalSemitones;
    // octave up (more params will be added here)
    0 => int octave;
    if( Math.random2f(0.0, 1.0) < octaveUp )        1 => octave;
    else if( Math.random2f(0.0, 1.0) < octaveDown ) -1 => octave;
    octave * 12.0 +=> totalSemitones;
    // pitch spray (semitones)
    if( Math.random2f(0.0, 1.0) < pitchProb )
        Math.random2f(-pitchRange, pitchRange) +=> totalSemitones;
    // fine detune (cents → semitones: *0.01)
    if( Math.random2f(0.0, 1.0) < fineProb )
        Math.random2f(-fineRange, fineRange) * 0.01 +=> totalSemitones;
    Math.pow(2.0, totalSemitones / 12.0) => float grainRate;
    grainBuffer.rate(v, grainRate);
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

// ===== OSC PARAMETER CONTROL =====
// osc-router.ck writes each param's normalized 0..1 value into these globals.
// We poll them and map 0..1 -> [MIN, MAX], feeding the bounded setters (which
// re-clamp). 0 -> param minimum, 1 -> maximum — same contract as theremin.
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
global float g_granulator_inputgain;
global float g_granulator_mastervol;

// map a normalized 0..1 into a float range
fun float mapF(float g, float lo, float hi) { return lo + g * (hi - lo); }
// map a normalized 0..1 into a duration range (work in ms, return dur)
fun dur mapD(float g, dur lo, dur hi) {
    return (lo/ms + g * (hi/ms - lo/ms))::ms;
}

fun void oscControl() {
    while( true ) {
        // grain
        setGrainSize( mapD(g_granulator_grainsize, GRAIN_SIZE_MIN, GRAIN_SIZE_MAX) );
        setDensity(   mapF(g_granulator_density,   DENSITY_MIN,    DENSITY_MAX) );
        setPosition(  mapF(g_granulator_position,  POSITION_MIN,   POSITION_MAX) );
        setPosSpray(  mapF(g_granulator_posspray,  POS_SPRAY_MIN,  POS_SPRAY_MAX) );
        setPanSpray(  mapF(g_granulator_panspray,  PAN_SPRAY_MIN,  PAN_SPRAY_MAX) );
        // pitch
        setOctaveUp(   mapF(g_granulator_octaveup,   OCTAVE_UP_MIN,   OCTAVE_UP_MAX) );
        setOctaveDown( mapF(g_granulator_octavedown, OCTAVE_DOWN_MIN, OCTAVE_DOWN_MAX) );
        setPitchRange( mapF(g_granulator_pitchrange, PITCH_RANGE_MIN, PITCH_RANGE_MAX) );
        setPitchProb(  mapF(g_granulator_pitchprob,  PITCH_PROB_MIN,  PITCH_PROB_MAX) );
        setFineRange(  mapF(g_granulator_finerange,  FINE_RANGE_MIN,  FINE_RANGE_MAX) );
        setFineProb(   mapF(g_granulator_fineprob,   FINE_PROB_MIN,   FINE_PROB_MAX) );
        // limiter
        setDynoThresh(  mapF(g_granulator_thresh,  DYNO_THRESH_MIN,  DYNO_THRESH_MAX) );
        setDynoAttack(  mapD(g_granulator_attack,  DYNO_ATTACK_MIN,  DYNO_ATTACK_MAX) );
        setDynoRelease( mapD(g_granulator_release, DYNO_RELEASE_MIN, DYNO_RELEASE_MAX) );
        // delay
        setDelayTimeL(   mapD(g_granulator_delayleft,  DELAY_TIME_MIN, DELAY_TIME_MAX) );
        setDelayTimeR(   mapD(g_granulator_delayright, DELAY_TIME_MIN, DELAY_TIME_MAX) );
        setDelayFeedback( mapF(g_granulator_feedback,  DELAY_FB_MIN,   DELAY_FB_MAX) );
        setDelayMix(      mapF(g_granulator_delaymix,  DELAY_MIX_MIN,  DELAY_MIX_MAX) );
        // reverb
        setReverbMix( mapF(g_granulator_reverbmix, REVERB_MIX_MIN, REVERB_MIX_MAX) );
        // output
        setInputGain( mapF(g_granulator_inputgain, INPUT_GAIN_MIN, INPUT_GAIN_MAX) );
        setMasterVol( mapF(g_granulator_mastervol, MASTER_VOL_MIN, MASTER_VOL_MAX) );

        10::ms => now;
    }
}

spork ~ oscControl();

while( true ) { 1::second => now; }
