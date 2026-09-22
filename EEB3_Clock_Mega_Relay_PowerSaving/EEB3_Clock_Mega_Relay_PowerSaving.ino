/* ============================================================================
   EEB3 SOLID-STATE CLOCK - 220V bulb 7-segment digits
   RELEASE BUILD: September 22, 2026 (FW 4.2-BASIC)
   ----------------------------------------------------------------------------
   Board  : Arduino MEGA 2560
   Clock  : DS3231 RTC (I2C, SDA=20, SCL=21 on MEGA)
   Baud   : 9600
   ----------------------------------------------------------------------------
   Stripped down to the essentials: accurate HH:MM time display, automatic
   Brussels DST (CET/CEST) that recalculates every year forever (no hardcoded
   dates), and a power-saving window that cuts the display outside school
   hours. No period schedule, no boot self-test, no master-relay feature.

   VERIFIED HARDWARE MAPPING (2026-09-22):
     Module 1 (Hours Tens)   : Pins 22-29 (IN1..IN8), IN8 = Colon
     Module 2 (Hours Units)  : Pins 30-37 (IN1..IN8), IN8 = Unused
     Module 3 (Minutes Tens) : Pins 38-45 (IN1..IN8)
     Module 4 (Minutes Units): Pins { 53, 52, 48, 50, 49, 51, 46, 47 }
                               IN3 = Pin 48 (Seg b - Top Right)
                               IN6 = Pin 51 (Seg c - Bottom Right)

   SEGMENT TO RELAY MAPPING:
     SEG2RELAY[7] order is a,b,c,d,e,f,g
     a->1 (IN2), b->2 (IN3), c->5 (IN6), d->6 (IN7), e->4 (IN5), f->0 (IN1), g->3 (IN4)
     const uint8_t SEG2RELAY[7] = { 1, 2, 5, 6, 4, 0, 3 };

   POWER SAVING SCHEDULE:
     CLOCK_ON_MINS  = 8 * 60;   // 08:00 AM
     CLOCK_OFF_MINS = 17 * 60;  // 05:00 PM (17:00)

   TIME SYNC: send T<10-digit-unix-UTC>, e.g. T1749736800

   WIRING DIAGNOSTICS (for tracing bulb/relay connections):
     D1        -> enter diagnostic mode (pauses the clock, all relays off)
     D0        -> exit diagnostic mode (resumes normal clock display)
     R<m><i><s>-> while in diagnostic mode, set module m(0-3) index i(0-7)
                  to state s(0=off,1=on), e.g. R071 turns M0 IN8 ON
   ============================================================================ */

#include <Wire.h>
#include <RTClib.h>
#include <avr/wdt.h>

#define FW_VERSION          "4.3-DIAG-2026-09-22"
#define SERIAL_BAUD         9600
#define SERIAL_WAIT_MS      8000UL
#define RELAY_ACTIVE_LOW    true

// Power Saving active schedule: 08:00 AM to 05:00 PM
const int CLOCK_ON_MINS  = 8 * 60;   // 08:00 AM (480 minutes)
const int CLOCK_OFF_MINS = 17 * 60;  // 05:00 PM (1020 minutes)

const uint8_t PINS[4][8] = {
  { 22, 23, 24, 25, 26, 27, 28, 29 },  // Module 1 (Hours Tens)
  { 30, 31, 32, 33, 34, 35, 36, 37 },  // Module 2 (Hours Units - IN8 unused)
  { 38, 39, 40, 41, 42, 43, 44, 45 },  // Module 3 (Minutes Tens)
  { 53, 52, 48, 50, 49, 51, 46, 47 }   // Module 4 (Minutes Units - IN3=Pin48, IN6=Pin51)
};

const uint8_t COLON_RELAY_INDEX = 7;

// SEG2RELAY[seg] = relay index (a,b,c,d,e,f,g)
const uint8_t SEG2RELAY[7] = { 1, 2, 5, 6, 4, 0, 3 };
const char    SEG_NAME[7]  = {'a','b','c','d','e','f','g'};

bool relayState[4][8];
RTC_DS3231 rtc;
static bool rtcOk = false;
static bool diagMode = false;

/* ============================================================================
   SERIAL TAG HELPERS
   ============================================================================ */
void tag(const __FlashStringHelper* t) {
  Serial.print(F("[")); Serial.print(t); Serial.print(F("] "));
}
void sep() { Serial.println(F("------------------------------------------------------------")); }

/* ============================================================================
   SEGMENT FONT
   bit0=a  bit1=b  bit2=c  bit3=d  bit4=e  bit5=f  bit6=g
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
    case '-': return 0b1000000;   // middle bar only (error indicator)
    case ' ':
    default:  return 0b0000000;
  }
}

/* ============================================================================
   RELAY ENGINE
   ============================================================================ */
