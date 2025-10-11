#!/bin/bash
#
# Quick Project Review Script
#
# Usage:
#   ./quick_review.sh <project_path> [requirements_doc]
#
# Example:
#   ./quick_review.sh ./sunday_com/sunday_com requirements_document.md
#

set -e

PROJECT_PATH="${1}"
REQUIREMENTS_DOC="${2:-requirements_document.md}"

if [ -z "$PROJECT_PATH" ]; then
    echo "Usage: $0 <project_path> [requirements_doc]"
    exit 1
fi

if [ ! -d "$PROJECT_PATH" ]; then
    echo "Error: Project path does not exist: $PROJECT_PATH"
    exit 1
fi

echo "================================================"
echo "Quick Project Review"
echo "================================================"
echo "Project: $PROJECT_PATH"
echo "Requirements: $REQUIREMENTS_DOC"
echo ""

# Step 1: Run analytical tools (fast)
echo "Step 1/2: Running analytical tools..."
python3.11 review_tools.py "$PROJECT_PATH"

echo ""
echo "================================================"
echo "Metrics Summary"
echo "================================================"

# Display key metrics from JSON
if [ -f "$PROJECT_PATH/PROJECT_METRICS.json" ]; then
    python3.11 -c "
import json
import sys

with open('$PROJECT_PATH/PROJECT_METRICS.json') as f:
    data = json.load(f)

m = data['metrics']
impl = data['implementation']
test = data['testing']
devops = data['devops']

print(f'''
📊 Project Statistics:
   Files: {m['total_files']} total, {sum(m['code_files'].values())} code, {m['test_files']} tests
   Lines: {m['code_lines']:,} code lines

🔨 Implementation:
   API Endpoints: {impl['api_endpoints_implemented']} implemented, {impl['api_endpoints_stubbed']} stubbed
   UI Pages: {impl['ui_pages_complete']} complete, {impl['ui_pages_stubbed']} stubbed
   DB Migrations: {impl['database_migrations']}

🧪 Testing:
   Test Files: {test['total_test_files']}
   Unit: {test['unit_tests']}, Integration: {test['integration_tests']}, E2E: {test['e2e_tests']}

🚀 DevOps:
   Docker: {'✓' if devops['has_docker'] else '✗'}
   Kubernetes: {'✓' if devops['has_kubernetes'] else '✗'}
   CI/CD: {'✓' if devops['has_ci_cd'] else '✗'}
''')
"
fi

echo ""
echo "================================================"
echo "✓ Quick review complete!"
echo "================================================"
echo ""
echo "📁 Detailed metrics: $PROJECT_PATH/PROJECT_METRICS.json"
echo ""
echo "For full AI-powered analysis with gap identification:"
echo "  python3.11 project_review_engine.py --project $PROJECT_PATH --requirements $REQUIREMENTS_DOC"
echo ""
