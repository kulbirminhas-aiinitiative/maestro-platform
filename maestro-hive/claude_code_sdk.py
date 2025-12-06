#!/usr/bin/env python3
"""
Claude Code SDK - Python Wrapper for @anthropic-ai/claude-code CLI

This module provides a Python interface to the Claude Code CLI tool,
enabling AI-powered code generation via subprocess calls.

Usage:
    from claude_code_sdk import query, ClaudeCodeOptions

    async for message in query("Create a hello world app", ClaudeCodeOptions()):
        print(message.content)
"""

import asyncio
import subprocess
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Find the claude CLI
CLAUDE_CLI_PATH = None
for path in [
    "/home/ec2-user/.nvm/versions/node/v22.19.0/lib/node_modules/@anthropic-ai/claude-code/cli.js",
    "/usr/local/lib/node_modules/@anthropic-ai/claude-code/cli.js",
    "/usr/lib/node_modules/@anthropic-ai/claude-code/cli.js",
]:
    if os.path.exists(path):
        CLAUDE_CLI_PATH = path
        break

if not CLAUDE_CLI_PATH:
    logger.warning("Claude Code CLI not found in standard locations")


@dataclass
class ClaudeCodeOptions:
    """Options for Claude Code execution"""
    model: str = "claude-sonnet-4-20250514"
    system_prompt: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    cwd: Optional[str] = None
    permission_mode: str = "acceptEdits"  # Auto-accept file edits
    continue_conversation: bool = False
    allowed_tools: List[str] = field(default_factory=lambda: ["read", "write", "bash", "glob", "grep"])
    timeout: int = 600


@dataclass
class ClaudeMessage:
    """Message returned from Claude"""
    message_type: str  # 'text', 'file_created', 'done', 'error'
    content: str
    role: str = "assistant"
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


async def query(
    prompt: str,
    options: Optional[ClaudeCodeOptions] = None
) -> AsyncGenerator[ClaudeMessage, None]:
    """
    Execute Claude Code CLI and stream results.

    Args:
        prompt: The prompt/requirement to send to Claude
        options: Configuration options

    Yields:
        ClaudeMessage objects containing responses and file operations
    """
    if options is None:
        options = ClaudeCodeOptions()

    if not CLAUDE_CLI_PATH:
        logger.error("Claude CLI not found - cannot execute")
        yield ClaudeMessage(
            message_type="error",
            content="Claude Code CLI not installed or not found",
            role="system"
        )
        return

    # Create working directory
    work_dir = Path(options.cwd) if options.cwd else Path.cwd()
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Build command for non-interactive mode
        cmd = [
            "node",
            CLAUDE_CLI_PATH,
            "--print",  # Non-interactive mode
            "--verbose",  # Required for stream-json output format
            "--output-format", "stream-json",  # Structured output
            "--permission-mode", options.permission_mode,  # Auto-accept edits
        ]

        # Add allowed tools
        if options.allowed_tools:
            cmd.extend(["--allowed-tools", " ".join(options.allowed_tools)])

        # Add model
        if options.model:
            cmd.extend(["--model", options.model])

        # Add system prompt if provided
        if options.system_prompt:
            cmd.extend(["--append-system-prompt", options.system_prompt])

        # Add the prompt as the final argument
        cmd.append(prompt)

        # Set up environment
        env = os.environ.copy()

        logger.info(f"🤖 Executing Claude Code CLI in {work_dir}")
        logger.debug(f"Command: {' '.join(cmd[:2])} [prompt]")

        # Track files before execution
        files_before = set(work_dir.rglob("*")) if work_dir.exists() else set()

        # Execute Claude CLI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(work_dir),
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Read and parse JSON stream output
        accumulated_output = []

        if process.stdout:
            async for line in process.stdout:
                line_text = line.decode('utf-8', errors='ignore').strip()
                if not line_text:
                    continue

                try:
                    # Parse JSON line
                    data = json.loads(line_text)

                    # Handle different message types from Claude CLI
                    if isinstance(data, dict):
                        msg_type = data.get('type', 'unknown')

                        if msg_type == 'text':
                            # Text content from assistant
                            content = data.get('text', '')
                            accumulated_output.append(content)
                            yield ClaudeMessage(
                                message_type="text",
                                content=content,
                                role="assistant"
                            )

                        elif msg_type == 'assistant':
                            # Assistant message with content array
                            message = data.get('message', {})
                            content_items = message.get('content', [])
                            for item in content_items:
                                if item.get('type') == 'text':
                                    content = item.get('text', '')
                                    if content:
                                        accumulated_output.append(content)
                                        yield ClaudeMessage(
                                            message_type="text",
                                            content=content,
                                            role="assistant"
                                        )

                        elif msg_type == 'result':
                            # Final result - content is in 'result' field
                            content = data.get('result', '') or data.get('text', '')
                            if content:
                                accumulated_output.append(content)
                                yield ClaudeMessage(
                                    message_type="text",
                                    content=content,
                                    role="assistant"
                                )

                except json.JSONDecodeError:
                    # Not JSON, treat as plain text
                    accumulated_output.append(line_text)
                    yield ClaudeMessage(
                        message_type="text",
                        content=line_text,
                        role="assistant"
                    )

        # Wait for completion
        await process.wait()

        # Check for new files
        files_after = set(work_dir.rglob("*")) if work_dir.exists() else set()
        new_files = files_after - files_before

        # Yield file creation messages
        for file_path in new_files:
            if file_path.is_file():
                yield ClaudeMessage(
                    message_type="file_created",
                    content=f"Created: {file_path.relative_to(work_dir)}",
                    role="system",
                    file_path=str(file_path)
                )

        # Yield completion
        full_output = "\n".join(accumulated_output)
        yield ClaudeMessage(
            message_type="done",
            content=full_output,
            role="assistant",
            metadata={
                "exit_code": process.returncode,
                "files_created": len(new_files),
                "working_directory": str(work_dir)
            }
        )

        if process.returncode != 0:
            stderr = await process.stderr.read() if process.stderr else b""
            error_msg = stderr.decode('utf-8', errors='ignore')
            logger.error(f"Claude CLI failed with exit code {process.returncode}: {error_msg}")
            yield ClaudeMessage(
                message_type="error",
                content=f"Process exited with code {process.returncode}: {error_msg}",
                role="system"
            )

    except asyncio.TimeoutError:
        logger.error(f"Claude CLI execution timed out after {options.timeout}s")
        yield ClaudeMessage(
            message_type="error",
            content=f"Execution timed out after {options.timeout} seconds",
            role="system"
        )

    except Exception as e:
        logger.error(f"Error executing Claude CLI: {e}", exc_info=True)
        yield ClaudeMessage(
            message_type="error",
            content=f"Execution error: {str(e)}",
            role="system"
        )


