Status
- Adapters: 3 (claude_agent, openai, gemini) wired via router
- SPI: implemented with async streaming
- Docs: master, plan, tool spec, tracker stub, capabilities/persona policy
- Tests: router selection, SPI shape

Next Steps
1) Implement real tool-calling adapters (Tier 1) for OpenAI
2) Add error types and retries; rate limit backoff
3) Migrate one simple persona from hive to use router
4) Add Anthropic SDK adapter (optional) and deprecate CLI path
5) Integration tests across providers
