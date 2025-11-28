# ContractManager Implementation Guide

**Date**: 2025-10-12
**Status**: 🟡 In Progress
**User Requirement**: "I need contractManager"

---

## Summary

The ContractManager has been located and partially integrated, but requires StateManager (which itself requires DatabaseManager + RedisManager) for full functionality. This guide documents the current state, required changes, and implementation path forward.

---

## Current State

### ✅ Completed
1. **Import Paths Fixed**:
   - `contract_manager.py` now correctly imports from `shared/claude_team_sdk/persistence/`
   - `team_execution_v2.py` imports ContractManager from local `contract_manager.py`
   - `team_execution_v2_split_mode.py` imports ContractManager from local `contract_manager.py`

2. **Persistence Module Updated**:
   - `persistence/__init__.py` now exports `Contract` and `ContractStatus` models
   - All necessary persistence models are available

3. **Helper Module Created**:
   - `state_manager_init.py` provides easy initialization functions
   - Supports both testing (SQLite + MockRedis) and production (PostgreSQL + real Redis)
   - Mock Redis manager for development without Redis server

### ⚠️ Incomplete
1. **Async Initialization Problem**:
   - `TeamExecutionEngineV2Split mode.__init__()` at line 74 tries to initialize ContractManager
   - ContractManager requires StateManager parameter
   - StateManager requires async initialization (`await db.initialize()`, `await redis.initialize()`)
   - Python `__init__` cannot be async

2. **No Contract Validation Method**:
   - `_validate_phase_boundary()` at line 878 calls `self.contract_manager.process_incoming_message()`
   - This method doesn't exist in current ContractManager
   - ContractManager has contract CRUD operations, not validation operations

---

## Architecture Overview

```
TeamExecutionEngineV2SplitMode
    ↓ requires
ContractManager(state_manager: StateManager)
    ↓ requires
StateManager(db_manager: DatabaseManager, redis_manager: RedisManager)
    ↓ requires
DatabaseManager(connection_string)  [async init]
RedisManager(host, port)             [async init]
```

**Key Challenge**: ContractManager needs StateManager, which needs async initialization, but Python classes can't have async __init__ methods.

---

## Implementation Options

### Option 1: Async Factory Pattern (Recommended)

Add an async factory method to `TeamExecutionEngineV2SplitMode`:

```python
class TeamExecutionEngineV2SplitMode:
    def __init__(self, ...):
        # Don't initialize ContractManager here
        self.contract_manager = None
        self._state_manager = None

    async def initialize_contract_manager(self):
        """
        Initialize ContractManager with StateManager.
        Must be called before using contract validation features.
        """
        if not CONTRACT_VALIDATION_AVAILABLE:
            return

        # Initialize StateManager
        from state_manager_init import init_state_manager_for_testing
        self._state_manager = await init_state_manager_for_testing()

        # Initialize ContractManager
        self.contract_manager = ContractManager(self._state_manager)
        self.enable_contracts = True
        logger.info("✅ ContractManager initialized with StateManager")

    async def cleanup(self):
        """Cleanup resources"""
        if self._state_manager:
            from state_manager_init import cleanup_state_manager
            await cleanup_state_manager(self._state_manager)
```

**Usage**:
```python
# Create engine
engine = TeamExecutionEngineV2SplitMode()

# Initialize async components
await engine.initialize_contract_manager()

# Use engine
context = await engine.execute_batch(requirement="...")

# Cleanup
await engine.cleanup()
```

### Option 2: Lazy Initialization

Initialize ContractManager when first accessed:

