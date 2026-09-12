/*
  DRISHTI - Combined vehicle node
  LD2450 radar + LDR visibility + L293D motor drive
  + autonomous prototype braking + ESP-NOW broadcast

  PINS
  Radar TX -> GPIO16 (ESP32 RX2)
  Radar RX -> GPIO17 (ESP32 TX2)
  LDR sense -> GPIO34
  Red LED -> GPIO18
  Green LED -> GPIO19
  Alert output -> GPIO23
  Motor IN1 -> GPIO4
  Motor IN2 -> GPIO5
  L293D EN1 -> +5V rail directly

  IMPORTANT: BRAKE_CM is a prototype/demo threshold and must be
  calibrated for the actual scaled vehicle before testing.
*/

#include <WiFi.h>
#include <esp_now.h>
#include <math.h>

#define RX_PIN 16
#define TX_PIN 17
#define LDR_PIN 34
#define LED_RED 18
#define LED_GREEN 19
#define ALERT_PIN 23
#define IN1 4
#define IN2 5

#define BRAKE_CM 30
#define FOG_THRESHOLD 45
#define FOG_CLEAR 60
#define RADAR_TIMEOUT_MS 500

uint8_t BCAST[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

typedef struct {
  char id[8];
  int radar_cm;
  int vis_m;
  bool danger;
} Msg;

Msg out;
uint8_t buf[30];
int idx = 0;
int lastGoodDist = -1;
unsigned long lastRadarUpdate = 0;
int clearRef = 0;
bool fogDetected = false;
bool braked = false;

int16_t dec(uint8_t lo, uint8_t hi) {
  int16_t m = (int16_t)((((uint16_t)hi << 8) | lo) & 0x7FFF);
  return (hi & 0x80) ? m : -m;
}

void driveForward() {
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
}

void motorBrake() {
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(256000, SERIAL_8N1, RX_PIN, TX_PIN);

  pinMode(LED_RED, OUTPUT);
  pinMode(LED_GREEN, OUTPUT);
  pinMode(ALERT_PIN, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  motorBrake();
  analogReadResolution(12);
  delay(500);

  Serial.println();
  Serial.println("============================================");
  Serial.println(" DRISHTI vehicle node - booting");
  Serial.println("============================================");

  Serial.println();
  Serial.println("=== CALIBRATING VISIBILITY ===");
  Serial.println("Keep the LDR beam CLEAR for 3 seconds...");
  delay(3000);

  long s = 0;
  for (int i = 0; i < 60; i++) {
    s += analogRead(LDR_PIN);
    delay(10);
  }

  clearRef = s / 60;
  Serial.printf("CLEAR REFERENCE = %d\n", clearRef);

  if (clearRef < 1500) {
    Serial.println("!!! Calibration looked wrong (beam may have been blocked)");
    Serial.println("!!! Forcing safe default of 3900");
    clearRef = 3900;
  }

  Serial.println();
  Serial.println("=== STARTING ESP-NOW ===");
  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init FAILED - continuing without broadcast");
  } else {
    esp_now_peer_info_t p = {};
    memcpy(p.peer_addr, BCAST, 6);
    p.channel = 0;
    p.encrypt = false;
    esp_now_add_peer(&p);
    Serial.println("ESP-NOW ready");
  }

  strcpy(out.id, "T47");

  Serial.println();
  Serial.println("=== ARMED - starting in 2 seconds ===");
  delay(2000);
  driveForward();
  Serial.println(">>> DRIVING");
  Serial.println();
}

void loop() {
  while (Serial2.available()) {
    uint8_t b = Serial2.read();

    if (idx == 0 && b != 0xAA) continue;
    if (idx == 1 && b != 0xFF) { idx = 0; continue; }
    if (idx == 2 && b != 0x03) { idx = 0; continue; }
    if (idx == 3 && b != 0x00) { idx = 0; continue; }

    buf[idx++] = b;

    if (idx >= 30) {
      idx = 0;

      if (buf[28] == 0x55 && buf[29] == 0xCC) {
        int x = dec(buf[4], buf[5]);
        int y = dec(buf[6], buf[7]);

        if (!(x == 0 && y == 0)) {
          lastGoodDist = (int)(sqrt((float)x * x + (float)y * y) / 10.0);
        } else {
          lastGoodDist = -1;
        }

        lastRadarUpdate = millis();
      }
    }
  }

  bool radarStale = (millis() - lastRadarUpdate) > RADAR_TIMEOUT_MS;

  int raw = analogRead(LDR_PIN);
  if (raw < 50 || raw > 4095) raw = clearRef;

  int pct = (clearRef > 0) ? (raw * 100 / clearRef) : 0;
  if (pct > 100) pct = 100;

  if (!fogDetected && pct < FOG_THRESHOLD) fogDetected = true;
  if (fogDetected && pct > FOG_CLEAR) fogDetected = false;

  int vis_m;
  if (pct >= 85) vis_m = 200;
  else if (pct >= 65) vis_m = 100;
  else if (pct >= 45) vis_m = 50;
  else if (pct >= 30) vis_m = 20;
  else if (pct >= 15) vis_m = 10;
  else vis_m = 4;

  bool radarClose = (!radarStale && lastGoodDist > 0 && lastGoodDist < BRAKE_CM);

  bool warnCondition = fogDetected || radarClose;
  digitalWrite(LED_RED, warnCondition);
  digitalWrite(LED_GREEN, !warnCondition);

  if (warnCondition) {
    digitalWrite(ALERT_PIN, HIGH);
    delay(50);
    digitalWrite(ALERT_PIN, LOW);
  }

  if (!braked && radarClose) {
    motorBrake();
    braked = true;

    Serial.println();
    Serial.println(">>> BRAKE APPLIED <<<");
    Serial.printf(" radar: %d cm | visibility: %d m | fog: %s | RED LED: ON\n",
                  lastGoodDist, vis_m, fogDetected ? "YES" : "no");
    Serial.println();
  }

  if (!braked) {
    Serial.printf("radar:%4d cm vis:%3d m (%3d%%) fog:%s stale:%s driving\n",
                  lastGoodDist, vis_m, pct,
                  fogDetected ? "Y" : "n",
                  radarStale ? "Y" : "n");
  }

  out.radar_cm = lastGoodDist;
  out.vis_m = vis_m;
  out.danger = warnCondition;
  esp_now_send(BCAST, (uint8_t*)&out, sizeof(out));

  delay(100);
}
