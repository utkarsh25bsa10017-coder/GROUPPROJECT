/*
 * ESP32 -> AWS IoT Core (MQTT over TLS)
 * Reads temperature + humidity (DHT22) and publishes JSON every 60s.
 *
 * Libraries needed (Arduino Library Manager):
 *   - PubSubClient      (Nick O'Leary)
 *   - ArduinoJson       (Benoit Blanchon)
 *   - DHT sensor library (Adafruit) + Adafruit Unified Sensor
 */

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <time.h>

// All WiFi credentials, AWS endpoint and certificates live in secrets.h
#include "secrets.h"

// ---- Sensor config ----
#define DHT_PIN   4
#define DHT_TYPE  DHT22      // use DHT11 if that's your sensor

#define PUBLISH_INTERVAL_MS 60000UL   // 1 minute

DHT dht(DHT_PIN, DHT_TYPE);
WiFiClientSecure net;
PubSubClient mqtt(net);

unsigned long lastPublish = 0;

// ---------------- WiFi ----------------
void connectWiFi() {
  Serial.print("WiFi: connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.print("\nWiFi connected. IP: ");
  Serial.println(WiFi.localIP());
}

// TLS needs correct time to validate certs
void syncTime() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Syncing time");
  time_t now = time(nullptr);
  while (now < 1700000000) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }
  Serial.println(" done.");
}

// ---------------- MQTT ----------------
void onMessage(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message on ");
  Serial.print(topic);
  Serial.print(": ");
  for (unsigned int i = 0; i < length; i++) Serial.print((char)payload[i]);
  Serial.println();
}

void connectAWS() {
  net.setCACert(AWS_CERT_CA);
  net.setCertificate(AWS_CERT_CRT);
  net.setPrivateKey(AWS_CERT_PRIVATE);

  mqtt.setServer(AWS_IOT_ENDPOINT, AWS_IOT_PORT);
  mqtt.setCallback(onMessage);
  mqtt.setBufferSize(1024);

  Serial.print("AWS IoT: connecting");
  while (!mqtt.connected()) {
    if (mqtt.connect(THING_NAME)) {
      Serial.println(" connected!");
      mqtt.subscribe(AWS_SUBSCRIBE_TOPIC);
    } else {
      Serial.print(" failed rc=");
      Serial.print(mqtt.state());
      Serial.println(" retrying in 3s");
      delay(3000);
    }
  }
}

// ---------------- Publish ----------------
void publishReading() {
  float temperature = dht.readTemperature();   // Celsius
  float humidity    = dht.readHumidity();      // %

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("Sensor read failed, skipping.");
    return;
  }

  StaticJsonDocument<256> doc;
  doc["device_id"]   = THING_NAME;
  doc["timestamp"]   = (unsigned long)time(nullptr);   // epoch seconds
  doc["temperature"] = temperature;
  doc["humidity"]    = humidity;

  char buffer[256];
  size_t n = serializeJson(doc, buffer);

  if (mqtt.publish(AWS_PUBLISH_TOPIC, buffer, n)) {
    Serial.print("Published: ");
    Serial.println(buffer);
  } else {
    Serial.println("Publish failed.");
  }
}

// ---------------- Main ----------------
void setup() {
  Serial.begin(115200);
  delay(1000);

  dht.begin();
  connectWiFi();
  syncTime();
  connectAWS();

  publishReading();
  lastPublish = millis();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) connectWiFi();
  if (!mqtt.connected())             connectAWS();

  mqtt.loop();

  if (millis() - lastPublish >= PUBLISH_INTERVAL_MS) {
    publishReading();
    lastPublish = millis();
  }
}