inline void writeRelay(uint8_t module, uint8_t idx, bool on) {
  if (relayState[module][idx] == on) return;
  relayState[module][idx] = on;
  digitalWrite(PINS[module][idx], (on == RELAY_ACTIVE_LOW) ? LOW : HIGH);
  tag(F("RELAY"));
  Serial.print(F("M")); Serial.print(module);
  Serial.print(F(" IN")); Serial.print(idx + 1);
  Serial.print(F(" pin")); Serial.print(PINS[module][idx]);
  Serial.print(F(" -> ")); Serial.println(on ? F("ON") : F("OFF"));
}

void allRelaysOff() {
  tag(F("RELAY")); Serial.println(F("ALL OFF"));
  for (uint8_t m = 0; m < 4; m++)
    for (uint8_t i = 0; i < 8; i++)
      writeRelay(m, i, false);
}

void writeSegment(uint8_t module, uint8_t seg, bool on) {
  writeRelay(module, SEG2RELAY[seg], on);
}

void applyDigit(uint8_t module, char ch) {
  byte mask = segMask(ch);
  tag(F("DIGIT"));
  Serial.print(F("M")); Serial.print(module);
  Serial.print(F(" char='")); Serial.print(ch);
  Serial.print(F("'  mask=0b"));
  for (int b = 6; b >= 0; b--) Serial.print((mask >> b) & 1);
  Serial.print(F("  segs: "));
  for (uint8_t s = 0; s < 7; s++)
    if (mask & (1 << s)) { Serial.print(SEG_NAME[s]); Serial.print(' '); }
  Serial.println();
  for (uint8_t seg = 0; seg < 7; seg++)
    writeSegment(module, seg, (bool)(mask & (1 << seg)));
}

void renderFrame(const char d[4], bool colonOn) {
  tag(F("FRAME"));
  Serial.print(F("'")); Serial.print(d[0]); Serial.print(d[1]);
  Serial.print(F(":")); Serial.print(d[2]); Serial.print(d[3]);
  Serial.print(F("'  colon=")); Serial.println(colonOn ? F("ON") : F("OFF"));
  for (uint8_t m = 0; m < 4; m++) applyDigit(m, d[m]);
  writeRelay(0, COLON_RELAY_INDEX, colonOn);
}

/* ============================================================================
   DST / TIMEZONE (Brussels CET/CEST, EU rule - recalculated every year)
   ============================================================================ */
uint8_t lastSundayDay(uint16_t year, uint8_t month) {
  const uint8_t dim[] = {0,31,28,31,30,31,30,31,31,30,31,30,31};
  uint8_t d = dim[month];
  if (month == 2 && (((year%4==0)&&(year%100!=0))||(year%400==0))) d = 29;
  return d - (uint8_t)DateTime(year, month, d, 0, 0, 0).dayOfTheWeek();
}

bool isEuSummerTime(const DateTime& u) {
  uint8_t m = u.month();
  if (m < 3 || m > 10) return false;
  if (m > 3 && m < 10) return true;
  uint8_t ls = lastSundayDay(u.year(), m);
  if (m == 3) { if (u.day()>ls) return true; if (u.day()<ls) return false; return u.hour()>=1; }
  if (u.day()<ls) return true; if (u.day()>ls) return false; return u.hour()<1;
}

bool isLocalSummerTime(const DateTime& l) {
  uint8_t m = l.month();
  if (m < 3 || m > 10) return false;
  if (m > 3 && m < 10) return true;
  uint8_t ls = lastSundayDay(l.year(), m);
  if (m == 3) { if (l.day()>ls) return true; if (l.day()<ls) return false; return l.hour()>=2; }
  if (l.day()<ls) return true; if (l.day()>ls) return false; return l.hour()<3;
}

DateTime utcToBrussels(const DateTime& utc) {
  bool s = isEuSummerTime(utc);
  tag(F("DST"));
  Serial.print(s ? F("CEST+2  ") : F("CET+1  "));
  DateTime local = utc + TimeSpan(0, s ? 2 : 1, 0, 0);
  Serial.println(local.timestamp());
  return local;
}

DateTime localToUtc(const DateTime& local) {
  return local - TimeSpan(0, isLocalSummerTime(local) ? 2 : 1, 0, 0);
}

/* ============================================================================
   RTC DIAGNOSTIC
   ============================================================================ */
