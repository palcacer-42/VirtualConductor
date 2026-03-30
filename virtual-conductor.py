#!/usr/bin/env python3
"""
Virtual Conductor — Real-time tracking with MIDI/OSC output.
"""

import cv2
import time
from tracker import HolisticTracker, draw_landmarks
from gui import ConductorGUI

CAMERA_ID = 0


def main():
    # --- Camera ---
    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print("Error opening camera")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Failed to open camera 0 or 1. Please check permissions.")
            return

    # --- GUI ---
    gui = ConductorGUI()

    # --- Tracker ---
    tracker = HolisticTracker()
    gui.set_recognizer(tracker.gesture_recognizer)
    print("Virtual Conductor Started: Face + Hands + Pose")

    # Check for black frames (macOS camera permission issue)
    camera_warning = None
    ret, test_frame = cap.read()
    if ret and test_frame is not None and test_frame.max() == 0:
        camera_warning = "Camera returns black frames. On macOS, grant camera permission in System Settings > Privacy > Camera."

    try:
        while not gui.should_close():
            gui.begin_frame()

            success, frame = cap.read()
            if not success:
                gui.render_no_frame(camera_warning)
                continue

            # Clear warning once we get a non-black frame
            if camera_warning and frame.max() > 0:
                camera_warning = None

            # Flip for mirror view
            frame = cv2.flip(frame, 1)

            # Get current UI settings
            active_modules, cc_settings, osc_settings = gui.get_settings()

            # Process tracking + send MIDI/OSC
            results = tracker.process_frame(frame, int(time.time() * 1000), active_modules, cc_settings, osc_settings)

            # Draw landmarks and convert for display
            annotated_frame = draw_landmarks(frame, results)
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

            # Render GUI
            gui.render(frame_rgb, results, camera_warning)

    finally:
        gui.shutdown()
        cap.release()


if __name__ == "__main__":
    main()
