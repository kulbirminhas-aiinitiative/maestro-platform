"""
Maestro CLI - Slash Command Interface

EPIC: MD-2502 - CLI Slash Command Interface (Sub-EPIC of MD-2493)

Provides the /maestro command entry point for Claude Code.
"""

from .command import MaestroCommand

__all__ = ["MaestroCommand"]
