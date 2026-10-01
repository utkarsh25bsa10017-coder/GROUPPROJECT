"""
Lambda 2: weather-api
Trigger : API Gateway (HTTP API)  GET /weather
Job     : read latest actual + forecast from Timestream, return JSON for dashboard.

Env vars:
  TS_DATABASE = weatherdb
  TS_TABLE    = readings

IAM: timestream:Select, timestream:DescribeEndpoints
Runtime: Python 3.12
"""

import os
import json
import boto3

DB = os.environ.get("TS_DATABASE", "weatherdb")
TBL = os.environ.get("TS_TABLE", "readings")

q = boto3.client("timestreamquery")


def run(sql):
    """Run query and return list of dicts."""
    r = q.query(QueryString=sql)
    cols = [c["Name"] for c in r["ColumnInfo"]]
    rows = []
    for row in r["Rows"]:
        vals = []
        for d in row["Data"]:
            vals.append(d.get("ScalarValue"))
        rows.append(dict(zip(cols, vals)))
    return rows


def lambda_handler(event, context):
    try:
        # latest actual reading
        current = run(f'''
            SELECT device_id, measure_name, measure_value::double AS value, time
            FROM "{DB}"."{TBL}"
            WHERE kind = 'actual'
              AND time > ago(2h)
            ORDER BY time DESC
            LIMIT 10
        ''')

        # forecast for the next 10 hours
        forecast = run(f'''
            SELECT hour_ahead, condition, measure_name,
                   measure_value::double AS value, time
            FROM "{DB}"."{TBL}"
            WHERE kind = 'forecast'
              AND time BETWEEN now() AND now() + 11h
            ORDER BY time ASC
        ''')

        # reshape forecast rows -> one object per hour
        buckets = {}
        for r in forecast:
            h = int(r["hour_ahead"])
            b = buckets.setdefault(h, {
                "hour_ahead": h,
                "time": r["time"],
                "condition": r["condition"],
            })
            b[r["measure_name"]] = float(r["value"])

        body = {
            "current": current,
            "forecast": [buckets[k] for k in sorted(buckets)],
        }
        code = 200
    except Exception as e:
        body = {"error": str(e)}
        code = 500

    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",   # so dashboard can fetch
        },
        "body": json.dumps(body),
    }
