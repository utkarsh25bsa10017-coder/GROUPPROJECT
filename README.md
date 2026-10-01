# ESP32 Weather Station → AWS IoT → Timestream → Dashboard

```
ESP32 (phone WiFi)
  → AWS IoT Core (MQTT/TLS)
      → IoT Rule → Lambda (runs model)
          → DynamoDB
              → API Gateway → Lambda → Dashboard
```

## 🚀 REAL PROJECT SETUP (Step-by-Step)

Follow these exact steps to deploy the working weather station:

### Step 1: AWS Services Setup

1. **Create DynamoDB Table**
   - Go to AWS Console → DynamoDB → Create table
   - Table name: `weather-readings`
   - Partition key: `device_id` (String)
   - Sort key: `timestamp` (String)
   - Click Create

2. **Create Lambda Function (Predict)**
   - Go to Lambda → Create function
   - Name: `Weather-predict`
   - Runtime: Python 3.12
   - Paste code from `lambda_predict/lambda_function.py`
   - Add environment variables: `TS_DATABASE=weatherdb`, `TS_TABLE=readings`
   - Add permission: AmazonDynamoDBFullAccess
   - Deploy

3. **Create Lambda Function (API)**
   - Go to Lambda → Create function
   - Name: `weather-api`
   - Runtime: Python 3.12
   - Paste code from `lambda_api/lambda_function.py`
   - Add permission: AmazonDynamoDBFullAccess
   - Deploy

4. **Create IoT Rule**
   - Go to IoT Core → Message routing → Rules
   - Name: `weather_to_lambda`
   - SQL: `SELECT * FROM 'weather/data'`
   - Action: Lambda → `Weather-predict`
   - Create rule

5. **Create API Gateway**
   - Go to API Gateway → Create API → HTTP API
   - Add integration: Lambda `weather-api`
   - Route: GET `/weather`
   - Deploy to stage: `prod`
   - Copy the API URL (e.g., `https://xxx.execute-api.region.amazonaws.com/prod/weather`)

### Step 2: ESP32 Hardware Setup

1. **Wire the components:**
   | Component | ESP32 Pin |
   |-----------|-----------|
   | BME280 SDA | GPIO 21 |
   | BME280 SCL | GPIO 22 |
   | TFT MOSI | GPIO 23 |
   | TFT SCK | GPIO 18 |
   | TFT CS | GPIO 5 |
   | TFT DC | GPIO 2 |
   | TFT RST | GPIO 4 |

2. **Install Arduino libraries:**
   - PubSubClient
   - ArduinoJson
   - Adafruit BME280
   - Adafruit Unified Sensor
   - TFT_eSPI (configure User_Setup.h)

3. **Configure secrets.h:**
   ```cpp
   #define WIFI_SSID "your-wifi-name"
   #define WIFI_PASSWORD "your-wifi-password"
   #define AWS_IOT_ENDPOINT "your-endpoint-ats.iot.region.amazonaws.com"
   ```

4. **Upload sketch** to ESP32

### Step 3: Dashboard Setup

1. Edit `dashboard/index.html`:
   ```javascript
   const API_URL = "https://your-api-url.execute-api.region.amazonaws.com/prod/weather";
   ```

2. Deploy to GitHub Pages, Vercel, or Netlify

3. Access dashboard in browser

---

## Demo Mode (No Hardware)

If BME280 or WiFi fails, use `laptop_publisher.py` to send simulated data:
```bash
pip3 install paho-mqtt
python3 laptop_publisher.py
```

---

## Original Documentation Below

## Files

| Path | What it is |
|---|---|
| `esp32_weather.ino` | ESP32 firmware — reads DHT22, publishes MQTT/TLS |
| `secrets.h.example` | Template — copy to `secrets.h` and fill in |
| `secrets.h` | Your real WiFi creds, AWS endpoint, certs **(gitignored)** |
| `lambda_predict/lambda_function.py` | Lambda 1 — runs the model, writes Timestream |
| `lambda_predict/test_local.py` | Run the model on your laptop, no AWS |
| `lambda_api/lambda_function.py` | Lambda 2 — reads Timestream, serves JSON |
| `dashboard/index.html` | Dashboard (plain HTML, no build step) |
| `infra/deploy.sh` | Creates everything on AWS in one run |
| `infra/policy_*.json` | IAM / IoT policies |
| `infra/lambda_trust_policy.json` | Lambda assume-role trust |
| `infra/test_event.json` | Sample payload for testing Lambda |
| `certs/` | Created by deploy.sh — device certificates |

