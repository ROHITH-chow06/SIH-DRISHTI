/*
  DRISHTI - V2V receiver node
  Receives the vehicle-node ESP-NOW warning message and indicates
  the remote vehicle's state with LEDs and Serial output.

  The Msg structure MUST remain byte-for-byte compatible with
  vehicle_node.ino.
*/

#include <WiFi.h>
#include <esp_now.h>

#define LED_RED 18
#define LED_BLUE 23

typedef struct {
  char id[8];
  int radar_cm;
  int vis_m;
  bool danger;
} Msg;

volatile bool alert = false;
volatile int lastRadar = -1;
volatile int lastVis = 0;
volatile unsigned long lastHeard = 0;
char otherId[8] = "----";

void onRecv(const esp_now_recv_info_t *info, const uint8_t *data, int len) {
  if (len != sizeof(Msg)) return;

  Msg in;
  memcpy(&in, data, sizeof(in));
  memcpy(otherId, in.id, 8);
  alert = in.danger;
  lastRadar = in.radar_cm;
  lastVis = in.vis_m;
  lastHeard = millis();
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_RED, OUTPUT);
  pinMode(LED_BLUE, OUTPUT);

  WiFi.mode(WIFI_STA);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW FAILED");
    return;
  }

  esp_now_register_recv_cb(onRecv);
  Serial.println("T-52 listening for other vehicles...");
}

void loop() {
  bool live = (millis() - lastHeard) < 2000;

  if (live && alert) {
    digitalWrite(LED_RED, HIGH);
    digitalWrite(LED_BLUE, HIGH);
    delay(120);
    digitalWrite(LED_BLUE, LOW);
    delay(180);

    Serial.printf("!! %s WARNS: radar %d cm, visibility %d m\n",
                  otherId, lastRadar, lastVis);
  } else {
    digitalWrite(LED_RED, LOW);
    digitalWrite(LED_BLUE, LOW);
    Serial.println(live ? "hearing T-47 - all clear"
                        : "no signal from other vehicles");
    delay(500);
  }
}
