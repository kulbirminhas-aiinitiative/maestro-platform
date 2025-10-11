#!/usr/bin/env python3
"""
DAG Feature Flags Verification Tool

Verifies the current DAG feature flag configuration and displays
system status in a human-readable format.

Usage:
    python3 verify_flags.py
    python3 verify_flags.py --json  # Output in JSON format
"""

import os
import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from team_execution_dual import FeatureFlags, ExecutionMode


def get_color_code(condition: bool) -> str:
    """Get ANSI color code based on condition"""
    return "\033[92m" if condition else "\033[91m"  # Green if True, Red if False


def reset_color() -> str:
    """Get ANSI reset code"""
    return "\033[0m"


def verify_environment() -> dict:
    """Verify environment variables and system state"""
    env_vars = {
        'MAESTRO_ENABLE_DAG_EXECUTION': os.getenv('MAESTRO_ENABLE_DAG_EXECUTION', 'not set'),
        'MAESTRO_ENABLE_PARALLEL_EXECUTION': os.getenv('MAESTRO_ENABLE_PARALLEL_EXECUTION', 'not set'),
        'MAESTRO_ENABLE_CONTEXT_PERSISTENCE': os.getenv('MAESTRO_ENABLE_CONTEXT_PERSISTENCE', 'not set'),
        'MAESTRO_ENABLE_EXECUTION_EVENTS': os.getenv('MAESTRO_ENABLE_EXECUTION_EVENTS', 'not set'),
        'MAESTRO_ENABLE_RETRY_LOGIC': os.getenv('MAESTRO_ENABLE_RETRY_LOGIC', 'not set'),
    }

    return env_vars


def verify_modules() -> dict:
    """Verify that DAG modules can be imported"""
    results = {}

    modules_to_test = [
        'dag_workflow',
        'dag_executor',
        'dag_compatibility',
        'team_execution_dual',
    ]

    for module_name in modules_to_test:
        try:
            __import__(module_name)
            results[module_name] = {'available': True, 'error': None}
        except Exception as e:
            results[module_name] = {'available': False, 'error': str(e)}

    return results


def verify_feature_flags() -> dict:
    """Verify feature flags configuration"""
    try:
        flags = FeatureFlags()
        flags_dict = flags.to_dict()
        flags_dict['mode_object'] = flags.get_execution_mode()
        flags_dict['valid'] = True
        return flags_dict
    except Exception as e:
        return {'valid': False, 'error': str(e)}


def check_compatibility() -> dict:
    """Check for flag compatibility issues"""
    issues = []
    warnings = []

    flags = FeatureFlags()

    # Check: If parallel execution is enabled, DAG execution must also be enabled
    if flags.enable_parallel_execution and not flags.enable_dag_execution:
        issues.append(
            "PARALLEL_EXECUTION is enabled but DAG_EXECUTION is disabled. "
            "Parallel execution requires DAG mode."
        )

    # Warning: Context persistence disabled means no recovery
    if not flags.enable_context_persistence:
        warnings.append(
            "Context persistence is disabled. Workflows cannot be resumed after crashes."
        )

    # Warning: Events disabled means no monitoring
    if not flags.enable_execution_events:
        warnings.append(
            "Execution events are disabled. Monitoring and progress tracking will be limited."
        )

    # Info: DAG disabled means using legacy mode
    if not flags.enable_dag_execution:
        warnings.append(
            "DAG execution is disabled. System will use legacy linear execution mode."
        )

    return {
        'issues': issues,
        'warnings': warnings,
        'compatible': len(issues) == 0
    }


