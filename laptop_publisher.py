#!/usr/bin/env python3
"""
Send dummy weather data to AWS IoT Core from laptop
Install: pip install paho-mqtt
"""

import json
import time
import random
import ssl
import paho.mqtt.client as mqtt

# ====== CONFIG ======
IOT_ENDPOINT = "YOUR_ENDPOINT_HERE-ats.iot.ap-south-1.amazonaws.com"
THING_NAME = "esp32-weather-01"
TOPIC = "weather/data"

# Certificate paths (from certs/ folder after deploy)
CA_CERT = "certs/AmazonRootCA1.pem"
CLIENT_CERT = "certs/certificate.pem.crt"
PRIVATE_KEY = "certs/private.pem.key"

# Simulated data starting point
temp = 28.0
humidity = 65.0


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to AWS IoT Core!")
    else:
        print(f"Connection failed with code {rc}")


def on_publish(client, userdata, mid):
    print(f"Message {mid} published")


client = mqtt.Client(client_id=THING_NAME)
client.on_connect = on_connect
client.on_publish = on_publish

# TLS setup
client.tls_set(CA_CERT, CLIENT_CERT, PRIVATE_KEY, ssl.CERT_REQUIRED, ssl.PROTOCOL_TLSv1_2)

print(f"Connecting to {IOT_ENDPOINT}...")
client.connect(IOT_ENDPOINT, 8883, 60)
client.loop_start()

try:
    while True:
        # Generate realistic dummy data
        temp += random.uniform(-0.5, 0.5)
        temp = max(20, min(38, temp))
        
        humidity = 70 - (temp - 25) * 2 + random.uniform(-3, 3)
        humidity = max(40, min(90, humidity))
        
        payload = {
            "device_id": THING_NAME,
            "timestamp": int(time.time()),
            "temperature": round(temp, 1),
            "humidity": round(humidity, 1)
        }
        
        msg = json.dumps(payload)
        client.publish(TOPIC, msg, qos=1)
        print(f"Sent: {msg}")
        
        time.sleep(10)  # Send every 10 seconds
        
except KeyboardInterrupt:
    print("\nStopping...")
    client.loop_stop()
    client.disconnect()