```python
class TeamExecutionEngineV2SplitMode:
    def __init__(self, ...):
        self._contract_manager = None
        self._state_manager = None
        self._contract_initialized = False

    async def _ensure_contract_manager_initialized(self):
        """Lazy initialization of ContractManager"""
        if self._contract_initialized:
            return

        if not CONTRACT_VALIDATION_AVAILABLE:
            self._contract_initialized = True
            return

        # Initialize StateManager
        from state_manager_init import init_state_manager_for_testing
        self._state_manager = await init_state_manager_for_testing()

        # Initialize ContractManager
        self._contract_manager = ContractManager(self._state_manager)
        self._contract_initialized = True
        logger.info("✅ ContractManager lazy-initialized")

    @property
    def contract_manager(self):
        return self._contract_manager

    async def _validate_phase_boundary(self, ...):
        # Ensure initialized before use
        await self._ensure_contract_manager_initialized()

        if not self._contract_manager:
            logger.info("   ⏭️  Skipping contract validation (disabled)")
            return

        # ... rest of validation logic
```

### Option 3: Pass StateManager from Outside

Let caller create and pass StateManager:

```python
class TeamExecutionEngineV2SplitMode:
    def __init__(
        self,
        output_dir: Optional[str] = None,
        checkpoint_dir: Optional[str] = None,
        quality_threshold: float = 0.70,
        enable_contracts: bool = True,
        state_manager: Optional[StateManager] = None  # NEW
    ):
        # ... existing init ...

        # Contract validation
        self.enable_contracts = enable_contracts
        self.contract_manager = None

        if enable_contracts and CONTRACT_VALIDATION_AVAILABLE and state_manager:
            self.contract_manager = ContractManager(state_manager)
            logger.info("✅ Contract validation enabled")
```

**Usage**:
```python
from state_manager_init import init_state_manager_for_testing

# Initialize StateManager
state_mgr = await init_state_manager_for_testing()

# Pass to engine
engine = TeamExecutionEngineV2SplitMode(state_manager=state_mgr)

# Use engine
context = await engine.execute_batch(requirement="...")
```

---

## Missing Functionality

### 1. Contract Validation Method

`_validate_phase_boundary()` calls `self.contract_manager.process_incoming_message()` which doesn't exist.

**Current ContractManager Methods**:
- `create_contract()` - Create new contract
- `evolve_contract()` - Version a contract
- `activate_contract()` - Activate draft contract
- `get_active_contract()` - Get current version
- `get_contract_history()` - Get all versions
- `register_consumer()` - Add consumer
- `get_contract_summary()` - Get summary

**Missing**:
- `process_incoming_message()` - Validate incoming messages against contracts
- Phase boundary validation logic
- Contract fulfillment checking

**Solution**: Either:
1. Add message validation methods to ContractManager
2. Use existing methods differently (check if contracts exist and are fulfilled)
3. Implement simple validation without message processing

---

## Recommended Implementation Steps

###  Step 1: Choose Async Pattern

**Recommendation**: Use **Option 1 (Async Factory Pattern)** because:
- Clean separation of sync and async initialization
- Explicit control over when resources are allocated
- Easy to add cleanup logic
- Clear API for users

### Step 2: Update team_execution_v2_split_mode.py

```python
# In __init__ (line 72-78), replace with:
# Contract validation (deferred initialization)
self.enable_contracts = enable_contracts
self.contract_manager = None
self._state_manager = None
self.circuit_breaker = PhaseCircuitBreaker()

logger.info("="*80)
logger.info("✅ Team Execution Engine V2 - Split Mode initialized")
logger.info(f"   Output directory: {self.output_dir}")
logger.info(f"   Checkpoint directory: {self.checkpoint_dir}")
logger.info(f"   Quality threshold: {self.quality_threshold:.0%}")
logger.info(f"   Contract validation: {self.enable_contracts} (will initialize on demand)")
logger.info("="*80)
```

### Step 3: Add Async Initialization Method

