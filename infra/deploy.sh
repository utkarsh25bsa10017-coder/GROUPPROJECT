#!/usr/bin/env bash
# =============================================================
# One-shot deploy of the whole AWS backend.
# Requires: aws cli v2, configured credentials, python3, zip
#
#   chmod +x infra/deploy.sh
#   ./infra/deploy.sh
# =============================================================
set -euo pipefail

# ----------------------- CONFIG ------------------------------
REGION="${AWS_REGION:-ap-south-1}"
DB="weatherdb"
TBL="readings"
THING="esp32-weather-01"
TOPIC="weather/data"

ROLE_PREDICT="weather-predict-role"
ROLE_API="weather-api-role"
FN_PREDICT="weather-predict"
FN_API="weather-api"
RULE="weather_to_lambda"
HTTP_API="weather-http-api"
# -------------------------------------------------------------

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Account $ACCOUNT_ID  Region $REGION"

# helper: swap placeholders in a policy file
render() { sed -e "s/REGION/$REGION/g" -e "s/ACCOUNT_ID/$ACCOUNT_ID/g" "$1"; }

# ============ 1. TIMESTREAM =================================
echo "== Timestream =="
aws timestream-write create-database --database-name "$DB" --region "$REGION" 2>/dev/null \
  || echo "   database exists"

# memory store 12h is REQUIRED: forecasts are written up to 10h in the future
aws timestream-write create-table \
  --database-name "$DB" --table-name "$TBL" --region "$REGION" \
  --retention-properties '{"MemoryStoreRetentionPeriodInHours":12,"MagneticStoreRetentionPeriodInDays":30}' \
  2>/dev/null || echo "   table exists"

# ============ 2. IAM ROLES ==================================
echo "== IAM roles =="
make_role () {
  local role=$1 policy_file=$2 policy_name=$3
  aws iam create-role --role-name "$role" \
    --assume-role-policy-document "file://$ROOT/infra/lambda_trust_policy.json" \
    >/dev/null 2>&1 || echo "   role $role exists"
  render "$ROOT/infra/$policy_file" > /tmp/$policy_name.json
  aws iam put-role-policy --role-name "$role" \
    --policy-name "$policy_name" \
    --policy-document file:///tmp/$policy_name.json
  echo "   $role ok"
}
make_role "$ROLE_PREDICT" policy_lambda_predict.json predict-policy
make_role "$ROLE_API"     policy_lambda_api.json     api-policy

echo "   waiting 10s for IAM propagation..."
sleep 10

# ============ 3. LAMBDAS ====================================
echo "== Lambdas =="
deploy_fn () {
  local name=$1 dir=$2 role=$3 timeout=$4
  ( cd "$ROOT/$dir" && rm -f /tmp/$name.zip && zip -qr /tmp/$name.zip lambda_function.py )
  if aws lambda get-function --function-name "$name" --region "$REGION" >/dev/null 2>&1; then
    aws lambda update-function-code --function-name "$name" \
      --zip-file fileb:///tmp/$name.zip --region "$REGION" >/dev/null
    echo "   $name code updated"
  else
    aws lambda create-function --function-name "$name" \
      --runtime python3.12 --handler lambda_function.lambda_handler \
      --role "arn:aws:iam::$ACCOUNT_ID:role/$role" \
      --zip-file fileb:///tmp/$name.zip \
      --timeout "$timeout" --memory-size 256 \
      --environment "Variables={TS_DATABASE=$DB,TS_TABLE=$TBL}" \
      --region "$REGION" >/dev/null
    echo "   $name created"
  fi
  aws lambda update-function-configuration --function-name "$name" \
    --environment "Variables={TS_DATABASE=$DB,TS_TABLE=$TBL}" \
    --region "$REGION" >/dev/null
}
deploy_fn "$FN_PREDICT" lambda_predict "$ROLE_PREDICT" 15
deploy_fn "$FN_API"     lambda_api     "$ROLE_API"     20

