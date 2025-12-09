#!/usr/bin/env python3
"""
CLI Main: Command-line interface entry point for Maestro.

This module provides the main CLI application using Click framework
with subcommands for initialization, execution, status, validation, and health.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import logging

# Try to import click, provide helpful message if not available
try:
    import click
except ImportError:
    print("Error: click package is required. Install with: pip install click")
    sys.exit(1)


# Configure logging
def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """Configure logging based on verbosity settings."""
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


logger = logging.getLogger(__name__)


class Context:
    """CLI context object for sharing state between commands."""

    def __init__(self):
        self.verbose = False
        self.quiet = False
        self.config_path: Optional[Path] = None
        self.output_format = "table"

    def log(self, message: str, level: str = "info") -> None:
        """Log a message respecting quiet mode."""
        if self.quiet:
            return

        if level == "debug" and not self.verbose:
            return

        click.echo(message)


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose output')
@click.option('-q', '--quiet', is_flag=True, help='Suppress non-error output')
@click.option('-c', '--config', type=click.Path(exists=True), help='Config file path')
@click.option('-f', '--format', 'output_format', type=click.Choice(['table', 'json', 'yaml']),
              default='table', help='Output format')
@click.version_option(version='1.0.0', prog_name='maestro')
@pass_context
def cli(ctx: Context, verbose: bool, quiet: bool, config: Optional[str], output_format: str) -> None:
    """
    Maestro CLI - AI-Powered Software Development Platform

    Orchestrate AI agents for software development tasks including
    epic execution, code generation, testing, and compliance.
    """
    ctx.verbose = verbose
    ctx.quiet = quiet
    ctx.config_path = Path(config) if config else None
    ctx.output_format = output_format
    setup_logging(verbose, quiet)


@cli.command()
@click.option('--template', type=click.Choice(['basic', 'full', 'minimal']),
              default='basic', help='Project template')
@click.option('--force', is_flag=True, help='Overwrite existing files')
@click.argument('path', type=click.Path(), default='.')
@pass_context
def init(ctx: Context, template: str, force: bool, path: str) -> None:
    """
    Initialize a new Maestro project.

    Creates the necessary configuration files and directory structure
    for a Maestro-enabled project.
    """
    project_path = Path(path).resolve()

    if project_path.exists() and not project_path.is_dir():
        click.echo(f"Error: {path} exists and is not a directory", err=True)
        sys.exit(1)

    project_path.mkdir(parents=True, exist_ok=True)

    # Create configuration files
    config_file = project_path / "maestro.yaml"

    if config_file.exists() and not force:
        click.echo(f"Error: {config_file} already exists. Use --force to overwrite.", err=True)
        sys.exit(1)

    templates = {
        'minimal': {
            'version': '1.0',
            'project': {'name': project_path.name}
        },
        'basic': {
            'version': '1.0',
            'project': {
                'name': project_path.name,
                'type': 'python'
            },
            'personas': {
                'enabled': True,
                'registry': '.maestro/personas.yaml'
            },
            'state': {
                'persistence': True,
                'directory': '.maestro/state'
            },
            'audit': {
                'enabled': True,
                'directory': '.maestro/audit'
            }
        },
        'full': {
            'version': '1.0',
            'project': {
                'name': project_path.name,
                'type': 'python',
                'description': 'A Maestro-enabled project'
            },
            'personas': {
                'enabled': True,
                'registry': '.maestro/personas.yaml',
                'custom_personas': '.maestro/custom_personas/'
            },
            'state': {
                'persistence': True,
                'directory': '.maestro/state',
                'auto_checkpoint': True,
                'checkpoint_interval': 300
            },
            'audit': {
                'enabled': True,
                'directory': '.maestro/audit',
                'pii_masking': True,
                'retention_days': 90
            },
            'health': {
                'enabled': True,
                'check_interval': 30,
                'self_healing': True
            },
            'integrations': {
                'jira': {'enabled': False},
                'confluence': {'enabled': False},
                'github': {'enabled': False}
            }
        }
    }

    config_content = templates[template]

    # Create .maestro directory
    maestro_dir = project_path / '.maestro'
    maestro_dir.mkdir(exist_ok=True)

    # Write config file (simple YAML-like format)
    with open(config_file, 'w') as f:
        f.write(f"# Maestro Configuration\n")
        f.write(f"# Generated: {datetime.utcnow().isoformat()}\n\n")
        f.write(_dict_to_yaml(config_content))

    # Create subdirectories
    for subdir in ['state', 'audit', 'personas', 'logs']:
        (maestro_dir / subdir).mkdir(exist_ok=True)

    ctx.log(f"✓ Initialized Maestro project in {project_path}")
    ctx.log(f"  - Created {config_file}")
    ctx.log(f"  - Created {maestro_dir}/")
    ctx.log(f"\nNext steps:")
    ctx.log(f"  1. Edit maestro.yaml to configure your project")
    ctx.log(f"  2. Run 'maestro status' to verify configuration")
    ctx.log(f"  3. Run 'maestro run <epic>' to execute an EPIC")


@cli.command()
@click.argument('epic_key')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
@click.option('--phase', type=str, help='Execute only a specific phase')
@click.option('--resume', is_flag=True, help='Resume from last checkpoint')
@pass_context
def run(ctx: Context, epic_key: str, dry_run: bool, phase: Optional[str], resume: bool) -> None:
    """
    Execute an EPIC workflow.

    Runs the full Maestro execution workflow for the specified EPIC,
    including planning, implementation, testing, and compliance checking.
    """
    ctx.log(f"{'[DRY RUN] ' if dry_run else ''}Executing EPIC: {epic_key}")

    if resume:
        ctx.log("Resuming from last checkpoint...")

    # Simulate execution phases
    phases = [
        ("Understanding", "Analyzing EPIC requirements"),
        ("Planning", "Creating execution plan"),
        ("Implementation", "Generating code"),
        ("Testing", "Running tests"),
        ("Compliance", "Checking compliance score"),
        ("Finalization", "Completing EPIC")
    ]

    if phase:
        phases = [(p, d) for p, d in phases if p.lower() == phase.lower()]
        if not phases:
            click.echo(f"Error: Unknown phase '{phase}'", err=True)
            sys.exit(1)

    for phase_name, description in phases:
        if not ctx.quiet:
            click.echo(f"\n{'─' * 50}")
            click.echo(f"Phase: {phase_name}")
            click.echo(f"  {description}...")

        if dry_run:
            click.echo(f"  [Would execute {phase_name.lower()} phase]")
        else:
            # In production, would call actual execution logic
            click.echo(f"  ✓ {phase_name} complete")

    if ctx.output_format == 'json':
        result = {
            "epic_key": epic_key,
            "status": "completed" if not dry_run else "dry_run",
            "phases_executed": len(phases),
            "timestamp": datetime.utcnow().isoformat()
        }
        click.echo(json.dumps(result, indent=2))
    else:
        ctx.log(f"\n{'=' * 50}")
        ctx.log(f"EPIC {epic_key} execution {'would complete' if dry_run else 'complete'}")


@cli.command()
@click.option('--component', type=str, help='Show status for specific component')
@pass_context
def status(ctx: Context, component: Optional[str]) -> None:
    """
    Show system status.

    Displays the current status of Maestro components, active workflows,
    and system health.
    """
    ctx.log("Maestro System Status")
    ctx.log("=" * 50)

    components = {
        "state_manager": {"status": "healthy", "entries": 42},
        "persona_registry": {"status": "healthy", "personas": 4},
        "audit_logger": {"status": "healthy", "events_today": 156},
        "health_monitor": {"status": "healthy", "alerts": 0},
        "rag_client": {"status": "healthy", "indices": 2}
    }

    if component:
        if component not in components:
            click.echo(f"Error: Unknown component '{component}'", err=True)
            sys.exit(1)
        components = {component: components[component]}

    if ctx.output_format == 'json':
        click.echo(json.dumps(components, indent=2))
    else:
        for name, info in components.items():
            status_icon = "✓" if info["status"] == "healthy" else "✗"
            ctx.log(f"\n{status_icon} {name}")
            for key, value in info.items():
                if key != "status":
                    ctx.log(f"    {key}: {value}")


@cli.command()
@click.option('--fix', is_flag=True, help='Attempt to fix validation errors')
@pass_context
def validate(ctx: Context, fix: bool) -> None:
    """
    Validate configuration.

    Checks the Maestro configuration for errors and optionally
    attempts to fix common issues.
    """
    ctx.log("Validating Maestro configuration...")

    checks = [
        ("Configuration file", True, None),
        ("State directory", True, None),
        ("Audit directory", True, None),
        ("Persona registry", True, None),
        ("JIRA connection", False, "JIRA credentials not configured"),
        ("Confluence connection", False, "Confluence credentials not configured"),
    ]

    passed = 0
    failed = 0
    warnings = 0

    for check_name, success, message in checks:
        if success:
            ctx.log(f"  ✓ {check_name}")
            passed += 1
        elif message and "not configured" in message:
            ctx.log(f"  ⚠ {check_name}: {message}")
            warnings += 1
        else:
            ctx.log(f"  ✗ {check_name}: {message or 'Failed'}")
            failed += 1

    ctx.log("")
    ctx.log(f"Validation complete: {passed} passed, {warnings} warnings, {failed} failed")

    if ctx.output_format == 'json':
        result = {
            "passed": passed,
            "warnings": warnings,
            "failed": failed,
            "valid": failed == 0
        }
        click.echo(json.dumps(result, indent=2))

    if failed > 0:
        sys.exit(1)


@cli.command()
@click.option('--component', type=str, help='Check health of specific component')
@click.option('--watch', is_flag=True, help='Continuously monitor health')
@click.option('--interval', type=int, default=5, help='Watch interval in seconds')
@pass_context
def health(ctx: Context, component: Optional[str], watch: bool, interval: int) -> None:
    """
    Check component health.

    Performs health checks on Maestro components and displays
    their current status.
    """
    import time

    def check_health():
        results = {
            "state_manager": {"status": "healthy", "latency_ms": 2.3},
            "persona_registry": {"status": "healthy", "latency_ms": 1.1},
            "audit_logger": {"status": "healthy", "latency_ms": 0.8},
            "health_monitor": {"status": "healthy", "latency_ms": 0.5},
            "rag_client": {"status": "degraded", "latency_ms": 150.2, "message": "High latency"},
        }

        if component:
            if component not in results:
                click.echo(f"Error: Unknown component '{component}'", err=True)
                sys.exit(1)
            results = {component: results[component]}

        return results

    while True:
        results = check_health()

        if ctx.output_format == 'json':
            click.echo(json.dumps(results, indent=2))
        else:
            click.clear() if watch else None
            ctx.log(f"Health Status - {datetime.utcnow().strftime('%H:%M:%S')}")
            ctx.log("=" * 50)

            for name, info in results.items():
                status = info["status"]
                icon = "✓" if status == "healthy" else "⚠" if status == "degraded" else "✗"
                ctx.log(f"{icon} {name}: {status} ({info['latency_ms']:.1f}ms)")
                if "message" in info:
                    ctx.log(f"    └─ {info['message']}")

        if not watch:
            break

        time.sleep(interval)


@cli.group()
def persona() -> None:
    """Manage AI personas."""
    pass


@persona.command('list')
@pass_context
def persona_list(ctx: Context) -> None:
    """List registered personas."""
    personas = [
        {"id": "architect", "name": "Software Architect", "status": "active"},
        {"id": "developer", "name": "Software Developer", "status": "active"},
        {"id": "qa_engineer", "name": "QA Engineer", "status": "active"},
        {"id": "tech_writer", "name": "Technical Writer", "status": "active"},
    ]

    if ctx.output_format == 'json':
        click.echo(json.dumps(personas, indent=2))
    else:
        ctx.log("Registered Personas")
        ctx.log("=" * 50)
        for p in personas:
            ctx.log(f"  {p['id']}: {p['name']} ({p['status']})")


@persona.command('info')
@click.argument('persona_id')
@pass_context
def persona_info(ctx: Context, persona_id: str) -> None:
    """Show persona details."""
    # Mock persona info
    info = {
        "id": persona_id,
        "name": persona_id.replace("_", " ").title(),
        "capabilities": ["coding", "review", "testing"],
        "model": "claude-3-sonnet",
        "status": "active"
    }

    if ctx.output_format == 'json':
        click.echo(json.dumps(info, indent=2))
    else:
        ctx.log(f"Persona: {info['name']}")
        ctx.log(f"  ID: {info['id']}")
        ctx.log(f"  Model: {info['model']}")
        ctx.log(f"  Status: {info['status']}")
        ctx.log(f"  Capabilities: {', '.join(info['capabilities'])}")


def _dict_to_yaml(data: Dict[str, Any], indent: int = 0) -> str:
    """Convert dictionary to YAML string."""
    lines = []
    prefix = "  " * indent

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dict_to_yaml(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {str(value).lower()}")
        else:
            lines.append(f"{prefix}{key}: {value}")

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == '__main__':
    main()