void rtcDiagnostic() {
  sep();
  tag(F("RTC")); Serial.println(F("=== RTC Diagnostic ==="));

  Wire.beginTransmission(0x68);
  uint8_t err = Wire.endTransmission();
  tag(F("RTC")); Serial.print(F("I2C 0x68: "));
  if (err == 0) Serial.println(F("OK - device ACK"));
  else { Serial.print(F("FAIL code=")); Serial.print(err); Serial.println(F(" CHECK SDA(20)/SCL(21)")); }

  tag(F("RTC")); Serial.print(F("rtc.begin(): ")); Serial.println(rtcOk ? F("OK") : F("FAILED"));
  if (!rtcOk) { sep(); return; }

  bool lp = rtc.lostPower();
  tag(F("RTC")); Serial.println(lp ? F("lostPower: TRUE - NEEDS SYNC") : F("lostPower: false - OK"));

  DateTime now = rtc.now();
  tag(F("RTC")); Serial.print(F("UTC raw: ")); Serial.print(now.timestamp());
  Serial.print(F("  unix=")); Serial.println(now.unixtime());

  tag(F("RTC")); Serial.print(F("Year check: "));
  Serial.println((now.year()>=2024 && now.year()<=2099) ? F("PASS") : F("FAIL - sync needed!"));

  tag(F("RTC")); Serial.print(F("Temp: ")); Serial.print(rtc.getTemperature(),1); Serial.println(F("C"));

  DateTime local = utcToBrussels(now);
  tag(F("RTC")); Serial.print(F("Brussels: "));
  if(local.hour()<10)Serial.print('0'); Serial.print(local.hour());
  Serial.print(':');
  if(local.minute()<10)Serial.print('0'); Serial.println(local.minute());

  int lm = (int)local.hour()*60+(int)local.minute();
  tag(F("RTC")); Serial.print(F("Local mins=")); Serial.print(lm);
  Serial.print(F("  window=")); Serial.print(CLOCK_ON_MINS);
  Serial.print(F("-")); Serial.print(CLOCK_OFF_MINS);
  Serial.println((lm>=CLOCK_ON_MINS&&lm<CLOCK_OFF_MINS) ? F("  ACTIVE") : F("  NIGHT MODE"));
  sep();
}

/* ============================================================================
   NON-BLOCKING SERIAL COMMAND PARSER
   Send: T1749736800  (T + 10 digit UTC unix timestamp)
   ============================================================================ */
static char           cmdBuf[16];
static uint8_t        cmdPos          = 0;
static bool           inNightMode     = false;
static unsigned long  lastRenderedKey = 0xFFFFFFFFUL;
static uint32_t       loopCount       = 0;
static uint8_t        heartbeat       = 0;

void checkSerialCommands() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (cmdPos > 0) {
        cmdBuf[cmdPos] = '\0';
        if (cmdBuf[0] == 'T' && strlen(cmdBuf) >= 11) {
          unsigned long v = strtoul(cmdBuf + 1, nullptr, 10);
          if (v > 1700000000UL) {
            rtc.adjust(DateTime(v));
            tag(F("SYNC")); Serial.print(F("RTC set UTC=")); Serial.println(DateTime(v).timestamp());
            rtcDiagnostic();
          }
        } else if (cmdBuf[0] == 'D' && strlen(cmdBuf) == 2) {
          diagMode = (cmdBuf[1] == '1');
          allRelaysOff();
          lastRenderedKey = 0xFFFFFFFFUL;
          tag(F("DIAG")); Serial.println(diagMode ? F("ENTER") : F("EXIT"));
        } else if (cmdBuf[0] == 'R' && strlen(cmdBuf) == 4 && diagMode) {
          uint8_t m = cmdBuf[1]-'0', i = cmdBuf[2]-'0', s = cmdBuf[3]-'0';
          if (m < 4 && i < 8) writeRelay(m, i, s != 0);
        }
        cmdPos = 0;
      }
    } else if (cmdPos < 15) {
      cmdBuf[cmdPos++] = c;
    }
  }
}

/* ============================================================================
   SETUP
   ============================================================================ */
