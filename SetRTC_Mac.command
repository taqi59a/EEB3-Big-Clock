#!/bin/bash
# EEB3 Clock — Set RTC Time (Mac)
# Double-click this file in Finder after every Arduino upload.
# It will open a Terminal, connect to the Arduino, and set the exact time.

# Move to the folder this script lives in (works from any location)
cd "$(dirname "$0")"

echo "================================================"
echo "  EEB3 Clock — RTC Time Setter"
echo "================================================"
echo ""

# Check Python3 is available
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 not found."
  echo "Install it from https://www.python.org/downloads/"
  read -p "Press Enter to close..."
  exit 1
fi

# Install pyserial silently if missing
python3 -c "import serial" 2>/dev/null || {
  echo "Installing required library (pyserial)..."
  pip3 install pyserial --quiet
}

# Run the time-setter script
python3 set_rtc.py

echo ""
read -p "Press Enter to close..."
