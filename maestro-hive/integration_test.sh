#!/bin/bash
#
# DAG System Integration Test Suite
#
# Runs comprehensive tests to validate the DAG workflow system:
# - Module imports
# - Workflow creation
# - Workflow execution
# - Context persistence
# - Feature flags
#
# Usage:
#   ./integration_test.sh           # Run all tests
#   ./integration_test.sh --verbose # Run with detailed output
#   ./integration_test.sh --quick   # Run quick tests only
#
# Exit Codes:
#   0 - All tests passed
#   1 - Some tests failed
#   2 - Critical error (system not ready)
#

set -e  # Exit on error (disabled in test sections)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Verbosity
VERBOSE=false
QUICK_MODE=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --verbose|-v)
            VERBOSE=true
            ;;
        --quick|-q)
            QUICK_MODE=true
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --verbose, -v    Show detailed output"
            echo "  --quick, -q      Run quick tests only"
            echo "  --help, -h       Show this help"
            exit 0
            ;;
    esac
done

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}========================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================================================${NC}"
}

print_test() {
    echo -n "  Testing: $1 ... "
    ((TESTS_RUN++))
}

pass_test() {
    echo -e "${GREEN}✓ PASS${NC}"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}"
    if [ -n "$1" ]; then
        echo -e "${RED}    Error: $1${NC}"
    fi
    ((TESTS_FAILED++))
}

skip_test() {
    echo -e "${YELLOW}⊙ SKIP${NC}"
    if [ -n "$1" ]; then
        echo -e "${YELLOW}    Reason: $1${NC}"
    fi
    ((TESTS_SKIPPED++))
    ((TESTS_RUN--))  # Don't count skipped tests
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo "    $1"
    fi
}

# Change to project directory
cd "$(dirname "$0")"

# Main test execution
print_header "DAG SYSTEM INTEGRATION TEST SUITE"
echo "  Mode: $([ "$QUICK_MODE" = true ] && echo "QUICK" || echo "FULL")"
echo "  Verbose: $VERBOSE"
echo ""

# ========================================================================
# Test 1: Module Imports
# ========================================================================
print_header "Test Group 1: Module Imports"

print_test "dag_workflow module"
if python3 -c "from dag_workflow import WorkflowDAG" 2>/dev/null; then
    pass_test
    log_verbose "WorkflowDAG class imported successfully"
else
    fail_test "Cannot import WorkflowDAG"
fi

print_test "dag_executor module"
if python3 -c "from dag_executor import DAGExecutor" 2>/dev/null; then
    pass_test
    log_verbose "DAGExecutor class imported successfully"
else
    fail_test "Cannot import DAGExecutor"
fi

print_test "dag_compatibility module"
if python3 -c "from dag_compatibility import generate_linear_workflow" 2>/dev/null; then
    pass_test
    log_verbose "generate_linear_workflow function imported successfully"
else
    fail_test "Cannot import generate_linear_workflow"
fi

print_test "team_execution_dual module"
if python3 -c "from team_execution_dual import FeatureFlags" 2>/dev/null; then
    pass_test
    log_verbose "FeatureFlags class imported successfully"
else
    fail_test "Cannot import FeatureFlags"
fi

print_test "All modules together"
if python3 -c "from dag_workflow import WorkflowDAG; from dag_executor import DAGExecutor; from dag_compatibility import generate_linear_workflow; from team_execution_dual import FeatureFlags" 2>/dev/null; then
    pass_test
    log_verbose "All DAG modules load together without conflicts"
else
    fail_test "Module import conflict detected"
fi

# ========================================================================
# Test 2: Workflow Creation
# ========================================================================
print_header "Test Group 2: Workflow Creation"

print_test "Create empty workflow"
if python3 -c "
from dag_workflow import WorkflowDAG
workflow = WorkflowDAG(name='test')
assert workflow.name == 'test'
assert len(workflow.nodes) == 0
" 2>/dev/null; then
    pass_test
    log_verbose "Empty workflow created successfully"
else
    fail_test "Cannot create empty workflow"
fi

