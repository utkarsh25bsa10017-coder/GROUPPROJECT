"""
Lambda: weather-predict
Uses DynamoDB instead of Timestream
"""

import os
import math
import time
import json
import boto3

# DynamoDB setup
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('weather-readings')

def predict_next_hours(temp_c, humidity, start_hour, hours=10):
    amplitude = 4.0
    PEAK_HOUR = 15.0

    def diurnal(h):
        return math.cos((h - PEAK_HOUR) * math.pi / 12.0)

    base = temp_c - amplitude * diurnal(start_hour)

    out = []
    for i in range(1, hours + 1):
        h = (start_hour + i) % 24
        t = base + amplitude * diurnal(h)
        rh = humidity - (t - temp_c) * 2.5
        rh = max(10.0, min(100.0, rh))
        
        a, b = 17.27, 237.7
        alpha = (a * t) / (b + t) + math.log(max(rh, 1.0) / 100.0)
        dew = (b * alpha) / (a - alpha)
        spread = t - dew
        rain = max(0.0, min(100.0, (rh - 60.0) * 2.0 - spread * 8.0))

        if rain > 60:
            cond = "Rain likely"
        elif rain > 30:
            cond = "Cloudy"
        elif rh > 80:
            cond = "Humid / Hazy"
        else:
            cond = "Clear"

        out.append({
            "hour_ahead": i,
            "clock_hour": int(h),
            "temperature": round(t, 2),
            "humidity": round(rh, 1),
            "rain_chance": round(rain, 1),
            "condition": cond,
        })
    return out


def lambda_handler(event, context):
    print("event:", event)

    # Handle IoT Core message or direct invoke
    if isinstance(event, str):
        event = json.loads(event)

    device = event.get("device_id", "esp32-weather-01")
    temp = float(event.get("temperature", 28.0))
    hum = float(event.get("humidity", 72.0))
    epoch_s = int(event.get("timestamp") or time.time())

    start_hour = time.gmtime(epoch_s).tm_hour + 5.5
    start_hour %= 24

    forecast = predict_next_hours(temp, hum, start_hour)

    # Store in DynamoDB
    item = {
        "device_id": device,
        "timestamp": epoch_s,
        "temperature": temp,
        "humidity": hum,
        "forecast": forecast,
        "ttl": epoch_s + 86400  # Delete after 24 hours
    }

    table.put_item(Item=item)

    return {
        "statusCode": 200,
        "device_id": device,
        "current": {"temperature": temp, "humidity": hum},
        "forecast": forecast,
    }
