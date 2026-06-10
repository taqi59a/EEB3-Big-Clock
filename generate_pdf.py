#!/usr/bin/env python3
"""
EEB3 Clock — Technical Reference Booklet
Run:    python3 generate_pdf.py
Output: EEB3_Clock_Reference.pdf  (same folder)
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib import colors
import os

# ── Output path ────────────────────────────────────────────────────────────
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "EEB3_Clock_Reference.pdf")

# ── Page geometry (all in ReportLab points) ────────────────────────────────
PAGE_W, PAGE_H = A4               # 595.28 x 841.89 pts
ML = MR = 18.0 * mm              # 51.02 pts each
MT = MB = 22.0 * mm
BW = round(PAGE_W - ML - MR, 2)  # 493.23 pts  ← every table uses this

# ── Palette (greyscale only) ────────────────────────────────────────────────
C_BLACK  = colors.black
C_WHITE  = colors.white
C_DARK   = colors.HexColor("#111111")
C_MID    = colors.HexColor("#555555")
C_LGREY  = colors.HexColor("#cccccc")
C_PGREY  = colors.HexColor("#f2f2f2")
C_CODEBG = colors.HexColor("#e6e6e6")

# ── Style factory (unique names — avoids any global-registry collisions) ──
_sn = 0
def ST(**kw):
    global _sn; _sn += 1
    return ParagraphStyle(f"_s{_sn}", **kw)

# Document text styles
S_CVT  = ST(fontName="Helvetica-Bold",    fontSize=60, leading=66,  textColor=C_BLACK, spaceAfter=2*mm)
S_CVS  = ST(fontName="Helvetica-Bold",    fontSize=22, leading=28,  textColor=C_MID,  spaceAfter=4*mm)
S_CVB  = ST(fontName="Helvetica",         fontSize=12, leading=17,  textColor=C_DARK, spaceAfter=2*mm)
S_CVM  = ST(fontName="Helvetica-Oblique", fontSize=9,  leading=13,  textColor=C_MID,  spaceAfter=1*mm)
S_H1   = ST(fontName="Helvetica-Bold",    fontSize=13, leading=17,  textColor=C_BLACK, spaceBefore=5*mm, spaceAfter=2*mm)
S_H2   = ST(fontName="Helvetica-Bold",    fontSize=10, leading=14,  textColor=C_BLACK, spaceBefore=3*mm, spaceAfter=1.5*mm)
S_BODY = ST(fontName="Helvetica",         fontSize=8.5,leading=12.5,textColor=C_DARK, alignment=TA_JUSTIFY, spaceAfter=2*mm)
S_BODL = ST(fontName="Helvetica",         fontSize=8.5,leading=12.5,textColor=C_DARK, alignment=TA_LEFT,    spaceAfter=1.5*mm)
S_NOTE = ST(fontName="Helvetica-Oblique", fontSize=7.5,leading=11,  textColor=C_MID,  spaceAfter=1.5*mm)
S_WARN = ST(fontName="Helvetica-Bold",    fontSize=8,  leading=11.5,textColor=C_BLACK,
            borderPad=3, borderWidth=0.6, borderColor=C_BLACK, backColor=C_PGREY, spaceAfter=2*mm)
S_CODE = ST(fontName="Courier",           fontSize=7.2,leading=10,  textColor=C_BLACK,
            leftIndent=3*mm, spaceAfter=0)
S_FOOT = ST(fontName="Helvetica-Oblique", fontSize=8,  leading=11,  textColor=C_MID, alignment=TA_CENTER)

# Table cell styles — created once, reused everywhere
# All body cells: Helvetica 7.5pt — fits comfortably in narrow columns
S_TH = ST(fontName="Helvetica-Bold",  fontSize=8,   leading=11, textColor=C_WHITE)
S_TD = ST(fontName="Helvetica",       fontSize=7.5, leading=11, textColor=C_DARK)
S_TM = ST(fontName="Courier",         fontSize=7.2, leading=10, textColor=C_DARK)

# ── Pre-computed column widths (must sum to BW = 493.23 pts) ──────────────
# These are the column widths in pts for every table in the document.
# NEVER pass arithmetic into make_table — use these named values only.

def _w(*parts_mm):
    """Convert mm values to pts, give last col the remainder to guarantee sum=BW."""
    pts = [round(p * mm, 2) for p in parts_mm[:-1]]
    pts.append(round(BW - sum(pts), 2))
    return pts

# ── Helpers ────────────────────────────────────────────────────────────────
def SP(h=3*mm):   return Spacer(1, h)
def HR(t=0.5, c=C_LGREY): return HRFlowable(width="100%", thickness=t,
                                              color=c, spaceAfter=3*mm, spaceBefore=1*mm)

def section_box(text):
    c = Paragraph(text, ST(fontName="Helvetica-Bold", fontSize=11,
                            leading=15, textColor=C_WHITE))
    t = Table([[c]], colWidths=[BW])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), C_BLACK),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 7),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
    ]))
    return t

def make_table(headers, rows, col_widths, mono_cols=None):
    """
    headers    : list of header strings
    rows       : list of lists of strings
    col_widths : list of widths in pts — use _w() helper, must sum to BW
    mono_cols  : set of 0-based column indices to render in Courier
    """
    if mono_cols is None:
        mono_cols = set()

    # Verify total width (catches bugs immediately)
    total = round(sum(col_widths), 1)
    expected = round(BW, 1)
    assert abs(total - expected) < 1.0, \
        f"Column widths sum to {total:.1f} but BW={expected:.1f}"

    # Header row
    data = [[Paragraph(h, S_TH) for h in headers]]

    # Data rows — explicit Paragraph for every cell guarantees word-wrap
    for row in rows:
        data.append([
            Paragraph(str(cell), S_TM if ci in mono_cols else S_TD)
            for ci, cell in enumerate(row)
        ])

    # Build alternating-row style commands explicitly
    # (ROWBACKGROUNDS has a known rendering bug in ReportLab 4.5.x)
    cmds = [
        ("BACKGROUND",    (0, 0), (-1,  0),  C_BLACK),
        ("GRID",          (0, 0), (-1, -1),  0.3, C_LGREY),
        ("LINEBELOW",     (0, 0), (-1,  0),  0.5, C_LGREY),
        ("VALIGN",        (0, 0), (-1, -1),  "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1),  5),
        ("RIGHTPADDING",  (0, 0), (-1, -1),  5),
        ("TOPPADDING",    (0, 0), (-1, -1),  3),
        ("BOTTOMPADDING", (0, 0), (-1, -1),  3),
    ]
    # Alternate grey/white rows starting from row 1
    for i in range(1, len(data)):
        bg = C_PGREY if i % 2 == 0 else C_WHITE
        cmds.append(("BACKGROUND", (0, i), (-1, i), bg))

    t = Table(data, colWidths=col_widths, splitByRow=1)
    t.setStyle(TableStyle(cmds))
    return t

# ─────────────────────────────────────────────────────────────────────────────
# HEADER / FOOTER CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────
def on_first_page(canvas, doc):
    pass   # cover has no header/footer

def on_page(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(C_LGREY)
    canvas.setLineWidth(0.4)
    canvas.line(ML, h - MT + 6*mm, w - MR, h - MT + 6*mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_MID)
    canvas.drawString(ML,       h - MT + 8*mm, "EEB3 BIG CLOCK — Technical Reference")
    canvas.drawRightString(w - MR, h - MT + 8*mm, "European School of Brussels, Ixelles")
    canvas.line(ML, MB - 4*mm, w - MR, MB - 4*mm)
    canvas.drawCentredString(w / 2, MB - 9*mm, str(doc.page))
    canvas.restoreState()

# ─────────────────────────────────────────────────────────────────────────────
# CODE TEXT (full listing)
# ─────────────────────────────────────────────────────────────────────────────
CODE_TEXT = """\
/* ============================================================================
   EEB3 BIG CLOCK  -  220V bulb 7-segment digits driven by 4x 8-relay modules
   ----------------------------------------------------------------------------
   Board : Arduino MEGA 2560
   Clock : DS3231 RTC (I2C)  -  RTC is kept in UTC, local time is computed in
           software so Brussels daylight-saving is handled WITHOUT ever touching
           the hardware (no buttons needed). Good for 20+ years.

   Display layout (HH:MM):
        [Module 1]  [Module 2]   :   [Module 3]  [Module 4]
         hours-tens  hours-units      mins-tens   mins-units
                        colon (the two dots) = relay 8 of Module 1

   SEGMENT MAP  (matches your "clock frame numbered.jpg"):
        relay 1 -> segment f (top-left)      x.1
        relay 2 -> segment a (top)           x.2
        relay 3 -> segment b (top-right)     x.3
        relay 4 -> segment g (middle)        x.4
        relay 5 -> segment e (bottom-left)   x.5
        relay 6 -> segment c (bottom-right)  x.6
        relay 7 -> segment d (bottom)        x.7
        relay 8 -> (Module 1 only) the colon dots   1.8
                   (relay 8 of modules 2,3,4 is unused)

   BEHAVIOUR
     - Normal:        shows HH:MM, colon ON steady (NEVER blinks -> saves the
                      colon relay from millions of pointless switch cycles).
     - At second 58:  shows "EEb3", colon OFF  (during active periods only).
     - At second 59:  shows the current period number, colon OFF  (periods only).
                      During breaks/gaps/before P1/after P9 -> plain time.
     - Outside 08:00-17:00: all 32 relays OFF - completely dark.

   RELIABILITY ("long life") choices made on purpose:
     - A relay is only switched when that segment actually changes state.
     - The colon does not blink.
     - All relays rest completely outside school hours (08:00-17:00).
     - Hardware watchdog reboots the Mega automatically if it ever hangs.
     - RTC is read defensively; garbage reads are ignored.
   ============================================================================ */

