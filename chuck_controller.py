"""
ChucK Controller — process management for ChucK scripts.
"""

import os
import subprocess
import threading
from collections import deque


SCRIPTS = {
    "Theremin": "chuck-scripts/theremin.ck",
    "Synth":    "chuck-scripts/synth.ck",
}


class ChuckController:
    def __init__(self):
        self._project_dir = os.path.dirname(os.path.abspath(__file__))
        self.scripts = SCRIPTS
        self._proc = None
        self.active = None
        self.log = deque(maxlen=200)

    def launch(self, name):
        self.kill()
        self.log.clear()
        self.log.append(f"[Launching {name}...]")
        self._proc = subprocess.Popen(
            ["chuck", self.scripts[name]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=self._project_dir,
        )
        self.active = name
        threading.Thread(target=self._read_output, daemon=True).start()

    def kill(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        self.active = None

    def poll(self):
        """Check if process died on its own. Returns exit code or None if still running."""
        if self._proc:
            return self._proc.poll()
        return None

    @property
    def returncode(self):
        return self._proc.returncode if self._proc else None

    def _read_output(self):
        for line in self._proc.stdout:
            self.log.append(line.rstrip())
