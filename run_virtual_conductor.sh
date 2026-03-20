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

# Run the tracker
echo "🚀 Launching Virtual Conductor (Face + Hands + Pose)..."
echo "   Output: Sending MIDI (Virtual Port) and OSC (127.0.0.1:8000)"
echo "   Close the window to quit."
echo ""

python3 virtual-conductor.py

# Deactivate on exit
deactivate

echo ""
echo "👋 Virtual Conductor closed."
