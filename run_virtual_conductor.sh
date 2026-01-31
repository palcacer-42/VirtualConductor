#!/bin/bash
# Virtual Conductor Launcher
# Activates virtual environment and starts the Holistic Tracker with MIDI/OSC support.

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Navigate to the project directory
cd "$SCRIPT_DIR"

echo "✨ Virtual Conductor Launcher"
echo "==========================="
echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found in venv/"
    exit 1
fi

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated"
echo ""

# Check camera permissions
echo "🎥 Testing camera access..."
python3 test_camera.py

if [ $? -ne 0 ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  CAMERA PERMISSION REQUIRED"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Please grant Terminal camera access in System Settings."
    echo "Try running: tccutil reset Camera"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    deactivate
    exit 1
fi

echo "✅ Camera access confirmed!"
echo ""

# Run the tracker
echo "🚀 Launching Virtual Conductor (Face + Hands + Pose)..."
echo "   Controls: Toggle features in the 'Controls' window."
echo "   Output: Sending MIDI (Virtual Port) and OSC (127.0.0.1:8000)"
echo "   Press 'q' or 'ESC' to quit."
echo ""

python3 holistic_tracker.py

# Deactivate on exit
deactivate

echo ""
echo "👋 Virtual Conductor closed."
