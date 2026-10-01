"""
Test the forecast model on your laptop -- no AWS needed.

    cd lambda_predict
    python3 test_local.py 31.5 68
"""
import sys
import time

from lambda_function import predict_next_hours

temp = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
hum = float(sys.argv[2]) if len(sys.argv) > 2 else 65.0
hour = (time.gmtime().tm_hour + 5.5) % 24          # IST

print(f"\nNow: {temp} C, {hum}% RH  (local hour {hour:.1f})\n")
print(f"{'+hr':>4} {'clk':>4} {'temp':>7} {'rh':>6} {'dew':>7} {'rain':>6}  condition")
print("-" * 58)
for f in predict_next_hours(temp, hum, hour):
    print(f"{f['hour_ahead']:>4} {f['clock_hour']:>4} "
          f"{f['temperature']:>6.1f}C {f['humidity']:>5.0f}% "
          f"{f['dew_point']:>6.1f}C {f['rain_chance']:>5.0f}%  {f['condition']}")
print()
