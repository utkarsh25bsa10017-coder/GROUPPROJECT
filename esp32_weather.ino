/*
 * ESP32 Weather Station - Display Only
 * Shows fake WiFi connecting, then static weather data
 */

#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

void setup() {
  // Init display
  tft.init();
  tft.setRotation(0);
  tft.fillScreen(TFT_BLACK);
  
  // Show "WiFi..." for 5 seconds
  tft.setTextColor(TFT_WHITE, TFT_BLACK);
  tft.setTextSize(3);
  tft.setCursor(70, 140);
  tft.print("WiFi...");
  
  delay(5000);
  
  // Clear and show weather
  tft.fillScreen(TFT_BLACK);
  
  // Title
  tft.setTextColor(TFT_CYAN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(70, 10);
  tft.print("WEATHER");
  
  // WiFi status - green OK
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setTextSize(1);
  tft.setCursor(180, 20);
  tft.print("OK");
  
  // Temperature - fixed 28.5
  tft.setTextColor(TFT_ORANGE, TFT_BLACK);
  tft.setTextSize(5);
  tft.setCursor(20, 60);
  tft.print("28.5");
  tft.setTextSize(3);
  tft.print("C");
  
  // Humidity - fixed 72%
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(30, 140);
  tft.print("Humidity: 72.0%");
  
  // Pressure - fixed 1013 hPa
  tft.setTextColor(TFT_YELLOW, TFT_BLACK);
  tft.setCursor(30, 180);
  tft.print("Pressure: 1013hPa");
  

}

void loop() {
  // Nothing to update - static display
  delay(1000);
}
