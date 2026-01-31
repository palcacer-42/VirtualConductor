# Hand Tracking Implementation Roadmap

## Project Overview
A real-time hand tracking application using MediaPipe and OpenCV that displays webcam input with visual hand landmark detection and skeletal connections.

---

## Prerequisites

### System Requirements
- **Python Version**: 3.8 - 3.11 (recommended: **3.10**)
- **Operating System**: macOS, Windows, or Linux
- **Webcam**: Built-in or external USB camera

> [!IMPORTANT]
> Python 3.12+ may have compatibility issues with some MediaPipe versions. Python 3.10 is the most stable choice.

---

## Phase 1: Environment Setup

### Step 1.1: Verify Python Installation
```bash
# Check Python version
python3 --version
```

Expected output: `Python 3.10.x` (or 3.8-3.11)

### Step 1.2: Navigate to Project Directory
```bash
# Navigate to the project folder (adjust path as needed)
cd ~/Documents/CODE/kiko
```

### Step 1.3: Create Virtual Environment
```bash
# Create virtual environment in the kiko folder
python3 -m venv venv
```

### Step 1.4: Activate Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**On Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

> [!TIP]
> You should see `(venv)` appear at the beginning of your terminal prompt when activated.

### Step 1.5: Upgrade pip
```bash
# Ensure pip is up to date
pip install --upgrade pip
```

---

## Phase 2: Dependency Installation

### Step 2.1: Install Required Packages

```bash
# Install OpenCV for webcam capture and visualization
pip install opencv-python==4.9.0.80

# Install MediaPipe for hand detection
pip install mediapipe==0.10.9
```

**Package Breakdown:**
| Package | Version | Purpose |
|---------|---------|---------|
| `opencv-python` | 4.9.0.80 | Webcam access, image processing, display window |
| `mediapipe` | 0.10.9 | Hand landmark detection and tracking |

### Step 2.2: Verify Installation
```bash
# List installed packages
pip list
```

Expected output should include:
```
mediapipe    0.10.9
opencv-python 4.9.0.80
```

### Step 2.3: Create Requirements File
```bash
# Generate requirements.txt for reproducibility
pip freeze > requirements.txt
```

> [!NOTE]
> This allows others (or future you) to recreate the exact environment with `pip install -r requirements.txt`

---

## Phase 3: Implementation

### Step 3.1: Create Main Script
Create a file named `hand_tracker.py` in your kiko directory.

### Step 3.2: Code Structure

The implementation will follow this architecture:

```
1. Import Dependencies
   ├── cv2 (OpenCV)
   └── mediapipe

2. Initialize MediaPipe Hands
   ├── Set detection confidence threshold
   ├── Set tracking confidence threshold
   └── Configure max number of hands

3. Setup Webcam Capture
   └── Initialize cv2.VideoCapture(0)

4. Main Processing Loop
   ├── Read frame from webcam
   ├── Convert BGR → RGB (MediaPipe requirement)
   ├── Process with MediaPipe
   ├── Extract hand landmarks
   ├── Draw landmarks and connections
   └── Display annotated frame

5. Cleanup
   ├── Release webcam
   └── Close all windows
```

### Step 3.3: Key Configuration Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `max_num_hands` | 2 | Maximum hands to detect (1 or 2) |
| `min_detection_confidence` | 0.7 | Minimum confidence for initial detection (0.0-1.0) |
| `min_tracking_confidence` | 0.5 | Minimum confidence for tracking (0.0-1.0) |

### Step 3.4: Visual Output Details

**Hand Landmarks:**
- 21 keypoints per hand
- Each point represents a specific joint or fingertip
- Color-coded by MediaPipe's drawing utilities

**Connections:**
- Lines connecting related landmarks
- Forms a "skeleton" visualization
- Helps visualize hand pose and gestures

---

## Phase 4: Execution

### Step 4.1: Run the Application
```bash
# Ensure you're in the project directory and venv is activated
source venv/bin/activate
python hand_tracker.py
```

### Step 4.2: Expected Behavior
1. A window titled "Hand Tracking" will appear
2. Your webcam feed will display in real-time
3. When hands enter the frame, you'll see:
   - **Blue dots** on each landmark
   - **Green lines** connecting the landmarks
4. Press `q` or `ESC` to quit the application

### Step 4.3: Performance Expectations
- **Frame Rate**: 20-30 FPS on most modern computers
- **Latency**: < 50ms for hand detection
- **CPU Usage**: Moderate (30-50% on a single core)

---

## Phase 5: Testing & Validation

### Test Cases

✅ **Single Hand Detection**
- Hold one hand in front of camera
- Verify all 21 landmarks are detected
- Move hand slowly to test tracking

✅ **Two Hands Detection**
- Hold both hands in frame
- Verify both hands are tracked simultaneously

✅ **Various Lighting Conditions**
- Test in bright light
- Test in dim light
- Test with backlight

✅ **Different Hand Poses**
- Open palm
- Closed fist
- Pointing finger
- Peace sign

✅ **Occlusion Handling**
- Partially hide hand behind object
- Overlap hands
- Move hand in/out of frame

---

## Troubleshooting

### Issue: Camera Not Detected
**Solution:**
```python
# Try different camera indices
cap = cv2.VideoCapture(1)  # Instead of 0
```

### Issue: Low Frame Rate
**Solutions:**
- Lower camera resolution
- Reduce `max_num_hands` to 1
- Close other applications using the camera

### Issue: Poor Detection Accuracy
**Solutions:**
- Ensure good lighting
- Increase `min_detection_confidence`
- Keep hands clearly visible (not too far or too fast)

### Issue: Import Errors
**Solution:**
```bash
# Deactivate and reactivate venv
deactivate
source venv/bin/activate

# Reinstall packages
pip install --force-reinstall opencv-python mediapipe
```

---

## Next Steps & Enhancements

Once the basic implementation works, consider:

1. **Add Gesture Recognition** - Detect specific hand shapes (thumbs up, peace sign, etc.)
2. **Record Landmark Data** - Save coordinates to CSV for machine learning
3. **Add Face Detection** - Upgrade to MediaPipe Holistic
4. **Create Interactive Controls** - Use hand gestures to control applications
5. **Performance Optimization** - Multi-threading for better FPS

---

## Project Structure

```
kiko/
├── venv/                    # Virtual environment (git-ignored)
├── hand_tracker.py          # Main application script
├── requirements.txt         # Python dependencies
└── IMPLEMENTATION_ROADMAP.md # This file
```

---

## Quick Reference Commands

```bash
# Navigate to project directory
cd ~/Documents/CODE/kiko  # Or wherever you cloned/placed the project

# Activate virtual environment (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python hand_tracker.py

# Deactivate virtual environment
deactivate
```

---

## Additional Resources

- [MediaPipe Hands Documentation](https://google.github.io/mediapipe/solutions/hands.html)
- [OpenCV Python Tutorials](https://docs.opencv.org/4.x/d6/d00/tutorial_py_root.html)
- [MediaPipe Hand Landmark Model](https://google.github.io/mediapipe/solutions/hands#hand-landmark-model)

---

**Version**: 1.0  
**Last Updated**: 2026-01-31  
**Python**: 3.10+  
**Status**: Ready for Implementation
