"""
Gesture Collector — Records labeled landmark samples for gesture training.
"""

import json
import os
import math
from datetime import datetime

DATASET_PATH = os.path.join(os.path.dirname(__file__), 'gestures', 'dataset.json')


def normalize_hand(landmarks):
    """Normalize hand landmarks: translate to wrist origin, scale by hand size."""
    wrist = landmarks[0]
    wx, wy, wz = wrist.x, wrist.y, wrist.z

    # Hand size = distance from wrist (0) to middle finger MCP (9)
    mcp = landmarks[9]
    hand_size = math.sqrt((mcp.x - wx)**2 + (mcp.y - wy)**2 + (mcp.z - wz)**2)
    if hand_size < 1e-6:
        hand_size = 1e-6

    normalized = []
    for lm in landmarks:
        normalized.extend([
            (lm.x - wx) / hand_size,
            (lm.y - wy) / hand_size,
            (lm.z - wz) / hand_size,
        ])
    return normalized


class GestureCollector:
    def __init__(self):
        self.recording = False
        self.current_label = ""
        self.current_source = ""
        self.buffer = []
        self.dataset = self._load_dataset()

    def _load_dataset(self):
        if os.path.exists(DATASET_PATH):
            with open(DATASET_PATH, 'r') as f:
                return json.load(f)
        return {"samples": []}

    def _save_dataset(self):
        os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
        with open(DATASET_PATH, 'w') as f:
            json.dump(self.dataset, f)

    def start_recording(self, label, source="right_hand"):
        self.recording = True
        self.current_label = label
        self.current_source = source
        self.buffer = []

    def record_sample(self, landmarks):
        """Call each frame while recording. Normalizes and buffers the sample."""
        if not self.recording:
            return

        if self.current_source in ("right_hand", "left_hand"):
            normalized = normalize_hand(landmarks)
        else:
            # Future: different normalization for face/pose
            normalized = []
            for lm in landmarks:
                normalized.extend([lm.x, lm.y, lm.z])

        self.buffer.append({
            "label": self.current_label,
            "source": self.current_source,
            "landmarks": normalized,
            "timestamp": datetime.now().isoformat()
        })

    def stop_recording(self):
        """Stop recording and flush buffer to dataset."""
        if self.buffer:
            self.dataset["samples"].extend(self.buffer)
            self._save_dataset()
        count = len(self.buffer)
        self.buffer = []
        self.recording = False
        return count

    def get_status(self):
        return {
            "recording": self.recording,
            "label": self.current_label,
            "sample_count": len(self.buffer),
        }

    def get_summary(self):
        """Return {(source, label): count} for all collected data."""
        summary = {}
        for s in self.dataset["samples"]:
            key = (s["source"], s["label"])
            summary[key] = summary.get(key, 0) + 1
        return summary

    def delete_gesture(self, label, source):
        """Remove all samples for a given label and source."""
        self.dataset["samples"] = [
            s for s in self.dataset["samples"]
            if not (s["label"] == label and s["source"] == source)
        ]
        self._save_dataset()
