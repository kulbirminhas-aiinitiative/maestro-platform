# DDE and BDV Network Diagrams

## Your Understanding is Correct!

You're right - the **Contract** is the fundamental transaction unit. Each node represents:
- A **Contract** (agreement between personas)
- An **Action** (work performed by provider persona)
- **Deliverables** (outputs produced)

---

## 1. DDE Network (Performance Tracking)

DDE tracks **execution performance** at the contract level.

```
                         DDE NETWORK
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │   ┌─────────────────────────────────────────────┐   │
    │   │           AGENT REGISTRY                    │   │
    │   │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │   │
    │   │  │Agent A  │ │Agent B  │ │Agent C  │        │   │
    │   │  │(Analyst)│ │(Backend)│ │(QA)     │        │   │
    │   │  │WIP: 1/3 │ │WIP: 2/3 │ │WIP: 0/3 │        │   │
    │   │  │Score:92%│ │Score:95%│ │Score:88%│        │   │
    │   │  └────┬────┘ └────┬────┘ └────┬────┘        │   │
    │   └───────┼──────────┼──────────┼───────────────┘   │
    │           │          │          │                   │
    │           ▼          ▼          ▼                   │
    │   ┌─────────────────────────────────────────────┐   │
    │   │         PERFORMANCE TRACKER                 │   │
    │   │                                             │   │
    │   │  For each CONTRACT execution:               │   │
    │   │  ┌─────────────────────────────────────┐    │   │
    │   │  │ ExecutionMetric                     │    │   │
    │   │  │ ├── execution_id                    │    │   │
    │   │  │ ├── agent_id (who)                  │    │   │
    │   │  │ ├── task_type                       │    │   │
    │   │  │ ├── duration_seconds                │    │   │
    │   │  │ ├── quality_score (0.0-1.0)         │    │   │
    │   │  │ ├── contract_fulfilled (bool)       │    │   │
    │   │  │ ├── files_generated (count)         │    │   │
    │   │  │ └── error_count                     │    │   │
    │   │  └─────────────────────────────────────┘    │   │
    │   └─────────────────────────────────────────────┘   │
    │                        │                            │
    │                        ▼                            │
    │   ┌─────────────────────────────────────────────┐   │
    │   │              DDE SCORE                      │   │
    │   │  ┌────────────────────────────────────┐     │   │
    │   │  │ avg_quality_score: 0.92            │     │   │
    │   │  │ contract_fulfillment_rate: 1.0     │     │   │
    │   │  │ error_rate: 0.02                   │     │   │
    │   │  └────────────────────────────────────┘     │   │
    │   │            Weight: 35%                      │   │
    │   └─────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────┘
```

### DDE Node Structure:
```
┌────────────────────────────────────────┐
│            CONTRACT NODE               │
│  ┌──────────────────────────────────┐  │
│  │ Contract ID: contract_abc123     │  │
│  │ Provider: backend_developer      │  │
│  │ Consumer: qa_engineer            │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ EXECUTION METRICS (DDE)          │  │
│  │ • Duration: 194.85s              │  │
│  │ • Quality: 100%                  │  │
│  │ • Fulfilled: YES                 │  │
│  │ • Files: 6                       │  │
│  │ • Errors: 0                      │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
```

---

## 2. BDV Network (Behavior Validation)

BDV validates **contract fulfillment** through scenarios.