#include <Wire.h>
#include <RTClib.h>
#include <avr/wdt.h>

RTC_DS3231 rtc;

/* ----------------------------------------------------------------------------
   1) RTC TIME SYNC  -  bulletproof two-stage system

   STAGE 1 (primary, millisecond-accurate):
     After every upload, run  python3 set_rtc.py  in Terminal.
     The script sends the exact current UTC to the Arduino over Serial.
     The Arduino sets the RTC from that - accurate to within 1 second.
     Your Mac clock is NTP-synced so this is always correct.

   STAGE 2 (automatic fallback):
     If the Python script is NOT run within SERIAL_WAIT_MS milliseconds,
     the Arduino falls back to the compile-time stamp from your Mac clock,
     automatically converted from Brussels local time to UTC.
     This is typically 10-20 seconds behind real time - fine for a clock.

   SERIAL_WAIT_MS   How long to wait for the Python script (milliseconds).
                    5000 = 5 seconds.
---------------------------------------------------------------------------- */
#define SERIAL_WAIT_MS   5000UL

/* ----------------------------------------------------------------------------
   2) RELAY POLARITY
   The common blue 8-relay boards are ACTIVE LOW (IN pin LOW = relay ON).
   If your board turns the bulb ON when the IN pin is HIGH, set this to false.
---------------------------------------------------------------------------- */
#define RELAY_ACTIVE_LOW    true

/* ----------------------------------------------------------------------------
   3) DISPLAY OPTIONS
---------------------------------------------------------------------------- */
#define BLANK_LEADING_HOUR_ZERO  true   // " 9:05" instead of "09:05"
const uint8_t EEB3_SECOND   = 58;      // second :58 shows "EEb3" (periods only)
const uint8_t PERIOD_SECOND = 59;      // second :59 shows period label (periods only)

/* ----------------------------------------------------------------------------
   3b) OPERATING HOURS
   Outside these hours ALL relays are switched OFF completely.
   This gives the relay contacts a long rest every day and maximises
   the lifespan of all 32 relays and the light bulbs.
   Times in LOCAL Brussels time, minutes from midnight.
   08:00 = 8*60 = 480     17:00 = 17*60 = 1020
---------------------------------------------------------------------------- */
const int CLOCK_ON_MINS  = 8  * 60;    // 08:00 - relays wake up
const int CLOCK_OFF_MINS = 17 * 60;    // 17:00 - relays go to sleep

/* ----------------------------------------------------------------------------
   4) PIN MAP  -  each module's 8 IN pins kept together in one neat block.
      Module N: { IN1, IN2, IN3, IN4, IN5, IN6, IN7, IN8 }
      (index 0 = IN1 = relay 1 = segment f ... see SEGMENT MAP above)
---------------------------------------------------------------------------- */
const uint8_t PINS[4][8] = {
  { 22, 23, 24, 25, 26, 27, 28, 29 },   // Module 1  (hours tens)  + colon on IN8
  { 30, 31, 32, 33, 34, 35, 36, 37 },   // Module 2  (hours units)
  { 38, 39, 40, 41, 42, 43, 44, 45 },   // Module 3  (minutes tens)
  { 46, 47, 48, 49, 50, 51, 52, 53 }    // Module 4  (minutes units)
};
const uint8_t COLON_RELAY_INDEX = 7;    // IN8 of module 1 (0-based index 7)

