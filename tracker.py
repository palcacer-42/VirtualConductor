"""
Holistic Tracker — MediaPipe face, hand, and pose tracking + MIDI/OSC output.
"""

import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
import numpy as np
import os
from midi_controller import MidiController
from osc_controller import OscController

# Configuration
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
FACE_MODEL = os.path.join(MODEL_DIR, 'face_landmarker.task')
HAND_MODEL = os.path.join(MODEL_DIR, 'hand_landmarker.task')
POSE_MODEL = os.path.join(MODEL_DIR, 'pose_landmarker.task')

# Standard MIDI CCs to cycle through
MIDI_CC_OPTIONS = [1, 2, 7, 10, 11, 74, 71, 73]  # Mod, Breath, Vol, Pan, Exp, Cutoff, Res, Attack


class HolisticTracker:
    def __init__(self):
        self.base_options = mp.tasks.BaseOptions
        self.vision_running_mode = mp.tasks.vision.RunningMode

        # Initialize Detectors
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

        # Structure results
        holistic_data = {
            "face": face_result if (face_result and face_result.face_landmarks) else None,
            "pose": pose_result if (pose_result and pose_result.pose_landmarks) else None,
            "left_hand": None,
            "right_hand": None,
            "midi_values": {"left": 0, "right": 0}
        }

        # Process hands to identify Left vs Right
        if hand_result and hand_result.hand_landmarks:
            for idx, hand_landmarks in enumerate(hand_result.hand_landmarks):
                handedness = hand_result.handedness[idx][0].category_name
                # Swapped to match user's mirror view expectation
                if handedness == "Left":
                    holistic_data["right_hand"] = hand_landmarks
                else:
                    holistic_data["left_hand"] = hand_landmarks

        # Send MIDI/OSC — Left Hand
        if holistic_data["left_hand"]:
            index_y = 1.0 - holistic_data["left_hand"][8].y
            holistic_data["midi_values"]["left"] = int(index_y * 127)
            self.midi.send_control_change(0, cc_settings["left"], index_y)

            fingers = [("thumb", 4), ("index", 8), ("middle", 12), ("ring", 16), ("pinky", 20)]
            for name, idx in fingers:
                pt = holistic_data["left_hand"][idx]
                self.osc.send_vector(f"/left-hand/{name}", pt.x, pt.y, pt.z)

        # Send MIDI/OSC — Right Hand
        if holistic_data["right_hand"]:
            index_y = 1.0 - holistic_data["right_hand"][8].y
            holistic_data["midi_values"]["right"] = int(index_y * 127)
            self.midi.send_control_change(0, cc_settings["right"], index_y)

            fingers = [("thumb", 4), ("index", 8), ("middle", 12), ("ring", 16), ("pinky", 20)]
            for name, idx in fingers:
                pt = holistic_data["right_hand"][idx]
                self.osc.send_vector(f"/right-hand/{name}", pt.x, pt.y, pt.z)

        return holistic_data


def draw_landmarks(image, results):
    annotated_image = image.copy()

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
            mp_drawing.draw_landmarks(
                annotated_image,
                face_landmarks,
                vision.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION,
                None,
                mp_drawing_styles.get_default_face_mesh_tesselation_style()
            )
            mp_drawing.draw_landmarks(
                annotated_image,
                face_landmarks,
                vision.FaceLandmarksConnections.FACE_LANDMARKS_CONTOURS,
                None,
                mp_drawing_styles.get_default_face_mesh_contours_style()
            )

    # 3. Draw Left Hand
    if results["left_hand"]:
        mp_drawing.draw_landmarks(
            annotated_image,
            results["left_hand"],
            vision.HandLandmarksConnections.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style()
        )
        hand = results["left_hand"]
        height, width, _ = image.shape
        x = int(hand[0].x * width)
        y = int(hand[0].y * height) - 20
        cv2.putText(annotated_image, "Left", (x, y), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)

    # 4. Draw Right Hand
    if results["right_hand"]:
        mp_drawing.draw_landmarks(
            annotated_image,
            results["right_hand"],
            vision.HandLandmarksConnections.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style()
        )
        hand = results["right_hand"]
        height, width, _ = image.shape
        x = int(hand[0].x * width)
        y = int(hand[0].y * height) - 20
        cv2.putText(annotated_image, "Right", (x, y), cv2.FONT_HERSHEY_DUPLEX, 1, (0, 255, 0), 2)

    return annotated_image
