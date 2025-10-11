#!/bin/bash
# Quick test runner for Quality Fabric integration

echo "🚀 Running Quality Fabric Integration Tests"
echo "==========================================="
echo ""

# Use Python 3.11
PYTHON=python3.11

echo "Python version:"
$PYTHON --version
echo ""

echo "Test 1: Client Library Test"
echo "----------------------------"
$PYTHON quality_fabric_client.py
echo ""

echo "Test 2: Full Integration Test"
echo "------------------------------"
$PYTHON test_quality_integration.py
echo ""

echo "✅ All tests complete!"
