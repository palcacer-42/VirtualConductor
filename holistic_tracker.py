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

# Configuration
FACE_MODEL = 'face_landmarker.task'
HAND_MODEL = 'hand_landmarker.task'
POSE_MODEL = 'pose_landmarker.task'
CAMERA_ID = 0

# MIDI Mapping
MIDI_CC_LEFT_INDEX = 1   # Modulation
MIDI_CC_RIGHT_INDEX = 11 # Expression

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

    def process_frame(self, frame, timestamp_ms):
        # Convert to MediaPipe Image
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        
        # Run detection synchronously
        face_result = self.face_landmarker.detect_for_video(mp_image, timestamp_ms)
        hand_result = self.hand_landmarker.detect_for_video(mp_image, timestamp_ms)
        pose_result = self.pose_landmarker.detect_for_video(mp_image, timestamp_ms)
        
        # Structure results clearly as requested
        holistic_data = {
            "face": face_result if face_result.face_landmarks else None,
            "pose": pose_result if pose_result.pose_landmarks else None,
            "left_hand": None,
            "right_hand": None
        }
        
        # Process hands to identify Left vs Right
        if hand_result.hand_landmarks:
            for idx, hand_landmarks in enumerate(hand_result.hand_landmarks):
                # Get handedness (label is "Left" or "Right")
                handedness = hand_result.handedness[idx][0].category_name
                
                # Assign to correct key
                # Note: Swapped logic to match user's mirror view expectation.
                # When user raises Left hand, MediaPipe might say "Right" or "Left" depending on model mode,
                # but user wants the visual left side to be labeled "Left".
                # Empirically swapping based on user report.
                if handedness == "Left":
                    holistic_data["right_hand"] = hand_landmarks
                else:
                    holistic_data["left_hand"] = hand_landmarks

        # Send MIDI Data
        # Left Hand Index Tip (Y axis) -> CC 1
        if holistic_data["left_hand"]:
            # Y is normalized 0.0 (top) to 1.0 (bottom).
            # We usually want 0 at bottom, so invert it: 1.0 - y
            index_y = 1.0 - holistic_data["left_hand"][8].y
            self.midi.send_control_change(0, MIDI_CC_LEFT_INDEX, index_y)
            
        # Right Hand Index Tip (Y axis) -> CC 11
        if holistic_data["right_hand"]:
            index_y = 1.0 - holistic_data["right_hand"][8].y
            self.midi.send_control_change(0, MIDI_CC_RIGHT_INDEX, index_y)
                    
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
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success: continue

            # Flip for mirror view
            frame = cv2.flip(frame, 1)
            results = tracker.process_frame(frame, int(time.time() * 1000))
            
            # Visualization
            annotated_frame = draw_landmarks(frame, results)
            
            # Display status
            status_text = []
            if results["face"]: status_text.append("Face")
            if results["pose"]: status_text.append("Pose")
            if results["left_hand"]: status_text.append("L-Hand")
            if results["right_hand"]: status_text.append("R-Hand")
            
            cv2.putText(annotated_frame, f"Tracking: {', '.join(status_text)}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow('Holistic Tracking', annotated_frame)
            
            if cv2.waitKey(1) & 0xFF in [ord('q'), 27]:
                break
                
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
