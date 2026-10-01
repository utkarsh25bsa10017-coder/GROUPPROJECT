/*
 * Minimal Display Test - Fixed rotation
 */

#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include <TFT_eSPI.h>

#define BME_SDA 21
#define BME_SCL 22
#define TOUCH_PIN 15

Adafruit_BME280 bme;
TFT_eSPI tft = TFT_eSPI();

bool displayOn = true;
bool lastTouch = LOW;

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("Starting...");
  
  // Init display
  tft.init();
  
  // Try different rotations: 0, 1, 2, 3
  // 0=portrait, 1=landscape, 2=portrait upside down, 3=landscape other way
  tft.setRotation(2);  // Try 2 for correct portrait
  
  // Fill with color to see full screen
  tft.fillScreen(TFT_BLACK);
  
  // Draw border to see edges
  tft.drawRect(0, 0, tft.width(), tft.height(), TFT_RED);
  tft.drawRect(2, 2, tft.width()-4, tft.height()-4, TFT_GREEN);
  
  // Show dimensions
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 10);
  tft.print(tft.width());
  tft.print("x");
  tft.print(tft.height());
  
  delay(1000);
  
  // Init I2C
  Wire.begin(BME_SDA, BME_SCL);
  
  // Init BME280
  bool bmeOk = false;
  if (bme.begin(0x76, &Wire)) {
    bmeOk = true;
  } else if (bme.begin(0x77, &Wire)) {
    bmeOk = true;
  }
  
  if (!bmeOk) {
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.setCursor(40, 150);
    tft.println("BME ERROR!");
    while (1) delay(100);
  }
  
  pinMode(TOUCH_PIN, INPUT);
  Serial.println("Ready!");
}

void loop() {
  // Check touch
  bool touch = digitalRead(TOUCH_PIN);
  if (touch == HIGH && lastTouch == LOW) {
    displayOn = !displayOn;
    delay(200);
  }
  lastTouch = touch;
  
  // Read sensor
  float temp = bme.readTemperature();
  float hum = bme.readHumidity();
  float pres = bme.readPressure();
  
  // Update display
  tft.fillScreen(TFT_BLACK);
  
  // Header at top
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(3);
  tft.setCursor(40, 20);
  tft.print("WEATHER");
  
  // Temp in middle
  tft.setTextColor(TFT_ORANGE, TFT_BLACK);
  tft.setTextSize(5);
  tft.setCursor(30, 100);
  tft.printf("%.1f", temp);
  tft.setTextSize(3);
  tft.print(" C");
  
  // Humidity
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(30, 200);
  tft.printf("Hum: %.1f%%", hum);
  
  // Pressure
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.setCursor(30, 240);
  tft.printf("Pres: %.0f hPa", pres/100.0);
  
  // Touch indicator
  if (touch) {
    tft.fillCircle(200, 50, 15, TFT_RED);
  }
  
  delay(500);
}