```python
async def initialize_contract_manager(self):
    """
    Initialize ContractManager with StateManager.
    Must be called before using contract validation features.

    This is async because StateManager requires async initialization
    of database and Redis connections.
    """
    if not self.enable_contracts:
        logger.info("   Contract validation disabled by configuration")
        return

    if not CONTRACT_VALIDATION_AVAILABLE:
        logger.warning("   ContractManager not available (import failed)")
        return

    try:
        # Initialize StateManager
        from state_manager_init import init_state_manager_for_testing
        logger.info("   Initializing StateManager for ContractManager...")
        self._state_manager = await init_state_manager_for_testing(
            db_path="./maestro_contracts.db",
            use_mock_redis=True  # Use mock for now, can switch to real Redis later
        )

        # Initialize ContractManager
        self.contract_manager = ContractManager(self._state_manager)
        logger.info("✅ ContractManager initialized with StateManager")

    except Exception as e:
        logger.error(f"❌ Failed to initialize ContractManager: {e}")
        self.enable_contracts = False
        self.contract_manager = None

async def cleanup(self):
    """Cleanup StateManager resources"""
    if self._state_manager:
        logger.info("   Cleaning up StateManager...")
        from state_manager_init import cleanup_state_manager
        await cleanup_state_manager(self._state_manager)
        logger.info("✅ StateManager cleaned up")
```

### Step 4: Update _validate_phase_boundary()

Since `process_incoming_message()` doesn't exist, use simpler validation:

```python
async def _validate_phase_boundary(
    self,
    phase_from: str,
    phase_to: str,
    context: TeamExecutionContext
):
    """Validate phase boundary using ContractManager"""
    if not self.enable_contracts or not self.contract_manager:
        logger.info("   ⏭️  Skipping contract validation (disabled)")
        return

    boundary_id = f"{phase_from}-{phase_to}"

    # Check circuit breaker
    if self.circuit_breaker.is_open(boundary_id):
        logger.error(f"   🔴 Circuit breaker OPEN for {boundary_id}")
        raise ValidationException(f"Circuit breaker open for {boundary_id}")

    try:
        # Get previous phase result
        prev_result = context.workflow.get_phase_result(phase_from)
        if not prev_result:
            logger.warning(f"   ⚠️  No result from {phase_from}, skipping validation")
            return

        # SIMPLIFIED VALIDATION: Check if contracts exist for transition
        team_id = context.workflow.workflow_id
        contract_name = f"phase_boundary_{phase_from}_to_{phase_to}"

        # Try to get active contract for this boundary
        active_contract = await self.contract_manager.get_active_contract(
            team_id=team_id,
            contract_name=contract_name
        )

        if active_contract:
            logger.info(f"   ✅ Found contract for {boundary_id}: {active_contract['version']}")
            self.circuit_breaker.record_success(boundary_id)
        else:
            # No contract defined - that's OK, just log it
            logger.info(f"   ℹ️  No contract defined for {boundary_id} (proceeding anyway)")
            self.circuit_breaker.record_success(boundary_id)

        # Record validation
        context.workflow.add_contract_validation(
            phase=phase_to,
            contract_id=boundary_id,
            validation_result={"passed": True, "contract_found": active_contract is not None}
        )

        logger.info(f"   ✅ Phase boundary validation passed")

    except Exception as e:
        self.circuit_breaker.record_failure(boundary_id)
        logger.error(f"   ❌ Contract validation failed: {e}")
        # Don't raise - allow workflow to continue
        logger.warning(f"   ⚠️  Continuing despite validation error")
```

###  Step 5: Update CLI/Main Usage

```python
async def main():
    """CLI entry point"""
    # ... argparse setup ...

    # Create engine
    engine = TeamExecutionEngineV2SplitMode(
        output_dir=args.output,
        checkpoint_dir=args.checkpoint_dir,
        quality_threshold=args.quality_threshold
    )

    # Initialize async components
    if args.enable_contracts:  # Add this CLI flag
        await engine.initialize_contract_manager()

    # Execute based on mode
    if args.batch:
        context = await engine.execute_batch(
            requirement=args.requirement,
            create_checkpoints=args.create_checkpoints
        )
    # ... rest of execution ...

    # Cleanup
    await engine.cleanup()
```

