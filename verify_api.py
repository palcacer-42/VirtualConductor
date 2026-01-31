
import mediapipe as mp
try:
    from mediapipe.tasks.python import vision
    
    print("✅ MediaPipe Tasks API detected")
    
    # Verify Pose
    if hasattr(vision.PoseLandmarksConnections, 'POSE_LANDMARKS'):
        print(f"✅ Pose Connection Constant: vision.PoseLandmarksConnections.POSE_LANDMARKS (Verified)")
    else:
        print("❌ Pose Connection Constant NOT found")

    # Verify Hands
    if hasattr(vision.HandLandmarksConnections, 'HAND_CONNECTIONS'):
        print(f"✅ Hand Connection Constant: vision.HandLandmarksConnections.HAND_CONNECTIONS (Verified)")
    else:
        print("❌ Hand Connection Constant NOT found")

    # Verify Face
    if hasattr(vision.FaceLandmarksConnections, 'FACE_LANDMARKS_TESSELATION'):
        print(f"✅ Face Tesselation Constant: vision.FaceLandmarksConnections.FACE_LANDMARKS_TESSELATION (Verified)")
    else:
        print("❌ Face Tesselation Constant NOT found")
        
except ImportError as e:
    print(f"❌ Failed to import Tasks API: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
