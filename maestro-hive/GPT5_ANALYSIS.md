# Team Execution V2 Split Mode: Critical Review and Validation Plan

Date: 2025-10-11
Author: System Analysis (GPT-5)

---

## Executive Summary

This document reviews the current team_execution_v2_split_mode implementation and adjacent systems to assess whether phases pass both full context and explicit instructions to subsequent agents (AutoGen-style), why recent runs failed to generate a usable frontend, and how to reliably enforce workflow contracts across SDLC phases.

Key findings:
- AutoGen-style context+instruction passing is supported conceptually and documented (see AUTOGEN_CONTEXT_SHARING_ANALYSIS.md), but not fully implemented in split-mode runtime. The current handoff is a short, lossy text assembled from previous outputs, not a structured, enforceable instruction set.
- Frontend not generated: Due to insufficient/ambiguous instructions to the frontend persona, minimal context (no explicit artifact paths or mock endpoints), and fallback execution that doesn’t honor nested directory deliverable patterns, resulting in no real frontend scaffold.
- Workflow leakage: Phase boundary validation does not require a structured “next-phase handoff” that includes concrete artifacts and acceptance criteria, so the process can progress without the next phase receiving actionable instructions.

---

## Scope Reviewed
- team_execution_v2_split_mode.py (phase orchestrator and checkpoints)
- team_execution_v2.py (AI-driven engine, blueprint selection, contract design)
- parallel_coordinator_v2.py (parallel persona orchestration and mocks)
- persona_executor_v2.py (persona prompts, mock generation, fallback execution)
- team_execution_context.py (checkpoint model and persistence)
- session_manager.py (session context builder)
- AUTOGEN_CONTEXT_SHARING_ANALYSIS.md (design doc for conversation-based sharing)

---

## Findings

### 1) AutoGen capability: passing context and instructions
- Confirmed capability: AutoGen natively supports shared conversation history and explicit next-step instruction passing. Your repo’s AUTOGEN_CONTEXT_SHARING_ANALYSIS.md outlines how to replicate this with a ConversationHistory and GroupChat pattern without the library.
- Current implementation gaps:
  - Split-mode uses `_extract_phase_requirement()` to compose a short text from prior outputs (truncated JSON). This is not a structured handoff (no explicit artifact paths, no acceptance criteria).
  - Personas do not receive a persisted shared conversation/history; prompts are built from the persona’s contract plus a small context dict that currently lacks artifact paths and mock endpoints.
  - Result: Downstream phases/agents lack the precise, enforceable instructions needed to consistently produce expected deliverables.

### 2) Why the frontend was not generated
- Insufficient instruction in contracts:
  - The frontend contract references a glob deliverable like `frontend/src/components/**/*.tsx` but does not mandate a scaffold (package.json, Vite config, main.tsx, App.tsx). Without explicit scaffolding deliverables, personas (or fallback) create minimal or misplaced files.
- Inadequate context to the frontend persona:
  - Even when backend creates an OpenAPI spec and mock server under `./contracts` with endpoint `http://localhost:3001`, this information isn’t injected into the persona’s prompt with concrete file paths and usage instructions.
- Agents not loading context from .json:
  - While checkpoints capture rich workflow/team state, personas do not load a phase-specific handoff JSON to guide work.
- Fallback execution behavior:
  - When the Claude SDK is unavailable, fallback creates files by flattening artifact patterns into names under a persona directory. Nested/wildcard patterns don’t map to a real frontend tree, so no usable frontend project appears.

### 3) Phase workflow contracts and leakage
- What works:
  - Phased execution, checkpoints, optional contract validation (if available), and mock generation are in place.
- Where leakage occurs:
  - No synthesized “handoff contract” that the next phase must consume. Boundary validation doesn’t require it. As a result, the next phase proceeds without actionable instructions or artifact pointers.

---

## Validation Plan (to run when executing a sample requirement)

Sample requirement:
“Build a small CRUD web app with a React frontend and a Node/Express backend. The backend should expose REST endpoints for /api/items. The frontend should list items and allow creating new items.”

Steps:
1) Run split-mode batch execution with checkpoints:
   - Command: `python team_execution_v2_split_mode.py --batch --requirement "<sample requirement>" --create-checkpoints`
