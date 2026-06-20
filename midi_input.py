"""
midi_input.py — Listen to a connected MIDI input device.

Infrastructure only for now: enumerate the input ports that are plugged in,
open the selected one, and surface incoming messages two ways — a text log for
the GUI monitor, and an optional `on_message` hook where the future routing
(ChucK triggers / params) will plug in. Built on mido + the python-rtmidi
backend, so it works on macOS (CoreMIDI), Windows (WinMM) and Linux (ALSA).
"""

from collections import deque

import mido

# Sentinel dropdown entry meaning "listen to nothing".
NONE_PORT = "None"


class MidiListener:
    """Owns at most one open MIDI input today, but keys its open ports by name so
    a future multi-device setup drops in without reshaping this class."""

    def __init__(self, log_maxlen=200):
        # name -> open mido input port. Single entry for now; a dict so listening
        # to several devices later needs no redesign.
        self._ports = {}
        self.selected = NONE_PORT
        # Incoming messages as display strings for the GUI monitor. A deque so it
        # self-trims; the GUI snapshots it with list() before iterating, because
        # the mido callback appends from a background thread.
        self.log = deque(maxlen=log_maxlen)
        # Optional hook called with each mido.Message. The future trigger/param
        # mapping plugs in here; None today (nothing consumes the messages yet).
        self.on_message = None

    @staticmethod
    def available_ports():
        """["None"] + the input ports connected right now, re-read on each call so
        the GUI dropdown always reflects what's currently plugged in."""
        try:
            return [NONE_PORT] + mido.get_input_names()
        except Exception as e:
            print(f"MIDI: failed to list input ports: {e}")
            return [NONE_PORT]

    def select(self, port_name):
        """Open `port_name` for listening, closing whatever was open first. "None"
        (or an empty name) just closes. Safe to call with a name that's no longer
        present — it logs the failure and falls back to None."""
        if port_name == self.selected:
            return
        self._close_all()
        self.selected = NONE_PORT
        if not port_name or port_name == NONE_PORT:
            return
        try:
            # The callback fires on a background thread, decoupled from the GUI /
            # camera frame loop — low latency, like the OSC burst trigger.
            port = mido.open_input(port_name, callback=self._on_midi)
            self._ports[port_name] = port
            self.selected = port_name
            self.log.append(f"-- opened {port_name} --")
        except Exception as e:
            self.log.append(f"-- failed to open {port_name}: {e} --")
            print(f"MIDI: failed to open {port_name}: {e}")

    def _on_midi(self, msg):
        """mido callback (background thread): record for the monitor, then fan out
        to the optional routing hook."""
        self.log.append(str(msg))
        if self.on_message is not None:
            try:
                self.on_message(msg)
            except Exception as e:
                print(f"MIDI: on_message handler error: {e}")

    def clear_log(self):
        self.log.clear()

    def _close_all(self):
        for port in self._ports.values():
            try:
                port.close()
            except Exception:
                pass
        self._ports.clear()

    def close(self):
        """Close every open port — call on shutdown."""
        self._close_all()
        self.selected = NONE_PORT