```
                         BDV NETWORK
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │  ┌────────────────────────────────────────────┐     │
    │  │         CONTRACT (Input)                   │     │
    │  │  ┌────────────────────────────────────┐    │     │
    │  │  │ id: contract_abc123                │    │     │
    │  │  │ name: Backend Developer Contract   │    │     │
    │  │  │ acceptance_criteria:               │    │     │
    │  │  │   - "API returns valid response"   │    │     │
    │  │  │   - "Auth validates token"         │    │     │
    │  │  │ deliverables:                      │    │     │
    │  │  │   - main.py                        │    │     │
    │  │  │   - tests/test_api.py              │    │     │
    │  │  └────────────────────────────────────┘    │     │
    │  └─────────────────────┬──────────────────────┘     │
    │                        │                            │
    │                        ▼                            │
    │  ┌────────────────────────────────────────────┐     │
    │  │       FEATURE GENERATOR                    │     │
    │  │  Converts contract → Gherkin              │     │
    │  └─────────────────────┬──────────────────────┘     │
    │                        │                            │
    │                        ▼                            │
    │  ┌────────────────────────────────────────────┐     │
    │  │       GENERATED SCENARIOS                  │     │
    │  │  ┌────────────────────────────────────┐    │     │
    │  │  │ @criterion_1                       │    │     │
    │  │  │ Scenario: Acceptance Criterion 1   │    │     │
    │  │  │   Given system is in initial state │    │     │
    │  │  │   When the criterion is evaluated  │    │     │
    │  │  │   Then it should satisfy: "API..." │    │     │
    │  │  └────────────────────────────────────┘    │     │
    │  │  ┌────────────────────────────────────┐    │     │
    │  │  │ @deliverable                       │    │     │
    │  │  │ Scenario: Deliverable - main.py    │    │     │
    │  │  │   Given execution is complete      │    │     │
    │  │  │   When I check for "main.py"       │    │     │
    │  │  │   Then deliverable should exist    │    │     │
    │  │  └────────────────────────────────────┘    │     │
    │  └─────────────────────┬──────────────────────┘     │
    │                        │                            │
    │                        ▼                            │
    │  ┌────────────────────────────────────────────┐     │
    │  │           PYTEST-BDD RUNNER                │     │
    │  │  Executes scenarios with step definitions  │     │
    │  └─────────────────────┬──────────────────────┘     │
    │                        │                            │
    │                        ▼                            │
    │  ┌────────────────────────────────────────────┐     │
    │  │              BDV SCORE                     │     │
    │  │  ┌────────────────────────────────────┐    │     │
    │  │  │ total_contracts: 5                 │    │     │
    │  │  │ contracts_fulfilled: 5             │    │     │
    │  │  │ scenarios_passed: 62               │    │     │
    │  │  │ scenarios_failed: 0                │    │     │
    │  │  │ pass_rate: 100%                    │    │     │
    │  │  └────────────────────────────────────┘    │     │
    │  │            Weight: 35%                     │     │
    │  └────────────────────────────────────────────┘     │
    └─────────────────────────────────────────────────────┘
```

### BDV Node Structure:
```
┌────────────────────────────────────────┐
│            CONTRACT NODE               │
│  ┌──────────────────────────────────┐  │
│  │ Contract ID: contract_abc123     │  │
│  │ acceptance_criteria: [2 items]   │  │
│  │ deliverables: [2 files]          │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │ BDV SCENARIOS (Generated)        │  │
│  │ • Criterion 1: PASSED            │  │
│  │ • Criterion 2: PASSED            │  │
│  │ • Deliverable main.py: PASSED    │  │
│  │ • Deliverable test_api.py: PASSED│  │
│  └──────────────────────────────────┘  │
│                                        │
│  CONTRACT FULFILLED: YES (4/4)         │
└────────────────────────────────────────┘
```

---

## 3. OVERLAPPED NETWORK (DDE + BDV Together)

This shows how both systems attach to the **same contract node**:

```
                    TRIMODAL NETWORK VIEW
                    (DDE + BDV Overlapped)

    ┌─────────────────────────────────────────────────────────────────┐
    │                      EXECUTION FLOW                             │
    │                                                                 │
    │    REQUIREMENT                                                  │
    │         │                                                       │
    │         ▼                                                       │
    │    ┌─────────┐      ┌─────────┐      ┌─────────┐      ┌─────┐  │
    │    │Contract │ ──▶  │Contract │ ──▶  │Contract │ ──▶  │ ... │  │
    │    │   1     │      │   2     │      │   3     │      │     │  │
    │    └────┬────┘      └────┬────┘      └────┬────┘      └──┬──┘  │
    │         │                │                │               │     │
    └─────────┼────────────────┼────────────────┼───────────────┼─────┘
              │                │                │               │
              ▼                ▼                ▼               ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │         ╔═══════════════════════════════════════╗               │
    │         ║      CONTRACT NODE (Expanded)         ║               │
    │         ╠═══════════════════════════════════════╣               │
    │         ║                                       ║               │
    │         ║  ┌─────────────────────────────────┐  ║               │
    │         ║  │      CONTRACT DEFINITION        │  ║               │
    │         ║  │  • id: contract_xyz789          │  ║               │
    │         ║  │  • provider: backend_developer  │  ║               │
    │         ║  │  • consumer: qa_engineer        │  ║               │
    │         ║  │  • acceptance_criteria: [...]   │  ║               │
    │         ║  │  • deliverables: [...]          │  ║               │
    │         ║  └─────────────────────────────────┘  ║               │
    │         ║                  │                    ║               │
    │         ║     ┌────────────┴────────────┐      ║               │
    │         ║     │                         │      ║               │
    │         ║     ▼                         ▼      ║               │
    │         ║  ┌──────────┐           ┌──────────┐ ║               │
    │         ║  │   DDE    │           │   BDV    │ ║               │
    │         ║  │ TRACKING │           │VALIDATION│ ║               │
    │         ║  ├──────────┤           ├──────────┤ ║               │
    │         ║  │Duration  │           │Scenarios │ ║               │
    │         ║  │Quality   │           │ Generated│ ║               │
    │         ║  │Files     │           │ from     │ ║               │
    │         ║  │Errors    │           │ criteria │ ║               │
    │         ║  │Fulfilled │           │ and      │ ║               │
    │         ║  │          │           │ deliver- │ ║               │
    │         ║  │          │           │ ables    │ ║               │
    │         ║  └────┬─────┘           └────┬─────┘ ║               │
    │         ║       │                      │       ║               │
    │         ╚═══════╪══════════════════════╪═══════╝               │
    │                 │                      │                        │
    │                 ▼                      ▼                        │
    │         ┌───────────────────────────────────────┐               │
    │         │         VERDICT AGGREGATOR            │               │
    │         │  ┌─────────────────────────────────┐  │               │
    │         │  │ DDE Score: 0.97 (35% weight)    │  │               │
    │         │  │ BDV Score: 1.00 (35% weight)    │  │               │
    │         │  │ ACC Score: 1.00 (30% weight)    │  │               │
    │         │  │ ─────────────────────────────── │  │               │
    │         │  │ OVERALL:  0.99  Grade: A+       │  │               │
    │         │  │ DECISION: APPROVED              │  │               │
    │         │  └─────────────────────────────────┘  │               │
    │         └───────────────────────────────────────┘               │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘
```

---

## 4. TRANSACTION UNIT: The Contract

Your assumption is **CORRECT**. The lowest-level transaction is the **Contract**:

```
┌────────────────────────────────────────────────────────────────┐
│                    TRANSACTION UNIT                            │
│                                                                │
│   ┌──────────────────────────────────────────────────────┐     │
│   │                   CONTRACT                           │     │
│   │                                                      │     │
│   │   WHO:     Provider Persona → Consumer Persona       │     │
│   │                                                      │     │
│   │   WHAT:    deliverables: ["api.py", "tests.py"]     │     │
│   │                                                      │     │
│   │   ACCEPT:  acceptance_criteria: [                    │     │
│   │              "API responds with 200",                │     │
│   │              "Tests pass"                            │     │
│   │            ]                                         │     │
│   └──────────────────────────────────────────────────────┘     │
│                          │                                     │
│              ┌───────────┴───────────┐                         │
│              │                       │                         │
│              ▼                       ▼                         │
│   ┌────────────────────┐  ┌────────────────────┐               │
│   │   DDE MONITORS     │  │   BDV VALIDATES    │               │
│   ├────────────────────┤  ├────────────────────┤               │
│   │ • Execution time   │  │ • Each criterion   │               │
│   │ • Quality score    │  │   → 1 scenario     │               │
│   │ • Files produced   │  │ • Each deliverable │               │
│   │ • Errors caught    │  │   → 1 scenario     │               │
│   │ • Fulfillment      │  │ • Pass/Fail for    │               │
│   │   status           │  │   each             │               │
│   └────────────────────┘  └────────────────────┘               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. Full Execution Network Example

```
SESSION: sdlc_abc123

    ┌─────────────────────────────────────────────────────────────┐
    │  REQUIREMENT: "Create REST API with auth and health check"  │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
    ╔═════════════════════════════════════════════════════════════╗
    ║                    CONTRACT CHAIN                           ║
    ╠═════════════════════════════════════════════════════════════╣
    ║                                                             ║
    ║  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     ║
    ║  │ CONTRACT 1  │───▶│ CONTRACT 2  │───▶│ CONTRACT 3  │     ║
    ║  │             │    │             │    │             │     ║
    ║  │ Provider:   │    │ Provider:   │    │ Provider:   │     ║
    ║  │ Req Analyst │    │ Backend Dev │    │ QA Engineer │     ║
    ║  │             │    │             │    │             │     ║
    ║  │ Deliverable:│    │ Deliverable:│    │ Deliverable:│     ║
    ║  │ - PRD.md    │    │ - app.py    │    │ - tests.py  │     ║
    ║  │ - specs.md  │    │ - routes.py │    │ - report.md │     ║
    ║  │             │    │ - models.py │    │             │     ║
    ║  │ DDE:        │    │ DDE:        │    │ DDE:        │     ║
    ║  │  Time: 46s  │    │  Time: 152s │    │  Time: 506s │     ║
    ║  │  Quality:92%│    │  Quality:100│    │  Quality:100│     ║
    ║  │             │    │             │    │             │     ║
    ║  │ BDV:        │    │ BDV:        │    │ BDV:        │     ║
    ║  │  3 scenarios│    │  5 scenarios│    │  4 scenarios│     ║
    ║  │  3 passed   │    │  5 passed   │    │  4 passed   │     ║
    ║  └─────────────┘    └─────────────┘    └─────────────┘     ║
    ║         │                  │                  │             ║
    ╚═════════╪══════════════════╪══════════════════╪═════════════╝
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   VERDICT AGGREGATOR   │
                    │                        │
                    │  DDE: 0.97 (35%)       │
                    │  BDV: 1.00 (35%)       │
                    │  ACC: 1.00 (30%)       │
                    │  ──────────────────    │
                    │  TOTAL: 0.99           │
                    │  GRADE: A+             │
                    │  DECISION: APPROVED    │
                    └────────────────────────┘
```

---

## Summary

| Component | What It Tracks | At What Level | Metrics |
|-----------|---------------|---------------|---------|
| **DDE** | Execution Performance | Per Contract | Duration, Quality, Files, Errors |
| **BDV** | Contract Fulfillment | Per Acceptance Criterion + Deliverable | Pass/Fail, Scenarios |
| **ACC** | Code Architecture | Per Project | Conformance, Violations, Cycles |

**Transaction Hierarchy:**
```
Session (SDLC run)
  └── Contract (DDE + BDV attach here)
        ├── Action (persona executes work)
        ├── Deliverables (files produced)
        └── Acceptance Criteria (validation rules)
              └── BDV Scenarios (test cases)
```

Your understanding is correct: **The Contract is the atomic transaction unit** where both DDE and BDV monitor and validate.
