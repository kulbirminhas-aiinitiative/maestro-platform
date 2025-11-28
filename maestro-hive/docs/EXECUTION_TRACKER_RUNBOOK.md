# Execution Tracker Runbook

- Phase 0: Done except defaulting hive to Gateway.
- Action now: switch default path to Gateway; keep Claude path behind feature flag.
- Validation: run gateway e2e against OpenAI and Gemini using EP_* keys in execution-platform/.env.
- Next: CI job using Poetry to run execution-platform tests.
