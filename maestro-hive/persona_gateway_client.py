from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from config import CLAUDE_CONFIG  # type: ignore

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8080")
CONFIG_PATH = Path(__file__).with_name("persona_config.json")

class PersonaGatewayClient:
    def __init__(self, base_url: Optional[str] = None, config_path: Optional[str] = None) -> None:
        self.base_url = (base_url or GATEWAY_URL).rstrip('/')
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self._cfg = self._load_config()
        self._gw = self._get_gateway_client()

    def _load_config(self) -> dict[str, Any]:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {"default": {"provider": "auto", "tools": [], "fallback": ["claude_agent_sdk", "openai", "anthropic", "mock"]}}

    def _get_gateway_client(self):
        try:
            from execution_platform.client import GatewayClient  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("execution-platform client not available; install or add to PYTHONPATH") from e
        return GatewayClient(self.base_url)

    def persona_cfg(self, persona_id: str) -> dict[str, Any]:
        return self._cfg.get(persona_id, self._cfg.get("default", {}))

    def _provider_chain(self, persona_id: str) -> list[str]:
        cfg = self.persona_cfg(persona_id)
        chain = [cfg.get("provider", "auto")] + cfg.get("fallback", [])
        # If Anthropic key missing, ensure claude_agent_sdk is preferred
        if not os.environ.get("ANTHROPIC_API_KEY") and "claude_agent_sdk" not in chain:
            chain = ["claude_agent_sdk"] + chain
        # de-dup while preserving order
        seen = set()
        out = []
        for p in chain:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    async def _stream_via_claude_agent_sdk(self, messages: list[dict]) -> AsyncIterator[dict]:
        # Build a simple prompt from messages
        sys_parts = [m["content"] for m in messages if m.get("role") == "system"]
        user_parts = [m["content"] for m in messages if m.get("role") in ("user", "tool")]  # include tool outputs
        system_prompt = "\n\n".join(sys_parts) if sys_parts else None
        prompt = "\n\n".join(user_parts) if user_parts else (messages[-1]["content"] if messages else "")

        try:
            from claude_code_sdk import ClaudeCodeOptions, query  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("claude_code_sdk not available; install CLI or add module") from e

        opts = ClaudeCodeOptions(
            model=CLAUDE_CONFIG.get("model", "claude-sonnet-4-20250514"),
            system_prompt=system_prompt,
            permission_mode=CLAUDE_CONFIG.get("permission_mode", "acceptEdits"),
            timeout=int(CLAUDE_CONFIG.get("timeout", 600000) / 1000),
        )

        async for msg in query(prompt, opts):
            if msg.message_type == "text" and msg.content:
                yield {"event": "token", "data": {"text": msg.content, "provider": "claude_agent_sdk"}}
            elif msg.message_type == "done":
                yield {"event": "done", "data": {"provider": "claude_agent_sdk", **(msg.metadata or {})}}
                return
            elif msg.message_type == "error":
                raise RuntimeError(msg.content)

        # Ensure a done event if the generator ended without explicit done
        yield {"event": "done", "data": {"provider": "claude_agent_sdk"}}

    async def stream_chat(self, persona_id: str, messages: list[dict], *, response_format: dict | None = None) -> AsyncIterator[dict]:
        cfg = self.persona_cfg(persona_id)
        tools = [{"name": t, "json_schema": {"type": "object", "properties": {}}} for t in cfg.get("tools", [])]
        requires = cfg.get("requires")
        last_exc: Exception | None = None
        for provider in self._provider_chain(persona_id):
            try:
                if provider == "claude_agent_sdk":
                    async for ev in self._stream_via_claude_agent_sdk(messages):
                        yield ev
                    return
                async for ev in self._gw.stream_chat(messages, provider=provider, persona_id=persona_id, tools=tools, response_format=response_format, requires=requires):
                    yield ev
                return
            except Exception as e:  # pragma: no cover
                last_exc = e
                continue
        if last_exc:
            raise last_exc

    async def invoke_tool(self, name: str, args: dict) -> dict:
        return await self._gw.invoke_tool(name, args)

    async def embeddings(self, inputs: list[str]) -> list[list[float]]:
        return await self._gw.embeddings(inputs)
