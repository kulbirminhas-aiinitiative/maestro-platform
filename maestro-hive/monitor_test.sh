#!/bin/bash
#
# Monitor Dog Marketplace Test Progress
#
# Usage: ./monitor_test.sh
#

echo "======================================================================"
echo "  Dog Marketplace Test Progress Monitor"
echo "======================================================================"
echo ""

# Check if test is running
if ps aux | grep -q "[t]est_dog_marketplace.py"; then
    echo "✅ Test is RUNNING"
    echo ""

    # Show process info
    echo "Process Info:"
    ps aux | grep "[t]est_dog_marketplace.py" | awk '{print "  PID: " $2 "  CPU: " $3 "%  MEM: " $4 "%  TIME: " $10}'
    echo ""
else
    echo "❌ Test is NOT running"
    echo ""
fi

# Check log file
if [ -f "dog_marketplace_test.log" ]; then
    echo "Log File: dog_marketplace_test.log"
    echo "  Size: $(du -h dog_marketplace_test.log | cut -f1)"
    echo "  Lines: $(wc -l < dog_marketplace_test.log)"
    echo ""

    # Show phase progress
    echo "Phase Progress:"
    for phase in REQUIREMENTS DESIGN IMPLEMENTATION TESTING DEPLOYMENT; do
        if grep -q "PHASE.*: $phase" dog_marketplace_test.log 2>/dev/null; then
            if grep -q "Phase completed successfully" dog_marketplace_test.log 2>/dev/null && grep -B5 "Phase completed successfully" dog_marketplace_test.log | grep -q "$phase"; then
                echo "  ✅ $phase - Completed"
            else
                echo "  ⏳ $phase - In Progress"
            fi
        else
            echo "  ⏸️  $phase - Pending"
        fi
    done
    echo ""

    # Show latest log entries
    echo "Latest Log Entries (last 10 lines):"
    tail -10 dog_marketplace_test.log | sed 's/^/  /'
    echo ""
else
    echo "⚠️  Log file not found"
    echo ""
fi

# Check for report files
echo "Generated Files:"
if [ -f "DOG_MARKETPLACE_TEST_REPORT.md" ]; then
    echo "  ✅ DOG_MARKETPLACE_TEST_REPORT.md ($(du -h DOG_MARKETPLACE_TEST_REPORT.md | cut -f1))"
fi
if [ -f "issues_identified.md" ]; then
    echo "  ✅ issues_identified.md ($(du -h issues_identified.md | cut -f1))"
fi
if [ -f "dog_marketplace_test_data.json" ]; then
    echo "  ✅ dog_marketplace_test_data.json ($(du -h dog_marketplace_test_data.json | cut -f1))"
fi
if [ -d "generated_dog_marketplace" ]; then
    file_count=$(find generated_dog_marketplace -type f | wc -l)
    echo "  ✅ generated_dog_marketplace/ ($file_count files)"
fi

echo ""
echo "======================================================================"
echo ""
echo "Commands:"
echo "  Watch live: tail -f dog_marketplace_test.log"
echo "  Stop test:  pkill -f test_dog_marketplace.py"
echo "  Resume (if stopped): python3 test_dog_marketplace.py &"
echo ""
