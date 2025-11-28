Execution Platform (Provider-Agnostic)

- Master doc: docs/MASTER_EXECUTION_DOCUMENT.md
- Status: docs/COMPREHENSIVE_STATUS_AND_NEXT_STEPS.md
- Tracker: docs/EXECUTION_TRACKER.md
- SPI: src/execution_platform/spi.py
- Capabilities: docs/capabilities.yaml
- Persona routing: docs/persona_policy.yaml

Quick start
1) Ensure Python 3.10+ and Poetry installed
2) cd execution-platform && poetry install --no-root
3) Run validation: ./scripts/run_validation.sh
4) Configure env: copy .env.example to .env and export variables before runtime
