# Testing Strategy

L0: API Contract (deterministic)
- Validate request/response/stream shapes; mock HTTP; schema checks.

L1: Capability (semi-deterministic)
- Tools, JSON mode, token counting; temp=0; provider emulators where possible.

L2: Quality (statistical)
- N=10 runs; semantic similarity thresholds; drift detection.

L3: Integration (E2E)
- Orchestrators via Gateway; deliverable structure assertions; provider variance allowed.

L4: Chaos
- Failure injection; fallback/circuit breakers; no data loss.

CI: L0/L1 gates; L2/L3 nightly; L4 staging.
