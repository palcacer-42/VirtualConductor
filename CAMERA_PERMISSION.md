# Camera Permission Setup Guide

## Problem
You're seeing a **black window** because the camera permission has not been granted to Terminal/Python.

## Solution

### Option 1: Grant Permission via System Preferences (Recommended)

1. **Open System Preferences** (or System Settings on macOS Ventura+)
2. Navigate to: **Security & Privacy** → **Privacy** → **Camera**
3. Look for **Terminal** (or **iTerm** if you use that)
4. **Check the box** next to Terminal to enable camera access
5. **Close** your current Terminal window
6. **Open a new Terminal window**
7. Run the script again: `./run_hand_tracker.sh`

### Option 2: Reset Camera Permissions

If Terminal doesn't appear in the Camera list:

```bash
tccutil reset Camera
```

Then run the hand tracker script again, and macOS will prompt you to grant permission.

## Verification

After granting permission, you can verify it works by running:

```bash
cd ~/Documents/CODE/kiko
source venv/bin/activate
python test_camera.py
```

You should see:
```
✓ Camera opened successfully
✓ Frame read successful: True
✓ Frame shape: (height, width, 3)
```

## Important Notes

- **You must close and reopen Terminal** after granting permission
- The permission applies to the Terminal app, not individual scripts
- If using an IDE (like VS Code), grant camera permission to that IDE instead

---

Once permission is granted, the hand tracker will show:
- Your webcam feed (mirrored)
- Hand landmarks and connections
- Left/Right hand labels
