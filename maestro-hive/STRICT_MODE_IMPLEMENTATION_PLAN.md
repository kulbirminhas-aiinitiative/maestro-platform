# Strict Mode Implementation Plan

**Date:** December 12, 2025
**Status:** Approved for Implementation
**Related Ticket:** MD-3162

## Overview

This document formalizes the decision to move `TeamExecutionEngineV2` to "Strict Mode". This means removing silent fallbacks and hardcoded templates in favor of explicit failures when AI components cannot fulfill requirements.

## Core Principle

> **Fail Fast, Not Silent**
>
> *   **REJECTED:** AI fails → Silent fallback → Garbage output → User discovers later
> *   **APPROVED:** AI fails → Explicit error → Stop immediately → User knows why

## Changes Required

### 1. ContractDesignerAgent (`src/maestro_hive/teams/team_execution_v2.py`)
- **Remove:** Hardcoded `_design_sequential_contracts` templates.
- **Add:** `AIContractDesignError` exception.
- **Logic:** If `ClaudeCLIClient` is unavailable or fails, raise `AIContractDesignError`.

### 2. BlueprintScorer (`src/maestro_hive/teams/team_execution_v2.py`)
- **Remove:** `_default_blueprint_recommendation` usage when confidence is low.
- **Add:** `LowConfidenceError` exception.
- **Logic:** If match score < threshold, raise `LowConfidenceError`.

### 3. Exception Hierarchy
- Define `GovernanceViolation` (existing)
- Define `AIContractDesignError` (new)
- Define `LowConfidenceError` (new)

## Documentation References

- **Proposal:** `PROPOSED_FIX_MD3162.md` (Detailed code changes)
- **Analysis:** `MAESTRO_GAP_ANALYSIS_MD3162.md` (Root cause analysis)
- **Advisory:** `docs/reviews/strict-mode-advisory.md` (Implementation guide)

## Next Steps

1.  Create JIRA Ticket for implementation.
2.  Apply code changes to `src/maestro_hive/teams/team_execution_v2.py`.
3.  Verify with MD-3162 test case.
