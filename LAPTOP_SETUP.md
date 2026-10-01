# Laptop Setup for AWS IoT Weather Demo

## Prerequisites
- AWS CLI installed and configured (`aws configure`)
- Python 3 installed
- AWS account with access

## Step 1: Deploy AWS Backend

Open Terminal on your Mac and run:

```bash
cd /Users/utkarsh/esp32_weather
export AWS_REGION=ap-south-1
chmod +x infra/deploy.sh
./infra/deploy.sh
```

This will take ~2 minutes. At the end, you'll see:
```
IoT Endpoint: xxxxxxxx-ats.iot.ap-south-1.amazonaws.com
API URL: https://xxxxxx.execute-api.ap-south-1.amazonaws.com/weather
```

**Copy these two values!**

## Step 2: Get Certificates

After deploy, you'll have a `certs/` folder with:
- `AmazonRootCA1.pem`
- `certificate.pem.crt`
- `private.pem.key`

## Step 3: Install Python Dependencies

```bash
pip3 install paho-mqtt
```

## Step 4: Update Publisher Script

Edit `/Users/utkarsh/esp32_weather/laptop_publisher.py`:

Replace `YOUR_ENDPOINT_HERE` with your actual IoT endpoint from Step 1.

Example:
```python
IOT_ENDPOINT = "a1b2c3d4e5f6g7-ats.iot.ap-south-1.amazonaws.com"
```

## Step 5: Run the Publisher

```bash
cd /Users/utkarsh/esp32_weather
python3 laptop_publisher.py
```

You should see:
```
Connecting to xxxxxxxx-ats.iot.ap-south-1.amazonaws.com...
Connected to AWS IoT Core!
Sent: {"device_id":"esp32-weather-01","timestamp":1234567890,"temperature":28.3,"humidity":71.5}
```

## Step 6: Test the Dashboard

Edit `dashboard/index.html`:
- Find `const API_URL = "..."`
- Replace with your API URL from Step 1

Then run:
```bash
cd /Users/utkarsh/esp32_weather/dashboard
python3 -m http.server 8080
```

Open browser: http://localhost:8080

You should see:
- Current temperature and humidity
- 10-hour forecast table

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No module named paho" | Run `pip3 install paho-mqtt` |
| "Connection refused" | Check IoT endpoint is correct |
| "SSL certificate verify failed" | Check cert paths are correct |
| Dashboard shows empty | Wait 30 seconds for Timestream |

## How It Works

1. **Laptop** sends MQTT message to AWS IoT Core
2. **IoT Rule** triggers Lambda function
3. **Lambda** runs weather prediction model
4. **Lambda** writes forecast to Timestream
5. **Dashboard** fetches data from API Gateway
6. **API Gateway** queries Timestream via Lambda

## Demo Flow

1. Show ESP32 display (static weather data)
2. Show laptop sending data to AWS
3. Show dashboard with predictions
4. Explain: "ESP32 sends sensor data → AWS predicts weather → Dashboard shows forecast"
