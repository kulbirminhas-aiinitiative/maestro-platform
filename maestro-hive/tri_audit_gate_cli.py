#!/usr/bin/env python3
"""
Tri-Modal Audit Deployment Gate CLI Tool

Command-line interface for checking deployment gates in CI/CD pipelines.

Usage:
    python tri_audit_gate_cli.py check --verdict ALL_PASS --iteration iter-123
    python tri_audit_gate_cli.py check --verdict SYSTEMIC_FAILURE --iteration iter-456 --json
    python tri_audit_gate_cli.py status --iteration iter-123

Exit Codes:
    0 = Deployment approved (gate PASS)
    1 = Deployment blocked (gate FAIL)
    2 = Invalid arguments or error
"""

import sys
import argparse
import json
from pathlib import Path

# Import from test file (in production, these would be in separate modules)
sys.path.insert(0, str(Path(__file__).parent / "tests" / "tri_audit" / "integration"))

try:
    from test_deployment_gate import (
        DeploymentGate,
        GateAuditLogger,
        OverrideManager,
        CICDIntegration,
        GateCLI,
        TriModalVerdict,
        GateStatus
    )
except ImportError:
    print("Error: Could not import deployment gate modules", file=sys.stderr)
    sys.exit(2)


def check_gate(args):
    """Check deployment gate"""
    gate = DeploymentGate()
    cli = GateCLI(gate)

    return cli.check(
        verdict=args.verdict,
        iteration_id=args.iteration,
        json_output=args.json
    )


def show_status(args):
    """Show gate status and audit trail"""
    logger = GateAuditLogger()

    # Get audit trail for iteration
    entries = logger.get_audit_trail(args.iteration)

    if args.json:
        output = {
            "iteration_id": args.iteration,
            "total_checks": len(entries),
            "checks": [
                {
                    "timestamp": e.timestamp,
                    "verdict": e.verdict,
                    "status": e.gate_status.value if hasattr(e.gate_status, 'value') else str(e.gate_status),
                    "deploy_allowed": e.deploy_allowed,
                    "trigger_user": e.trigger_user,
                    "override_used": e.override_used
                }
                for e in entries
            ]
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nDeployment Gate Status for {args.iteration}")
        print("=" * 60)
        print(f"Total Checks: {len(entries)}")

        if entries:
            print("\nRecent Checks:")
            for entry in entries[-5:]:  # Show last 5
                override_marker = " [OVERRIDE]" if entry.override_used else ""
                print(f"  {entry.timestamp}: {entry.verdict} -> {entry.gate_status.value if hasattr(entry.gate_status, 'value') else entry.gate_status}{override_marker}")
        else:
            print("\nNo checks found for this iteration")

    return 0


def show_metrics(args):
    """Show gate metrics"""
    logger = GateAuditLogger()

    pass_rate = logger.get_pass_rate(days=args.days)
    override_count = logger.get_override_count(days=args.days)
    all_entries = logger.get_audit_trail()

    if args.json:
        output = {
            "period_days": args.days,
            "pass_rate": pass_rate,
            "override_count": override_count,
            "total_checks": len(all_entries)
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nDeployment Gate Metrics (Last {args.days} days)")
        print("=" * 60)
        print(f"Pass Rate: {pass_rate:.1%}")
        print(f"Override Count: {override_count}")
        print(f"Total Checks: {len(all_entries)}")

    return 0


def request_override(args):
    """Request override for blocked deployment"""
    manager = OverrideManager()

    try:
        override = manager.request_override(
            iteration_id=args.iteration,
            requester=args.requester,
            justification=args.justification,
            verdict=args.verdict,
            duration_hours=args.duration
        )

        if args.json:
            print(json.dumps({
                "status": "success",
                "iteration_id": override.iteration_id,
                "requester": override.requester,
                "expiration": override.expiration
            }, indent=2))
        else:
            print(f"Override requested for {args.iteration}")
            print(f"Requester: {args.requester}")
            print(f"Expires: {override.expiration}")
            print("\nWaiting for approval...")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def approve_override(args):
    """Approve override request"""
    manager = OverrideManager()

    try:
        override = manager.approve_override(
            iteration_id=args.iteration,
            approver=args.approver
        )

        if args.json:
            print(json.dumps({
                "status": "success",
                "iteration_id": override.iteration_id,
                "approver": override.approver,
                "timestamp": override.timestamp
            }, indent=2))
        else:
            print(f"Override approved for {args.iteration}")
            print(f"Approver: {args.approver}")

        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Tri-Modal Audit Deployment Gate CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Check command
    check_parser = subparsers.add_parser("check", help="Check deployment gate")
    check_parser.add_argument("--verdict", required=True, choices=[v.value for v in TriModalVerdict],
                             help="Tri-modal verdict")
    check_parser.add_argument("--iteration", required=True, help="Iteration ID")
    check_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show gate status")
    status_parser.add_argument("--iteration", required=True, help="Iteration ID")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Show gate metrics")
    metrics_parser.add_argument("--days", type=int, default=30, help="Number of days (default: 30)")
    metrics_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Override command
    override_parser = subparsers.add_parser("override", help="Request override")
    override_parser.add_argument("--iteration", required=True, help="Iteration ID")
    override_parser.add_argument("--requester", required=True, help="Requester email")
    override_parser.add_argument("--justification", required=True, help="Justification (min 10 chars)")
    override_parser.add_argument("--verdict", required=True, help="Verdict being overridden")
    override_parser.add_argument("--duration", type=int, default=24, help="Duration in hours (default: 24)")
    override_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Approve override")
    approve_parser.add_argument("--iteration", required=True, help="Iteration ID")
    approve_parser.add_argument("--approver", required=True, help="Approver email")
    approve_parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 2

    # Route to appropriate handler
    handlers = {
        "check": check_gate,
        "status": show_status,
        "metrics": show_metrics,
        "override": request_override,
        "approve": approve_override
    }

    handler = handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    sys.exit(main())
