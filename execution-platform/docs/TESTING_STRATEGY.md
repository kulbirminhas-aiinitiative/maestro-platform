Testing Strategy

- L0 API contract: structure, errors, SSE; mocked adapters
- L1 Capability: tool call conformance, JSON mode, usage; temp=0
- L2 Statistical quality: semantic similarity across runs/providers (nightly)
- L3 E2E personas: deliverable structure, contract fulfillment
- L4 Chaos: failure injection, fallback, circuit breakers (staging)
- CI: L0/L1 per PR; L2/L3 nightly; L4 weekly
