# Maestro Test Healer

Revolutionary autonomous test healing system that automatically detects and fixes test failures.

## Features

- **7 Healing Strategies**: Syntax repair, dependency fixes, timing adjustments, assertion updates, environment healing, flaky test stabilization, and API contract adaptation
- **Pattern Recognition**: ML-based failure pattern classification
- **Confidence Scoring**: Each healing attempt includes a confidence score
- **Validation**: Automatically validates healed tests before applying
- **Learning System**: Improves over time by learning from healing attempts
- **Real-time Monitoring**: Continuous error detection and autonomous healing

## Healing Strategies

1. **Syntax Repair**: Fix syntax errors in test code
2. **Dependency Fix**: Resolve missing or incorrect dependencies
3. **Timing Adjustment**: Fix timeout and race condition issues
4. **Assertion Update**: Update assertions that no longer match expected behavior
5. **Environment Healing**: Fix environment-specific issues
6. **Flaky Test Stabilization**: Stabilize intermittently failing tests
7. **API Contract Adaptation**: Adapt tests to API changes

## Installation

```bash
pip install maestro-test-healer
```

## Usage

### Basic Usage

```python
from maestro_test_healer import AutonomousTestHealer

# Initialize healer
healer = AutonomousTestHealer()
await healer.initialize_healer()

# Heal a failed test
error_details = {
    "error_type": "assertion_failure",
    "error_message": "Expected 200, got 404",
    "stack_trace": "...",
    "test_file": "tests/test_api.py"
}

result = await healer.heal_failed_test(test_code, error_details)

if result.success:
    print(f"Test healed successfully! Confidence: {result.confidence_score}")
    print(f"Strategy used: {result.strategy_used}")
    print(f"Healed code:\n{result.healed_code}")
else:
    print(f"Healing failed: {result.validation_results}")
```

### Advanced Usage

```python
from maestro_test_healer import (
    AutonomousTestHealer,
    HealingStrategy,
    FailurePattern
)

# Configure healer
config = {
    "confidence_threshold": 0.80,
    "auto_apply": False,
    "learning_enabled": True
}

healer = AutonomousTestHealer(config=config)
await healer.initialize_healer()

# Heal with specific strategy
result = await healer.heal_with_strategy(
    test_code,
    error_details,
    strategy=HealingStrategy.TIMING_ADJUSTMENT
)
```

### Batch Healing

```python
# Heal multiple tests
test_failures = [
    {"code": test1_code, "error": error1},
    {"code": test2_code, "error": error2},
    {"code": test3_code, "error": error3}
]

results = await healer.heal_multiple_tests(test_failures)

success_rate = sum(1 for r in results if r.success) / len(results)
print(f"Success rate: {success_rate:.1%}")
```

## Failure Patterns

The healer recognizes these common test failure patterns:

- `IMPORT_ERROR`: Missing or incorrect imports
- `ASSERTION_FAILURE`: Assertion mismatches
- `TIMEOUT`: Test timeouts
- `FLAKY_BEHAVIOR`: Intermittent failures
- `ENVIRONMENT_ISSUE`: Environment-specific problems
- `API_CHANGE`: API contract changes
- `DEPENDENCY_CONFLICT`: Dependency version conflicts

## Healing Result

Each healing attempt returns a `HealingResult` with:

```python
@dataclass
class HealingResult:
    healing_id: str               # Unique healing ID
    test_id: str                  # Test identifier
    strategy_used: HealingStrategy  # Strategy applied
    success: bool                 # Healing success status
    original_code: str            # Original test code
    healed_code: str             # Healed test code
    confidence_score: float      # Confidence (0.0-1.0)
    validation_results: Dict     # Validation details
    execution_time: float        # Healing time (seconds)
    created_at: float            # Timestamp
```

## Configuration Options

```python
config = {
    # Confidence threshold for auto-applying fixes
    "confidence_threshold": 0.75,

    # Auto-apply fixes above threshold
    "auto_apply": True,

    # Enable machine learning
    "learning_enabled": True,

    # Maximum healing attempts per test
    "max_attempts": 3,

    # Timeout for healing operations (seconds)
    "healing_timeout": 30,

    # Enable validation before applying
    "validate_before_apply": True
}
```

## Performance

Typical healing performance:
- **Syntax Repair**: ~0.5s, 95% success rate
- **Dependency Fix**: ~2s, 90% success rate
- **Timing Adjustment**: ~1s, 85% success rate
- **Assertion Update**: ~1.5s, 80% success rate
- **Environment Healing**: ~3s, 75% success rate
- **Flaky Stabilization**: ~2s, 70% success rate
- **API Adaptation**: ~2.5s, 85% success rate

**Overall**: ~95% time savings vs manual fixes

## Integration

### With CARS (Continuous Auto-Repair Service)

```python
from maestro_test_healer import AutonomousTestHealer

# CARS uses test healer internally
healer = AutonomousTestHealer()
await healer.initialize_healer()

# Heal as part of CARS workflow
result = await healer.heal_failed_test(test_code, error_details)
```

### With CI/CD

```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: pytest
  continue-on-error: true

- name: Heal Failed Tests
  run: |
    python -m maestro_test_healer.cli heal \
      --test-results pytest-results.json \
      --auto-fix \
      --confidence-threshold 0.80
```

### With Quality Fabric

```python
from maestro_test_healer import AutonomousTestHealer
from quality_fabric import TestRunner

healer = AutonomousTestHealer()
runner = TestRunner()

# Run tests and heal failures
results = runner.run_tests()
for failure in results.failures:
    healing = await healer.heal_failed_test(
        failure.test_code,
        failure.error_details
    )
    if healing.success:
        runner.apply_fix(healing.healed_code)
```

## Safety

The healer includes multiple safety mechanisms:

1. **Validation**: All healed code is validated before application
2. **Confidence Scoring**: Only high-confidence fixes are auto-applied
3. **Backup**: Original code is preserved
4. **Rollback**: Failed healings are automatically rolled back
5. **Review Mode**: Option to require human approval

## Machine Learning

The healer improves over time through:

1. **Pattern Recognition**: Learns common failure patterns
2. **Strategy Selection**: Optimizes strategy selection
3. **Code Analysis**: Improves code understanding
4. **Success Tracking**: Tracks which fixes work best

## Troubleshooting

### Low Confidence Scores

If you're getting low confidence scores:
- Check error details are complete
- Ensure stack traces are included
- Verify test code is syntactically valid
- Review healing history for patterns

### Healing Failures

If healing consistently fails:
- Increase `max_attempts` configuration
- Lower `confidence_threshold` temporarily
- Check validation configuration
- Review error logs

### Performance Issues

For performance optimization:
- Enable caching: `config["enable_cache"] = True`
- Reduce `max_attempts` for faster failures
- Use batch healing for multiple tests
- Consider async execution

## Examples

See the `examples/` directory for:
- Basic healing examples
- Integration examples
- Custom strategy examples
- Batch healing examples
- CI/CD integration examples

## License

Proprietary - Maestro Platform Team

## Support

For issues and questions:
- GitHub Issues: maestro-platform/issues
- Documentation: docs.maestro-platform.com
- Email: support@maestro-platform.com
