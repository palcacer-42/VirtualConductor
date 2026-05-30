// osc-router.ck — Routes landmark inputs to effect parameters.
// Routing is read from chuck-scripts/config/<module>.cfg, one "param : landmark"
// per line. Falls back to built-in defaults if a file or entry is missing.
// The landmark name->value table lives in landmarks.ck (loaded before this file).

// --- Effect parameter globals ---
global float g_theremin_pitch;
global float g_theremin_volume;
global float g_synth_pitch;
global float g_synth_cutoff;

// Config files live one level up from core/.
me.dir() + "../config/" => string cfgDir;

// Reads <param>'s landmark from the .cfg at <path>; returns <fallback> if the
// file is missing or has no entry for <param>. Surrounding spaces are ignored.
fun string route(string path, string param, string fallback) {
    FileIO fio;
    fio.open(path, FileIO.READ);
    if (!fio.good()) {
        <<< "[osc-router] no config at", path, "- default", param, "<-", fallback >>>;
        return fallback;
    }

    fallback => string result;
    while (!fio.eof()) {
        fio.readLine() => string line;
        line.find(":") => int sep;
        if (sep < 0) continue;                         // blank/comment/garbage line
        line.substring(0, sep).trim() => string key;   // left of ':'  -> param
        line.substring(sep + 1).trim() => string val;  // right of ':' -> landmark
        if (key == param) {
            val => result;
            break;
        }
    }
    fio.close();
    return result;
}

// --- Resolve routing once at startup ---
route(cfgDir + "theremin.cfg", "pitch",  "hand_right_index_y") => string thereminPitch;
route(cfgDir + "theremin.cfg", "volume", "hand_left_index_y")  => string thereminVolume;
route(cfgDir + "synth.cfg",    "pitch",  "hand_right_index_y") => string synthPitch;
route(cfgDir + "synth.cfg",    "cutoff", "hand_left_index_y")  => string synthCutoff;

<<< "[osc-router] theremin:  pitch <-", thereminPitch, " volume <-", thereminVolume >>>;
<<< "[osc-router] synth:     pitch <-", synthPitch, " cutoff <-", synthCutoff >>>;

// --- Drive params from their routed landmarks ---
fun void updateRouting() {
    while(true) {
        Landmarks.value(thereminPitch)  => g_theremin_pitch;
        Landmarks.value(thereminVolume) => g_theremin_volume;
        Landmarks.value(synthPitch)     => g_synth_pitch;
        Landmarks.value(synthCutoff)    => g_synth_cutoff;
        1::ms => now;
    }
}
spork ~ updateRouting();

while(true) { 1::second => now; }
