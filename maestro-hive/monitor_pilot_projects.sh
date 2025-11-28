#!/bin/bash

# Pilot Project Monitoring Script
# Continuously monitors 2 pilot workflows and generates real-time reports
# Date: 2025-10-12

if [ -z "$1" ]; then
    echo "Usage: $0 <log_directory>"
    echo "Example: $0 ./pilot_run_20251012_123456"
    exit 1
fi

LOG_DIR="$1"
WORKFLOW_IDS="${LOG_DIR}/workflow_ids.txt"

if [ ! -f "${WORKFLOW_IDS}" ]; then
    echo "ERROR: Workflow IDs file not found: ${WORKFLOW_IDS}"
    exit 1
fi

# Load workflow IDs
source ${WORKFLOW_IDS}

echo "==================================="
echo "Pilot Project Monitor"
echo "==================================="
echo "TastyTalk Workflow: ${TASTYTALK_WF_ID}"
echo "Footprint360 Workflow: ${FOOTPRINT_WF_ID}"
echo "Started: ${TIMESTAMP}"
echo "==================================="
echo ""

# Create monitoring log
MONITOR_LOG="${LOG_DIR}/monitor.log"
ANALYSIS_LOG="${LOG_DIR}/analysis.log"

# Function to get workflow status
get_status() {
    local WF_ID=$1
    local NAME=$2

    RESPONSE=$(curl -s http://localhost:5001/api/workflow/${WF_ID}/status 2>/dev/null)

    if [ $? -ne 0 ] || [ -z "${RESPONSE}" ]; then
        echo "${NAME}: ERROR - Cannot reach server"
        return 1
    fi

    # Extract key fields (handle cases where jq might not be available)
    STATUS=$(echo ${RESPONSE} | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4)
    CURRENT_PHASE=$(echo ${RESPONSE} | grep -o '"current_phase":"[^"]*"' | head -1 | cut -d'"' -f4)
    PROGRESS=$(echo ${RESPONSE} | grep -o '"progress":[0-9.]*' | head -1 | cut -d':' -f2)

    # Get completed phases count
    COMPLETED=$(echo ${RESPONSE} | grep -o '"completed"' | wc -l)

    echo "${NAME}:"
    echo "  Status: ${STATUS:-unknown}"
    echo "  Current Phase: ${CURRENT_PHASE:-none}"
    echo "  Progress: ${PROGRESS:-0}%"
    echo "  Completed Phases: ${COMPLETED:-0}"

    # Save to log
    echo "[$(date)] ${NAME} - Status: ${STATUS}, Phase: ${CURRENT_PHASE}, Progress: ${PROGRESS}%" >> ${MONITOR_LOG}

    # Check if workflow is complete
    if [ "${STATUS}" = "completed" ] || [ "${STATUS}" = "failed" ]; then
        return 0
    else
        return 1
    fi
}

# Function to generate analysis
generate_analysis() {
    echo "" | tee -a ${ANALYSIS_LOG}
    echo "==================================" | tee -a ${ANALYSIS_LOG}
    echo "Workflow Analysis - $(date)" | tee -a ${ANALYSIS_LOG}
    echo "==================================" | tee -a ${ANALYSIS_LOG}
    echo "" | tee -a ${ANALYSIS_LOG}

    # TastyTalk detailed status
    echo "--- TastyTalk (B2C) ---" | tee -a ${ANALYSIS_LOG}
    curl -s http://localhost:5001/api/workflow/${TASTYTALK_WF_ID}/status | tee ${LOG_DIR}/tastytalk_status.json | grep -E '"status"|"current_phase"|"progress"|"error"' | tee -a ${ANALYSIS_LOG}
    echo "" | tee -a ${ANALYSIS_LOG}

    # Footprint360 detailed status
    echo "--- Footprint360 (B2B) ---" | tee -a ${ANALYSIS_LOG}
    curl -s http://localhost:5001/api/workflow/${FOOTPRINT_WF_ID}/status | tee ${LOG_DIR}/footprint360_status.json | grep -E '"status"|"current_phase"|"progress"|"error"' | tee -a ${ANALYSIS_LOG}
    echo "" | tee -a ${ANALYSIS_LOG}
}

# Monitor loop
ITERATION=0
BOTH_COMPLETE=false

echo "Monitoring started... (Ctrl+C to stop)"
echo "Logs: ${MONITOR_LOG}"
echo ""

while [ "${BOTH_COMPLETE}" = "false" ]; do
    ITERATION=$((ITERATION + 1))

    echo "==================================="
    echo "Iteration ${ITERATION} - $(date)"
    echo "==================================="

    # Check TastyTalk
    get_status ${TASTYTALK_WF_ID} "TastyTalk"
    TASTYTALK_DONE=$?

    echo ""

    # Check Footprint360
    get_status ${FOOTPRINT_WF_ID} "Footprint360"
    FOOTPRINT_DONE=$?

    echo ""

    # Check if both are complete
    if [ ${TASTYTALK_DONE} -eq 0 ] && [ ${FOOTPRINT_DONE} -eq 0 ]; then
        BOTH_COMPLETE=true
        echo "✅ Both workflows completed!"
        generate_analysis
        break
    fi

    # Generate periodic analysis every 10 iterations
    if [ $((ITERATION % 10)) -eq 0 ]; then
        generate_analysis
    fi

    # Wait before next check
    sleep 10
done

# Final analysis
echo ""
echo "==================================="
echo "Final Analysis"
echo "==================================="
generate_analysis

echo ""
echo "Monitoring complete. Logs saved to:"
echo "  - ${MONITOR_LOG}"
echo "  - ${ANALYSIS_LOG}"
echo "  - ${LOG_DIR}/tastytalk_status.json"
echo "  - ${LOG_DIR}/footprint360_status.json"
echo ""
