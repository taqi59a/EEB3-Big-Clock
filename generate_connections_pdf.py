#!/usr/bin/env python3
"""
EEB3 Clock — Connection Guide Generator
Run:    python generate_connections_pdf.py
Output: EEB3_Clock_Connections.pdf (same folder)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib import colors
import os

# ── Output path ────────────────────────────────────────────────────────────
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "EEB3_Clock_Connections.pdf")

# ── Page geometry (all in ReportLab points) ────────────────────────────────
PAGE_W, PAGE_H = A4               # 595.28 x 841.89 pts
ML = MR = 15.0 * mm              # 42.52 pts each
MT = MB = 18.0 * mm
BW = round(PAGE_W - ML - MR, 2)  # 510.28 pts  ← every table uses this

# ── Palette (greyscale only) ────────────────────────────────────────────────
C_BLACK  = colors.black
C_WHITE  = colors.white
C_DARK   = colors.HexColor("#111111")
C_MID    = colors.HexColor("#555555")
C_LGREY  = colors.HexColor("#cccccc")
C_PGREY  = colors.HexColor("#f2f2f2")
C_WARN   = colors.HexColor("#333333")

# ── Style factory ──────────────────────────────────────────────────────────
_sn = 0
def ST(**kw):
    global _sn; _sn += 1
    return ParagraphStyle(f"_conn_s{_sn}", **kw)

# Document text styles
S_TITLE = ST(fontName="Helvetica-Bold",    fontSize=20, leading=24,  textColor=C_BLACK, alignment=TA_CENTER, spaceAfter=2*mm)
S_SUB   = ST(fontName="Helvetica-Bold",    fontSize=11, leading=15,  textColor=C_MID,   alignment=TA_CENTER, spaceAfter=5*mm)
S_H1    = ST(fontName="Helvetica-Bold",    fontSize=11, leading=15,  textColor=C_BLACK, spaceBefore=4*mm, spaceAfter=2*mm)
S_BODY  = ST(fontName="Helvetica",         fontSize=8.2,leading=12,  textColor=C_DARK,  alignment=TA_LEFT,    spaceAfter=2*mm)
S_WARN  = ST(fontName="Helvetica-Bold",    fontSize=8,  leading=11.5,textColor=C_WHITE,
            borderPad=4, borderWidth=0, backColor=C_WARN, spaceAfter=2*mm, alignment=TA_CENTER)
S_FOOT  = ST(fontName="Helvetica-Oblique", fontSize=8,  leading=11,  textColor=C_MID,   alignment=TA_CENTER)

# Table cell styles
S_TH = ST(fontName="Helvetica-Bold",  fontSize=8,   leading=11, textColor=C_WHITE)
S_TD = ST(fontName="Helvetica",       fontSize=7.8, leading=11, textColor=C_DARK)
S_TM = ST(fontName="Courier",         fontSize=7.5, leading=10, textColor=C_DARK)

def _w(*parts_mm):
    """Convert mm values to pts, give last col the remainder to guarantee sum=BW."""
    pts = [round(p * mm, 2) for p in parts_mm]
    pts.append(round(BW - sum(pts), 2))
    return pts

def SP(h=3*mm):   return Spacer(1, h)
def HR(t=0.5, c=C_LGREY): return HRFlowable(width="100%", thickness=t,
                                              color=c, spaceAfter=3*mm, spaceBefore=1*mm)

def section_box(text):
    c = Paragraph(text, ST(fontName="Helvetica-Bold", fontSize=10,
                            leading=14, textColor=C_WHITE))
    t = Table([[c]], colWidths=[BW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_BLACK),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 8),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
    ]))
    return t

def make_table(headers, rows, col_widths, mono_cols=None):
    if mono_cols is None:
        mono_cols = set()

    total = round(sum(col_widths), 1)
    expected = round(BW, 1)
    assert abs(total - expected) < 1.0, \
        f"Column widths sum to {total:.1f} but BW={expected:.1f}"

    data = [[Paragraph(h, S_TH) for h in headers]]

    for row in rows:
        data.append([
            Paragraph(str(cell), S_TM if ci in mono_cols else S_TD)
            for ci, cell in enumerate(row)
        ])

    cmds = [
        ("BACKGROUND",    (0, 0), (-1,  0),  C_BLACK),
        ("GRID",          (0, 0), (-1, -1),  0.3, C_LGREY),
        ("LINEBELOW",     (0, 0), (-1,  0),  0.5, C_LGREY),
        ("VALIGN",        (0, 0), (-1, -1),  "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1),  6),
        ("RIGHTPADDING",  (0, 0), (-1, -1),  6),
        ("TOPPADDING",    (0, 0), (-1, -1),  2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1),  2.5),
    ]
    for i in range(1, len(data)):
        bg = C_PGREY if i % 2 == 0 else C_WHITE
        cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

    t = Table(data, colWidths=col_widths, splitByRow=1)
    t.setStyle(TableStyle(cmds))
    return t

def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(C_LGREY)
    canvas.setLineWidth(0.4)
    canvas.line(ML, h - MT + 4*mm, w - MR, h - MT + 4*mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_MID)
    canvas.drawString(ML,       h - MT + 6*mm, "EEB3 SOLID-STATE CLOCK — Connections Reference Guide")
    canvas.drawRightString(w - MR, h - MT + 6*mm, "European School of Brussels, Ixelles")
    canvas.line(ML, MB - 4*mm, w - MR, MB - 4*mm)
    canvas.drawCentredString(w / 2, MB - 8*mm, f"Page {doc.page}")
    canvas.restoreState()

# ═════════════════════════════════════════════════════════════════════════════
# STORY
# ═════════════════════════════════════════════════════════════════════════════
story = []

# ─── PAGE 1: TITLE & POWER & RTC ─────────────────────────────────────────────
story += [
    SP(2*mm),
    Paragraph("EEB3 SOLID-STATE CLOCK", S_TITLE),
    Paragraph("Hardware Wiring & Connection Guide (Parallel Power & Opto-Isolation)", S_SUB),
    HR(1.0, C_BLACK),
    SP(1*mm),
    
    section_box("1. POWER WIRING (5V / 3A Regulated Parallel Power Setup)"),
    SP(2*mm),
    Paragraph("<b>Wiring Goal:</b> Power the Arduino Mega and the 4 relay modules from the same 5V adapter. "
              "To isolate the Arduino from coil noise, <b>remove the yellow jumpers</b> on all relay boards.", S_BODY),
    make_table(
        ["Connection Line", "From", "To Pin", "Connection Notes / Details"],
        [
            ["Main Adapter Power (+)", "External 5V (+) Power Rail", "Mega 5V (Header Pin) & all 4 relay boards JD-VCC pins", "<b>CRITICAL:</b> Yellow JD-VCC jumper MUST be removed on all boards."],
            ["Main Adapter Ground (-)", "External 5V (-) Ground Rail", "Mega GND (Header Pin) & all 4 relay boards GND pins (on 3-pin headers)", "Provides a clean common return path for both logic and coils."],
            ["Optocoupler Power", "Arduino Mega 5V", "All 4 relay boards VCC pins (on 10-pin headers)", "Powers the opto-isolation diodes from the Mega's regulated 5V line."],
            ["Signal Control Lines", "Arduino Mega Pins 22-53", "IN1 to IN8 on 10-pin headers", "Do NOT bridge Arduino GND to the 10-pin header GND. Leave it disconnected."]
        ],
        _w(40, 42, 50)
    ),
    SP(4*mm),
    
    section_box("2. DS3231 RTC (Real-Time Clock) CONNECTIONS"),
    SP(2*mm),
    Paragraph("<b>Note:</b> Wire the RTC DS3231 module directly to the Arduino Mega using the hardware I2C pins. "
              "Pins 20 and 21 are the <i>only</i> hardware I2C pins on the Mega.", S_BODY),
    make_table(
        ["RTC Pin", "Arduino Mega Pin", "Function", "Connection Details / Notes"],
        [
            ["VCC", "Mega 5V (POWER header)", "Logic Supply", "Draws only ~2 mA. Completely safe to power from Arduino Mega's 5V line."],
            ["GND", "Mega GND", "Ground", "Common ground reference."],
            ["SDA", "Mega Pin 20", "I2C Data", "Hardware SDA on Arduino Mega (do not use Uno A4)."],
            ["SCL", "Mega Pin 21", "I2C Clock", "Hardware SCL on Arduino Mega (do not use Uno A5)."]
        ],
        _w(20, 38, 22),
        mono_cols={0, 1}
    ),
    SP(4*mm),
    
    section_box("3. RELAY BOARD TO BULB MAIN SIDE (220V AC WIRING)"),
    SP(2*mm),
    make_table(
        ["Relay Terminal", "Wire Connects To", "Relay State OFF", "Relay State ON"],
        [
            ["COM (Common)", "Mains 220V Live Wire", "Mains connected to common terminal", "Mains connected to common terminal"],
            ["NO (Normally Open)", "Light Bulb Terminal A", "Open Circuit (Bulb is OFF)", "Closed Circuit (Bulb is ON)"],
            ["NC (Normally Closed)", "Leave Unconnected", "Closed Circuit", "Open Circuit"]
        ],
        _w(32, 42, 50),
        mono_cols={0, 2, 3}
    ),
    SP(3*mm),
    Paragraph("WARNING: 220V wiring carries lethal voltages. All mains connections must be fused, insulated, "
              "and enclosed in a protective chassis. Ensure mains power is disconnected before wiring.", S_WARN),
    PageBreak()
]

# ─── PAGE 2: SIGNAL MAPPING & DIGIT LAYOUT ────────────────────────────────────
story += [
    section_box("4. SIGNAL CONTROL WIRE PINMAPS (Arduino Mega Pins 22 to 53)"),
    SP(2*mm),
    Paragraph("The signal cables connect the Arduino Mega's double-row header to the 10-pin header on each relay board.", S_BODY),
    
    # Grid table for Modules 1 & 2
    Paragraph("<b>Module 1 (Hours Tens) & Module 2 (Hours Units)</b>", ST(fontName="Helvetica-Bold", fontSize=8.5, leading=11, spaceAfter=1.5*mm)),
    make_table(
        ["Relay IN", "Module 1 Pin", "Segment", "Frame", "Relay IN", "Module 2 Pin", "Segment", "Frame"],
        [
            ["IN1", "Pin 22", "f (Top-Left)", "1.1", "IN1", "Pin 30", "f (Top-Left)", "2.1"],
            ["IN2", "Pin 23", "a (Top)", "1.2", "IN2", "Pin 31", "a (Top)", "2.2"],
            ["IN3", "Pin 24", "b (Top-Right)", "1.3", "IN3", "Pin 32", "b (Top-Right)", "2.3"],
            ["IN4", "Pin 25", "g (Middle)", "1.4", "IN4", "Pin 33", "g (Middle)", "2.4"],
            ["IN5", "Pin 26", "e (Bottom-Left)", "1.5", "IN5", "Pin 34", "e (Bottom-Left)", "2.5"],
            ["IN6", "Pin 27", "c (Bottom-Right)", "1.6", "IN6", "Pin 35", "c (Bottom-Right)", "2.6"],
            ["IN7", "Pin 28", "d (Bottom)", "1.7", "IN7", "Pin 36", "d (Bottom)", "2.7"],
            ["IN8", "Pin 29", "Colon Dots", "1.8", "IN8", "Pin 37", "Unused / Empty", "—"]
        ],
        _w(16, 18, 28, 12, 16, 18, 28),
        mono_cols={0, 1, 3, 4, 5, 7}
    ),
    SP(3*mm),

    # Grid table for Modules 3 & 4
    Paragraph("<b>Module 3 (Minutes Tens) & Module 4 (Minutes Units)</b>", ST(fontName="Helvetica-Bold", fontSize=8.5, leading=11, spaceAfter=1.5*mm)),
    make_table(
        ["Relay IN", "Module 3 Pin", "Segment", "Frame", "Relay IN", "Module 4 Pin", "Segment", "Frame"],
        [
            ["IN1", "Pin 38", "f (Top-Left)", "3.1", "IN1", "Pin 53", "f (Top-Left)", "4.1"],
            ["IN2", "Pin 39", "a (Top)", "3.2", "IN2", "Pin 52", "a (Top)", "4.2"],
            ["IN3", "Pin 40", "b (Top-Right)", "3.3", "IN3", "Pin 48", "b (Top-Right)", "4.3"],
            ["IN4", "Pin 41", "g (Middle)", "3.4", "IN4", "Pin 50", "g (Middle)", "4.4"],
            ["IN5", "Pin 42", "e (Bottom-Left)", "3.5", "IN5", "Pin 49", "e (Bottom-Left)", "4.5"],
            ["IN6", "Pin 43", "c (Bottom-Right)", "3.6", "IN6", "Pin 51", "c (Bottom-Right)", "4.6"],
            ["IN7", "Pin 44", "d (Bottom)", "3.7", "IN7", "Pin 46", "d (Bottom)", "4.7"],
            ["IN8", "Pin 45", "Unused / Empty", "—", "IN8", "Pin 47", "Unused / Empty", "—"]
        ],
        _w(16, 18, 28, 12, 16, 18, 28),
        mono_cols={0, 1, 3, 4, 5, 7}
    ),
    Paragraph("<b>Module 4 wiring-swap fix:</b> unlike Modules 1-3, Module 4's connector pins are "
              "NOT in sequential IN1-IN8 order. IN3 is on Pin 48 and IN6 is on Pin 51 — the reverse "
              "of what a naive sequential wiring would suggest. This was a confirmed jumbled-connector "
              "fix; wire Module 4 exactly as tabulated above, not by pin-number order.", S_BODY),
    SP(4*mm),

    section_box("5. SEGMENT REF MAP (SEG2RELAY[7] = { 1, 2, 5, 6, 4, 0, 3 })"),
    SP(2*mm),
    Paragraph("The software controls digits by mapping standard segment indices (0-6 corresponding to a-g) "
              "to relay channels. The segment locations on the physical frame are shown below.", S_BODY),
    make_table(
        ["Segment Index", "Letter", "Relay Input Channel", "Standard Position on Clock Frame"],
        [
            ["0", "a", "IN2", "Top horizontal segment"],
            ["1", "b", "IN3", "Top-right vertical segment"],
            ["2", "c", "IN6", "Bottom-right vertical segment"],
            ["3", "d", "IN7", "Bottom horizontal segment"],
            ["4", "e", "IN5", "Bottom-left vertical segment"],
            ["5", "f", "IN1", "Top-left vertical segment"],
            ["6", "g", "IN4", "Middle horizontal segment"]
        ],
        _w(25, 18, 38),
        mono_cols={0, 1, 2}
    ),
    SP(6*mm),
    PageBreak(),

    section_box("6. WIRING VERIFICATION — DIAGNOSTIC MODE"),
    SP(2*mm),
    Paragraph("Once all signal and mains connections above are made, use the firmware's built-in "
              "diagnostic protocol to confirm every relay fires the correct bulb before buttoning "
              "up the enclosure — no need to wait for a particular time of day to test a segment.", S_BODY),
    make_table(
        ["Serial Command", "Effect"],
        [
            ["D1", "Enter diagnostic mode — clock display pauses, all relays forced OFF."],
            ["D0", "Exit diagnostic mode — normal HH:MM clock display resumes."],
            ["R&lt;m&gt;&lt;i&gt;&lt;s&gt;", "Fire one relay directly: m = module 0-3, i = relay index 0-7 (IN1=0 ... IN8=7), "
                            "s = 0/1. Example: R071 turns Module 0 IN8 (the colon) ON."],
        ],
        _w(30),
        mono_cols={0}
    ),
    SP(2*mm),
    Paragraph("<b>clock_diagnostics.html</b> (in the EEB3_Clock_Mega_Relay_PowerSaving folder) wraps this "
              "protocol in a browser UI: open it in Chrome or Edge (Web Serial required), click Connect and "
              "pick the Arduino's serial port, and it automatically sends D1 and exposes a Test button for "
              "every relay on every module — each press sends the matching R&lt;m&gt;&lt;i&gt;&lt;s&gt; command so you can "
              "trace bulb-to-relay wiring one channel at a time. Disconnecting sends D0 to resume the clock.", S_BODY),
    SP(6*mm),
    HR(0.8, C_BLACK),
    Paragraph("EEB3 Solid-State Clock Wiring Guide | European School of Brussels, Ixelles | Taqi Abbas", S_FOOT)
]

# ─────────────────────────────────────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=ML, rightMargin=MR,
    topMargin=MT,  bottomMargin=MB,
    title="EEB3 Big Clock Connections Reference Guide",
    author="Taqi Abbas",
    subject="Wiring and Pin Connection Schematics, Arduino MEGA 2560",
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"Done:\n  {OUT}")
