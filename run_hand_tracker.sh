#!/bin/bash
# Hand Tracker Launcher with Camera Permission Check
# Simple script to activate virtual environment and run the hand tracking application

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate to the project directory
cd "$SCRIPT_DIR"

echo "🖐️  Hand Tracker Launcher"
echo "=========================="
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated"
echo ""

# Check camera permission first
echo "🎥 Testing camera access..."
python test_camera.py

if [ $? -ne 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  CAMERA PERMISSION REQUIRED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "The application cannot access your camera."
    echo ""
    echo "📋 TO FIX THIS:"
    echo ""
    echo "1. Open System Preferences (or System Settings on newer macOS)"
    echo "2. Go to: Security & Privacy → Privacy → Camera"
    echo "3. Enable camera access for: Terminal (or iTerm, if using)"
    echo "4. Close this terminal window and open a new one"
    echo "5. Run this script again"
    echo ""
    echo "OR run this command in Terminal:"
    echo "   tccutil reset Camera"
    echo "   (Then grant permission when prompted)"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    deactivate
    exit 1
fi

echo "✅ Camera access granted!"
echo ""

# Run the holistic tracker
echo "🚀 Launching Holistic Tracker (Face + Hands + Pose)..."
echo "   Press 'q' or 'ESC' to quit"
echo ""
python holistic_tracker.py

# Deactivate virtual environment after program exits
deactivate

echo ""
echo "👋 Hand tracker closed"
