#!/bin/bash

# Register Member Card Schema with Authentication

API_URL="https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/schemavault/"
SCHEMA_FILE="./src/ContentProcessorAPI/samples/schemas/membercard.py"
TENANT_ID="7f7bc67d-797f-4224-b0f2-a0569dd15e85"
API_SCOPE="api://445cde4d-2ab0-4d53-9a41-900716241a95/.default"

echo "🔐 Getting access token..."
echo "You may need to authenticate in your browser..."

# Get access token using Azure CLI with device code flow
ACCESS_TOKEN=$(az account get-access-token \
    --resource "api://445cde4d-2ab0-4d53-9a41-900716241a95" \
    --query accessToken -o tsv 2>&1)

# Check if token retrieval failed
if [[ $ACCESS_TOKEN == *"ERROR"* ]] || [[ $ACCESS_TOKEN == *"AADSTS"* ]]; then
    echo "❌ Failed to get access token. Trying device code authentication..."
    echo "Please run this command to authenticate:"
    echo ""
    echo "az login --tenant $TENANT_ID --scope $API_SCOPE --use-device-code"
    echo ""
    echo "After authentication, run this script again."
    exit 1
fi

echo "✅ Got access token"
echo ""
echo "📤 Registering Member Card schema..."

# Create JSON payload
DATA_JSON='{"ClassName": "MemberCard", "Description": "Member Enrollment Card"}'

# Register the schema
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$API_URL" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H "Content-Type: multipart/form-data" \
    -F "file=@$SCHEMA_FILE;filename=membercard.py;type=text/x-python" \
    -F "data=$DATA_JSON")

# Extract HTTP status
HTTP_STATUS=$(echo "$RESPONSE" | sed -n 's/.*HTTP_STATUS://p')
RESPONSE_BODY=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:.*//')

# Check result
if [ "$HTTP_STATUS" -eq 200 ]; then
    SCHEMA_ID=$(echo "$RESPONSE_BODY" | jq -r '.Id')
    DESC=$(echo "$RESPONSE_BODY" | jq -r '.Description')
    echo "✅ Success! Schema registered:"
    echo "   Description: $DESC"
    echo "   Schema ID: $SCHEMA_ID"
    echo ""
    echo "🎉 You can now select 'Member Enrollment Card' in the web app!"
else
    echo "❌ Failed to register schema. HTTP Status: $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
    exit 1
fi