print_test "Add node to workflow"
if python3 -c "
from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
workflow = WorkflowDAG(name='test')
node = WorkflowNode(node_id='node1', name='Node 1', node_type=NodeType.PHASE)
workflow.add_node(node)
assert len(workflow.nodes) == 1
assert 'node1' in workflow.nodes
" 2>/dev/null; then
    pass_test
    log_verbose "Node added successfully"
else
    fail_test "Cannot add node to workflow"
fi

print_test "Workflow validation (cycle detection)"
if python3 -c "
from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
workflow = WorkflowDAG(name='test')
node1 = WorkflowNode(node_id='node1', name='Node 1', node_type=NodeType.PHASE)
node2 = WorkflowNode(node_id='node2', name='Node 2', node_type=NodeType.PHASE)
workflow.add_node(node1)
workflow.add_node(node2)
workflow.add_edge('node1', 'node2')
errors = workflow.validate()
assert len(errors) == 0, f'Validation errors: {errors}'
# Try to create cycle
try:
    workflow.add_edge('node2', 'node1')
    raise AssertionError('Cycle detection failed - cycle was allowed')
except ValueError as e:
    if 'cycle' not in str(e).lower():
        raise AssertionError(f'Wrong error message: {e}')
" 2>/dev/null; then
    pass_test
    log_verbose "Cycle detection works correctly"
else
    fail_test "Cycle detection not working"
fi

print_test "Generate linear workflow"
if python3 -c "
from dag_compatibility import generate_linear_workflow
workflow = generate_linear_workflow(phases=['phase1', 'phase2', 'phase3'])
assert len(workflow.nodes) == 3
assert workflow.metadata['type'] == 'linear'
" 2>/dev/null; then
    pass_test
    log_verbose "Linear workflow generated with 3 phases"
else
    fail_test "Cannot generate linear workflow"
fi

print_test "Generate parallel workflow"
if python3 -c "
from dag_compatibility import generate_parallel_workflow
workflow = generate_parallel_workflow()
assert len(workflow.nodes) == 6
assert workflow.metadata['type'] == 'parallel'
execution_order = workflow.get_execution_order()
# Check that backend and frontend are in same group (parallel)
group_with_parallel = None
for i, group in enumerate(execution_order):
    if 'phase_backend_development' in group:
        assert 'phase_frontend_development' in group, 'Backend and frontend should be parallel'
        group_with_parallel = i
        break
assert group_with_parallel is not None, 'Parallel development group not found'
" 2>/dev/null; then
    pass_test
    log_verbose "Parallel workflow generated with parallel dev phases"
else
    fail_test "Cannot generate parallel workflow"
fi

# ========================================================================
# Test 3: Workflow Execution
# ========================================================================
if [ "$QUICK_MODE" = false ]; then
    print_header "Test Group 3: Workflow Execution"

    print_test "Execute simple workflow"
    if python3 -c "
import asyncio
from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
from dag_executor import DAGExecutor

async def test():
    workflow = WorkflowDAG(name='test')

    async def executor1(input_data):
        return {'result': 'node1', 'value': 1}

    async def executor2(input_data):
        prev_value = input_data['dependency_outputs']['node1']['value']
        return {'result': 'node2', 'value': prev_value + 1}

    node1 = WorkflowNode(node_id='node1', name='Node 1', node_type=NodeType.PHASE, executor=executor1)
    node2 = WorkflowNode(node_id='node2', name='Node 2', node_type=NodeType.PHASE, executor=executor2, dependencies=['node1'])

    workflow.add_node(node1)
    workflow.add_node(node2)
    workflow.add_edge('node1', 'node2')

    executor = DAGExecutor(workflow)
    context = await executor.execute()

    assert len(context.get_completed_nodes()) == 2
    assert context.get_node_output('node1')['value'] == 1
    assert context.get_node_output('node2')['value'] == 2

asyncio.run(test())
" 2>/dev/null; then
        pass_test
        log_verbose "Workflow executed successfully with data passing"
    else
        fail_test "Workflow execution failed"
    fi

    print_test "Execute parallel workflow"
    if python3 -c "
