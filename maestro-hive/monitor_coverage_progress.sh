#!/bin/bash
# Monitor coverage progress toward 80% goal

GOAL_COVERAGE=80.0
METRICS_DIR="/tmp/maestro_workflow_metrics"

echo "========================================================================"
echo "  MAESTRO TEMPLATE COVERAGE PROGRESS MONITOR"
echo "========================================================================"
echo ""

# Get latest metrics
LATEST_METRICS=$(ls -t "$METRICS_DIR"/*.json 2>/dev/null | head -1)

if [ -z "$LATEST_METRICS" ]; then
    echo "❌ No metrics found. Waiting for first run..."
    exit 1
fi

echo "📊 Latest Run: $(basename $LATEST_METRICS)"
echo ""

# Parse and display key metrics
python3 << 'EOF'
import json
import sys
from pathlib import Path

METRICS_DIR = Path("/tmp/maestro_workflow_metrics")
GOAL_COVERAGE = 80.0

# Get all metrics files sorted by time
metrics_files = sorted(METRICS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime)

if not metrics_files:
    print("No metrics found yet.")
    sys.exit(1)

# Read latest
with open(metrics_files[-1]) as f:
    latest = json.load(f)

current_coverage = latest["overall_coverage_before"]
gaps = latest["total_gaps_identified"]
critical_gaps = latest["critical_gaps"]
recommendations = latest["recommendations_generated"]

# Intelligence metrics
similarity_checks = latest.get("similarity_checks_performed", 0)
reuse = latest.get("templates_reused", 0)
variant = latest.get("templates_variants_created", 0)
new = latest.get("templates_new_created", 0)
avg_sim = latest.get("avg_template_similarity", 0) * 100

# Calculate progress
progress = (current_coverage / GOAL_COVERAGE) * 100
remaining = GOAL_COVERAGE - current_coverage

# Status
if current_coverage >= GOAL_COVERAGE:
    status = "✅ GOAL ACHIEVED"
    status_icon = "🎉"
elif current_coverage >= GOAL_COVERAGE * 0.75:
    status = "🟢 EXCELLENT PROGRESS"
    status_icon = "📈"
elif current_coverage >= GOAL_COVERAGE * 0.5:
    status = "🟡 GOOD PROGRESS"
    status_icon = "📊"
else:
    status = "🔴 NEEDS IMPROVEMENT"
    status_icon = "⚠️"

print(f"{status_icon} CURRENT STATUS: {status}")
print(f"")
print(f"📊 Coverage: {current_coverage:.1f}% / {GOAL_COVERAGE:.1f}% ({progress:.1f}% of goal)")
print(f"📉 Remaining: {remaining:.1f} percentage points needed")
print(f"")
print(f"🎯 Gap Analysis:")
print(f"   Total gaps: {gaps}")
print(f"   Critical gaps: {critical_gaps}")
print(f"   Recommendations: {recommendations}")
print(f"")
print(f"🧠 Intelligence Decisions:")
print(f"   Similarity checks: {similarity_checks}")
print(f"   REUSE: {reuse}")
print(f"   VARIANT: {variant}")
print(f"   CREATE_NEW: {new}")
print(f"   Avg similarity: {avg_sim:.1f}%")
print(f"")

# Progress bar
bar_length = 50
filled = int((current_coverage / GOAL_COVERAGE) * bar_length)
bar = "█" * filled + "░" * (bar_length - filled)
print(f"Progress: [{bar}] {progress:.1f}%")
print(f"")

# Historical trend
if len(metrics_files) >= 2:
    with open(metrics_files[-2]) as f:
        previous = json.load(f)

    prev_coverage = previous["overall_coverage_before"]
    change = current_coverage - prev_coverage

    if change > 0:
        trend = "📈 UP"
        trend_icon = "+"
    elif change < 0:
        trend = "📉 DOWN"
        trend_icon = ""
    else:
        trend = "➡️ STABLE"
        trend_icon = ""

    print(f"📈 Trend: {trend} ({trend_icon}{change:.1f}% from previous run)")
    print(f"")

# Total runs
print(f"📊 Total runs completed: {len(metrics_files)}")
print(f"")

# Next steps
if current_coverage < GOAL_COVERAGE:
    print(f"🔄 Service will continue running every 5 minutes until {GOAL_COVERAGE}% coverage is achieved.")
    print(f"⏰ Check back regularly to monitor progress!")
else:
    print(f"🎉 Goal achieved! Consider switching to less frequent runs:")
    print(f"   - Every 2 hours: sudo sed -i 's/--interval 300/--interval 7200/g' /etc/systemd/system/automated_workflow.service")
    print(f"   - Daily: sudo sed -i 's/--interval 300/--interval 86400/g' /etc/systemd/system/automated_workflow.service")
    print(f"   Then: sudo systemctl daemon-reload && sudo systemctl restart automated_workflow")

EOF

echo ""
echo "========================================================================"
echo "To watch live updates: sudo journalctl -u automated_workflow -f"
echo "To run this monitor again: bash $0"
echo "========================================================================"