//                          a  b  c  d  e  f  g
const uint8_t SEG2RELAY[7] = {1, 2, 5, 6, 4, 0, 3};

/* ----------------------------------------------------------------------------
   5) BELL SCHEDULE  (LOCAL Brussels time, minutes from midnight)
      Edit freely. disp must be exactly 4 characters.
      Break (10:55-11:15) is a gap - no entry - clock shows plain time.
---------------------------------------------------------------------------- */
struct Period { int startMins; int endMins; const char* disp; };

Period schedule[] = {
  { 8 * 60 + 30,  9 * 60 + 15, "P  1" },
  { 9 * 60 + 20, 10 * 60 +  5, "P  2" },
  {10 * 60 + 10, 10 * 60 + 55, "P  3" },
  // 10:55 - 11:15  BREAK  - gap in schedule, shows time only
  {11 * 60 + 15, 12 * 60 +  0, "P  4" },
  {12 * 60 +  5, 12 * 60 + 50, "P  5" },
  {13 * 60 +  0, 13 * 60 + 45, "P  6" },
  {13 * 60 + 50, 14 * 60 + 35, "P  7" },
  {14 * 60 + 40, 15 * 60 + 25, "P  8" },
  {15 * 60 + 30, 16 * 60 + 15, "P  9" }
  // 16:15 - 17:00  after last period - shows time only
};
const int NUM_PERIODS = sizeof(schedule) / sizeof(schedule[0]);

const char* getActivePeriod(int localMins) {
  for (int i = 0; i < NUM_PERIODS; i++)
    if (localMins >= schedule[i].startMins && localMins < schedule[i].endMins)
      return schedule[i].disp;
  return nullptr;
}

/* ============================================================================
   7-SEGMENT FONT
   bit0=a bit1=b bit2=c bit3=d bit4=e bit5=f bit6=g
   ============================================================================ */
byte segMask(char ch) {
  switch (ch) {
    case '0': return 0b0111111;
    case '1': return 0b0000110;
    case '2': return 0b1011011;
    case '3': return 0b1001111;
    case '4': return 0b1100110;
    case '5': return 0b1101101;
    case '6': return 0b1111101;
    case '7': return 0b0000111;
    case '8': return 0b1111111;
    case '9': return 0b1101111;
    case 'E': return 0b1111001;
    case 'b': return 0b1111100;
    case 'P': return 0b1110011;
    case 'r': return 0b1010000;
    case 'c': return 0b1011000;
    case 'd': return 0b1011110;
    case '-': return 0b1000000;
    case ' ':
    default:  return 0b0000000;
  }
}

/* ============================================================================
   EU / BRUSSELS DAYLIGHT-SAVING  (rule based, no lookup table needed)
   Summer time (CEST, UTC+2): last Sunday of March 01:00 UTC ->
                              last Sunday of October 01:00 UTC.
   Otherwise winter time (CET, UTC+1).
   ============================================================================ */
uint8_t lastSundayDay(uint16_t year, uint8_t month) {
  DateTime lastDay(year, month, 31, 0, 0, 0);
  uint8_t dow = lastDay.dayOfTheWeek();        // 0 = Sunday
  return 31 - dow;
}

bool isEuSummerTime(const DateTime& u) {
  uint8_t m = u.month();
  if (m < 3 || m > 10) return false;
  if (m > 3 && m < 10) return true;
  uint8_t ls = lastSundayDay(u.year(), m);
  if (m == 3) {
    if (u.day() > ls) return true;
    if (u.day() < ls) return false;
    return u.hour() >= 1;
  } else {
    if (u.day() < ls) return true;
    if (u.day() > ls) return false;
    return u.hour() < 1;
  }
}

DateTime utcToBrussels(const DateTime& utc) {
  int offsetHours = isEuSummerTime(utc) ? 2 : 1;
  return utc + TimeSpan(0, offsetHours, 0, 0);
}

bool isLocalBrusselsSummerTime(const DateTime& local) {
  uint8_t m = local.month();
  if (m < 3 || m > 10) return false;
  if (m > 3 && m < 10) return true;
  uint8_t ls = lastSundayDay(local.year(), m);
  if (m == 3) {
    if (local.day() > ls) return true;
    if (local.day() < ls) return false;
    return local.hour() >= 2;
  } else {
    if (local.day() < ls) return true;
    if (local.day() > ls) return false;
    return local.hour() < 3;
  }
}

DateTime brusselsLocalToUtc(const DateTime& local) {
  int offsetHours = isLocalBrusselsSummerTime(local) ? 2 : 1;
  return local - TimeSpan(0, offsetHours, 0, 0);
}

/* ============================================================================
   RELAY OUTPUT with change-tracking (only switch when state actually changes)
   ============================================================================ */
bool relayState[4][8];

inline void writeRelay(uint8_t module, uint8_t idx, bool on) {
  if (relayState[module][idx] == on) return;
  relayState[module][idx] = on;
  uint8_t level = (on == RELAY_ACTIVE_LOW) ? LOW : HIGH;
  digitalWrite(PINS[module][idx], level);
}

// Turn every relay OFF - used outside operating hours.
// writeRelay() skips pins already off, so zero clicks once already dark.
void allRelaysOff() {
  for (uint8_t m = 0; m < 4; m++)
    for (uint8_t i = 0; i < 8; i++)
      writeRelay(m, i, false);
}

void applyDigit(uint8_t module, char ch) {
  byte mask = segMask(ch);
  for (uint8_t seg = 0; seg < 7; seg++) {
    bool on = mask & (1 << seg);
    writeRelay(module, SEG2RELAY[seg], on);
  }
}

void setColon(bool on) {
  writeRelay(0, COLON_RELAY_INDEX, on);
}

void renderFrame(const char d[4], bool colonOn) {
  for (uint8_t m = 0; m < 4; m++) applyDigit(m, d[m]);
  setColon(colonOn);
}

/* ============================================================================
   SETUP
   ============================================================================ */
