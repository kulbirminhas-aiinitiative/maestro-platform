#!/usr/bin/env python3
"""
Quick test to verify Claude SDK is working
"""
import asyncio
from claude_code_sdk import query, ClaudeCodeOptions

async def main():
    print("Testing Claude SDK...")
    print("=" * 80)

    options = ClaudeCodeOptions(
        system_prompt="You are a helpful assistant. Be concise.",
        model="claude-sonnet-4-20250514"
    )

    prompt = "Say 'Hello from Claude SDK!' and nothing else."

    print(f"\nPrompt: {prompt}\n")
    print("Response:")
    print("-" * 80)

    async for message in query(prompt=prompt, options=options):
        print(f"Message type: {type(message).__name__}")
        if hasattr(message, 'content'):
            print(f"Content: {message.content}")
        print()

    print("=" * 80)
    print("✅ Claude SDK test complete!")

if __name__ == "__main__":
    asyncio.run(main())
