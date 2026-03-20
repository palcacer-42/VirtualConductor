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
import glfw
import imgui
from imgui.integrations.glfw import GlfwRenderer
import OpenGL.GL as gl

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

def create_video_texture():
    """Create an OpenGL texture for the video feed."""
    texture_id = gl.glGenTextures(1)
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
    gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
    return texture_id

def update_texture(texture_id, frame_rgb):
    """Upload an RGB frame to an existing OpenGL texture."""
    h, w = frame_rgb.shape[:2]
    gl.glBindTexture(gl.GL_TEXTURE_2D, texture_id)
    gl.glTexImage2D(
        gl.GL_TEXTURE_2D, 0, gl.GL_RGB,
        w, h, 0,
        gl.GL_RGB, gl.GL_UNSIGNED_BYTE,
        frame_rgb
    )

def main():
    # --- Camera ---
    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        print("Error opening camera")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Failed to open camera 0 or 1. Please check permissions.")
            return

    # --- GLFW + ImGui Init ---
    if not glfw.init():
        print("Failed to initialize GLFW")
        return

    window = glfw.create_window(1100, 700, "Virtual Conductor", None, None)
    if not window:
        glfw.terminate()
        print("Failed to create GLFW window")
        return

    glfw.make_context_current(window)
    glfw.swap_interval(1)

    imgui.create_context()
    impl = GlfwRenderer(window)

    # --- Tracker ---
    tracker = HolisticTracker()
    print("Holistic Tracker Started: Face + Hands + Pose")

    # --- State ---
    active_face = True
    active_hands = True
    active_pose = True
    lcc_index = 0
    rcc_index = 4
    cc_labels = [str(cc) for cc in MIDI_XX_OPTIONS]

    # --- Video Texture ---
    video_texture = create_video_texture()
    camera_warning = None

    # Check for black frames (macOS camera permission issue)
    ret, test_frame = cap.read()
    if ret and test_frame is not None and test_frame.max() == 0:
        camera_warning = "Camera returns black frames. On macOS, grant camera permission in System Settings > Privacy > Camera."

    try:
        while not glfw.window_should_close(window):
            glfw.poll_events()
            impl.process_inputs()

            success, frame = cap.read()
            if not success:
                # Still render ImGui so the warning is visible
                imgui.new_frame()
                imgui.begin("Camera Feed")
                imgui.text("No camera frame available.")
                if camera_warning:
                    imgui.text_colored(camera_warning, 1.0, 0.3, 0.3)
                imgui.end()
                imgui.render()
                gl.glClearColor(0.1, 0.1, 0.1, 1.0)
                gl.glClear(gl.GL_COLOR_BUFFER_BIT)
                impl.render(imgui.get_draw_data())
                glfw.swap_buffers(window)
                continue

            # Clear warning once we get a non-black frame
            if camera_warning and frame.max() > 0:
                camera_warning = None

            # Flip for mirror view
            frame = cv2.flip(frame, 1)

            active_modules = {
                "face": active_face,
                "hands": active_hands,
                "pose": active_pose
            }
            cc_settings = {
                "left": MIDI_XX_OPTIONS[lcc_index],
                "right": MIDI_XX_OPTIONS[rcc_index]
            }

            results = tracker.process_frame(frame, int(time.time() * 1000), active_modules, cc_settings)

            # Draw landmarks on frame and upload as texture
            annotated_frame = draw_landmarks(frame, results)
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            update_texture(video_texture, frame_rgb)
            vid_h, vid_w = frame_rgb.shape[:2]

            # --- ImGui Frame ---
            imgui.new_frame()

            # Video Window
            imgui.begin("Camera Feed")
            if camera_warning:
                imgui.text_colored(camera_warning, 1.0, 0.3, 0.3)
            imgui.image(video_texture, vid_w, vid_h)
            imgui.end()

            # Controls Window
            imgui.begin("Controls")

            # Tracking toggles
            _, active_face = imgui.checkbox("Face", active_face)
            imgui.same_line()
            _, active_hands = imgui.checkbox("Hands", active_hands)
            imgui.same_line()
            _, active_pose = imgui.checkbox("Pose", active_pose)

            imgui.separator()

            # MIDI CC selectors
            imgui.text("MIDI CC Assignment")
            imgui.set_next_item_width(120)
            _, lcc_index = imgui.combo("L-CC", lcc_index, cc_labels)
            imgui.same_line()
            imgui.set_next_item_width(120)
            _, rcc_index = imgui.combo("R-CC", rcc_index, cc_labels)

            # MIDI value bars
            left_val = results["midi_values"]["left"] / 127.0
            right_val = results["midi_values"]["right"] / 127.0
            imgui.progress_bar(left_val, (120, 14), f"L: {results['midi_values']['left']}")
            imgui.same_line()
            imgui.progress_bar(right_val, (120, 14), f"R: {results['midi_values']['right']}")

            imgui.end()

            # Data Window
            imgui.begin("Tracking Data")

            digits = [("Thumb", 4), ("Index", 8), ("Mid", 12), ("Ring", 16), ("Pinky", 20)]

            # Left Hand
            imgui.text_colored("LEFT HAND", 0.4, 0.8, 1.0)
            if not active_hands:
                imgui.text("[OFF]")
            elif results["left_hand"]:
                for name, idx in digits:
                    pt = results["left_hand"][idx]
                    imgui.text(f"  {name}: {pt.x:.2f}, {pt.y:.2f}")
            else:
                imgui.text("  No Detection")

            imgui.spacing()

            # Right Hand
            imgui.text_colored("RIGHT HAND", 0.4, 1.0, 0.4)
            if not active_hands:
                imgui.text("[OFF]")
            elif results["right_hand"]:
                for name, idx in digits:
                    pt = results["right_hand"][idx]
                    imgui.text(f"  {name}: {pt.x:.2f}, {pt.y:.2f}")
            else:
                imgui.text("  No Detection")

            imgui.spacing()

            # Face
            imgui.text_colored("FACE", 1.0, 1.0, 0.4)
            if not active_face:
                imgui.text("[OFF]")
            elif results["face"]:
                face = results["face"].face_landmarks[0]
                nose = face[1]
                imgui.text(f"  Nose: {nose.x:.2f}, {nose.y:.2f}")
                eye_l = face[33]
                eye_r = face[263]
                imgui.text(f"  L-Eye: {eye_l.x:.2f}, {eye_l.y:.2f}")
                imgui.text(f"  R-Eye: {eye_r.x:.2f}, {eye_r.y:.2f}")
                m_x = (face[13].x + face[14].x) / 2
                m_y = (face[13].y + face[14].y) / 2
                imgui.text(f"  Mouth: {m_x:.2f}, {m_y:.2f}")
            else:
                imgui.text("  No Detection")

            imgui.end()

            # --- Render ---
            imgui.render()
            gl.glClearColor(0.1, 0.1, 0.1, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT)
            impl.render(imgui.get_draw_data())
            glfw.swap_buffers(window)

    finally:
        gl.glDeleteTextures(1, [video_texture])
        impl.shutdown()
        cap.release()
        glfw.terminate()

if __name__ == "__main__":
    main()
