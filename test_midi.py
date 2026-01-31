from midi_controller import MidiController
import time

def test_midi():
    print("Initializing MIDI Controller...")
    midi = MidiController()
    
    if midi.output:
        print(f"Sending test messages to {midi.output.name if hasattr(midi.output, 'name') else 'output'}...")
        for i in range(10):
            val = i / 10.0
            print(f"Sending CC 1 value: {val}")
            midi.send_control_change(0, 1, val)
            time.sleep(0.1)
        print("Test complete.")
        midi.close()
    else:
        print("MIDI Test Failed: No output port opened.")

if __name__ == "__main__":
    test_midi()