void setup() {
  Serial.begin(9600);

  // Force all relay outputs OFF before enabling them (no boot glitch)
  for (uint8_t m = 0; m < 4; m++) {
    for (uint8_t i = 0; i < 8; i++) {
      uint8_t offLevel = RELAY_ACTIVE_LOW ? HIGH : LOW;
      digitalWrite(PINS[m][i], offLevel);
      pinMode(PINS[m][i], OUTPUT);
      digitalWrite(PINS[m][i], offLevel);
      relayState[m][i] = false;
    }
  }

  Wire.begin();
  if (!rtc.begin()) {
    Serial.println(F("RTC not found! Check wiring (SDA=20, SCL=21)."));
  }

  Serial.println(F("READY"));

  bool synced = false;
  unsigned long waitStart = millis();
  while ((millis() - waitStart) < SERIAL_WAIT_MS) {
    if (Serial.available()) {
      char cmd = Serial.read();
      if (cmd == 'T') {
        unsigned long unixUtc = Serial.parseInt();
        if (unixUtc > 1700000000UL) {
          rtc.adjust(DateTime(unixUtc));
          Serial.print(F("RTC SET via script -> UTC: "));
          Serial.println(DateTime(unixUtc).timestamp());
          synced = true;
          break;
        }
      }
    }
  }

  if (!synced) {
    DateTime compileLocal(F(__DATE__), F(__TIME__));
    DateTime utcNow = brusselsLocalToUtc(compileLocal);
    rtc.adjust(utcNow);
    Serial.print(F("RTC FALLBACK (compile time) -> UTC: "));
    Serial.println(utcNow.timestamp());
    Serial.println(F("Run  python3 set_rtc.py  for exact time next upload."));
  }

  wdt_enable(WDTO_8S);
}

/* ============================================================================
   LOOP
   ============================================================================ */
int   lastRenderedSecondKey = -1;

