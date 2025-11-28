#!/bin/bash

# Pilot Project Execution Script
# Runs 2 projects in parallel to validate DAG workflow system
# Date: 2025-10-12

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="./pilot_run_${TIMESTAMP}"
mkdir -p ${LOG_DIR}

echo "==================================="
echo "Pilot Project Execution"
echo "==================================="
echo "Time: $(date)"
echo "Log Directory: ${LOG_DIR}"
echo ""

# Check if server is running
echo "Checking server status..."
if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "ERROR: Server not running at http://localhost:5001"
    echo "Please start the server first"
    exit 1
fi
echo "✅ Server is running"
echo ""

# Project 1: TastyTalk (B2C - AI Cooking Platform)
echo "==================================="
echo "Project 1: TastyTalk (B2C)"
echo "==================================="

TASTYTALK_REQ='TastyTalk is an AI-powered platform that helps people learn to cook in their own mother tongue. By combining regional language understanding, voice interaction, and visual step-by-step guidance, it makes cooking easy, personal, and culturally connected. TastyTalk preserves the warmth of traditional kitchen learning while using modern AI to guide users through recipes, suggest dishes based on available ingredients, and teach techniques in a language they truly understand.'

echo "Launching TastyTalk workflow..."
TASTYTALK_RESPONSE=$(curl -s -X POST http://localhost:5001/api/workflow/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"requirement\": \"${TASTYTALK_REQ}\",
    \"mode\": \"dag\",
    \"project_name\": \"tastytalk\",
    \"quality_threshold\": 0.70
  }")

TASTYTALK_WF_ID=$(echo ${TASTYTALK_RESPONSE} | grep -o '"workflow_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "${TASTYTALK_WF_ID}" ]; then
    echo "ERROR: Failed to launch TastyTalk workflow"
    echo "Response: ${TASTYTALK_RESPONSE}"
    exit 1
fi

echo "✅ TastyTalk workflow launched"
echo "   Workflow ID: ${TASTYTALK_WF_ID}"
echo "   Track: http://localhost:5001/api/workflow/${TASTYTALK_WF_ID}/status"
echo ""

# Project 2: Footprint360 (B2B - Business Intelligence)
echo "==================================="
echo "Project 2: Footprint360 (B2B)"
echo "==================================="

FOOTPRINT_REQ='Footprint360 is a business intelligence and process transformation initiative that partners with organizations to map, measure, and enhance their operational footprints. By immersing into each industry'\''s ecosystem, it evaluates how processes truly perform on the ground—identifying inefficiencies, uncovering hidden opportunities, and designing practical fixes. Through a structured "Identify–Fix–Support–Enhance" model, Footprint360 helps businesses streamline operations, improve decision-making, and achieve sustainable growth, turning every process insight into measurable value.'

echo "Launching Footprint360 workflow..."
FOOTPRINT_RESPONSE=$(curl -s -X POST http://localhost:5001/api/workflow/execute \
  -H "Content-Type: application/json" \
  -d "{
    \"requirement\": \"${FOOTPRINT_REQ}\",
    \"mode\": \"dag\",
    \"project_name\": \"footprint360\",
    \"quality_threshold\": 0.70
  }")

FOOTPRINT_WF_ID=$(echo ${FOOTPRINT_RESPONSE} | grep -o '"workflow_id":"[^"]*"' | cut -d'"' -f4)

if [ -z "${FOOTPRINT_WF_ID}" ]; then
    echo "ERROR: Failed to launch Footprint360 workflow"
    echo "Response: ${FOOTPRINT_RESPONSE}"
    exit 1
fi

echo "✅ Footprint360 workflow launched"
echo "   Workflow ID: ${FOOTPRINT_WF_ID}"
echo "   Track: http://localhost:5001/api/workflow/${FOOTPRINT_WF_ID}/status"
echo ""

# Save workflow IDs for monitoring
cat > ${LOG_DIR}/workflow_ids.txt <<EOF
TASTYTALK_WF_ID=${TASTYTALK_WF_ID}
FOOTPRINT_WF_ID=${FOOTPRINT_WF_ID}
TIMESTAMP=${TIMESTAMP}
EOF

echo "==================================="
echo "Both Workflows Launched Successfully"
echo "==================================="
echo ""
echo "Workflow IDs saved to: ${LOG_DIR}/workflow_ids.txt"
echo ""
echo "Monitor with:"
echo "  watch -n 5 'curl -s http://localhost:5001/api/workflow/${TASTYTALK_WF_ID}/status | jq'"
echo "  watch -n 5 'curl -s http://localhost:5001/api/workflow/${FOOTPRINT_WF_ID}/status | jq'"
echo ""
echo "Or use the monitoring script:"
echo "  ./monitor_pilot_projects.sh ${LOG_DIR}"
echo ""