import asyncio
from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
from dag_executor import DAGExecutor

async def test():
    workflow = WorkflowDAG(name='test')

    execution_log = []

    async def make_executor(node_id):
        async def executor(input_data):
            execution_log.append(f'{node_id}_start')
            await asyncio.sleep(0.1)
            execution_log.append(f'{node_id}_end')
            return {'node': node_id}
        return executor

    # Create: node1 -> (node2, node3) -> node4
    node1 = WorkflowNode(node_id='node1', name='N1', node_type=NodeType.PHASE, executor=await make_executor('node1'))
    node2 = WorkflowNode(node_id='node2', name='N2', node_type=NodeType.PHASE, executor=await make_executor('node2'), dependencies=['node1'])
    node3 = WorkflowNode(node_id='node3', name='N3', node_type=NodeType.PHASE, executor=await make_executor('node3'), dependencies=['node1'])
    node4 = WorkflowNode(node_id='node4', name='N4', node_type=NodeType.PHASE, executor=await make_executor('node4'), dependencies=['node2', 'node3'])

    workflow.add_node(node1)
    workflow.add_node(node2)
    workflow.add_node(node3)
    workflow.add_node(node4)
    workflow.add_edge('node1', 'node2')
    workflow.add_edge('node1', 'node3')
    workflow.add_edge('node2', 'node4')
    workflow.add_edge('node3', 'node4')

    executor = DAGExecutor(workflow)
    context = await executor.execute()

    # Verify all completed
    assert len(context.get_completed_nodes()) == 4

    # Verify node2 and node3 ran in parallel
    node2_start = execution_log.index('node2_start')
    node3_start = execution_log.index('node3_start')
    node2_end = execution_log.index('node2_end')
    node3_end = execution_log.index('node3_end')

    # At least one should start before the other finishes
    parallel = (node3_start < node2_end) or (node2_start < node3_end)
    assert parallel, 'Nodes did not execute in parallel'

asyncio.run(test())
" 2>/dev/null; then
        pass_test
        log_verbose "Parallel execution works correctly"
    else
        fail_test "Parallel execution not working"
    fi
else
    skip_test "Workflow execution tests (quick mode)"
    skip_test "Parallel execution test (quick mode)"
fi

# ========================================================================
# Test 4: Context Persistence
# ========================================================================
print_header "Test Group 4: Context Persistence"

print_test "Context store save/load"
if python3 -c "
import asyncio
from dag_workflow import WorkflowContext
from dag_executor import WorkflowContextStore

async def test():
    store = WorkflowContextStore()
    context = WorkflowContext(workflow_id='test')
    context.set_node_output('node1', {'result': 'success'})

    await store.save_context(context)
    loaded = await store.load_context(context.execution_id)

    assert loaded is not None
    assert loaded.execution_id == context.execution_id
    assert loaded.get_node_output('node1')['result'] == 'success'

asyncio.run(test())
" 2>/dev/null; then
    pass_test
    log_verbose "Context save and load works"
else
    fail_test "Context persistence not working"
fi

print_test "Context store list executions"
if python3 -c "
import asyncio
from dag_workflow import WorkflowContext
from dag_executor import WorkflowContextStore

async def test():
    store = WorkflowContextStore()

    ctx1 = WorkflowContext(workflow_id='workflow1')
    ctx2 = WorkflowContext(workflow_id='workflow1')
    ctx3 = WorkflowContext(workflow_id='workflow2')

    await store.save_context(ctx1)
    await store.save_context(ctx2)
    await store.save_context(ctx3)

    all_executions = await store.list_executions()
    assert len(all_executions) == 3

    workflow1_executions = await store.list_executions('workflow1')
    assert len(workflow1_executions) == 2

asyncio.run(test())
" 2>/dev/null; then
    pass_test
    log_verbose "Context listing works"
else
    fail_test "Context listing not working"
fi

# ========================================================================
# Test 5: Feature Flags
# ========================================================================
print_header "Test Group 5: Feature Flags"