---

## Testing Checklist

### 1. Test Import Fixes
```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive
python3 -c "from contract_manager import ContractManager; print('✅ ContractManager imports successfully')"
```

### 2. Test StateManager Initialization
```bash
python3 state_manager_init.py
# Should see: ✅ StateManager initialized
```

### 3. Test ContractManager with StateManager
```python
import asyncio
from state_manager_init import init_state_manager_for_testing
from contract_manager import ContractManager

async def test():
    # Initialize StateManager
    state_mgr = await init_state_manager_for_testing()

    # Initialize ContractManager
    contract_mgr = ContractManager(state_mgr)

    # Test create contract
    contract = await contract_mgr.create_contract(
        team_id="test_team",
        contract_name="TestContract",
        version="v1.0",
        contract_type="REST_API",
        specification={"endpoints": ["/api/test"]},
        owner_role="Tech Lead",
        owner_agent="test_agent"
    )

    print(f"✅ Contract created: {contract['id']}")

    # Cleanup
    from state_manager_init import cleanup_state_manager
    await cleanup_state_manager(state_mgr)

asyncio.run(test())
```

### 4. Test Full Integration
```bash
# Test with batch execution
python3 team_execution_v2_split_mode.py \
    --batch \
    --requirement "Build a simple API" \
    --enable-contracts  # New flag
```

---

## Files Modified

1. **contract_manager.py** (lines 22-24):
   - Fixed sys.path to point to claude_team_sdk
   - ✅ COMPLETE

2. **persistence/__init__.py**:
   - Added Contract, ContractStatus, TeamMembership, etc. to exports
   - ✅ COMPLETE

3. **team_execution_v2.py** (lines 56-64):
   - Fixed import to use local contract_manager
   - ✅ COMPLETE

4. **team_execution_v2_split_mode.py** (lines 67-77):
   - Fixed import to use local contract_manager
   - ⚠️ NEEDS: Async initialization pattern (see Step 2-4 above)

5. **state_manager_init.py**:
   - NEW FILE - Helper for StateManager initialization
   - ✅ COMPLETE

6. **CONTRACT_MANAGER_IMPLEMENTATION_GUIDE.md**:
   - NEW FILE - This documentation
   - ✅ COMPLETE

---

## Next Steps for User

1. **Review Options**: Choose async initialization pattern (recommend Option 1)

2. **Implement Async Init**: Add `initialize_contract_manager()` method to TeamExecutionEngineV2SplitMode

3. **Update _validate_phase_boundary()**: Use simpler contract validation (get_active_contract)

4. **Test Integration**: Run test to verify ContractManager works with StateManager

5. **Add Contract Creation**: Optionally add logic to create phase boundary contracts automatically

---

## Questions for User

1. **Redis**: Do you want to use real Redis or is MockRedis sufficient for now?
   - MockRedis = No Redis server required (good for development/testing)
   - Real Redis = Full pub/sub events, distributed locking (good for production)

2. **Database**: SQLite OK for testing or need PostgreSQL?
   - SQLite = File-based, simple, good for single-process
   - PostgreSQL = Better for production, multi-process

3. **Validation Strictness**: Should phase boundary validation be:
   - **Strict**: Fail workflow if contract validation fails
   - **Permissive**: Log warning but continue workflow

4. **Auto-Create Contracts**: Should system automatically create phase boundary contracts?
   - **Manual**: Contracts must be explicitly created
   - **Auto**: System creates contracts for each phase transition

---

## Summary

**Current Status**:
- ✅ Imports fixed
- ✅ Persistence models available
- ✅ StateManager helper created
- ⚠️ Async initialization pattern needed
- ⚠️ Contract validation method needs simplification

**Recommended Next Action**:
Implement Option 1 (Async Factory Pattern) as outlined in Steps 2-5 above. This provides clean separation between sync and async initialization while maintaining a clear API.

**Time Estimate**: 1-2 hours for implementation + testing