# ============ 4. IOT RULE ===================================
echo "== IoT rule =="
cat > /tmp/rule.json <<JSON
{
  "sql": "SELECT * FROM '$TOPIC'",
  "awsIotSqlVersion": "2016-03-23",
  "ruleDisabled": false,
  "actions": [
    { "lambda": { "functionArn": "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FN_PREDICT" } }
  ]
}
JSON
aws iot create-topic-rule --rule-name "$RULE" \
  --topic-rule-payload file:///tmp/rule.json --region "$REGION" 2>/dev/null \
  || aws iot replace-topic-rule --rule-name "$RULE" \
       --topic-rule-payload file:///tmp/rule.json --region "$REGION"

aws lambda add-permission --function-name "$FN_PREDICT" \
  --statement-id iot-invoke --action "lambda:InvokeFunction" \
  --principal iot.amazonaws.com \
  --source-arn "arn:aws:iot:$REGION:$ACCOUNT_ID:rule/$RULE" \
  --region "$REGION" >/dev/null 2>&1 || echo "   permission exists"

# ============ 5. IOT THING + CERTS ==========================
echo "== IoT thing + certificates =="
CERTDIR="$ROOT/certs"
if [ -f "$CERTDIR/certificate.pem.crt" ]; then
  echo "   certs already in $CERTDIR, skipping"
else
  mkdir -p "$CERTDIR"
  aws iot create-thing --thing-name "$THING" --region "$REGION" >/dev/null 2>&1 || true

  CERT_ARN=$(aws iot create-keys-and-certificate --set-as-active \
    --certificate-pem-outfile "$CERTDIR/certificate.pem.crt" \
    --private-key-outfile     "$CERTDIR/private.pem.key" \
    --public-key-outfile      "$CERTDIR/public.pem.key" \
    --region "$REGION" --query certificateArn --output text)

  render "$ROOT/infra/policy_iot_device.json" > /tmp/iot_policy.json
  aws iot create-policy --policy-name esp32-weather-policy \
    --policy-document file:///tmp/iot_policy.json --region "$REGION" >/dev/null 2>&1 || true

  aws iot attach-policy --policy-name esp32-weather-policy --target "$CERT_ARN" --region "$REGION"
  aws iot attach-thing-principal --thing-name "$THING" --principal "$CERT_ARN" --region "$REGION"

  curl -s -o "$CERTDIR/AmazonRootCA1.pem" https://www.amazontrust.com/repository/AmazonRootCA1.pem
  echo "   certs written to $CERTDIR"
fi

# ============ 6. HTTP API ===================================
echo "== API Gateway =="
API_ID=$(aws apigatewayv2 get-apis --region "$REGION" \
  --query "Items[?Name=='$HTTP_API'].ApiId | [0]" --output text)

if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  API_ID=$(aws apigatewayv2 create-api --name "$HTTP_API" \
    --protocol-type HTTP --target "arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FN_API" \
    --route-key "GET /weather" \
    --cors-configuration 'AllowOrigins=*,AllowMethods=GET,AllowHeaders=*' \
    --region "$REGION" --query ApiId --output text)
  echo "   api created $API_ID"
else
  echo "   api exists $API_ID"
fi

aws lambda add-permission --function-name "$FN_API" \
  --statement-id apigw-invoke --action "lambda:InvokeFunction" \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID/*/*/weather" \
  --region "$REGION" >/dev/null 2>&1 || echo "   permission exists"

# ============ DONE ==========================================
ENDPOINT=$(aws iot describe-endpoint --endpoint-type iot:Data-ATS \
  --region "$REGION" --query endpointAddress --output text)

cat <<DONE

===============================================================
 DEPLOY COMPLETE

 Put in secrets.h:
   AWS_IOT_ENDPOINT  "$ENDPOINT"
   THING_NAME        "$THING"
   certs             ./certs/

 Put in dashboard/index.html:
   API_URL = "https://$API_ID.execute-api.$REGION.amazonaws.com/weather"

 Test:
   curl "https://$API_ID.execute-api.$REGION.amazonaws.com/weather"
===============================================================
DONE