2) Inspect generated artifacts:
   - Contracts and mock artifacts under `./generated_project/contracts/`:
     - OpenAPI spec (e.g., `*_spec.yaml`)
     - Mock server file (`*_mock_server.js`)
     - README with mock usage
   - Frontend output:
     - With current code, expect no usable `./frontend/` scaffold. At best, placeholder files in persona-specific directories.
3) Inspect checkpoints under `./checkpoints/`:
   - Verify they include workflow and team state but no structured next-phase handoff instructions.
4) Review quality and phase results in logs:
   - Confirm that metrics may report success without end-to-end usable frontend deliverables.

Expected outcome (current state):
- Backend artifacts (mock/spec) are present.
- Frontend scaffold is missing or incomplete.
- Checkpoints lack a structured handoff JSON.

These observations validate the assumptions: insufficient instruction and context for the frontend and lack of enforceable handoffs.

---

## Recommendations (minimal, high-impact)

1) Create a structured “handoff contract” per phase and persist it:
- After each phase, synthesize a JSON object containing:
  - `phase_from`, `phase_to`
  - `instructions`: concrete tasks for the next phase (e.g., scaffold frontend with Vite, set base API URL, use OpenAPI file at path X, implement specific components)
  - `artifacts_from_previous_phase`: resolved paths (OpenAPI spec, mock server file, mock endpoint)
  - `acceptance_criteria_for_next_phase`: targeted for the next persona(s)
- Save into context and as a file: `./checkpoints/{workflow_id}_{phase}_handoff.json`.

2) Enrich persona-level execution context:
- In the coordinator, pass the handoff JSON and artifact paths in the `context` dict to PersonaExecutorV2. Include the mock endpoint and spec path so prompts are actionable.

3) Strengthen frontend contract deliverables:
- Add explicit scaffold files to frontend deliverables:
  - `frontend/package.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/ItemsList.tsx`, `frontend/src/components/ItemCreateForm.tsx`.
- Define acceptance criteria referencing the mock endpoint and spec path.

4) Improve fallback execution:
- When patterns include directories/wildcards, create representative files in correct subdirectories to yield a recognizable project structure.

5) Enhance boundary validation to require handoff presence:
- In phase boundary validation, fail fast if a complete handoff JSON is missing for the next phase. This prevents leakage by enforcing the workflow contract.

---

## Success Criteria
- Presence of `./frontend/` with a minimal running scaffold (Vite/React) and component stubs.
- Persona prompts include concrete artifact paths (e.g., `./generated_project/contracts/api_spec.yaml`) and mock endpoints.
- Checkpoints contain `{phase}_handoff.json` with explicit next-phase instructions and acceptance criteria.
- Phase boundary validation fails when handoff is missing or incomplete.

---

## Implementation Notes (where to make small changes)
- Handoff generation: `team_execution_v2_split_mode.py` (after each `execute_phase`), add creation and persistence of a `phase_handoff` JSON.
- Context enrichment: `parallel_coordinator_v2.py` → include `handoff`, `mock_endpoint`, `spec_path`, `mock_file` in `context` passed to `PersonaExecutorV2.execute`.
- Frontend contract deliverables: `ContractDesignerAgent._design_parallel_contracts()` in `team_execution_v2.py` → add explicit scaffold files and acceptance criteria.
- Fallback behavior: `PersonaExecutorV2._fallback_execution()` → map patterns to realistic directories and representative files (avoid flattened names).
- Optional: Implement ConversationHistory per AUTOGEN_CONTEXT_SHARING_ANALYSIS.md for richer AutoGen-style collaboration.

---

## Conclusion
The core architecture is sound (contracts, mocks, phased execution), but the handoff between phases is currently text-only and lossy. By introducing a structured handoff JSON, enriching persona prompts with artifact paths and mock endpoints, and making frontend contract deliverables explicit, the system will reliably produce end-to-end outputs—including the frontend—while enforcing workflow contracts and preventing leakage.

A rerun of the sample requirement following these changes should yield a usable frontend scaffold alongside backend mocks, passing acceptance criteria and closing the gaps identified in this report.