def print_human_readable(data: dict):
    """Print verification results in human-readable format"""
    print("\n" + "=" * 80)
    print("DAG SYSTEM FEATURE FLAGS VERIFICATION")
    print("=" * 80)

    # Environment Variables
    print("\n📋 Environment Variables:")
    print("-" * 80)
    for var, value in data['environment'].items():
        status = "✓" if value not in ['not set', 'false'] else "○"
        print(f"  {status} {var:45s} = {value}")

    # Feature Flags
    print("\n🚩 Feature Flags (Parsed):")
    print("-" * 80)
    flags = data['feature_flags']
    if flags['valid']:
        flag_display = [
            ('DAG Execution', flags['enable_dag_execution']),
            ('Parallel Execution', flags['enable_parallel_execution']),
            ('Context Persistence', flags['enable_context_persistence']),
            ('Execution Events', flags['enable_execution_events']),
            ('Retry Logic', flags['enable_retry_logic']),
        ]

        for name, value in flag_display:
            color = get_color_code(value)
            status = f"{color}{'ENABLED' if value else 'DISABLED'}{reset_color()}"
            print(f"  • {name:25s}: {status}")

        # Execution Mode
        print(f"\n  📊 Execution Mode: {get_color_code(True)}{flags['execution_mode'].upper()}{reset_color()}")
    else:
        print(f"  ❌ Error loading flags: {flags['error']}")

    # Module Availability
    print("\n📦 Module Availability:")
    print("-" * 80)
    all_available = True
    for module, status in data['modules'].items():
        if status['available']:
            print(f"  ✓ {module:30s} Available")
        else:
            print(f"  ✗ {module:30s} UNAVAILABLE - {status['error']}")
            all_available = False

    # Compatibility Check
    print("\n⚙️  Compatibility Check:")
    print("-" * 80)
    compat = data['compatibility']

    if compat['compatible']:
        print(f"  {get_color_code(True)}✓ Configuration is valid{reset_color()}")
    else:
        print(f"  {get_color_code(False)}✗ Configuration has issues{reset_color()}")

    if compat['issues']:
        print("\n  Issues:")
        for issue in compat['issues']:
            print(f"    ❌ {issue}")

    if compat['warnings']:
        print("\n  Warnings:")
        for warning in compat['warnings']:
            print(f"    ⚠️  {warning}")

    # Recommendations
    print("\n💡 Recommendations:")
    print("-" * 80)

    flags_obj = FeatureFlags()
    mode = flags_obj.get_execution_mode()

    if mode == ExecutionMode.LINEAR:
        print("  • Currently using LEGACY linear execution mode")
        print("  • To enable DAG linear mode:")
        print("      export MAESTRO_ENABLE_DAG_EXECUTION=true")
        print("  • To enable parallel execution:")
        print("      export MAESTRO_ENABLE_DAG_EXECUTION=true")
        print("      export MAESTRO_ENABLE_PARALLEL_EXECUTION=true")
    elif mode == ExecutionMode.DAG_LINEAR:
        print("  • Currently using DAG execution with linear workflow")
        print("  • To enable parallel execution:")
        print("      export MAESTRO_ENABLE_PARALLEL_EXECUTION=true")
    elif mode == ExecutionMode.DAG_PARALLEL:
        print("  • ✓ Running in optimal mode (DAG with parallel execution)")
        print("  • No changes recommended")

    # Overall Status
    print("\n" + "=" * 80)
    if all_available and compat['compatible']:
        print(f"{get_color_code(True)}✅ SYSTEM READY{reset_color()}")
    elif all_available and not compat['compatible']:
        print(f"{get_color_code(False)}⚠️  CONFIGURATION ISSUES DETECTED{reset_color()}")
    else:
        print(f"{get_color_code(False)}❌ MODULE ERRORS DETECTED{reset_color()}")
    print("=" * 80 + "\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Verify DAG feature flags configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results in JSON format'
    )

    args = parser.parse_args()

    # Collect verification data
    data = {
        'environment': verify_environment(),
        'modules': verify_modules(),
        'feature_flags': verify_feature_flags(),
        'compatibility': check_compatibility(),
    }

    # Output
    if args.json:
        # JSON output for machine parsing
        print(json.dumps(data, indent=2, default=str))
    else:
        # Human-readable output
        print_human_readable(data)

    # Exit code based on results
    all_modules_ok = all(m['available'] for m in data['modules'].values())
    config_ok = data['compatibility']['compatible']

    if all_modules_ok and config_ok:
        sys.exit(0)  # Success
    elif all_modules_ok:
        sys.exit(1)  # Config issues
    else:
        sys.exit(2)  # Module errors


if __name__ == "__main__":
    main()
