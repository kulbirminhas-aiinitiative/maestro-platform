#!/usr/bin/env python3
"""
Claude Agent SDK - Fixed Version (yoga.wasm Bug Workaround)

This module patches claude-agent-sdk to fix the yoga.wasm module resolution bug
in the Claude CLI by forcing the subprocess to run from the CLI's directory.

Root Cause:
- Claude CLI uses CWD-relative path resolution for yoga.wasm
- When spawned from arbitrary directory, it can't find yoga.wasm
- Solution: Run CLI subprocess from its own directory

Usage:
    # Instead of:
    from claude_agent_sdk import query, ClaudeAgentOptions

    # Use:
    from claude_agent_sdk_fixed import query, ClaudeAgentOptions

    # Everything else works the same!
    async for message in query(prompt="Hello", options=ClaudeAgentOptions()):
        print(message)

Author: MAESTRO Platform
Date: October 10, 2025
Status: Production Workaround (until Anthropic fixes upstream)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the original SDK components
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        # Re-export all types
        AgentDefinition,
        AssistantMessage,
        CanUseTool,
        ContentBlock,
        HookCallback,
        HookContext,
        HookMatcher,
        McpSdkServerConfig,
        McpServerConfig,
        Message,
        PermissionMode,
        PermissionResult,
        PermissionResultAllow,
        PermissionResultDeny,
        PermissionUpdate,
        ResultMessage,
        SettingSource,
        SystemMessage,
        TextBlock,
        ThinkingBlock,
        ToolPermissionContext,
        ToolResultBlock,
        ToolUseBlock,
        UserMessage,
        create_sdk_mcp_server,
        tool,
        SdkMcpTool,
        # Errors
        ClaudeSDKError,
        CLIConnectionError,
        CLINotFoundError,
        ProcessError,
        CLIJSONDecodeError,
    )
    from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport
    from claude_agent_sdk._internal.client import InternalClient

    SDK_AVAILABLE = True
    logger.info("✅ claude-agent-sdk imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import claude-agent-sdk: {e}")
    SDK_AVAILABLE = False
    raise


# ============================================================================
# PATCH: Fix yoga.wasm resolution bug
# ============================================================================

# Store original connect method
_original_connect = SubprocessCLITransport.connect

async def _patched_connect(self):
    """
    Patched connect() method that fixes yoga.wasm resolution.

    The fix:
    1. Detect CLI directory and locate yoga.wasm
    2. Create symlink to yoga.wasm in work directory (if it exists)
    3. Let subprocess run from work directory with yoga.wasm available locally

    This approach:
    - Keeps subprocess CWD as the work directory (correct for file operations)
    - Makes yoga.wasm available in work directory via symlink (fixes resolution)
    - No disk space wasted, always points to current version
    - No need to change CWD or environment variables
    """

    # Get CLI directory - IMPORTANT: Resolve symlinks!
    cli_path_real = os.path.realpath(self._cli_path)
    cli_dir = os.path.dirname(cli_path_real)
    yoga_source = os.path.join(cli_dir, 'yoga.wasm')

    logger.debug(f"🔧 Applying yoga.wasm fix:")
    logger.debug(f"   CLI dir: {cli_dir}")
    logger.debug(f"   Work dir: {self._cwd}")
    logger.debug(f"   yoga.wasm source: {yoga_source}")

    # Create symlink to yoga.wasm in work directory if it exists and work dir is set
    yoga_linked = False
    if self._cwd and os.path.exists(yoga_source):
        try:
            # Ensure work directory exists
            os.makedirs(self._cwd, exist_ok=True)

            yoga_dest = os.path.join(self._cwd, 'yoga.wasm')

            # Create symlink if it doesn't exist or is broken
            if os.path.islink(yoga_dest):
                # Check if existing symlink is valid
                if os.path.exists(yoga_dest) and os.path.samefile(os.readlink(yoga_dest), yoga_source):
                    logger.debug(f"   yoga.wasm symlink already exists")
                    yoga_linked = True
                else:
                    # Remove broken or wrong symlink
                    os.unlink(yoga_dest)
                    logger.debug(f"   Removed invalid yoga.wasm symlink")

            if not yoga_linked:
                if os.path.exists(yoga_dest):
                    # Remove regular file if it exists
                    os.remove(yoga_dest)
                    logger.debug(f"   Removed existing yoga.wasm file")

                # Create symlink
                os.symlink(yoga_source, yoga_dest)
                logger.debug(f"   Created symlink to yoga.wasm")
                yoga_linked = True

        except Exception as e:
            logger.warning(f"   Could not create yoga.wasm symlink: {e}")
            logger.warning(f"   This may cause CLI startup issues")

    # Call original connect
    # If yoga.wasm symlink was created, subprocess will find it in work dir
    # If not linked, CLI may fail to start
    try:
        await _original_connect(self)

        if yoga_linked:
            logger.info(f"✅ CLI subprocess started successfully")
            logger.info(f"   Work dir: {self._cwd}")
            logger.info(f"   yoga.wasm symlink created ✅")
        else:
            logger.info(f"✅ CLI subprocess started (yoga.wasm not linked)")

    except Exception as e:
        logger.error(f"❌ Failed to start CLI: {e}")
        raise


# Apply the patch
SubprocessCLITransport.connect = _patched_connect

logger.info("🔧 Applied yoga.wasm resolution fix to SubprocessCLITransport")


# ============================================================================
# Patched query() function
# ============================================================================

from claude_agent_sdk import query as _original_query
from claude_agent_sdk._internal.query import Query as _InternalQuery
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

async def query(
    *,
    prompt: str | AsyncIterable[dict[str, Any]],
    options: ClaudeAgentOptions | None = None,
) -> AsyncIterator[Message]:
    """
    Fixed version of claude_agent_sdk.query() that works around yoga.wasm bug.

    This is a drop-in replacement for the original query() function.
    The patch is applied to SubprocessCLITransport, so this just calls the original.

    Args:
        prompt: The prompt to send (string or async iterable)
        options: Configuration options

    Yields:
        Messages from Claude

    Example:
        async for message in query(
            prompt="Create a Python REST API",
            options=ClaudeAgentOptions(
                cwd="/my/project",
                allowed_tools=["Write", "Edit", "Bash"],
                permission_mode="bypassPermissions"
            )
        ):
            print(message)
    """
    # The patch is already applied to SubprocessCLITransport.connect()
    # So we just call the original query() which will use our patched transport
    async for message in _original_query(prompt=prompt, options=options):
        yield message


# ============================================================================
# Export everything (same API as original SDK)
# ============================================================================

__all__ = [
    # Main exports
    "query",
    # Client
    "ClaudeSDKClient",
    # Types
    "ClaudeAgentOptions",
    "PermissionMode",
    "McpServerConfig",
    "McpSdkServerConfig",
    "UserMessage",
    "AssistantMessage",
    "SystemMessage",
    "ResultMessage",
    "Message",
    "TextBlock",
    "ThinkingBlock",
    "ToolUseBlock",
    "ToolResultBlock",
    "ContentBlock",
    # Tool callbacks
    "CanUseTool",
    "ToolPermissionContext",
    "PermissionResult",
    "PermissionResultAllow",
    "PermissionResultDeny",
    "PermissionUpdate",
    "HookCallback",
    "HookContext",
    "HookMatcher",
    # Agent support
    "AgentDefinition",
    "SettingSource",
    # MCP Server Support
    "create_sdk_mcp_server",
    "tool",
    "SdkMcpTool",
    # Errors
    "ClaudeSDKError",
    "CLIConnectionError",
    "CLINotFoundError",
    "ProcessError",
    "CLIJSONDecodeError",
]

logger.info("=" * 80)
logger.info("🔧 Claude Agent SDK - Fixed Version Loaded")
logger.info("=" * 80)
logger.info("✅ yoga.wasm resolution patch applied")
logger.info("✅ All SDK features available (file tools, Bash, MCP)")
logger.info("✅ Drop-in replacement for claude_agent_sdk")
logger.info("")
logger.info("Usage: from claude_agent_sdk_fixed import query, ClaudeAgentOptions")
logger.info("=" * 80)
