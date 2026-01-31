import cv2
import sys

print("Testing camera access...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("ERROR: Cannot open camera 0")
    print("Trying camera 1...")
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("ERROR: Cannot open camera 1 either")
        print("\nThis means camera permission is likely not granted.")
        print("Go to: System Preferences -> Security & Privacy -> Camera")
        sys.exit(1)

print("✓ Camera opened successfully")

# Try to read a frame
ret, frame = cap.read()
print(f"✓ Frame read successful: {ret}")

if ret and frame is not None:
    print(f"✓ Frame shape: {frame.shape}")
    print(f"✓ Frame data type: {frame.dtype}")
    print(f"✓ Frame min/max values: {frame.min()}/{frame.max()}")
    
    # Check if frame is all black
    if frame.max() == 0:
        print("\n⚠️  WARNING: Frame is completely black!")
        print("Possible issues:")
        print("  1. Camera lens is covered")
        print("  2. Camera is being used by another application")
        print("  3. Camera needs to warm up")
else:
    print("✗ Failed to read frame from camera")

cap.release()
print("\n✓ Test complete")