async def query_simple(
    prompt: str,
    options: Optional[ClaudeCodeOptions] = None
) -> str:
    """
    Simplified query that returns complete response as string.

    Args:
        prompt: The prompt to send to Claude
        options: Configuration options

    Returns:
        Complete response text
    """
    response_text = ""
    async for message in query(prompt, options):
        if message.message_type == "text":
            response_text += message.content + "\n"
    return response_text.strip()


# For backward compatibility
def sync_query(prompt: str, options: Optional[ClaudeCodeOptions] = None) -> str:
    """
    Synchronous wrapper for query_simple.

    Note: This is less efficient than async, use async version when possible.
    """
    return asyncio.run(query_simple(prompt, options))


if __name__ == "__main__":
    # Simple test
    async def test():
        print("Testing Claude Code SDK...")
        print("=" * 80)

        if not CLAUDE_CLI_PATH:
            print("❌ Claude CLI not found!")
            print("Install with: npm install -g @anthropic-ai/claude-code")
            return

        print(f"✅ Claude CLI found: {CLAUDE_CLI_PATH}")
        print()

        options = ClaudeCodeOptions(
            system_prompt="You are a helpful coding assistant.",
            cwd=tempfile.mkdtemp()
        )

        print(f"Working directory: {options.cwd}")
        print()
        print("Prompt: 'Create a simple hello.py file that prints Hello, World!'")
        print("-" * 80)

        file_count = 0
        async for msg in query("Create a simple hello.py file that prints 'Hello, World!'", options):
            if msg.message_type == "text":
                print(f"💬 {msg.content}")
            elif msg.message_type == "file_created":
                file_count += 1
                print(f"📄 {msg.content}")
            elif msg.message_type == "done":
                print(f"\n✅ Done! Exit code: {msg.metadata.get('exit_code', 'N/A')}")
                print(f"📦 Files created: {msg.metadata.get('files_created', 0)}")
            elif msg.message_type == "error":
                print(f"❌ Error: {msg.content}")

        print("=" * 80)

    asyncio.run(test())
