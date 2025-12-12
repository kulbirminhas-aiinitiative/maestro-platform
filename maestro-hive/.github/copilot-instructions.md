# Maestro Hive - AI Coding Agent Instructions

You are working on **Maestro Hive**, an autonomous SDLC engine that orchestrates 11 specialized AI personas to build software.

## 🏗️ Architecture & Organization

- **Core Logic**: `src/maestro_hive/` contains the main application logic.
  - **Teams**: `src/maestro_hive/teams/` (e.g., `team_execution_v2.py` is the main engine).
  - **Personas**: `src/maestro_hive/personas/` defines the 11 roles (Analyst, Architect, Developer, etc.).
  - **Governance**: `src/maestro_hive/governance/` implements the `Enforcer` middleware for policy checks.
  - **Quality**: `src/maestro_hive/quality/` contains `QualityFabricClient`.
- **Shared Modules**: The root directory contains shared packages used across the platform:
  - `observability/`: Logging, metrics (Prometheus), and tracing (OpenTelemetry).
  - `orchestrator/`: Event bus and workflow orchestration.
  - `dde/`: Dependency-Driven Execution.
  - `bdv/`: Behavior-Driven Validation.
  - `acc/`: Architectural Conformance Checking.
  - `contracts/`: API and data contracts.

## 🧩 Key Patterns & Conventions

- **Governance-First**: All tool calls and major actions must be validated by the **Enforcer** (`src/maestro_hive/governance/enforcer.py`).
  - *Example*: `self.enforcer.check(agent=context, tool_name="write_file", ...)`
- **Async/Await**: The codebase is heavily asynchronous. Use `async def` and `await` for I/O operations.
- **Event-Driven**: Components communicate via an **Event Bus** (`orchestrator/event_bus.py`).
- **Strict Typing**: Use Python type hints (`typing.List`, `typing.Optional`, etc.) and Pydantic models.
- **Error Handling**: Use specific exception hierarchies (e.g., `GovernanceViolation`, `AIContractDesignError`).

## 🛠️ Developer Workflow

- **Dependency Management**: Uses **Poetry**.
  - `pyproject.toml` defines dependencies and tool configurations.
- **Testing**: Uses **pytest**.
  - Run all tests: `pytest`
  - Run specific types: `pytest -m unit`, `pytest -m integration`, `pytest -m acc`
  - Configuration: `pytest.ini`
- **Code Quality**:
  - Formatting: `black` (line length 100), `isort`.
  - Linting: `flake8`, `mypy`.

## 🚀 Critical Files

- `src/maestro_hive/teams/team_execution_v2.py`: The V2 execution engine.
- `AI_UNIVERSE_VISION.md`: High-level architectural vision.
- `PROPOSED_FIX_MD3162.md`: Current active proposal for fixing contract design.

## ⚠️ "Strict Mode" Awareness

The project is currently moving towards a "Strict Mode" where AI failures must raise explicit errors instead of falling back to hardcoded defaults.
- **Do not** implement silent fallbacks.
- **Do** raise specific exceptions (e.g., `AIContractDesignError`) when AI generation fails.