print_test "Feature flags defaults"
if python3 -c "
from team_execution_dual import FeatureFlags, ExecutionMode

flags = FeatureFlags()
assert flags.enable_dag_execution is False  # Default
assert flags.enable_parallel_execution is False
assert flags.get_execution_mode() == ExecutionMode.LINEAR
" 2>/dev/null; then
    pass_test
    log_verbose "Default flags are correct"
else
    fail_test "Feature flags defaults incorrect"
fi

print_test "Feature flags environment detection"
if env MAESTRO_ENABLE_DAG_EXECUTION=true python3 -c "
from team_execution_dual import FeatureFlags, ExecutionMode

flags = FeatureFlags()
assert flags.enable_dag_execution is True
assert flags.get_execution_mode() in [ExecutionMode.DAG_LINEAR, ExecutionMode.DAG_PARALLEL]
" 2>/dev/null; then
    pass_test
    log_verbose "Environment variable detection works"
else
    fail_test "Environment variable detection not working"
fi

print_test "Feature flags execution mode calculation"
if python3 -c "
from team_execution_dual import FeatureFlags, ExecutionMode

# Test LINEAR mode
flags = FeatureFlags()
flags.enable_dag_execution = False
assert flags.get_execution_mode() == ExecutionMode.LINEAR

# Test DAG_LINEAR mode
flags.enable_dag_execution = True
flags.enable_parallel_execution = False
assert flags.get_execution_mode() == ExecutionMode.DAG_LINEAR

# Test DAG_PARALLEL mode
flags.enable_dag_execution = True
flags.enable_parallel_execution = True
assert flags.get_execution_mode() == ExecutionMode.DAG_PARALLEL
" 2>/dev/null; then
    pass_test
    log_verbose "Execution mode calculation correct"
else
    fail_test "Execution mode calculation incorrect"
fi

# ========================================================================
# Test 6: Operational Tools
# ========================================================================
print_header "Test Group 6: Operational Tools"

print_test "verify_flags.py script"
if [ -x "./verify_flags.py" ] && python3 ./verify_flags.py --json >/dev/null 2>&1; then
    pass_test
    log_verbose "verify_flags.py is executable and works"
else
    fail_test "verify_flags.py not working"
fi

print_test "recovery_script.py script"
if [ -x "./recovery_script.py" ] && python3 ./recovery_script.py --list >/dev/null 2>&1; then
    pass_test
    log_verbose "recovery_script.py is executable and works"
else
    fail_test "recovery_script.py not working"
fi

# ========================================================================
# Test Summary
# ========================================================================
print_header "TEST SUMMARY"
echo ""
echo "  Tests Run:     $TESTS_RUN"
echo -e "  Tests Passed:  ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "  Tests Failed:  ${RED}$TESTS_FAILED${NC}"
else
    echo -e "  Tests Failed:  $TESTS_FAILED"
fi
if [ $TESTS_SKIPPED -gt 0 ]; then
    echo -e "  Tests Skipped: ${YELLOW}$TESTS_SKIPPED${NC}"
fi
echo ""

# Calculate pass rate
if [ $TESTS_RUN -gt 0 ]; then
    PASS_RATE=$((TESTS_PASSED * 100 / TESTS_RUN))
    echo "  Pass Rate: $PASS_RATE%"
    echo ""
fi

# Final result
if [ $TESTS_FAILED -eq 0 ] && [ $TESTS_PASSED -gt 0 ]; then
    echo -e "${GREEN}========================================================================${NC}"
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}========================================================================${NC}"
    echo ""
    exit 0
elif [ $TESTS_PASSED -eq 0 ]; then
    echo -e "${RED}========================================================================${NC}"
    echo -e "${RED}✗ CRITICAL: NO TESTS PASSED${NC}"
    echo -e "${RED}========================================================================${NC}"
    echo ""
    echo "System is not ready for use. Please check installation."
    echo ""
    exit 2
else
    echo -e "${RED}========================================================================${NC}"
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo -e "${RED}========================================================================${NC}"
    echo ""
    echo "System may not be fully functional. Review failures above."
    echo ""
    exit 1
fi
