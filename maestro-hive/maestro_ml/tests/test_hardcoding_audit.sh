#!/bin/bash
#
# Maestro ML Platform - Hardcoding Audit
# Purpose: Scan codebase for hardcoded values and TODO items
# Usage: ./tests/test_hardcoding_audit.sh
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$TESTS_DIR")"

echo "======================================="
echo "Hardcoding Audit"
echo "======================================="
echo "Scanning directory: $PROJECT_DIR"
echo ""

ISSUES_FOUND=0

# Function to search and report
search_and_report() {
    local pattern=$1
    local description=$2
    local file_type=$3

    echo -e "${BLUE}[AUDIT]${NC} Checking: $description"

    local count=0
    local files=""

    if [ "$file_type" == "py" ]; then
        files=$(find "$PROJECT_DIR" -name "*.py" -type f ! -path "*/tests/*" ! -path "*/__pycache__/*" ! -path "*/.venv/*" ! -path "*/venv/*" 2>/dev/null || true)
    elif [ "$file_type" == "yaml" ]; then
        files=$(find "$PROJECT_DIR" -name "*.yaml" -o -name "*.yml" -type f ! -path "*/tests/*" ! -path "*/.venv/*" 2>/dev/null || true)
    else
        files=$(find "$PROJECT_DIR" -type f ! -path "*/tests/*" ! -path "*/__pycache__/*" ! -path "*/.git/*" ! -path "*/.venv/*" ! -path "*/venv/*" 2>/dev/null || true)
    fi

    if [ -n "$files" ]; then
        while IFS= read -r file; do
            if grep -l "$pattern" "$file" 2>/dev/null; then
                if [ $count -eq 0 ]; then
                    echo -e "  ${YELLOW}Found in:${NC}"
                fi
                echo "    - $file"
                count=$((count + 1))
            fi
        done <<< "$files"
    fi

    if [ $count -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} No issues found"
    else
        echo -e "  ${RED}✗${NC} Found in $count file(s)"
        ISSUES_FOUND=$((ISSUES_FOUND + count))
    fi

    echo ""
}

# 1. Check for TODO comments
echo "1. TODO Comments"
echo "-----------------------------------"
search_and_report "TODO" "TODO comments in Python files" "py"

# 2. Check for hardcoded URLs
echo "2. Hardcoded URLs"
echo "-----------------------------------"
search_and_report "http://localhost" "localhost URLs in Python files" "py"
search_and_report "http://127.0.0.1" "127.0.0.1 URLs in Python files" "py"

# 3. Check for hardcoded tracking URIs
echo "3. Hardcoded MLflow Tracking URIs"
echo "-----------------------------------"
search_and_report 'tracking_uri\s*=\s*"http' "Hardcoded tracking_uri in Python files" "py"

# 4. Check for hardcoded database credentials
echo "4. Hardcoded Credentials (YAML)"
echo "-----------------------------------"
search_and_report "password:\s*['\"]" "Hardcoded passwords in YAML files" "yaml"

# 5. Check for hardcoded thresholds
echo "5. Hardcoded Thresholds"
echo "-----------------------------------"
echo -e "${BLUE}[INFO]${NC} This check is informational only"
echo -e "  ${YELLOW}Note:${NC} Thresholds should ideally be in config files"
echo ""

# 6. Check for print debugging statements
echo "6. Debug Print Statements"
echo "-----------------------------------"
search_and_report "print\(.*DEBUG" "Debug print statements" "py"

# 7. Check for hardcoded ports in code
echo "7. Hardcoded Ports in Code"
echo "-----------------------------------"
echo -e "${BLUE}[INFO]${NC} Checking for common hardcoded ports..."
search_and_report ":5000\"" "Port 5000 hardcoded" "py"
search_and_report ":8080\"" "Port 8080 hardcoded" "py"

# 8. Check for FIXME comments
echo "8. FIXME Comments"
echo "-----------------------------------"
search_and_report "FIXME" "FIXME comments" "py"

# 9. Check for XXX comments
echo "9. XXX Comments"
echo "-----------------------------------"
search_and_report "XXX" "XXX comments" "py"

# 10. Check for HACK comments
echo "10. HACK Comments"
echo "-----------------------------------"
search_and_report "HACK" "HACK comments" "py"

# Summary
echo "======================================="
echo "Audit Summary"
echo "======================================="

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ No hardcoding issues found!${NC}"
    echo ""
    exit 0
else
    echo -e "${YELLOW}⚠️  Found issues in $ISSUES_FOUND file(s)${NC}"
    echo ""
    echo "Recommended Actions:"
    echo "1. Move hardcoded values to config/platform-config.yaml"
    echo "2. Use environment variables for sensitive data"
    echo "3. Remove or complete TODO/FIXME comments"
    echo "4. Update code to use ConfigLoader for retrieving values"
    echo ""
    echo "Example fix:"
    echo "  Before: tracking_uri = 'http://mlflow:5000'"
    echo "  After:  tracking_uri = get_config_value('mlflow.tracking_uri')"
    echo ""
    exit 0  # Don't fail build, just warn
fi
