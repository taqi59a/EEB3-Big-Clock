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
     - At second 58:  shows "EEb3", colon OFF.
     - At second 59:  shows the current period number, colon OFF.
                      (If no period is active right now it just keeps the time.)
     - At second 00:  back to the time.

   RELIABILITY ("long life") choices made on purpose:
     - A relay is only switched when that segment actually changes state, so the
       relays click as little as physically possible.
     - The colon does not blink.
     - Hardware watchdog reboots the Mega automatically if it ever hangs.
     - RTC is read defensively; garbage reads are ignored.
   ============================================================================ */

#include <Wire.h>
#include <RTClib.h>
#include <avr/wdt.h>

RTC_DS3231 rtc;

/* ----------------------------------------------------------------------------
   1) RTC TIME SYNC  —  bulletproof two-stage system

   STAGE 1 (primary, millisecond-accurate):
     After every upload, run  python3 set_rtc.py  in Terminal.
     The script sends the exact current UTC to the Arduino over Serial.
     The Arduino sets the RTC from that — accurate to within 1 second.
     Your Mac clock is NTP-synced so this is always correct.

   STAGE 2 (automatic fallback):
     If the Python script is NOT run within SERIAL_WAIT_MS milliseconds,
     the Arduino falls back to the compile-time stamp from your Mac clock,
     automatically converted from Brussels local time to UTC.
     This is typically 10-20 seconds behind real time — fine for a clock.

   SERIAL_WAIT_MS   How long to wait for the Python script (milliseconds).
                    5000 = 5 seconds. Upload takes ~10 s so the script
                    has 5 s after the board resets before fallback kicks in.
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

// EEb3 shows from second EEB3_START up to (not including) PERIOD_START  -> 4 seconds
// Period label shows from PERIOD_START to :59                            -> 3 seconds
// Total announcement window: 7 seconds per minute, only during active periods.
// Each boundary is ONE relay transition — no extra clicking, safe for bulbs.
const uint8_t EEB3_START   = 53;   // :53 :54 :55 :56  — "EEb3"
const uint8_t PERIOD_START = 57;   // :57 :58 :59      — period label (e.g. "P  1")

/* ----------------------------------------------------------------------------
   3b) OPERATING HOURS
   Outside these hours ALL relays are switched OFF completely.
   This gives the relay contacts a long rest every day and maximises
   the lifespan of all 32 relays and the light bulbs.
   Times in LOCAL Brussels time, minutes from midnight.
   08:00 = 8*60 = 480     17:00 = 17*60 = 1020
---------------------------------------------------------------------------- */
const int CLOCK_ON_MINS  = 8  * 60;    // 08:00 — relays wake up
const int CLOCK_OFF_MINS = 17 * 60;    // 17:00 — relays go to sleep

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

/* Map each logical segment (a..g) to the relay index (0-based) on a module,
   following YOUR frame numbering:
   a=relay2(idx1) b=relay3(idx2) c=relay6(idx5) d=relay7(idx6)
   e=relay5(idx4) f=relay1(idx0) g=relay4(idx3)                          */
//                          a  b  c  d  e  f  g
const uint8_t SEG2RELAY[7] = {1, 2, 5, 6, 4, 0, 3};

/* ----------------------------------------------------------------------------
   5) BELL SCHEDULE  (your times, in LOCAL Brussels time, minutes from midnight)
      Edit freely. disp must be exactly 4 characters.
---------------------------------------------------------------------------- */
struct Period { int startMins; int endMins; const char* disp; };

Period schedule[] = {
  { 8 * 60 + 30,  9 * 60 + 15, "P  1" },
  { 9 * 60 + 20, 10 * 60 +  5, "P  2" },
  {10 * 60 + 10, 10 * 60 + 55, "P  3" },
  // 10:55 – 11:15  BREAK  — gap in schedule, shows time only
  {11 * 60 + 15, 12 * 60 +  0, "P  4" },
  {12 * 60 +  5, 12 * 60 + 50, "P  5" },
  {13 * 60 +  0, 13 * 60 + 45, "P  6" },
  {13 * 60 + 50, 14 * 60 + 35, "P  7" },
  {14 * 60 + 40, 15 * 60 + 25, "P  8" },
  {15 * 60 + 30, 16 * 60 + 15, "P  9" }
  // 16:15 – 17:00  after last period — shows time only
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
    case 'E': return 0b1111001;   // E
    case 'b': return 0b1111100;   // b
    case 'P': return 0b1110011;   // P
    case 'r': return 0b1010000;   // r
    case 'c': return 0b1011000;   // c
    case 'd': return 0b1011110;   // d
    case '-': return 0b1000000;   // dash (segment g)
    case ' ':
    default:  return 0b0000000;   // blank
  }
}

