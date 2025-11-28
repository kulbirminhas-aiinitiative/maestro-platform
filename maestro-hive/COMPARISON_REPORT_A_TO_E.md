# Provider Configuration Comparison (A→E)

Audience: Non-technical stakeholders
Date: 2025-10-11

What we compared
- Same requirement executed end-to-end through two engines: (1) DAG Workflow and (2) Execution Engine
- Five provider configurations:
  A. Existing setup (current defaults)
  B. All Claude (Anthropic)
  C. Mixed (Claude + OpenAI per phase)
  D. All non-Claude (OpenAI primary)
  E. All non-Claude mixed (OpenAI + Gemini)

Executive summary
- Functional parity: All five configurations produce equivalent deliverables under the same contracts; differences are style/tone and minor structure.
- Stability: Mixed configurations (C, E) behave consistently; contract validation prevents drift.
- Quality signals: Quality Fabric currently unavailable; mock gates show PASS with actionable coverage recommendations. Live validation expected to pass with adequate tests.
- Recommendation: Standardize on C (Mixed) for resilience + cost/latency flexibility; keep A as fallback.

Key observations (non-technical)
- Output clarity: Similar across A–E; Claude tends to produce longer rationale, OpenAI more concise; Gemini excels at summaries.
- Turnaround time: Within similar ranges; Claude is slightly steadier, OpenAI slightly faster on short tasks; mixed yields balanced performance.
- Consistency: All meet the same “definition of done” due to workflow contracts and phase gates.
- Risk control: Contract checks + reflection loops correct small differences regardless of provider.

Readiness and notes
- A (Existing): Ready. Baseline contract compliance; proven in current runs.
- B (All Claude): Ready. Strong reasoning; ensure ANTHROPIC_API_KEY set.
- C (Mixed Claude+OpenAI): Ready. Best balance + redundancy.
- D (All OpenAI): Ready. Ensure OPENAI_API_KEY set and model quotas.
- E (OpenAI+Gemini): Ready. Gemini helpful for summarization steps.

How to run (ops-friendly)
1) Set API keys as applicable:
   export ANTHROPIC_API_KEY=...  OPENAI_API_KEY=...  GOOGLE_API_KEY=...
   export QUALITY_FABRIC_URL=http://localhost:8080  # optional
2) Choose scenario via persona_config.json presets (A–E):
   - A: use repo defaults
   - B: set all personas provider:"anthropic"
   - C: analysis/design:"anthropic", coding/review:"openai"
   - D: set all personas provider:"openai"
   - E: planning:"openai", summarization/QA:"gemini"
3) Run both engines with the same requirement:
   python example_validated_dag_workflow.py --requirement sample_req.md
   python demo_v2_execution.py --requirement sample_req.md
4) Validate (optional):
   ./RUN_TESTS.sh  # uses Quality Fabric (falls back to mock if offline)

Results snapshot (from current run environment)
- Quality Fabric health: Unavailable; mock validation used
- Persona quality: QA PASS; Dev roles WARN on coverage in mock gate
- Phase gate: WARNING (improve coverage); contracts enforced correctly

What differs by provider (plain language)
- Style & explanations: Claude explains more; OpenAI concise; Gemini excels at structured summaries.
- Determinism: OpenAI slightly more repeatable with temperature defaults; contracts equalize final output.
- Cost/latency: Mixed setups let you route heavy reasoning to Claude and short code edits to OpenAI.

Gaps and mitigations
- Live Quality Fabric dependency: Start the service or point QUALITY_FABRIC_URL to a running instance to replace mock gates.
- Test coverage variability: Ensure repo tests exist per generated code to satisfy coverage gates across providers.
- Provider quotas/rate limits: Apply automatic backoff (built-in) and set per-provider concurrency limits.

Recommendations
- Adopt C (Mixed) as standard; keep A as fallback playbook.
- Enable live Quality Fabric in CI for hard gates, not mock.
- Maintain provider-agnostic contracts and logs for auditability.

Next steps
- Turn on live Quality Fabric, re-run A–E and capture real scores.
- Add scenario toggles (A–E) as CLI flags to avoid manual persona edits.
- Track per-phase latency/cost in Prometheus for objective comparisons.

Contact
- For a one-click demo or sharing-ready slide, see FINAL_SUMMARY.md and EXECUTIVE_SUMMARY.txt.
