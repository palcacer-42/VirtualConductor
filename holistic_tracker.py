#!/usr/bin/env python3
"""
Holistic Tracking Application
Real-time Face, Hand, and Pose tracking using MediaPipe Tasks API
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import time
from midi_controller import MidiController
from osc_controller import OscController

import os

# Configuration
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')

FACE_MODEL = os.path.join(MODEL_DIR, 'face_landmarker.task')
HAND_MODEL = os.path.join(MODEL_DIR, 'hand_landmarker.task')
POSE_MODEL = os.path.join(MODEL_DIR, 'pose_landmarker.task')
CAMERA_ID = 0

# Standard MIDI CCs to cycle through
MIDI_XX_OPTIONS = [1, 2, 7, 10, 11, 74, 71, 73] # Mod, Breath, Vol, Pan, Exp, Cutoff, Res, Attack

# Drawing constants
MARGIN = 10
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)  # vibrant green

class HolisticTracker:
    def __init__(self):
        # Initialize MediaPipe components
        self.base_options = mp.tasks.BaseOptions
        self.vision_running_mode = mp.tasks.vision.RunningMode
        
        # Initialize Detectors
        self.face_landmarker = self._init_face_landmarker()
        self.hand_landmarker = self._init_hand_landmarker()
        self.face_landmarker = self._init_face_landmarker()
        self.hand_landmarker = self._init_hand_landmarker()
        self.pose_landmarker = self._init_pose_landmarker()

        # Initialize MIDI
        self.midi = MidiController()
        
        # Initialize OSC
        self.osc = OscController()

    def _init_face_landmarker(self):
        options = vision.FaceLandmarkerOptions(
            base_options=self.base_options(model_asset_path=FACE_MODEL),
            running_mode=self.vision_running_mode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.5,
            min_face_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return vision.FaceLandmarker.create_from_options(options)

    def _init_hand_landmarker(self):
        options = vision.HandLandmarkerOptions(
            base_options=self.base_options(model_asset_path=HAND_MODEL),
            running_mode=self.vision_running_mode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return vision.HandLandmarker.create_from_options(options)

    def _init_pose_landmarker(self):
        options = vision.PoseLandmarkerOptions(
            base_options=self.base_options(model_asset_path=POSE_MODEL),
            running_mode=self.vision_running_mode.VIDEO,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        return vision.PoseLandmarker.create_from_options(options)

    def process_frame(self, frame, timestamp_ms, active_modules, cc_settings):
        # active_modules: {"face": bool, ...}
        # cc_settings: {"left": int, "right": int}
        
        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        
        face_result = None
        hand_result = None
        pose_result = None
        
        # Run detection synchronously ONLY if active
        if active_modules["face"]:
            face_result = self.face_landmarker.detect_for_video(mp_image, timestamp_ms)
            
        if active_modules["hands"]:
            hand_result = self.hand_landmarker.detect_for_video(mp_image, timestamp_ms)
            
        if active_modules["pose"]:
            pose_result = self.pose_landmarker.detect_for_video(mp_image, timestamp_ms)
        
        # Structure results clearly as requested
        holistic_data = {
            "face": face_result if (face_result and face_result.face_landmarks) else None,
            "pose": pose_result if (pose_result and pose_result.pose_landmarks) else None,
            "left_hand": None,
            "right_hand": None,
            "midi_values": {"left": 0, "right": 0} # Return sent values for UI
        }
        
        # Process hands to identify Left vs Right
        if hand_result and hand_result.hand_landmarks:
            for idx, hand_landmarks in enumerate(hand_result.hand_landmarks):
                # Get handedness (label is "Left" or "Right")
                handedness = hand_result.handedness[idx][0].category_name
                
                # Assign to correct key
                # Note: Swapped logic to match user's mirror view expectation.
                if handedness == "Left":
                    holistic_data["right_hand"] = hand_landmarks
                else:
                    holistic_data["left_hand"] = hand_landmarks

        # Send MIDI Data
        # Left Hand Index Tip (Y axis) -> Dynamic CC
        if holistic_data["left_hand"]:
            # Y is normalized 0.0 (top) to 1.0 (bottom).
            # We usually want 0 at bottom, so invert it: 1.0 - y
            index_y = 1.0 - holistic_data["left_hand"][8].y
            
            # Store for UI (0-127 representation)
            holistic_data["midi_values"]["left"] = int(index_y * 127)
            
            self.midi.send_control_change(0, cc_settings["left"], index_y)
            
            # Send OSC - Left hand fingertips
            fingers = [
                ("thumb", 4),
                ("index", 8),
                ("middle", 12),
                ("ring", 16),
                ("pinky", 20)
            ]
            for name, idx in fingers:
                pt = holistic_data["left_hand"][idx]
                self.osc.send_vector(f"/left-hand/{name}", pt.x, pt.y, pt.z)

        # Right Hand Index Tip (Y axis) -> Dynamic CC
        if holistic_data["right_hand"]:
            index_y = 1.0 - holistic_data["right_hand"][8].y
            
            # Store for UI
            holistic_data["midi_values"]["right"] = int(index_y * 127)
            
            self.midi.send_control_change(0, cc_settings["right"], index_y)
            
            # Send OSC - Right hand fingertips
            fingers = [
                ("thumb", 4),
                ("index", 8),
                ("middle", 12),
                ("ring", 16),
                ("pinky", 20)
            ]
            for name, idx in fingers:
                pt = holistic_data["right_hand"][idx]
                self.osc.send_vector(f"/right-hand/{name}", pt.x, pt.y, pt.z)
                    
        return holistic_data

def draw_landmarks(image, results):
    annotated_image = image.copy()
    
    # Imports for connections constants
    from mediapipe.tasks.python import vision
    
    # Drawing utilities
    mp_drawing = vision.drawing_utils
    mp_drawing_styles = vision.drawing_styles
    
    # 1. Draw Pose
    if results["pose"]:
        for pose_landmarks in results["pose"].pose_landmarks:
            mp_drawing.draw_landmarks(
                annotated_image,
                pose_landmarks,
                vision.PoseLandmarksConnections.POSE_LANDMARKS,
                mp_drawing_styles.get_default_pose_landmarks_style()
            )

    # 2. Draw Face
    if results["face"]:
        for face_landmarks in results["face"].face_landmarks:
            # Draw tesselation
            mp_drawing.draw_landmarks(
                annotated_image,
                face_landmarks,
                vision.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
                None,
                mp_drawing_styles.get_default_face_mesh_tesselation_style()
            )
            # Draw contours
            mp_drawing.draw_landmarks(
                annotated_image,
                face_landmarks,
                vision.FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS,
                None,
                mp_drawing_styles.get_default_face_mesh_contours_style()
            )

    # 3. Draw Hands
    # Draw Left Hand
    if results["left_hand"]:
        mp_drawing.draw_landmarks(
            annotated_image,
            results["left_hand"],
            vision.HandLandmarksConnections.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style()
        )
        # Add Label
        hand = results["left_hand"]
        height, width, _ = image.shape
        x = int(hand[0].x * width)
        y = int(hand[0].y * height) - 20
        cv2.putText(annotated_image, "Left", (x, y), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)

    # Draw Right Hand
    if results["right_hand"]:
        mp_drawing.draw_landmarks(
            annotated_image,
            results["right_hand"],
            vision.HandLandmarksConnections.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style()
        )
        # Add Label
        hand = results["right_hand"]
        height, width, _ = image.shape
        x = int(hand[0].x * width)
        y = int(hand[0].y * height) - 20
        cv2.putText(annotated_image, "Right", (x, y), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)

    return annotated_image

def main():
    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print("Error opening camera")
        # Try fallback
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Failed to open camera 0 or 1. Please check permissions.")
            return

    tracker = HolisticTracker()
    print("Holistic Tracker Started: Face + Hands + Pose")
    
    # Control Window Setup
    cv2.namedWindow('Controls')
    cv2.resizeWindow('Controls', 400, 200) # Ensure window is large enough
    
    # Main Window Setup
    cv2.namedWindow('Virtual Conductor', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Virtual Conductor', 800, 600)
    
    # Button Configuration
    # Types: 'toggle' or 'cycle'
    buttons = {
        "Face":  {"type": "toggle", "state": True, "rect": (10, 20, 80, 40)},
        "Hands": {"type": "toggle", "state": True, "rect": (100, 20, 80, 40)},
        "Pose":  {"type": "toggle", "state": True, "rect": (190, 20, 80, 40)},
        
        # MIDI Assignment Buttons (Cycle)
        "L-CC":  {"type": "cycle", "index": 0, "rect": (10, 80, 100, 50), "value_out": 0},
        "R-CC":  {"type": "cycle", "index": 4, "rect": (120, 80, 100, 50), "value_out": 0} # Start at CC 11 (index 4)
    }
    
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for name, btn in buttons.items():
                bx, by, bw, bh = btn["rect"]
                if bx <= x <= bx + bw and by <= y <= by + bh:
                    if btn["type"] == "toggle":
                        btn["state"] = not btn["state"]
                    elif btn["type"] == "cycle":
                        btn["index"] = (btn["index"] + 1) % len(MIDI_XX_OPTIONS)
                        
                    print(f"Clicked {name}")

    cv2.setMouseCallback('Controls', mouse_callback)

    def draw_controls(buttons):
        # Create black background (now taller for more controls)
        control_img = np.zeros((150, 400, 3), dtype=np.uint8)
        
        for name, btn in buttons.items():
            bx, by, bw, bh = btn["rect"]
            
            # Button Logic
            if btn["type"] == "toggle":
                state = btn["state"]
                color = (0, 255, 0) if state else (100, 100, 100)
                label = name
                text_color = (0, 0, 0) if state else (255, 255, 255)
                
            elif btn["type"] == "cycle":
                cc_num = MIDI_XX_OPTIONS[btn["index"]]
                color = (255, 100, 0) # Orange for setting
                label = f"{name}: {cc_num}"
                text_color = (255, 255, 255)
                
                # Draw Value Bar at bottom of button
                val_norm = btn["value_out"] / 127.0
                bar_h = int(bh * val_norm)
                if bar_h > 0:
                    cv2.rectangle(control_img, (bx, by + bh - bar_h), (bx + bw, by + bh), (255, 150, 50), -1)
            
            # Draw Button Background
            cv2.rectangle(control_img, (bx, by), (bx + bw, by + bh), color, -1)
            
            # Draw Outer Border
            cv2.rectangle(control_img, (bx, by), (bx + bw, by + bh), (200, 200, 200), 1)
            
            # Draw Text
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            text_x = bx + (bw - text_size[0]) // 2
            text_y = by + (bh + text_size[1]) // 2
            cv2.putText(control_img, label, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
            
        return control_img
    
    try:
        windows_positioned = False
        while cap.isOpened():
            success, frame = cap.read()
            if not success: continue

            # Update Active Modules from Button States
            active_modules = {
                "face": buttons["Face"]["state"],
                "hands": buttons["Hands"]["state"],
                "pose": buttons["Pose"]["state"]
            }
            
            # Get Current CC Settings
            cc_settings = {
                "left": MIDI_XX_OPTIONS[buttons["L-CC"]["index"]],
                "right": MIDI_XX_OPTIONS[buttons["R-CC"]["index"]]
            }

            # Flip for mirror view
            frame = cv2.flip(frame, 1)
            results = tracker.process_frame(frame, int(time.time() * 1000), active_modules, cc_settings)
            
            # Update Button UI with output values for visualization
            buttons["L-CC"]["value_out"] = results["midi_values"]["left"]
            buttons["R-CC"]["value_out"] = results["midi_values"]["right"]
            
            # Visualization
            annotated_frame = draw_landmarks(frame, results)
            
            # --- Data Info Overlay ---
            # Constants for layout
            col_width = 230
            line_height = 28
            start_x = 10
            start_y = 60
            font_scale = 0.7
            
            # Data Containers
            left_lines = ["--- LEFT HAND ---"]
            right_lines = ["--- RIGHT HAND ---"]
            face_lines = ["--- FACE ---"]

            # Finger Names for loop
            digits = [("Thumb", 4), ("Index", 8), ("Mid", 12), ("Ring", 16), ("Pinky", 20)]

            # 1. Left Hand Data
            if not active_modules["hands"]:
                left_lines.append("[OFF]")
            elif results["left_hand"]:
                for name, idx in digits:
                    pt = results["left_hand"][idx]
                    left_lines.append(f"{name}: {pt.x:.2f}, {pt.y:.2f}")
            else:
                left_lines.append("No Detection")

            # 2. Right Hand Data
            if not active_modules["hands"]:
                right_lines.append("[OFF]")
            elif results["right_hand"]:
                for name, idx in digits:
                    pt = results["right_hand"][idx]
                    right_lines.append(f"{name}: {pt.x:.2f}, {pt.y:.2f}")
            else:
                right_lines.append("No Detection")
                
            # 3. Face Data
            if not active_modules["face"]:
                face_lines.append("[OFF]")
            elif results["face"]:
                face = results["face"].face_landmarks[0]
                # Nose Tip (1)
                nose = face[1]
                face_lines.append(f"Nose: {nose.x:.2f}, {nose.y:.2f}")
                # Eyes (33=L, 263=R)
                eye_l = face[33]
                eye_r = face[263]
                face_lines.append(f"L-Eye: {eye_l.x:.2f}, {eye_l.y:.2f}")
                face_lines.append(f"R-Eye: {eye_r.x:.2f}, {eye_r.y:.2f}")
                # Mouth
                m_x = (face[13].x + face[14].x) / 2
                m_y = (face[13].y + face[14].y) / 2
                face_lines.append(f"Mouth: {m_x:.2f}, {m_y:.2f}")
            else:
                face_lines.append("No Detection")

            # Draw Background Box
            # Width = 2 columns + padding
            # Height = Max(Left, Right) + Face Rows
            max_hand_rows = max(len(left_lines), len(right_lines))
            total_rows = max_hand_rows + len(face_lines) + 1
            box_h = int(total_rows * line_height) + 10
            box_w = (col_width * 2) + 20
            
            cv2.rectangle(annotated_frame, (5, 45), (5 + box_w, 45 + box_h), (0, 0, 0), -1)
            
            # Function to draw column
            def draw_col(lines, x_pos, start_y):
                y = start_y
                for line in lines:
                    color = (200, 200, 200) # Grayish standard
                    if "LEFT" in line: color = (100, 200, 255) # Orange-ish/Blue? Let's go Cyan for Left
                    if "RIGHT" in line: color = (100, 255, 100) # Green for Right
                    if "FACE" in line: color = (255, 255, 100) # Yellow for Face
                    
                    cv2.putText(annotated_frame, line, (x_pos, y), 
                               cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1)
                    y += line_height
                return y

            # Draw Left Col
            draw_col(left_lines, start_x, start_y)
            
            # Draw Right Col
            draw_col(right_lines, start_x + col_width, start_y)
            
            # Draw Face (Centered-ish below)
            # Calculate Y start for face based on max hand lines
            face_start_y = start_y + (max_hand_rows * line_height) + 5
            draw_col(face_lines, start_x, face_start_y)
            # -------------------------
            
            # Display status on main frame
            status_text = []
            if results["face"]: status_text.append("Face")
            if results["pose"]: status_text.append("Pose")
            if results["left_hand"]: status_text.append("L-Hand")
            if results["right_hand"]: status_text.append("R-Hand")
            
            cv2.putText(annotated_frame, f"Tracking: {', '.join(status_text)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow('Virtual Conductor', annotated_frame)
            
            # Draw and Show Controls
            control_ui = draw_controls(buttons)
            cv2.imshow('Controls', control_ui)
            
            # Position windows once on startup (Vertical Stack)
            if not windows_positioned:
                cv2.moveWindow('Virtual Conductor', 0, 0)
                # Position Controls below the main window (Fixed 600 height + 50 px buffer)
                cv2.moveWindow('Controls', 0, 650)
                windows_positioned = True
            
            if cv2.waitKey(1) & 0xFF in [ord('q'), 27]:
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