void loop() {
  wdt_reset();

  static unsigned long lastTick = 0;
  if (millis() - lastTick < 200) return;
  lastTick = millis();

  DateTime utc = rtc.now();
  if (utc.year() < 2024 || utc.year() > 2099) return;

  DateTime local = utcToBrussels(utc);
  uint8_t hh = local.hour();
  uint8_t mm = local.minute();
  uint8_t ss = local.second();
  int localMins = hh * 60 + mm;

  // Outside 08:00-17:00: all relays off. Sentinel -2 prevents repeat clicks.
  if (localMins < CLOCK_ON_MINS || localMins >= CLOCK_OFF_MINS) {
    if (lastRenderedSecondKey != -2) {
      lastRenderedSecondKey = -2;
      allRelaysOff();
      Serial.println(F("Clock OFF (outside operating hours)."));
    }
    return;
  }

  // EEb3/:59 only during active periods. Breaks/gaps/before P1/after P9
  // show plain time the entire minute.
  char frame[4];
  bool colonOn;

  const char* activePeriod = getActivePeriod(localMins);
  bool periodActive = (activePeriod != nullptr);

  if (periodActive && ss == EEB3_SECOND) {
    frame[0] = 'E'; frame[1] = 'E'; frame[2] = 'b'; frame[3] = '3';
    colonOn = false;
  }
  else if (periodActive && ss == PERIOD_SECOND) {
    frame[0] = activePeriod[0]; frame[1] = activePeriod[1];
    frame[2] = activePeriod[2]; frame[3] = activePeriod[3];
    colonOn = false;
  }
  else {
    frame[0] = (BLANK_LEADING_HOUR_ZERO && hh < 10) ? ' ' : ('0' + hh / 10);
    frame[1] = '0' + hh % 10;
    frame[2] = '0' + mm / 10;
    frame[3] = '0' + mm % 10;
    colonOn = true;
  }

  int key = (frame[0] << 24) ^ (frame[1] << 16) ^ (frame[2] << 8)
            ^ frame[3] ^ (colonOn ? 0x100000 : 0);
  if (key != lastRenderedSecondKey) {
    lastRenderedSecondKey = key;
    renderFrame(frame, colonOn);

    Serial.print(F("UTC "));   Serial.print(utc.timestamp());
    Serial.print(F("  Local "));
    Serial.print(hh); Serial.print(':');
    if (mm < 10) Serial.print('0'); Serial.print(mm);
    Serial.print(F("  period=")); Serial.print(periodActive ? activePeriod : "none");
    Serial.print(F("  showing "));
    Serial.write((const uint8_t*)frame, 4);
    Serial.print(F("  colon=")); Serial.println(colonOn ? "ON" : "off");
  }
}"""

# ═════════════════════════════════════════════════════════════════════════════
# STORY
# ═════════════════════════════════════════════════════════════════════════════
story = []

# ─── COVER ───────────────────────────────────────────────────────────────────
story += [SP(28*mm),
          Paragraph("EEB3", S_CVT),
          Paragraph("BIG CLOCK", S_CVS),
          HR(1.5, C_BLACK), SP(3*mm),
          Paragraph("220 V Bulb 7-Segment Display<br/>"
                    "Driven by 4 x 8-Relay Modules<br/>"
                    "Arduino MEGA 2560  +  DS3231 RTC", S_CVB),
          SP(50*mm), HR(0.5),
          Paragraph("Prepared by: <b>Taqi Abbas</b>", S_CVM),
          Paragraph("Location: European School of Brussels, Ixelles", S_CVM),
          Paragraph("Required library: RTClib by Adafruit (v2.x)", S_CVM),
          PageBreak()]

# ─── 1. SYSTEM OVERVIEW ──────────────────────────────────────────────────────
story += [section_box("1.  SYSTEM OVERVIEW"), SP(3*mm),
          Paragraph("What this clock does", S_H1),
          Paragraph(
            "A large wooden-frame wall clock for European School of Brussels, Ixelles. "
            "Each segment of each digit is an individual 220 V light bulb. "
            "Four 8-relay modules switch the bulbs (one module per digit). "
            "A DS3231 real-time clock module provides accurate timekeeping. "
            "An Arduino MEGA 2560 is the controller.", S_BODY),

          Paragraph("Display layout — HH:MM", S_H2),
          make_table(
            ["Position", "Module", "Mega pins", "Notes"],
            [["Digit 1 — hours tens",    "Module 1", "22–29", "IN8 (pin 29) = colon dots"],
             ["Digit 2 — hours units",   "Module 2", "30–37", "IN8 (pin 37) unused"],
             ["Digit 3 — minutes tens",  "Module 3", "38–45", "IN8 (pin 45) unused"],
             ["Digit 4 — minutes units", "Module 4", "46–53", "IN8 (pin 53) unused"]],
            _w(50, 28, 35),
            mono_cols={1, 2}),

          Paragraph("Relay-to-segment mapping (same for every module)", S_H2),
          Paragraph("Each relay IN pin drives one bulb segment. "
                    "The frame label e.g. 2.3 means digit 2, relay 3.", S_BODL),
          make_table(
            ["Relay / IN pin", "Segment", "Position on digit", "Frame label"],
            [["IN1", "f", "Top-left vertical",     "x.1"],
             ["IN2", "a", "Top horizontal",        "x.2"],
             ["IN3", "b", "Top-right vertical",    "x.3"],
             ["IN4", "g", "Middle horizontal",     "x.4"],
             ["IN5", "e", "Bottom-left vertical",  "x.5"],
             ["IN6", "c", "Bottom-right vertical", "x.6"],
             ["IN7", "d", "Bottom horizontal",     "x.7"],
             ["IN8", "—", "Colon dots (Module 1 only)", "1.8"]],
            _w(30, 18, 56),
            mono_cols={0, 1, 3}),
          PageBreak()]

# ─── 2. HARDWARE LIST ────────────────────────────────────────────────────────
story += [section_box("2.  HARDWARE LIST"), SP(3*mm),
          make_table(
            ["Component", "Qty"],
            [["Arduino MEGA 2560 (Elegoo or genuine)", "1"],
             ["DS3231 RTC module with CR2032 coin cell", "1"],
             ["8-channel 5 V relay module — active-LOW blue boards", "4"],
             ["External 5 V DC supply, minimum 3 A (relay boards only)", "1"],
             ["USB-B cable (printer style) for programming", "1"],
             ["220 V E27 bulbs — one per segment, two for the colon", "30"],
             ["Mains-rated cable for bulb wiring", "as needed"],
             ["CR2032 spare coin cell (RTC backup battery)", "1 spare"],
             ["DuPont jumper wires, female-to-male", "~50"],
             ["Screw-terminal power rail for 5 V distribution", "1"]],
            _w(18),   # 1 column fills BW, qty appended
          ),
          PageBreak()]

# Wait — hardware needs 2 cols. Fix:
story.pop()  # remove PageBreak
story.pop()  # remove that table
story += [make_table(
            ["Component", "Qty"],
            [["Arduino MEGA 2560 (Elegoo or genuine)", "1"],
             ["DS3231 RTC module with CR2032 coin cell", "1"],
             ["8-channel 5 V relay module — active-LOW blue boards", "4"],
             ["External 5 V DC supply, minimum 3 A (relay boards only)", "1"],
             ["USB-B cable (printer style) for programming", "1"],
             ["220 V E27 bulbs — one per segment, two for the colon", "30"],
             ["Mains-rated cable for bulb wiring", "as needed"],
             ["CR2032 spare coin cell (RTC backup battery)", "1 spare"],
             ["DuPont jumper wires, female-to-male", "~50"],
             ["Screw-terminal power rail for 5 V distribution", "1"]],
            _w(155),
          ),
          PageBreak()]

# ─── 3. CONNECTIONS ──────────────────────────────────────────────────────────
story += [section_box("3.  CONNECTIONS"), SP(3*mm)]

# 3a Power
story += [Paragraph("3a.  Power architecture", S_H1),
          Paragraph(
            "Relay coils draw up to 2.5 A combined — far beyond what the Mega USB "
            "or onboard 5 V regulator can supply. Use a separate external 5 V / 3 A "
            "supply for the relay boards. The Mega 5 V pin powers only the RTC (~2 mA).", S_BODY),
          make_table(
            ["Connection", "From", "To", "Note"],
            [["Relay board power",  "External 5V (+)", "All 4 boards VCC and JD-VCC", "Daisy-chain or power rail"],
             ["Relay board ground", "External 5V (−)", "All 4 boards GND", "Must also join Mega GND"],
             ["Mega ground bridge", "Mega GND near pin 53", "Common ground rail", "Ties both supplies together"],
             ["RTC power",         "Mega 5V pin",     "RTC VCC", "Only ~2 mA — safe from Mega"],
             ["RTC ground",        "Mega GND",        "RTC GND", ""],
             ["Mega power input",  "USB or 7-12 V barrel", "Mega board only", "Independent of relay supply"]],
            _w(38, 40, 50)),
          SP(3*mm)]

# 3b RTC
story += [Paragraph("3b.  RTC (DS3231) — 4 wires", S_H1),
          make_table(
            ["RTC pin", "Connect to", "Notes"],
            [["VCC", "Mega 5V (POWER header)", "Low current — Mega regulator is fine here"],
             ["GND", "Mega GND (any)",          ""],
             ["SDA", "Mega pin 20",             "Hardware I2C — only valid SDA pin on MEGA"],
             ["SCL", "Mega pin 21",             "Hardware I2C — only valid SCL pin on MEGA"]],
            _w(22, 52),
            mono_cols={0, 1}),
          Paragraph("Pins 20 and 21 are the ONLY hardware I2C pins on the Mega. "
                    "Do not use any other pins.", S_NOTE),
          SP(3*mm)]

# 3c Signal wires per module
story += [Paragraph("3c.  Signal wires — 32 wires total", S_H1),
          Paragraph(
            "All signal wires connect to the large double-row header at the top "
            "of the Mega (pins 22–53). Pin numbers are printed on the board.", S_BODL)]

SEG_NAMES = [
    "f — top-left vertical",  "a — top horizontal",
    "b — top-right vertical", "g — middle horizontal",
    "e — bottom-left vertical","c — bottom-right vertical",
    "d — bottom horizontal"
]
MOD_INFO = [
    ("Module 1 — HOURS TENS  +  colon on IN8", 22),
    ("Module 2 — HOURS UNITS  (IN8 unused)",   30),
    ("Module 3 — MINUTES TENS  (IN8 unused)",  38),
    ("Module 4 — MINUTES UNITS  (IN8 unused)", 46),
]
for mi, (label, start) in enumerate(MOD_INFO):
    rows = []
    for i in range(8):
        if i < 7:
            seg = SEG_NAMES[i]; fl = f"{mi+1}.{i+1}"
        else:
            seg = "colon dots" if mi == 0 else "unused — leave empty"
            fl  = "1.8"         if mi == 0 else "—"
        rows.append([f"IN{i+1}", f"pin {start+i}", seg, fl])
    story += [Paragraph(label, S_H2),
              make_table(["Board", "Mega", "Segment", "Frame label"],
                         rows, _w(18, 24, 88), mono_cols={0, 1, 3}),
              SP(2*mm)]

# 3d 220V
story += [Paragraph("3d.  220 V mains side", S_H1),
          Paragraph("Wire each bulb through COM to NO so it is off at power-up.", S_BODL),
          make_table(
            ["Terminal", "Connect to", "Relay OFF", "Relay ON"],
            [["COM", "Mains LIVE wire",   "—",              "—"],
             ["NO",  "Bulb terminal A",   "Open — bulb off", "Closed — bulb on"],
             ["NC",  "Leave unconnected", "Closed",          "Open"]],
            _w(22, 52, 44),
            mono_cols={0}),
          Paragraph(
            "WARNING: 220 V wiring must be installed and verified by a qualified "
            "electrician. All mains wiring must be fused and enclosed. "
            "Keep mains and low-voltage wiring physically separated.", S_WARN),
          PageBreak()]

# ─── 4. SETUP AND UPLOAD WORKFLOW ────────────────────────────────────────────
story += [section_box("4.  SETUP AND UPLOAD WORKFLOW"), SP(3*mm),

          Paragraph("Arduino IDE settings (do once, never change)", S_H1),
          make_table(
            ["Setting", "Value"],
            [["Board",      "Arduino Mega or Mega 2560"],
             ["Processor",  "ATmega2560 (Mega 2560)"],
             ["Port (Mac)", "/dev/cu.usbmodem101  or  /dev/cu.usbserial-XXXX"],
             ["Port (Win)", "COM3, COM4 … check Device Manager"],
             ["Library",    "RTClib by Adafruit — install via Library Manager"]],
            _w(32)),
          SP(3*mm),

          Paragraph("Every time you upload — exact two-step workflow", S_H1),
          Paragraph("The clock sets its own time automatically. "
                    "No manual UTC entry, no typing, no extra tools to install. "
                    "Your computer clock (NTP-synced) is the source of truth.", S_BODL),
          make_table(
            ["Step", "What you do", "What happens"],
            [["1",
              "Click Upload in Arduino IDE (as normal)",
              "IDE compiles the sketch and uploads it to the Mega. "
              "Takes about 10–15 seconds. The board resets and prints READY on Serial."],
             ["2 — Mac",
              "Double-click  SetRTC_Mac.command  in Finder",
              "A Terminal window opens. Script connects to the Arduino, "
              "reads exact UTC from your Mac clock, sends it. "
              "RTC is set to within 1 second. Window shows confirmation then closes."],
             ["2 — Win",
              "Double-click  SetRTC_Windows.bat  in File Explorer",
              "A Command Prompt opens. Same process as Mac. "
              "RTC is set to within 1 second. Window shows confirmation then closes."]],
            _w(20, 52),
            mono_cols={0}),
          SP(2*mm),
          Paragraph("Important: Steps 1 and 2 overlap in time. "
                    "You do NOT need to wait for Step 1 to finish before starting Step 2. "
                    "Double-click the file while the upload bar is still moving — "
                    "the script waits up to 30 seconds for the board to boot.", S_NOTE),
          SP(3*mm),

          Paragraph("What if you skip Step 2?", S_H2),
          Paragraph("If the script is not run within 5 seconds of the board booting, "
                    "the Arduino automatically falls back to the compile-time stamp "
                    "from your computer clock, converted to UTC. "
                    "The clock will run but may be 10–20 seconds behind. "
                    "For day-to-day use this is perfectly acceptable. "
                    "Run Step 2 any time to correct it precisely.", S_BODL),
          SP(3*mm),

          Paragraph("Project files — keep all in the same folder", S_H1),
          make_table(
            ["File", "Purpose", "Platform"],
            [["EEB3_Clock_Mega_Relay.ino", "Arduino sketch — open and upload with IDE", "Both"],
             ["SetRTC_Mac.command",        "Double-click after upload to set exact time", "Mac only"],
             ["SetRTC_Windows.bat",        "Double-click after upload to set exact time", "Windows only"],
             ["set_rtc.py",               "The actual time-setter — do not move or rename", "Both"],
             ["EEB3_Clock_Reference.pdf", "This document", "Both"]],
            _w(62, 82),
            mono_cols={0}),
          SP(2*mm),
          Paragraph("First time on a new computer: the .command / .bat file installs "
                    "the required pyserial library automatically. No manual pip install needed.", S_NOTE),
          SP(3*mm),

          Paragraph("Coin cell replacement", S_H1),
          Paragraph("The DS3231 uses a CR2032 cell. Typical life is 5–8 years. "
                    "After replacement simply upload the sketch and run the time-setter script. "
                    "The clock will be accurate within seconds.", S_BODL),
          PageBreak()]

# ─── 5. DISPLAY BEHAVIOUR ────────────────────────────────────────────────────
story += [section_box("5.  DISPLAY BEHAVIOUR"), SP(3*mm),

          Paragraph("Operating hours — relay rest cycle", S_H1),
          Paragraph("All 32 relays are completely switched OFF outside school hours. "
                    "This gives the relay contacts a long daily rest, dramatically "
                    "extending the lifespan of both the relays and the bulbs. "
                    "The transition happens exactly once per boundary — "
                    "no repeated clicking.", S_BODL),
          make_table(
            ["Time window", "Display", "All relays"],
            [["Before 08:00",        "Nothing — completely blank", "OFF"],
             ["08:00 – 17:00",       "Active (see table below)",   "Normal operation"],
             ["After 17:00",         "Nothing — completely blank", "OFF"]],
            _w(46, 80),
            mono_cols={0}),
          SP(3*mm),

          Paragraph("Display logic during operating hours (08:00–17:00)", S_H1),
          Paragraph("EEb3 and the period label appear ONLY during an active period (P1–P9). "
                    "During the break, between periods, before P1, and after P9 "
                    "the clock shows plain time the entire minute with no flash.", S_BODL),
          make_table(
            ["Condition", "Second :00–:57", "Second :58", "Second :59"],
            [["During a period (P1–P9)", "HH:MM  colon ON", "EEb3  colon OFF", "P  x  colon OFF"],
             ["Break (10:55–11:15)",     "HH:MM  colon ON", "HH:MM  colon ON", "HH:MM  colon ON"],
             ["Between periods / gaps",  "HH:MM  colon ON", "HH:MM  colon ON", "HH:MM  colon ON"],
             ["Before P1 (08:00–08:30)", "HH:MM  colon ON", "HH:MM  colon ON", "HH:MM  colon ON"],
             ["After P9  (16:15–17:00)", "HH:MM  colon ON", "HH:MM  colon ON", "HH:MM  colon ON"]],
            _w(44, 42, 36)),
          SP(4*mm),

          Paragraph("Bell schedule — local Brussels time", S_H1),
          make_table(
            ["Label", "Start", "End", "What the clock shows"],
            [["Before school", "08:00", "08:30", "HH:MM only — no flash"],
             ["Period 1",      "08:30", "09:15", "HH:MM, then EEb3 at :58, P  1 at :59"],
             ["Gap",           "09:15", "09:20", "HH:MM only — no flash"],
             ["Period 2",      "09:20", "10:05", "HH:MM, then EEb3 at :58, P  2 at :59"],
             ["Gap",           "10:05", "10:10", "HH:MM only — no flash"],
             ["Period 3",      "10:10", "10:55", "HH:MM, then EEb3 at :58, P  3 at :59"],
             ["Break",         "10:55", "11:15", "HH:MM only — no flash"],
             ["Period 4",      "11:15", "12:00", "HH:MM, then EEb3 at :58, P  4 at :59"],
             ["Gap",           "12:00", "12:05", "HH:MM only — no flash"],
             ["Period 5",      "12:05", "12:50", "HH:MM, then EEb3 at :58, P  5 at :59"],
             ["Gap",           "12:50", "13:00", "HH:MM only — no flash"],
             ["Period 6",      "13:00", "13:45", "HH:MM, then EEb3 at :58, P  6 at :59"],
             ["Gap",           "13:45", "13:50", "HH:MM only — no flash"],
             ["Period 7",      "13:50", "14:35", "HH:MM, then EEb3 at :58, P  7 at :59"],
             ["Gap",           "14:35", "14:40", "HH:MM only — no flash"],
             ["Period 8",      "14:40", "15:25", "HH:MM, then EEb3 at :58, P  8 at :59"],
             ["Gap",           "15:25", "15:30", "HH:MM only — no flash"],
             ["Period 9",      "15:30", "16:15", "HH:MM, then EEb3 at :58, P  9 at :59"],
             ["After school",  "16:15", "17:00", "HH:MM only — no flash"],
             ["Clock off",     "17:00", "08:00", "All relays OFF — completely dark"]],
            _w(28, 20, 20)),
          Paragraph("To edit times: update schedule[] in the code. "
                    "CLOCK_ON_MINS and CLOCK_OFF_MINS control the on/off hours. "
                    "All times are LOCAL Brussels time in minutes from midnight.", S_NOTE),
          PageBreak()]

# ─── 6. DST LOGIC ────────────────────────────────────────────────────────────
story += [section_box("6.  DAYLIGHT-SAVING TIME LOGIC (BRUSSELS)"), SP(3*mm),
          Paragraph("The RTC stores UTC permanently. Every second the code applies the "
                    "EU DST rule mathematically — no lookup table, no manual intervention, "
                    "valid for any future year.", S_BODY),
          make_table(
            ["Season", "Offset", "Starts", "Ends"],
            [["Summer — CEST", "UTC + 2 h",
              "Last Sunday of March, 01:00 UTC",
              "Last Sunday of October, 01:00 UTC"],
             ["Winter — CET",  "UTC + 1 h",
              "Last Sunday of October, 01:00 UTC",
              "Last Sunday of March, 01:00 UTC"]],
            _w(30, 22, 64)),
          SP(3*mm),

          Paragraph("How the calculation works", S_H2),
          Paragraph("lastSundayDay(year, month) takes the 31st of the month, reads "
                    "its day-of-week (0 = Sunday), and subtracts that from 31. "
                    "Both March and October have 31 days so no special case is needed. "
                    "This gives the correct last-Sunday date for any year.", S_BODL),
          Paragraph("If the EU ever abolishes DST, change only one line: replace "
                    "isEuSummerTime(utc) ? 2 : 1  with a fixed offset of 1 or 2.", S_NOTE),
          PageBreak()]

# ─── 7. SERIAL MONITOR ───────────────────────────────────────────────────────
story += [section_box("7.  SERIAL MONITOR DIAGNOSTICS"), SP(3*mm),
          Paragraph("Open Serial Monitor at 9600 baud. Every time the display "
                    "changes, one line is printed:", S_BODL),
          Paragraph("UTC 2026-06-09T10:05:32  Local 12:05  showing P  5  colon=off",
                    ST(fontName="Courier", fontSize=7.8, leading=11,
                       backColor=C_CODEBG, leftIndent=4*mm, spaceAfter=3*mm)),
          SP(2*mm),
          make_table(
            ["Serial Monitor message", "Meaning and action"],
            [["RTC not found! Check SDA=20, SCL=21",
              "RTC not responding. Check VCC, GND, SDA, SCL wiring. "
              "Re-seat the module or try a replacement."],
             ["RTC lost power -> compile-time fallback",
              "CR2032 coin cell flat or missing. Replace cell and re-set UTC "
              "using Section 4 Steps 1 to 5."],
             ["No output at all after upload",
              "Check port selection and baud rate (9600). "
              "If watchdog keeps rebooting, the RTC is absent — check I2C wiring."],
             ["UTC year shows 2000 or random value",
              "I2C glitch. Code auto-discards reads outside 2024-2099. "
              "If persistent, re-seat wiring and check 5V supply stability."],
             ["Display frozen, not updating",
              "Watchdog reboots Mega within 8 s automatically. "
              "If it keeps recurring, check I2C wiring and power supply voltage."]],
            _w(70)),
          PageBreak()]

# ─── 8. COMMON ISSUES ────────────────────────────────────────────────────────
story += [section_box("8.  COMMON ISSUES AND CHECKS"), SP(3*mm),
          make_table(
            ["Symptom", "Most likely cause", "Check / Fix"],
            [["Power LED flashes and instantly dies",
              "Short circuit in wiring",
              "Unplug relay board power wires first. Test bare Mega plus USB. "
              "Add wire groups back one at a time until short reappears."],
             ["Board not appearing in Mac port list",
              "CH340 USB driver missing",
              "Download CH340 driver. Install the pkg file. Approve in "
              "System Settings then Privacy and Security. Reboot Mac."],
             ["Board not in Windows port list",
              "Driver missing or wrong port",
              "Open Device Manager. Look for yellow ! on a COM entry. "
              "Install CH340 driver or update device driver."],
             ["A segment never lights or is always on",
              "Wire swapped or relay polarity wrong",
              "Verify pin number against Section 3c. "
              "Toggle RELAY_ACTIVE_LOW in code if all segments are inverted."],
             ["Wrong digit shows wrong number",
              "SEG2RELAY or PINS mismatch",
              "Check Serial Monitor for the frame being sent. "
              "Test each relay to confirm segment mapping."],
             ["Time wrong by exactly 1 or 2 hours",
              "RTC set to local time instead of UTC",
              "Re-set RTC using the correct UTC value. See Section 4."],
             ["Time drifts slowly over weeks",
              "DS3231 normal tolerance (+/-2 ppm)",
              "Under 1 minute per year is normal. "
              "Re-enter UTC if drift becomes noticeable."],
             ["Colon bulb flickers",
              "Loose relay terminal or failing relay",
              "Inspect Module 1 IN8 terminal and Mega pin 29 connection."],
             ["All bulbs off but Mega running",
              "External 5V supply not powered on",
              "Check relay supply. Measure voltage on relay VCC pin."],
             ["Mega reboots every 8 seconds",
              "Watchdog triggered by stalled loop",
              "Almost always the RTC is not responding. Check I2C wiring."]],
            _w(48, 50)),
          PageBreak()]

# ─── 9. RELIABILITY NOTES ────────────────────────────────────────────────────
story += [section_box("9.  RELIABILITY AND LONG-LIFE DESIGN NOTES"), SP(3*mm)]
notes = [
    ("Daily relay rest — operating hours 08:00–17:00",
     "All 32 relays are completely de-energised outside school hours. "
     "allRelaysOff() uses writeRelay() internally, so once the board is dark "
     "there are zero repeated clicks — only one transition at 08:00 and one at 17:00. "
     "That is ~15 hours of rest every day, dramatically extending relay and bulb lifespan. "
     "CLOCK_ON_MINS and CLOCK_OFF_MINS control the window."),
    ("Relay switching minimised",
     "writeRelay() checks current state before driving the pin. A relay only "
     "clicks when its segment genuinely changes. Showing the same digit twice "
     "produces zero relay operations."),
    ("Colon stays on — never blinks",
     "Blinking at 1 Hz would produce ~31 million operations per year on the "
     "colon relay alone. The colon stays steadily on during time display."),
    ("EEb3 and period label: active periods only",
     "The :58 EEb3 flash and :59 period label are shown ONLY when a lesson is "
     "in progress. During the break, between periods, before P1, and after P9 "
     "the clock shows plain HH:MM the whole minute — no unnecessary relay toggles."),
    ("Hardware watchdog",
     "wdt_enable(WDTO_8S) makes the microcontroller reboot itself if the "
     "main loop stops for more than 8 seconds, recovering from I2C hangs "
     "and unexpected lock-ups with no human intervention needed."),
    ("UTC-based timekeeping",
     "The RTC stores UTC and is never adjusted for DST. The clock corrects "
     "itself on every DST boundary automatically, requiring no physical access "
     "and no buttons."),
    ("Defensive RTC reads",
     "Any timestamp with a year outside 2024–2099 is silently discarded. "
     "This prevents corrupted I2C data from causing display errors."),
    ("Safe boot sequence",
     "All relay pins are driven to the OFF level before being configured as "
     "outputs, eliminating the brief boot glitch that would otherwise flash "
     "all bulbs on every power cycle."),
    ("Coin cell maintenance",
     "Replace the DS3231 CR2032 proactively every 5–7 years. "
     "After replacement, re-enter the UTC time once using Section 4."),
]
for title, body in notes:
    story.append(KeepTogether([Paragraph(title, S_H2), Paragraph(body, S_BODL)]))
story.append(PageBreak())

# ─── 10. CODE LISTING ────────────────────────────────────────────────────────
story += [section_box("10.  FULL CODE LISTING"), SP(2*mm),
          Paragraph("File: EEB3_Clock_Mega_Relay.ino  —  "
                    "Board: Arduino Mega or Mega 2560, Processor: ATmega2560", S_NOTE),
          SP(1*mm)]
for line in CODE_TEXT.split("\n"):
    safe = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    story.append(Paragraph(safe or " ", S_CODE))
story.append(PageBreak())

# ─── 11. QUICK REFERENCE ─────────────────────────────────────────────────────
story += [section_box("11.  QUICK REFERENCE"), SP(3*mm),
          Paragraph("All pin assignments", S_H1),
          make_table(
            ["Function", "Mega pins"],
            [["RTC SDA / SCL",                           "20, 21"],
             ["Module 1  IN1–IN8  (hours tens + colon)",  "22 23 24 25 26 27 28 29"],
             ["Module 2  IN1–IN8  (hours units)",         "30 31 32 33 34 35 36 37"],
             ["Module 3  IN1–IN8  (minutes tens)",        "38 39 40 41 42 43 44 45"],
             ["Module 4  IN1–IN8  (minutes units)",       "46 47 48 49 50 51 52 53"]],
            _w(90),
            mono_cols={1}),
          SP(5*mm),

          Paragraph("Configurable constants in code", S_H1),
          make_table(
            ["Constant", "Default", "Change when"],
            [["RELAY_ACTIVE_LOW",        "true",
              "Relay boards fire on HIGH instead of LOW (reverse polarity boards)"],
             ["BLANK_LEADING_HOUR_ZERO", "true",
              "You prefer 09:05 displayed instead of  9:05"],
             ["EEB3_SECOND",             "58",
              "Moving the EEb3 flash to a different second"],
             ["PERIOD_SECOND",           "59",
              "Moving the period label to a different second"],
             ["CLOCK_ON_MINS",           "8*60 = 480",
              "Time when relays wake up (08:00 by default)"],
             ["CLOCK_OFF_MINS",          "17*60 = 1020",
              "Time when all relays go to sleep (17:00 by default)"],
             ["SERIAL_WAIT_MS",          "5000",
              "Milliseconds to wait for the Python time-setter script at boot"]],
            _w(52, 38),
            mono_cols={0, 1}),

          SP(6*mm), HR(1, C_BLACK),
          Paragraph("Prepared by Taqi Abbas  |  European School of Brussels, Ixelles",
                    S_FOOT)]

# ─────────────────────────────────────────────────────────────────────────────
# BUILD
# ─────────────────────────────────────────────────────────────────────────────
doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=ML, rightMargin=MR,
    topMargin=MT,  bottomMargin=MB,
    title="EEB3 Big Clock — Technical Reference",
    author="Taqi Abbas",
    subject="220V relay-driven 7-segment clock, Arduino MEGA 2560",
)
doc.build(story, onFirstPage=on_first_page, onLaterPages=on_page)
print(f"Done:\n  {OUT}")
