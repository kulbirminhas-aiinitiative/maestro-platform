#!/bin/bash
set -e

# Discussion Orchestrator Test Script
# This script runs tests, linting, and generates coverage reports

echo "========================================="
echo "Discussion Orchestrator Test Suite"
echo "========================================="

# Navigate to the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies including test dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio black flake8 mypy

echo ""
echo "========================================="
echo "1. Running Code Formatting Check (Black)"
echo "========================================="
black --check src/ || {
    echo "⚠ Code formatting issues found. Run 'black src/' to fix."
    exit 1
}
echo "✓ Code formatting is correct"

echo ""
echo "========================================="
echo "2. Running Linting (Flake8)"
echo "========================================="
flake8 src/ --max-line-length=100 --extend-ignore=E203,W503 || {
    echo "⚠ Linting issues found. Please fix the errors above."
    exit 1
}
echo "✓ Linting passed"

echo ""
echo "========================================="
echo "3. Running Type Checking (MyPy)"
echo "========================================="
mypy src/ --ignore-missing-imports || {
    echo "⚠ Type checking issues found. Please fix the errors above."
    # Not failing on mypy errors for now
}

echo ""
echo "========================================="
echo "4. Running Tests (Pytest)"
echo "========================================="

# Create reports directory if it doesn't exist
mkdir -p reports

# Run pytest with coverage
pytest tests/ \
    -v \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html:reports/coverage \
    --cov-report=xml:reports/coverage.xml \
    --junit-xml=reports/junit.xml \
    || {
        echo "⚠ Tests failed. Please fix the failing tests."
        exit 1
    }

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo "✓ All tests passed"
echo "Coverage report: reports/coverage/index.html"
echo "JUnit report: reports/junit.xml"
echo "========================================="
