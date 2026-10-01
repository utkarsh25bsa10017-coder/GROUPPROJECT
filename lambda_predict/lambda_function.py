"""
Lambda 1: weather-predict
Trigger : AWS IoT Rule  ->  SELECT * FROM 'weather/data'
Job     : take current temp + humidity, predict next 10 hours, write to Timestream.

Env vars:
  TS_DATABASE = weatherdb
  TS_TABLE    = readings

IAM: timestream:WriteRecords, timestream:DescribeEndpoints
Runtime: Python 3.12
"""

import os
import math
import time
TS_DATABASE = os.environ.get("TS_DATABASE", "weatherdb")
TS_TABLE = os.environ.get("TS_TABLE", "readings")

# boto3 ships with the Lambda runtime; guard it so test_local.py works offline
try:
    import boto3
    ts = boto3.client("timestreamwrite")
except Exception:
    ts = None


# ---------------------------------------------------------------
# THE MODEL (simple physics-based diurnal model, no training data)
# ---------------------------------------------------------------
def predict_next_hours(temp_c, humidity, start_hour, hours=10):
    """
    Idea:
      1. Temperature follows a daily sine curve, peak ~15:00, min ~05:00.
      2. Humidity moves opposite to temperature (warm air -> lower RH).
      3. Rain chance rises when humidity is high and dew point is close to temp.
    """
    # how much temp swings over a day (half of daily max-min). ~4C is typical
    amplitude = 4.0
    PEAK_HOUR = 15.0

    def diurnal(h):
        # +1 at 15:00, -1 at 03:00
        return math.cos((h - PEAK_HOUR) * math.pi / 12.0)

    base = temp_c - amplitude * diurnal(start_hour)  # daily mean temperature

    out = []
    for i in range(1, hours + 1):
        h = (start_hour + i) % 24

        t = base + amplitude * diurnal(h)

        # humidity inversely tracks temperature change
        rh = humidity - (t - temp_c) * 2.5
        rh = max(10.0, min(100.0, rh))

        # dew point (Magnus formula)
        a, b = 17.27, 237.7
        alpha = (a * t) / (b + t) + math.log(max(rh, 1.0) / 100.0)
        dew = (b * alpha) / (a - alpha)

        # closer dew point + high RH => more likely rain
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
            "dew_point": round(dew, 2),
            "rain_chance": round(rain, 1),
            "condition": cond,
        })
    return out


# ---------------------------------------------------------------
# Timestream helpers
# ---------------------------------------------------------------
def _rec(name, value, dims, ts_ms):
    return {
        "Dimensions": dims,
        "MeasureName": name,
        "MeasureValue": str(value),
        "MeasureValueType": "DOUBLE",
        "Time": str(ts_ms),
        "TimeUnit": "MILLISECONDS",
    }


def write_timestream(records):
    for i in range(0, len(records), 100):  # max 100 records per call
        ts.write_records(
            DatabaseName=TS_DATABASE,
            TableName=TS_TABLE,
            Records=records[i:i + 100],
        )


# ---------------------------------------------------------------
# Handler
# ---------------------------------------------------------------
def lambda_handler(event, context):
    print("event:", event)

    device = event.get("device_id", "unknown")
    temp = float(event["temperature"])
    hum = float(event["humidity"])
    epoch_s = int(event.get("timestamp") or time.time())
    now_ms = epoch_s * 1000

    start_hour = time.gmtime(epoch_s).tm_hour + 5.5  # UTC -> IST, change if needed
    start_hour %= 24

    forecast = predict_next_hours(temp, hum, start_hour)

    records = []

    # 1) current actual reading
    dims_now = [
        {"Name": "device_id", "Value": device},
        {"Name": "kind", "Value": "actual"},
    ]
    records.append(_rec("temperature", temp, dims_now, now_ms))
    records.append(_rec("humidity", hum, dims_now, now_ms))

    # 2) the 10-hour forecast (timestamped at the future hour)
    for f in forecast:
        future_ms = now_ms + f["hour_ahead"] * 3600 * 1000
        dims = [
            {"Name": "device_id", "Value": device},
            {"Name": "kind", "Value": "forecast"},
            {"Name": "hour_ahead", "Value": str(f["hour_ahead"])},
            {"Name": "condition", "Value": f["condition"]},
        ]
        records.append(_rec("temperature", f["temperature"], dims, future_ms))
        records.append(_rec("humidity", f["humidity"], dims, future_ms))
        records.append(_rec("rain_chance", f["rain_chance"], dims, future_ms))

    write_timestream(records)

    return {
        "device_id": device,
        "current": {"temperature": temp, "humidity": hum},
        "forecast": forecast,
    }
