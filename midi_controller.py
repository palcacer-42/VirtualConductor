import os
import time

# Backend selection logic must run BEFORE mido import
try:
    import rtmidi
except ImportError:
    print("rtmidi not found. Falling back to pygame.")
    os.environ['MIDO_BACKEND'] = 'mido.backends.pygame'
    import pygame
    import pygame.midi
    pygame.init()
    pygame.midi.init()

import mido

class MidiController:
    """
    Handles MIDI communication for the Holistic Tracker.
    """
    def __init__(self, port_name=None):
        """
        Initialize MIDI output.
        If port_name is None, it tries to open the first available output.
        """
        self.output = None
        try:
            # List available ports
            ports = mido.get_output_names()
            print(f"Available MIDI Ports: {ports}")
            
            # Priority Logic: Look for "IAC" or "Driver"
            target_port = None
            
            if port_name and port_name in ports:
                target_port = port_name
            else:
                for p in ports:
                    if "IAC" in p or "Driver" in p:
                        target_port = p
                        break
                
                # Fallback to first available if priority not found
                if not target_port and ports:
                    target_port = ports[0]

            if target_port:
                print(f"Opening MIDI port: {target_port}")
                self.output = mido.open_output(target_port)
            else:
                print("No MIDI ports found. MIDI functionalities will be disabled.")
                print("Please enable IAC Driver in 'Audio MIDI Setup' on macOS.")
                
        except Exception as e:
            print(f"Failed to initialize MIDI: {e}")

    def send_control_change(self, channel, controller, value):
        """
        Send a Control Change (CC) message.
        value should be normalized 0.0 - 1.0
        """
        if not self.output:
            return

        # Clamp and scale value to 0-127
        midi_val = max(0, min(127, int(value * 127)))
        
        msg = mido.Message('control_change', channel=channel, control=controller, value=midi_val)
        self.output.send(msg)
        
    def send_note(self, channel, note, velocity):
        """
        Send a Note On message.
        """
        if not self.output:
            return
            
        msg = mido.Message('note_on', channel=channel, note=note, velocity=velocity)
        self.output.send(msg)

    def close(self):
        if self.output:
            self.output.close()
