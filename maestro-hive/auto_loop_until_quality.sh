#!/bin/bash
# Auto-loop team_execution until 90%+ quality/maturity is achieved
# Usage: ./auto_loop_until_quality.sh SESSION_ID PERSONAS MAX_ITERATIONS

SESSION_ID="$1"
shift
PERSONAS="$@"
MAX_ITERATIONS=3

echo "================================================================================"
echo "🔄 AUTO-LOOP UNTIL 90%+ QUALITY/MATURITY"
echo "================================================================================"
echo "📝 Session: $SESSION_ID"
echo "🤖 Personas: $PERSONAS"
echo "🎯 Max Iterations: $MAX_ITERATIONS"
echo "🎯 Target: 90%+ maturity/quality"
echo "================================================================================"

for iteration in $(seq 1 $MAX_ITERATIONS); do
    echo ""
    echo "================================================================================"
    echo "🔄 ITERATION $iteration/$MAX_ITERATIONS"
    echo "================================================================================"

    # Run team_execution with force mode
    poetry run python3 team_execution.py $PERSONAS --resume $SESSION_ID --output $SESSION_ID --force

    # Check if execution succeeded
    if [ $? -ne 0 ]; then
        echo "❌ Execution failed, stopping"
        exit 1
    fi

    echo ""
    echo "📊 Checking project_reviewer assessment..."

    # Check if metrics file exists
    METRICS_FILE="${SESSION_ID}/reviews/metrics_json.json"
    if [ ! -f "$METRICS_FILE" ]; then
        echo "⚠️  Metrics file not found at $METRICS_FILE"
        echo "🔄 Will try next iteration..."
        continue
    fi

    # Extract maturity level and completion percentage
    MATURITY=$(jq -r '.overall_metrics.maturity_level // 0' "$METRICS_FILE")
    COMPLETION=$(jq -r '.overall_metrics.completion_percentage // 0' "$METRICS_FILE")
    QUALITY=$(jq -r '.overall_metrics.quality_score // 0' "$METRICS_FILE")
    RECOMMENDATION=$(jq -r '.overall_metrics.recommended_action // "UNKNOWN"' "$METRICS_FILE")

    echo "================================================================================"
    echo "📊 ITERATION $iteration RESULTS"
    echo "================================================================================"
    echo "Maturity Level: $MATURITY/5"
    echo "Completion: $COMPLETION%"
    echo "Quality Score: $QUALITY/10"
    echo "Recommendation: $RECOMMENDATION"
    echo "================================================================================"

    # Calculate percentage (maturity * 20 to convert 5-scale to 100-scale)
    MATURITY_PERCENT=$(echo "$MATURITY * 20" | bc)

    # Check if we've met the 90% threshold
    MEETS_MATURITY=$(echo "$MATURITY_PERCENT >= 90" | bc)
    MEETS_COMPLETION=$(echo "$COMPLETION >= 90" | bc)
    MEETS_QUALITY=$(echo "$QUALITY >= 9" | bc)

    if [ "$MEETS_MATURITY" -eq 1 ] || [ "$MEETS_COMPLETION" -eq 1 ] || [ "$MEETS_QUALITY" -eq 1 ]; then
        echo ""
        echo "✅ ✅ ✅ TARGET ACHIEVED! ✅ ✅ ✅"
        echo "Project has reached 90%+ quality/maturity threshold"
        exit 0
    fi

    if [ "$RECOMMENDATION" = "GO" ]; then
        echo ""
        echo "✅ ✅ ✅ PROJECT APPROVED FOR PRODUCTION! ✅ ✅ ✅"
        exit 0
    fi

    if [ $iteration -lt $MAX_ITERATIONS ]; then
        echo ""
        echo "⚠️  Quality/Maturity below 90%, continuing to next iteration..."
        sleep 5
    fi
done

echo ""
echo "================================================================================"
echo "⚠️  Completed $MAX_ITERATIONS iterations"
echo "================================================================================"
echo "📊 Final Metrics:"
echo "   Maturity: $MATURITY/5 (${MATURITY_PERCENT}%)"
echo "   Completion: $COMPLETION%"
echo "   Quality: $QUALITY/10"
echo "================================================================================"

if [ "$COMPLETION" -ge 80 ]; then
    echo "✅ Project is 80%+ complete. Manual review recommended."
    exit 0
else
    echo "⚠️  Project did not reach 90% threshold. Consider additional iterations."
    exit 1
fi