/* ============================================================================
   EU / BRUSSELS DAYLIGHT-SAVING  (rule based, no lookup table needed)
   Summer time (CEST, UTC+2): last Sunday of March 01:00 UTC ->
                              last Sunday of October 01:00 UTC.
   Otherwise winter time (CET, UTC+1).
   ============================================================================ */
uint8_t lastSundayDay(uint16_t year, uint8_t month) {
  // March and October both have 31 days
  DateTime lastDay(year, month, 31, 0, 0, 0);
  uint8_t dow = lastDay.dayOfTheWeek();        // 0 = Sunday
  return 31 - dow;                             // date of the last Sunday
}

bool isEuSummerTime(const DateTime& u) {
  uint8_t m = u.month();
  if (m < 3 || m > 10) return false;           // Jan,Feb,Nov,Dec -> winter
  if (m > 3 && m < 10) return true;            // Apr..Sep        -> summer
  uint8_t ls = lastSundayDay(u.year(), m);
  if (m == 3) {                                // March changeover
    if (u.day() > ls) return true;
    if (u.day() < ls) return false;
    return u.hour() >= 1;                      // 01:00 UTC = 02:00->03:00 local
  } else {                                     // October changeover
    if (u.day() < ls) return true;
    if (u.day() > ls) return false;
    return u.hour() < 1;                       // 01:00 UTC = 03:00->02:00 local
  }
}

DateTime utcToBrussels(const DateTime& utc) {
  int offsetHours = isEuSummerTime(utc) ? 2 : 1;
  return utc + TimeSpan(0, offsetHours, 0, 0);
}

/* brusselsLocalToUtc()
   Used only at upload time to convert the compile-time stamp (which the
   Arduino IDE takes from your computer's LOCAL Brussels clock) into UTC.
   Spring transition: last Sunday of March  at 02:00 LOCAL -> CEST starts
   Autumn transition: last Sunday of October at 03:00 LOCAL -> CET  starts  */
bool isLocalBrusselsSummerTime(const DateTime& local) {
  uint8_t m = local.month();
  if (m < 3 || m > 10) return false;
  if (m > 3 && m < 10) return true;
  uint8_t ls = lastSundayDay(local.year(), m);
  if (m == 3) {
    if (local.day() > ls) return true;
    if (local.day() < ls) return false;
    return local.hour() >= 2;    // 02:00 local = CEST starts
  } else {
    if (local.day() < ls) return true;
    if (local.day() > ls) return false;
    return local.hour() < 3;     // 03:00 local = CET starts
  }
}

DateTime brusselsLocalToUtc(const DateTime& local) {
  int offsetHours = isLocalBrusselsSummerTime(local) ? 2 : 1;
  return local - TimeSpan(0, offsetHours, 0, 0);
}

/* ============================================================================
   RELAY OUTPUT with change-tracking (only switch when state actually changes)
   ============================================================================ */
bool relayState[4][8];   // true = bulb ON

inline void writeRelay(uint8_t module, uint8_t idx, bool on) {
  if (relayState[module][idx] == on) return;          // no change -> no click
  relayState[module][idx] = on;
  uint8_t level = (on == RELAY_ACTIVE_LOW) ? LOW : HIGH;
  // on=true  & active-low  -> LOW (ON)
  // on=false & active-low  -> HIGH (OFF)
  digitalWrite(PINS[module][idx], level);
}

// Turn every single relay OFF — used outside operating hours.
// writeRelay() skips if already off, so this produces zero clicks
// once the board is already dark.
void allRelaysOff() {
  for (uint8_t m = 0; m < 4; m++)
    for (uint8_t i = 0; i < 8; i++)
      writeRelay(m, i, false);
}

// Apply a character (its 7 segments) to one digit module.
void applyDigit(uint8_t module, char ch) {
  byte mask = segMask(ch);
  for (uint8_t seg = 0; seg < 7; seg++) {
    bool on = mask & (1 << seg);
    writeRelay(module, SEG2RELAY[seg], on);
  }
}

void setColon(bool on) {
  writeRelay(0, COLON_RELAY_INDEX, on);    // module 1, IN8
}

// Render 4 characters + colon
void renderFrame(const char d[4], bool colonOn) {
  for (uint8_t m = 0; m < 4; m++) applyDigit(m, d[m]);
  setColon(colonOn);
}

/* ============================================================================
   SETUP
   ============================================================================ */
