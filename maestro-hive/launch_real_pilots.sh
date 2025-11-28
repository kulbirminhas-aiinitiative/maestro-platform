#!/bin/bash

# Real Pilot Project Execution - Uses Correct API Endpoint
# Launches 2 projects with REAL AI personas

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="./pilot_real_${TIMESTAMP}"
mkdir -p ${LOG_DIR}

echo "==================================="
echo "REAL Pilot Project Execution"
echo "==================================="
echo "Time: $(date)"
echo "Log Directory: ${LOG_DIR}"
echo ""

# Check if server is running
echo "Checking server status..."
if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "ERROR: Server not running at http://localhost:5001"
    exit 1
fi
echo "✅ Server is running"
echo ""

# Project 1: TastyTalk (B2C - AI Cooking Platform)
echo "==================================="
echo "Project 1: TastyTalk (B2C)"
echo "==================================="

TASTYTALK_REQ='TastyTalk is an AI-powered platform that helps people learn to cook in their own mother tongue. By combining regional language understanding, voice interaction, and visual step-by-step guidance, it makes cooking easy, personal, and culturally connected.'

echo "Launching TastyTalk workflow..."
TASTYTALK_RESPONSE=$(curl -s -X POST http://localhost:5001/api/workflows/tastytalk_parallel/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"requirement\": \"${TASTYTALK_REQ}\",
    \"initial_context\": {
      \"project_name\": \"tastytalk\",
      \"project_type\": \"b2c_platform\"
    }
  }")

echo "${TASTYTALK_RESPONSE}" > ${LOG_DIR}/tastytalk_response.json

TASTYTALK_EXECUTION_ID=$(echo ${TASTYTALK_RESPONSE} | grep -o '"execution_id":"[^"]*"' | cut -d'"' -f4)
TASTYTALK_WF_ID=$(echo ${TASTYTALK_RESPONSE} | grep -o '"workflow_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "${TASTYTALK_EXECUTION_ID}" ]; then
    echo "ERROR: Failed to launch TastyTalk workflow"
    echo "Response: ${TASTYTALK_RESPONSE}"
    exit 1
fi

echo "✅ TastyTalk workflow launched"
echo "   Workflow ID: ${TASTYTALK_WF_ID}"
echo "   Execution ID: ${TASTYTALK_EXECUTION_ID}"
echo "   Track: http://localhost:5001/api/executions/${TASTYTALK_EXECUTION_ID}"
echo ""

# Project 2: Footprint360 (B2B - Business Intelligence)
echo "==================================="
echo "Project 2: Footprint360 (B2B)"
echo "==================================="

FOOTPRINT_REQ='Footprint360 is a business intelligence and process transformation initiative that partners with organizations to map, measure, and enhance their operational footprints. Through structured Identify-Fix-Support-Enhance model, it helps businesses streamline operations and improve decision-making.'

echo "Launching Footprint360 workflow..."
FOOTPRINT_RESPONSE=$(curl -s -X POST http://localhost:5001/api/workflows/footprint360_parallel/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"requirement\": \"${FOOTPRINT_REQ}\",
    \"initial_context\": {
      \"project_name\": \"footprint360\",
      \"project_type\": \"b2b_intelligence\"
    }
  }")

echo "${FOOTPRINT_RESPONSE}" > ${LOG_DIR}/footprint360_response.json

FOOTPRINT_EXECUTION_ID=$(echo ${FOOTPRINT_RESPONSE} | grep -o '"execution_id":"[^"]*"' | cut -d'"' -f4)
FOOTPRINT_WF_ID=$(echo ${FOOTPRINT_RESPONSE} | grep -o '"workflow_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "${FOOTPRINT_EXECUTION_ID}" ]; then
    echo "ERROR: Failed to launch Footprint360 workflow"
    echo "Response: ${FOOTPRINT_RESPONSE}"
    exit 1
fi

echo "✅ Footprint360 workflow launched"
echo "   Workflow ID: ${FOOTPRINT_WF_ID}"
echo "   Execution ID: ${FOOTPRINT_EXECUTION_ID}"
echo "   Track: http://localhost:5001/api/executions/${FOOTPRINT_EXECUTION_ID}"
echo ""

# Save execution IDs for monitoring
cat > ${LOG_DIR}/execution_ids.txt <<EOF
TASTYTALK_EXECUTION_ID=${TASTYTALK_EXECUTION_ID}
TASTYTALK_WF_ID=${TASTYTALK_WF_ID}
FOOTPRINT_EXECUTION_ID=${FOOTPRINT_EXECUTION_ID}
FOOTPRINT_WF_ID=${FOOTPRINT_WF_ID}
TIMESTAMP=${TIMESTAMP}
EOF

echo "==================================="
echo "Both Workflows Launched Successfully"
echo "==================================="
echo ""
echo "Execution IDs saved to: ${LOG_DIR}/execution_ids.txt"
echo ""
echo "Monitor with:"
echo "  curl -s http://localhost:5001/api/executions/${TASTYTALK_EXECUTION_ID} | jq"
echo "  curl -s http://localhost:5001/api/executions/${FOOTPRINT_EXECUTION_ID} | jq"
echo ""
echo "Check artifacts:"
echo "  ls -la /tmp/maestro_workflow/"
echo ""