---

## Step 0 — Prerequisites

```bash
aws --version      # need v2
aws configure      # access key, secret, region (e.g. ap-south-1)
python3 --version
```

Hardware: ESP32 dev board, BME280 sensor, 1.8" TFT display (ST7735), touch switch, jumper wires.

---

## Step 1 — Test the model locally (2 min, no AWS)

```bash
cd esp32_weather/lambda_predict
python3 test_local.py 31.5 68      # current temp °C, humidity %
```

You should see a 10-hour table. If the numbers look sane, the model is good.

---

## Step 2 — Deploy the whole AWS backend

```bash
cd esp32_weather
export AWS_REGION=ap-south-1        # your region
./infra/deploy.sh
```

This single script creates:

1. **Timestream** database `weatherdb` + table `readings`
   (memory retention 12 h — required, since forecasts are written up to 10 h in the future)
2. **Two IAM roles** with least-privilege policies
3. **Lambda `weather-predict`** (model + Timestream write)
4. **Lambda `weather-api`** (Timestream read)
5. **IoT Rule** `weather_to_lambda` → `SELECT * FROM 'weather/data'` → Lambda 1
6. **IoT Thing** `esp32-weather-01` + certificates downloaded to `./certs/`
7. **HTTP API** with route `GET /weather` → Lambda 2, CORS open

At the end it prints your **IoT endpoint** and **API URL**. Copy both.

> Re-running the script is safe — it updates instead of duplicating.

---

## Step 3 — Verify the backend before touching hardware

```bash
# a) fire a fake reading straight at Lambda 1
aws lambda invoke --function-name weather-predict \
  --payload fileb://infra/test_event.json /tmp/out.json
cat /tmp/out.json          # should contain a 10-entry "forecast"

# b) read it back through the API
curl "https://<API_ID>.execute-api.<REGION>.amazonaws.com/weather"
```

If (a) works but (b) returns empty, wait ~30 s — Timestream needs a moment.

---

## Step 4 — Wire the hardware

### BME280 Sensor (I2C)
| BME280 pin | ESP32 |
|---|---|
| VIN/VCC | 3V3 |
| GND | GND |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

### TFT Display 1.8" (SPI - ST7735)
| TFT pin | ESP32 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| MOSI (DIN) | GPIO 23 |
| SCK (CLK) | GPIO 18 |
| CS | GPIO 5 |
| DC | GPIO 2 |
| RST | GPIO 4 |

### Touch Switch
| Touch pin | ESP32 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SIG | GPIO 15 |

All power connections (3V3 and GND) can be shared on the breadboard power rails.

---

## Step 5 — Flash the ESP32

1. Arduino IDE → **Boards Manager** → install `esp32` by Espressif.
2. **Library Manager** → install:
   - `PubSubClient`
   - `ArduinoJson`
   - `Adafruit BME280 Library`
   - `Adafruit Unified Sensor`
   - `Adafruit GFX Library`
   - `TFT_eSPI` by Bodmer

3. **Configure TFT_eSPI:**
   - Navigate to Arduino libraries folder → `TFT_eSPI`
   - Copy `User_Setup.h` from this project to `TFT_eSPI/` folder
   - OR edit `User_Setup_Select.h` and uncomment: `#include <User_Setups/Setup25_TTGO_T_Display.h>`
   - OR use the provided `User_Setup.h` with custom pin definitions
3. Create your secrets file and open the sketch:
   ```bash
   cp secrets.h.example secrets.h     # secrets.h is gitignored
   ```
   Open `esp32_weather.ino` — `secrets.h` appears as a second tab.
