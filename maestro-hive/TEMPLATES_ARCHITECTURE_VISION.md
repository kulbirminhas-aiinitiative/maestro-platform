# Maestro Localized Templates-as-a-Service: Architecture & Vision

**Date:** December 7, 2025  
**Status:** Proposed  
**Context:** Self-Improving Platform / Knowledge Management

---

## 1. Executive Summary

Just as we transformed "Testing" from a manual task to a **Platform Service (TaaS)**, we must transform "Templates" from static files to a **Dynamic Template Service**.

**The Core Insight:**  
Currently, templates are treated as "Static Forms" (Python classes defining sections).  
**The New Vision:** Templates are **"Active Blueprints"**. The Template Service doesn't just hand you a blank SRS; it accepts a `ProjectContext` (e.g., "Fintech App, Python, High Security") and returns a **Hydrated Artifact** with intelligent defaults, relevant sections enabled/disabled, and pre-filled content.

We are moving from **"Here is a blank form"** to **"Here is your starting point."**

---

## 2. Core Philosophy

1.  **Atomic Assembly (The Lego Model)**:
    *   Templates are not monolithic files to be pruned. They are **Atomic Blocks** (e.g., `blocks/compliance/hipaa.md.j2`).
    *   The Engine acts as an **Assembler**, selecting the right blocks based on the `ProjectContext` and concatenating them.
    *   **Technology**: Use **Jinja2** for text generation. Do not embed text in Python classes.

2.  **Persistent Memory (The Single Source of Truth)**:
    *   The `ProjectContext` is not just an input; it is a **Persistent Ledger**.
    *   If the AI Hydrator decides "Database: PostgreSQL" during SRS generation, this decision is saved to `.maestro/context.json`.
    *   Subsequent templates (e.g., Architecture Doc) read this ledger to ensure consistency (preventing "Split-Brain").

3.  **Safe Updates (The Anchor Strategy)**:
    *   To support "Day 2" operations, the Engine must respect user content.
    *   Generated sections are wrapped in **Anchors** (markers). The Engine can update a managed section (e.g., Compliance) without overwriting the user's custom business logic.

4.  **Hyper-Evolutionary Learning (The Feedback Loop)**:
    *   **Concept**: Templates are living organisms, not static files.
    *   **Mechanism**: An ML-driven process continuously improves templates based on every interaction across 10,000+ processes.
    *   **Input**: Diffs between "Generated Artifact" and "Final User Code".
    *   **Process**:
        *   If users consistently rewrite a section -> **Update the Template**.
        *   If users consistently delete a section -> **Deprecate the Block**.
        *   If users add a missing section -> **Propose a New Block**.
    *   **Goal**: Templates become more adaptable, interface-driven, and less erroneous over time.

---

## 3. Architecture

```mermaid
graph TD
    subgraph "Upstream: The Architects"
        DDE[DDE Orchestrator]
        ACC[Adaptive Code Composer]
    end

    subgraph "The Memory"
        ContextFile[.maestro/context.json]
    end

    subgraph "Downstream: The Platform (Template Service)"
        Assembler[Block Assembler]
        Registry[Jinja2 Block Registry]
        Hydrator[AI Hydrator]
        Evolution[Evolution Engine (ML)]
    end

    subgraph "Output"
        Artifact[Hydrated Artifact]
        FinalCode[Final User Code]
    end

    DDE -->|Request| Assembler
    ContextFile <-->|Read/Write| Assembler
    Assembler -->|Select| Registry
    Registry -->|Blocks| Assembler
    Assembler -->|Hydrate| Hydrator
    Hydrator -->|Render| Artifact
    
    Artifact -->|User Edits| FinalCode
    FinalCode -->|Diff Analysis| Evolution
    Evolution -->|Refine| Registry
```

---

## 4. Component Breakdown

### A. The Memory (`.maestro/context.json`)
A persistent JSON file tracking decisions.

```json
{
  "project_name": "MediTrack",
  "decisions": {
    "database": "PostgreSQL",
    "auth_provider": "Auth0"
  },
  "compliance": ["HIPAA"]
}
```

### B. The Platform (`TemplateAssembler`)
*   **Role**: The "Builder".
*   **Responsibilities**:
    *   **Assembly**: Selects Jinja2 blocks based on tags (e.g., `tag:healthcare`).
    *   **Rendering**: Renders blocks using the Context.
    *   **Persistence**: Updates `context.json` with new decisions.

### C. The Blocks (`Jinja2 Atoms`)
*   **Format**: `.md.j2` files.
*   **Example**: `blocks/compliance/hipaa.md.j2`
    ```markdown
    ## HIPAA Compliance
    The system must encrypt PHI (Protected Health Information) using {{ context.decisions.encryption_algo }}.
    ```

---

## 5. Workflow: The "Atomic" Lifecycle

1.  **Inception**: 
    *   DDE initializes `.maestro/context.json`.

2.  **Assembly**:
    *   DDE requests "SRS".
    *   Assembler scans Registry for blocks tagged `srs` AND (`general` OR `healthcare`).
    *   Assembler finds `intro.md.j2`, `hipaa.md.j2`, `tech_stack.md.j2`.

3.  **Hydration & Persistence**:
    *   Assembler sees `{{ encryption_algo }}` is missing.
    *   Hydrator (AI) decides: "AES-256".
    *   Assembler saves "encryption_algo": "AES-256" to `context.json`.
    *   Assembler renders the artifact.

---

## 6. Implementation Plan (Revised)

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **Jinja2 Registry** | 🔴 P0 Priority | `src/maestro_hive/blocks/registry/` | Directory of `.j2` files. |
| **Context Manager** | 🔴 P1 Priority | `src/maestro_hive/blocks/context_manager.py` | Handles `context.json` I/O. |
| **Block Assembler** | 🟡 Beta | `src/maestro_hive/blocks/templates/engine.py` | Refactoring to use Jinja2. |
| **Evolutionary Learning** | ❌ Killed | N/A | Removed per advisory. |

---

## 7. Critical Advisory & Roadmap

**Status:** 🟡 **Conceptually Strong** / 🔴 **Implementation Risky**

**Immediate Priorities:**
1.  **The Standard**: Adopt Jinja2. Stop writing Python classes for text content.
2.  **The Memory**: Implement State Persistence (`context.json`) to solve Split-Brain.
3.  **The Assembler**: Build the Logic Engine to assemble Jinja blocks.

