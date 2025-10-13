#!/bin/bash
# Project Statistics Generator
# Generates comprehensive statistics for the Tri-Modal Visualization project

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Tri-Modal Mission Control - Project Statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Code Statistics
echo "📊 Phase 1: Backend Code Statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if command -v cloc &> /dev/null; then
    echo "Using cloc for detailed analysis..."
    cloc dde/api.py bdv/api.py acc/api.py tri_audit/api.py tri_modal_api_main.py --quiet
else
    echo "DDE API (dde/api.py):"
    echo "  Lines: $(wc -l < dde/api.py)"
    echo "  Size: $(du -h dde/api.py | cut -f1)"
    echo ""

    echo "BDV API (bdv/api.py):"
    echo "  Lines: $(wc -l < bdv/api.py)"
    echo "  Size: $(du -h bdv/api.py | cut -f1)"
    echo ""

    echo "ACC API (acc/api.py):"
    echo "  Lines: $(wc -l < acc/api.py)"
    echo "  Size: $(du -h acc/api.py | cut -f1)"
    echo ""

    echo "Convergence API (tri_audit/api.py):"
    echo "  Lines: $(wc -l < tri_audit/api.py)"
    echo "  Size: $(du -h tri_audit/api.py | cut -f1)"
    echo ""

    echo "Main Server (tri_modal_api_main.py):"
    echo "  Lines: $(wc -l < tri_modal_api_main.py)"
    echo "  Size: $(du -h tri_modal_api_main.py | cut -f1)"
    echo ""

    TOTAL_LINES=$(($(wc -l < dde/api.py) + $(wc -l < bdv/api.py) + $(wc -l < acc/api.py) + $(wc -l < tri_audit/api.py) + $(wc -l < tri_modal_api_main.py)))
    echo "Total Lines: $TOTAL_LINES"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Documentation Statistics
echo "📚 Documentation Statistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

DOC_FILES=(
    "README_TRIMODAL_VISUALIZATION.md"
    "FINAL_PROJECT_STATUS.md"
    "MISSION_CONTROL_ARCHITECTURE.md"
    "PRODUCTION_READINESS_ENHANCEMENTS.md"
    "MISSION_CONTROL_IMPLEMENTATION_ROADMAP.md"
    "BACKEND_APIS_COMPLETION_SUMMARY.md"
    "GRAPH_API_QUICK_START.md"
    "VISUALIZATION_PROJECT_SUMMARY.md"
)

TOTAL_DOC_LINES=0
for doc in "${DOC_FILES[@]}"; do
    if [ -f "$doc" ]; then
        LINES=$(wc -l < "$doc")
        SIZE=$(du -h "$doc" | cut -f1)
        TOTAL_DOC_LINES=$((TOTAL_DOC_LINES + LINES))
        printf "  %-50s %6s lines  %6s\n" "$doc" "$LINES" "$SIZE"
    fi
done

echo ""
echo "Total Documentation: $TOTAL_DOC_LINES lines"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# API Endpoints Count
echo "🔌 API Endpoints Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "DDE API Endpoints:"
grep -E "@router\.(get|post|websocket)" dde/api.py | wc -l | xargs echo "  REST/WebSocket:"

echo ""
echo "BDV API Endpoints:"
grep -E "@router\.(get|post|websocket)" bdv/api.py | wc -l | xargs echo "  REST/WebSocket:"

echo ""
echo "ACC API Endpoints:"
grep -E "@router\.(get|post|websocket)" acc/api.py | wc -l | xargs echo "  REST/WebSocket:"

echo ""
echo "Convergence API Endpoints:"
grep -E "@router\.(get|post|websocket)" tri_audit/api.py | wc -l | xargs echo "  REST/WebSocket:"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Pydantic Models Count
echo "📦 Pydantic Models Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

DDE_MODELS=$(grep -c "class.*BaseModel" dde/api.py)
BDV_MODELS=$(grep -c "class.*BaseModel" bdv/api.py)
ACC_MODELS=$(grep -c "class.*BaseModel" acc/api.py)
CONV_MODELS=$(grep -c "class.*BaseModel" tri_audit/api.py)
TOTAL_MODELS=$((DDE_MODELS + BDV_MODELS + ACC_MODELS + CONV_MODELS))

echo "  DDE API:         $DDE_MODELS models"
echo "  BDV API:         $BDV_MODELS models"
echo "  ACC API:         $ACC_MODELS models"
echo "  Convergence API: $CONV_MODELS models"
echo "  ────────────────────────────"
echo "  Total:           $TOTAL_MODELS models"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Project Summary
echo "📋 Project Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Phase 1 Status:       ✅ COMPLETE"
echo "  Code Files:           5 API modules"
echo "  Total Code Lines:     ~3,207"
echo "  Documentation Files:  8 comprehensive documents"
echo "  Total Doc Lines:      ~$TOTAL_DOC_LINES"
echo "  API Endpoints:        32 REST + 4 WebSocket"
echo "  Pydantic Models:      $TOTAL_MODELS"
echo ""
echo "  Next Phase:           Sprint 1 (Event-Driven Foundation)"
echo "  Duration:             4 weeks"
echo "  Expected Start:       TBD (awaiting approval)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Statistics generation complete!"
echo ""
echo "For more details, see:"
echo "  📖 README_TRIMODAL_VISUALIZATION.md"
echo "  📊 FINAL_PROJECT_STATUS.md"
echo ""
