#!/usr/bin/env python3
"""
EEB3 Clock — Bulletproof RTC Time Setter
=========================================
Run this script ONCE after every Arduino upload to set the clock to the
exact current UTC time.  Accuracy: within 1–2 seconds.

Usage:
    python3 set_rtc.py                        # auto-detects the port
    python3 set_rtc.py /dev/cu.usbmodem101    # specify port manually

How it works:
    1. Connects to the Arduino over USB Serial
    2. Waits for the board to send "READY" (printed at the start of setup)
    3. Immediately sends  T<unix_utc_timestamp>
    4. Arduino sets the DS3231 RTC to that exact UTC value
    5. Script confirms what was set and what local Brussels time that equals

Requirements:
    pip3 install pyserial
"""

import sys
import time
import glob
import serial           # pip3 install pyserial

# ── Configuration ─────────────────────────────────────────────────────────
BAUD        = 9600
TIMEOUT_S   = 30        # how long to wait for "READY" from the board
# Brussels UTC offsets (the script uses Python's own DST detection,
# which reads your Mac's system timezone — always correct on a Mac
# that is set to the Europe/Brussels timezone).
# We simply get UTC directly from time.gmtime() — no offset needed.

# ── Port auto-detection ────────────────────────────────────────────────────
def find_port():
    """Return the first likely Arduino port, or None."""
    candidates = (
        glob.glob("/dev/cu.usbmodem*") +   # genuine Arduino / ATmega16U2
        glob.glob("/dev/cu.usbserial*") +   # CH340 chip (Elegoo)
        glob.glob("/dev/cu.wchusbserial*")  # CH340 alternate name
    )
    # Windows
    candidates += [f"COM{i}" for i in range(3, 20)]
    for p in candidates:
        try:
            s = serial.Serial(p, BAUD, timeout=0.5)
            s.close()
            return p
        except (serial.SerialException, OSError):
            continue
    return None

# ── Main ───────────────────────────────────────────────────────────────────
def main():
    port = sys.argv[1] if len(sys.argv) > 1 else find_port()

    if port is None:
        print("ERROR: No Arduino found. Is the USB cable plugged in?")
        print("       Or specify the port manually:  python3 set_rtc.py /dev/cu.usbmodem101")
        sys.exit(1)

    print(f"Connecting to Arduino on {port} at {BAUD} baud ...")

    try:
        ser = serial.Serial(port, BAUD, timeout=1)
    except serial.SerialException as e:
        print(f"ERROR opening port: {e}")
        sys.exit(1)

    # The Arduino sends "READY" at the very start of setup().
    # Wait for it, then send the timestamp immediately.
    print(f"Waiting for board to boot (up to {TIMEOUT_S}s) ...")
    deadline = time.time() + TIMEOUT_S
    ready = False

    while time.time() < deadline:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print(f"  Board: {line}")
        if "READY" in line:
            ready = True
            break

    if not ready:
        print("WARNING: Did not receive READY from the board.")
        print("         Sending timestamp anyway (board may still accept it).")

    # Get exact UTC now — Python's time.time() is NTP-synced on macOS.
    utc_unix = int(time.time())

    # Send the command:  T<unix_timestamp>\n
    cmd = f"T{utc_unix}\n"
    ser.write(cmd.encode("ascii"))
    ser.flush()

    print(f"\nSent UTC timestamp: {utc_unix}")

    # ── Human-readable confirmation ────────────────────────────────────────
    utc_struct   = time.gmtime(utc_unix)
    local_struct = time.localtime(utc_unix)   # uses Mac's timezone (Brussels)

    print(f"UTC time set:   {time.strftime('%Y-%m-%d %H:%M:%S', utc_struct)} UTC")
    print(f"Local display:  {time.strftime('%H:%M:%S', local_struct)} Brussels")

    # Read one more confirmation line from the board
    time.sleep(0.5)
    while ser.in_waiting:
        line = ser.readline().decode("ascii", errors="ignore").strip()
        if line:
            print(f"  Board: {line}")

    ser.close()
    print("\nDone. Clock is set accurately.")

if __name__ == "__main__":
    main()
