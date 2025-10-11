#!/bin/bash
#
# Quick validation and remediation script for sunday_com project
#
# Usage:
#   ./validate_sunday_com.sh                    # Just validate
#   ./validate_sunday_com.sh --remediate        # Validate and fix issues
#

set -e

PROJECT_DIR="sunday_com/sunday_com"
SESSION_ID="sunday_com_remediation_$(date +%Y%m%d_%H%M%S)"

echo "========================================================================"
echo "🔍 SUNDAY.COM PROJECT VALIDATION & REMEDIATION"
echo "========================================================================"
echo "📁 Project: $PROJECT_DIR"
echo "🆔 Session: $SESSION_ID"
echo "========================================================================"
echo

# Check if project exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Project directory not found: $PROJECT_DIR"
    exit 1
fi

# Run validation
python3 phased_autonomous_executor.py \
    --validate "$PROJECT_DIR" \
    --session "$SESSION_ID" \
    $@

echo
echo "========================================================================"
echo "✅ Validation complete!"
echo "========================================================================"
echo "📋 Review the validation report above"
echo "📁 Session saved: sdlc_sessions/${SESSION_ID}.json"
echo "🔍 Validation reports: ${PROJECT_DIR}/validation_reports/"
echo
echo "To remediate issues, run:"
echo "  ./validate_sunday_com.sh --remediate"
echo "========================================================================"