void setup() {
  Serial.begin(9600);

  // --- Force all relay outputs OFF *before* enabling them, so nothing clicks
  //     on at power-up (important for active-low boards). ---
  for (uint8_t m = 0; m < 4; m++) {
    for (uint8_t i = 0; i < 8; i++) {
      uint8_t offLevel = RELAY_ACTIVE_LOW ? HIGH : LOW;
      digitalWrite(PINS[m][i], offLevel);   // drive OFF first
      pinMode(PINS[m][i], OUTPUT);
      digitalWrite(PINS[m][i], offLevel);
      relayState[m][i] = false;
    }
  }

  Wire.begin();
  if (!rtc.begin()) {
    Serial.println(F("RTC not found! Check wiring (SDA=20, SCL=21)."));
  }

  // ── Bulletproof RTC sync ────────────────────────────────────────────────
  // Signal the Python script that we are ready to receive a timestamp.
  Serial.println(F("READY"));

  // Wait up to SERIAL_WAIT_MS for a line of the form:  T<unix_utc>\n
  // e.g.  T1749466322
  // The Python script sends this immediately after upload finishes.
  bool synced = false;
  unsigned long waitStart = millis();

  while ((millis() - waitStart) < SERIAL_WAIT_MS) {
    if (Serial.available()) {
      char cmd = Serial.read();
      if (cmd == 'T') {
        // Read the Unix UTC timestamp (seconds since 1970-01-01 00:00:00 UTC)
        unsigned long unixUtc = Serial.parseInt();
        if (unixUtc > 1700000000UL) {           // sanity: after Nov 2023
          rtc.adjust(DateTime(unixUtc));
          Serial.print(F("RTC SET via script -> UTC: "));
          Serial.println(DateTime(unixUtc).timestamp());
          synced = true;
          break;
        }
      }
    }
  }

  // ── Fallback: use compile time if script was not run ───────────────────
  if (!synced) {
    DateTime compileLocal(F(__DATE__), F(__TIME__));
    DateTime utcNow = brusselsLocalToUtc(compileLocal);
    rtc.adjust(utcNow);
    Serial.print(F("RTC FALLBACK (compile time) -> UTC: "));
    Serial.println(utcNow.timestamp());
    Serial.println(F("Run  python3 set_rtc.py  for exact time next upload."));
  }

  // Hardware watchdog: if the loop ever hangs for >8s, the Mega auto-reboots.
  wdt_enable(WDTO_8S);
}

/* ============================================================================
   LOOP
   ============================================================================ */
int   lastRenderedSecondKey = -1;   // forces a render only when something changes

void loop() {
  wdt_reset();                       // pet the watchdog

  static unsigned long lastTick = 0;
  if (millis() - lastTick < 200) return;   // check ~5x/second, plenty
  lastTick = millis();

  DateTime utc = rtc.now();

  // Defensive: ignore obviously bad RTC reads (e.g. I2C glitch).
  if (utc.year() < 2024 || utc.year() > 2099) return;

  DateTime local = utcToBrussels(utc);
  uint8_t hh = local.hour();
  uint8_t mm = local.minute();
  uint8_t ss = local.second();
  int localMins = hh * 60 + mm;

  // ── Operating hours check ──────────────────────────────────────────────
  // Outside 08:00–17:00: all relays off. Uses a sentinel key so the
  // off-state is applied exactly once (no repeated clicking every 200 ms).
  if (localMins < CLOCK_ON_MINS || localMins >= CLOCK_OFF_MINS) {
    if (lastRenderedSecondKey != -2) {
      lastRenderedSecondKey = -2;
      allRelaysOff();
      Serial.println(F("Clock OFF (outside operating hours)."));
    }
    return;
  }

  // ── Decide what to show ─────────────────────────────────────────────────
  // EEb3 (:53-:56, 4 s) and period label (:57-:59, 3 s) are shown ONLY when
  // a period is active. Breaks, gaps, before P1, after P9 → plain time always.
  char frame[4];
  bool colonOn;

  const char* activePeriod = getActivePeriod(localMins);
  bool periodActive = (activePeriod != nullptr);

  if (periodActive && ss >= EEB3_START && ss < PERIOD_START) {
    // EEb3 for 4 seconds
    frame[0] = 'E'; frame[1] = 'E'; frame[2] = 'b'; frame[3] = '3';
    colonOn = false;
  }
  else if (periodActive && ss >= PERIOD_START) {
    // Period label for 3 seconds
    frame[0] = activePeriod[0]; frame[1] = activePeriod[1];
    frame[2] = activePeriod[2]; frame[3] = activePeriod[3];
    colonOn = false;
  }
  else {
    // All other seconds AND all non-period slots → plain time
    frame[0] = (BLANK_LEADING_HOUR_ZERO && hh < 10) ? ' ' : ('0' + hh / 10);
    frame[1] = '0' + hh % 10;
    frame[2] = '0' + mm / 10;
    frame[3] = '0' + mm % 10;
    colonOn = true;
  }

  // Only push to relays when the displayed picture actually changes
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
}
