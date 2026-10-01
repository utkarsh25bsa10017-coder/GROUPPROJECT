/*
 * WiFi Debug - Blinks LED + scans WiFi
 */

#include <WiFi.h>

#define LED 2

void setup() {
  pinMode(LED, OUTPUT);
  Serial.begin(115200);
  
  // Wait for serial
  int wait = 0;
  while (!Serial && wait < 30) {
    delay(100);
    wait++;
  }
  
  Serial.println("\n========== START ==========");
  
  // Blink to show alive
  for (int i = 0; i < 5; i++) {
    digitalWrite(LED, HIGH);
    delay(200);
    digitalWrite(LED, LOW);
    delay(200);
  }
  
  Serial.println("LED blink done");
  Serial.println("Scanning WiFi...");
  
  WiFi.mode(WIFI_STA);
  int n = WiFi.scanNetworks();
  
  Serial.print("Found ");
  Serial.print(n);
  Serial.println(" networks:");
  
  for (int i = 0; i < n; i++) {
    Serial.print("  ");
    Serial.print(WiFi.SSID(i));
    if (WiFi.SSID(i) == "utkarsh") {
      Serial.print(" <-- FOUND!");
    }
    Serial.println();
  }
  
  if (n == 0) {
    Serial.println("No networks found!");
  }
  
  Serial.println("Done.");
}

void loop() {
  digitalWrite(LED, HIGH);
  delay(1000);
  digitalWrite(LED, LOW);
  delay(1000);
}
