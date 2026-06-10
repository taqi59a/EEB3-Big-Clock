#include <SevSeg.h>
#include <Wire.h>
#include <RTClib.h>

SevSeg sevseg;
RTC_DS3231 rtc;

unsigned long previousCycleMillis = 0;
unsigned long lastRTCReadMillis = 0;
int currentDisplayTime = 0;
bool currentBlinkState = false;
int currentMins = 0;

struct Period {
  int startMins;
  int endMins;
  const char* disp;
};

Period schedule[] = {
  {8 * 60 + 30, 9 * 60 + 15, "P  1"},
  {9 * 60 + 20, 10 * 60 + 5, "P  2"},
  {10 * 60 + 10, 10 * 60 + 55, "P  3"},
  {10 * 60 + 55, 11 * 60 + 15, "brk "},
  {11 * 60 + 15, 12 * 60 + 0, "P  4"},
  {12 * 60 + 5, 12 * 60 + 50, "P  5"},
  {13 * 60 + 0, 13 * 60 + 45, "P  6"},
  {13 * 60 + 50, 14 * 60 + 35, "P  7"},
  {14 * 60 + 40, 15 * 60 + 25, "P  8"},
  {15 * 60 + 30, 16 * 60 + 15, "P  9"}
};
const int numPeriods = 10;

const char* getActivePeriod(int mins) {
  for (int i = 0; i < numPeriods; i++) {
    if (mins >= schedule[i].startMins && mins < schedule[i].endMins) {
      return schedule[i].disp;
    }
  }
  return nullptr; 
}

void setup() {
  Serial.begin(9600);
  
  Wire.begin();
  rtc.begin();
  
  if (rtc.lostPower()) {
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  }
  
  byte numDigits = 4;
  byte digitPins[] = {10, 11, 12, 13};
  byte segmentPins[] = {2, 3, 4, 5, 6, 7, 8, 9};
  bool resistorsOnSegments = true;
  byte hardwareConfig = COMMON_CATHODE; 
  
  sevseg.begin(hardwareConfig, numDigits, digitPins, segmentPins, resistorsOnSegments, false, false, false);
  sevseg.setBrightness(90);
}

void loop() {
  unsigned long currentMillis = millis();
  
  unsigned long elapsedSinceRead = currentMillis + (~lastRTCReadMillis + 1);
  if (elapsedSinceRead >= 1000) {
    lastRTCReadMillis = currentMillis;
    DateTime nowRTC = rtc.now();
    currentDisplayTime = nowRTC.hour() * 100 + nowRTC.minute();
    currentBlinkState = (nowRTC.second() % 2 == 0);
    currentMins = nowRTC.hour() * 60 + nowRTC.minute();
  }

  const char* activePeriod = getActivePeriod(currentMins);
  bool hasPeriod = (activePeriod != nullptr);
  
  unsigned long totalCycle = hasPeriod ? 11000 : 6000;
  
  unsigned long elapsedInCycle = currentMillis + (~previousCycleMillis + 1);

  if (elapsedInCycle >= totalCycle) {
    previousCycleMillis = currentMillis;
    elapsedInCycle = 0;
  }

  if (elapsedInCycle < 5000) {
    if (currentBlinkState) {
      sevseg.setNumber(currentDisplayTime, 2); 
    } else {
      sevseg.setNumber(currentDisplayTime); 
    }
  } else if (elapsedInCycle < 6000) {
    sevseg.setChars("EEb3");
  } else {
    sevseg.setChars(activePeriod);
  }

  sevseg.refreshDisplay();
}