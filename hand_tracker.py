#!/usr/bin/env python3
"""
Hand Tracking Application
Real-time hand tracking using MediaPipe HandLandmarker
Based on official MediaPipe example:
https://github.com/googlesamples/mediapipe/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import time

# Configuration
MODEL_PATH = 'hand_landmarker.task'
CAMERA_ID = 0

# Drawing constants
MARGIN = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
HANDEDNESS_TEXT_COLOR = (88, 205, 54)  # vibrant green

def draw_landmarks_on_image(rgb_image, detection_result):
    """
    Official MediaPipe visualization function for hand landmarks.
    Based on: https://github.com/googlesamples/mediapipe/blob/main/examples/hand_landmarker/python/hand_landmarker.ipynb
    """
    # Get MediaPipe drawing utilities from the new Tasks API
    mp_hands = mp.tasks.vision.HandLandmarksConnections
    mp_drawing = mp.tasks.vision.drawing_utils
    mp_drawing_styles = mp.tasks.vision.drawing_styles
    
    hand_landmarks_list = detection_result.hand_landmarks
    handedness_list = detection_result.handedness
    annotated_image = np.copy(rgb_image)
    
    # Loop through the detected hands to visualize
    for idx in range(len(hand_landmarks_list)):
        hand_landmarks = hand_landmarks_list[idx]
        handedness = handedness_list[idx]
        
        # Draw the hand landmarks
        mp_drawing.draw_landmarks(
            annotated_image,
            hand_landmarks,
            mp_hands.HAND_CONNECTIONS,
            mp_drawing_styles.get_default_hand_landmarks_style(),
            mp_drawing_styles.get_default_hand_connections_style()
        )
        
        # Get the top left corner of the detected hand's bounding box
        height, width, _ = annotated_image.shape
        x_coordinates = [landmark.x for landmark in hand_landmarks]
        y_coordinates = [landmark.y for landmark in hand_landmarks]
        text_x = int(min(x_coordinates) * width)
        text_y = int(min(y_coordinates) * height) - MARGIN
        
        # Swap handedness labels to match mirror view
        # Since we flip the image horizontally (mirror effect),
        # we swap Left↔Right so labels match what user sees
        detected_hand = handedness[0].category_name
        display_hand = "Right" if detected_hand == "Left" else "Left"
        
        # Draw handedness (left or right hand) on the image
        cv2.putText(annotated_image, display_hand,
                    (text_x, text_y), cv2.FONT_HERSHEY_DUPLEX,
                    FONT_SIZE, HANDEDNESS_TEXT_COLOR, FONT_THICKNESS, cv2.LINE_AA)
    
    return annotated_image

def main():
    # Initialize webcam
    cap = cv2.VideoCapture(CAMERA_ID)
    
    if not cap.isOpened():
        print(f"Error: Could not open webcam {CAMERA_ID}")
        print("Trying alternative camera index...")
        cap = cv2.VideoCapture(1)
        if not cap.isOpened():
            print("Error: No camera detected")
            return
    
    print("Hand Tracking Application Started")
    print("Using MediaPipe HandLandmarker with official visualization")
    print(f"Model: {MODEL_PATH}")
    print("Press 'q' or 'ESC' to quit")
    
    # Create HandLandmarker with LIVE_STREAM mode
    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    
    # Store the latest detection result
    detection_result = None
    
    def save_result(result: vision.HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
        nonlocal detection_result
        detection_result = result
    
    # Configure options
    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.LIVE_STREAM,
        num_hands=2,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        result_callback=save_result
    )
    
    # Create the hand landmarker
    with HandLandmarker.create_from_options(options) as landmarker:
        # Main processing loop
        frame_count = 0
        
        while cap.isOpened():
            success, frame = cap.read()
            
            if not success:
                print("Warning: Failed to read frame")
                continue
            
            # Flip frame horizontally for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Get timestamp in milliseconds
            timestamp_ms = int(time.time() * 1000)
            
            # Detect hands asynchronously
            landmarker.detect_async(mp_image, timestamp_ms)
            
            # Draw landmarks using official MediaPipe visualization
            if detection_result and detection_result.hand_landmarks:
                annotated_frame = draw_landmarks_on_image(rgb_frame, detection_result)
                # Convert back to BGR for OpenCV display
                frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)
                
                # Display hands count
                num_hands = len(detection_result.hand_landmarks)
                cv2.putText(frame, f"Hands: {num_hands}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 255, 0), 2)
            
            # Display the frame
            cv2.imshow('MediaPipe Hand Tracking', frame)
            
            # Check for quit key
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                print("Exiting...")
                break
            
            frame_count += 1
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print(f"Application closed successfully after processing {frame_count} frames")

if __name__ == "__main__":
    main()