void setup() {
  for (uint8_t m=0;m<4;m++) for (uint8_t i=0;i<8;i++) {
    uint8_t off = RELAY_ACTIVE_LOW ? HIGH : LOW;
    digitalWrite(PINS[m][i], off);
    pinMode(PINS[m][i], OUTPUT);
    digitalWrite(PINS[m][i], off);
    relayState[m][i] = false;
  }

  Serial.begin(SERIAL_BAUD);
  Wire.begin();

  Serial.println(F("READY"));

  sep();
  tag(F("BOOT")); Serial.print(F("EEB3 Clock FW=")); Serial.println(F(FW_VERSION));
  tag(F("BOOT")); Serial.print(F("Compiled ")); Serial.print(F(__DATE__)); Serial.print(' '); Serial.println(F(__TIME__));
  tag(F("BOOT")); Serial.print(F("Window: ")); Serial.print(CLOCK_ON_MINS); Serial.print(F("-")); Serial.println(CLOCK_OFF_MINS);
  tag(F("BOOT")); Serial.println(RELAY_ACTIVE_LOW ? F("Relay: ACTIVE LOW") : F("Relay: ACTIVE HIGH"));
  sep();

  rtcOk = rtc.begin();
  rtcDiagnostic();

  tag(F("BOOT")); Serial.println(F("Waiting 8s for serial sync (T<unix>)..."));
  unsigned long ws = millis(), ld = millis();
  while (millis() - ws < SERIAL_WAIT_MS) {
    wdt_reset();
    if (millis() - ld >= 1000UL) {
      ld = millis();
      Serial.print('.');
    }
    checkSerialCommands();
  }
  Serial.println();

  if (rtcOk && rtc.lostPower()) {
    DateTime cl(F(__DATE__), F(__TIME__));
    DateTime uf = localToUtc(cl);
    rtc.adjust(uf);
    tag(F("SYNC")); Serial.print(F("Fallback compile-time UTC=")); Serial.println(uf.timestamp());
  }

  tag(F("BOOT")); Serial.println(F("Watchdog WDTO_8S"));
  wdt_enable(WDTO_8S);
  tag(F("BOOT")); Serial.println(F("Entering main loop"));
  sep();
}

/* ============================================================================
   MAIN LOOP
   ============================================================================ */
void loop() {
  wdt_reset();
  loopCount++;

  checkSerialCommands();
  if (diagMode) return; // manual relay commands only; clock paused

  static unsigned long lastTick = 0;
  if (millis()-lastTick < 250UL) return;
  lastTick = millis();

  DateTime utc = rtc.now();

  if (++heartbeat >= 20) {
    heartbeat = 0;
    tag(F("LOOP"));
    Serial.print(F("tick #")); Serial.print(loopCount);
    Serial.print(F("  UTC=")); Serial.print(utc.timestamp());
    Serial.print(F("  temp=")); Serial.print(rtc.getTemperature(),1); Serial.println(F("C"));
  }

  // Year sanity - show dashes if RTC is corrupt
  if (utc.year()<2024 || utc.year()>2099) {
    tag(F("ERROR")); Serial.print(F("Bad year=")); Serial.println(utc.year());
    char bad[4]={'-','-','-','-'};
    renderFrame(bad, false);
    delay(1000);
    return;
  }

  bool summer    = isEuSummerTime(utc);
  int8_t offset  = summer ? 2 : 1;
  DateTime local = utc + TimeSpan(0, offset, 0, 0);
  uint8_t hh     = local.hour();
  uint8_t mm     = local.minute();
  int localMins  = (int)hh*60+(int)mm;

  // Power saving: relays off outside the active window
  if (localMins<CLOCK_ON_MINS || localMins>=CLOCK_OFF_MINS) {
    if (!inNightMode) {
      inNightMode=true;
      lastRenderedKey=0xFFFFFFFFUL;
      allRelaysOff();
      tag(F("NIGHT"));
      Serial.print(F("Night at "));
      if(hh<10)Serial.print('0'); Serial.print(hh); Serial.print(':');
      if(mm<10)Serial.print('0'); Serial.println(mm);
    }
    return;
  }
  if (inNightMode) {
    inNightMode=false;
    tag(F("NIGHT")); Serial.println(F("Exited night mode"));
  }

  // Build display frame: HH:MM
  char frame[4];
  frame[0] = (hh<10) ? ' ' : (char)('0'+hh/10);
  frame[1] = (char)('0'+hh%10);
  frame[2] = (char)('0'+mm/10);
  frame[3] = (char)('0'+mm%10);

  unsigned long key =
    ((unsigned long)(uint8_t)frame[0]<<24) |
    ((unsigned long)(uint8_t)frame[1]<<16) |
    ((unsigned long)(uint8_t)frame[2]<< 8) |
     (unsigned long)(uint8_t)frame[3];

  if (key != lastRenderedKey) {
    lastRenderedKey = key;
    tag(F("DISPLAY"));
    Serial.print(F("Time -> "));
    if(hh<10)Serial.print(' '); Serial.print(hh); Serial.print(':');
    if(mm<10)Serial.print('0'); Serial.print(mm);
    Serial.print(F("  ")); Serial.println(summer ? F("CEST+2") : F("CET+1"));
    renderFrame(frame, true);
    sep();
  }
}