4. Fill in `secrets.h`:

   | Field | Value |
   |---|---|
   | `WIFI_SSID` / `WIFI_PASSWORD` | your phone hotspot |
   | `AWS_IOT_ENDPOINT` | printed by deploy.sh |
   | `THING_NAME` | `esp32-weather-01` |
   | `AWS_CERT_CA` | paste `certs/AmazonRootCA1.pem` |
   | `AWS_CERT_CRT` | paste `certs/certificate.pem.crt` |
   | `AWS_CERT_PRIVATE` | paste `certs/private.pem.key` |

   Paste **between** the existing BEGIN/END lines — don't add a second pair.
5. Select board **ESP32 Dev Module**, pick the port, **Upload**.
6. Open Serial Monitor at **115200**. Expect:

```
WiFi connected. IP: 192.168.43.x
Syncing time... done.
AWS IoT: connecting connected!
Published: {"device_id":"esp32-weather-01","timestamp":...,"temperature":31.4,"humidity":68}
```

**Important:** set your phone hotspot to **2.4 GHz** — ESP32 cannot see 5 GHz.

---

## Step 6 — Watch the data arrive

AWS Console → IoT Core → **MQTT test client** → subscribe to `weather/data`.
You should see a message every 60 s.

---

## Step 7 — Run the dashboard

1. Edit `dashboard/index.html`, set:
   ```js
   const API_URL = "https://<API_ID>.execute-api.<REGION>.amazonaws.com/weather";
   ```
2. Serve it:
   ```bash
   cd dashboard && python3 -m http.server 8080
   ```
   Open <http://localhost:8080>.

Shows current temp/humidity plus the 10-hour forecast table, auto-refreshing every minute.

Optional — host it publicly:
```bash
aws s3 mb s3://my-weather-dash-123
aws s3 website s3://my-weather-dash-123 --index-document index.html
aws s3 cp dashboard/index.html s3://my-weather-dash-123/ --acl public-read
```

---

## How the model works

No training data needed — it's physics-based:

1. **Diurnal curve** — temperature follows a daily cosine, peak ~15:00, min ~03:00, amplitude 4 °C. The current reading is used to derive the daily mean, then projected hour by hour.
2. **Humidity** — moves inversely to temperature (−2.5 % RH per +1 °C).
3. **Dew point** — Magnus formula.
4. **Rain chance** — high RH + small dew-point spread → higher chance; mapped to `Clear` / `Humid / Hazy` / `Cloudy` / `Rain likely`.

Tune in `lambda_predict/lambda_function.py`:
- `amplitude` — larger for dry inland climates, smaller for coastal
- `PEAK_HOUR` — when your area is hottest
- the `+ 5.5` in `lambda_handler` — your UTC offset (currently IST)

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| WiFi stuck on dots | Hotspot must be 2.4 GHz; check SSID/password |
| MQTT `rc=-2` | Wrong endpoint, or certs not pasted correctly |
| MQTT connects then drops | IoT policy client ID must match `THING_NAME` |
| `BME280 not found` | Check I2C wiring (SDA=GPIO21, SCL=GPIO22), try address 0x76 or 0x77 |
| Display stays black | Check TFT_eSPI setup, verify SPI pins (MOSI=23, SCK=18, CS=5, DC=2, RST=4) |
| Display colors inverted | Change `ST7735_RGB_ORDER` to `ST7735_BGR` in User_Setup.h |
| Lambda `AccessDeniedException` | IAM still propagating — wait 30 s, retry |
| Timestream rejects writes | Memory store retention must be ≥ 12 h |
| API returns `[]` | No data in window yet — publish a reading first |
| Dashboard CORS error | Confirm CORS on the HTTP API; headers are already set in Lambda 2 |

---

## Cost

Within AWS Free Tier for a single device at 1 msg/min: ~43k messages/month
(IoT free tier 250k), Lambda ~86k invocations (free 1M), Timestream writes tiny.
Main risk is Timestream **query** cost if you poll the dashboard aggressively —
60 s refresh is fine.
