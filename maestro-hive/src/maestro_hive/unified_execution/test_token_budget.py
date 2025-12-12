"""
Test Suite for MD-3099: Token Budget Wiring

Tests that _check_token_budget() is properly called in the execution loop
and TokenBudgetExceeded is handled gracefully with BANKRUPT status.

ACCEPTANCE CRITERIA:
- AC-1: Call _check_token_budget() after each LLM response
- AC-2: Raise TokenBudgetExceeded when budget limit is hit
- AC-3: Handle exceeded budget gracefully (BANKRUPT status, save progress)
- AC-4: Add token usage to execution metrics/reports
"""

import sys
from pathlib import Path
import asyncio
import pytest

# Add source root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from maestro_hive.unified_execution.persona_executor import PersonaExecutor, ExecutionStatus, ExecutionResult
from maestro_hive.unified_execution.config import ExecutionConfig, TokenConfig
from maestro_hive.unified_execution.exceptions import TokenBudgetExceeded


# ============================================================================
# Test AC-1: Call _check_token_budget() after each LLM response
# ============================================================================

class TestAC1_TokenBudgetCalled:
    """Tests that _check_token_budget is called after task execution."""

    @pytest.mark.asyncio
    async def test_token_budget_called_on_success(self):
        """Token budget should be checked after successful task execution."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 1000

        executor = PersonaExecutor(config=config, persona_id="test")

        # Task that returns tokens
        async def task_with_tokens():
            return {"tokens_used": 100}

        result = await executor.execute(task_with_tokens, "test_task")

        assert result.final_status == ExecutionStatus.SUCCESS
        assert executor._tokens_used == 100
        assert result.total_tokens_used == 100

    @pytest.mark.asyncio
    async def test_token_budget_cumulative(self):
        """Token usage should accumulate across multiple tasks."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 1000

        executor = PersonaExecutor(config=config, persona_id="test")

        async def task_100_tokens():
            return {"tokens_used": 100}

        # Execute multiple tasks
        await executor.execute(task_100_tokens, "task1")
        await executor.execute(task_100_tokens, "task2")
        await executor.execute(task_100_tokens, "task3")

        assert executor._tokens_used == 300

    @pytest.mark.asyncio
    async def test_tokens_tracked_in_attempt(self):
        """Token usage should be tracked in each ExecutionAttempt."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 1000

        executor = PersonaExecutor(config=config, persona_id="test")

        async def task_150_tokens():
            return {"tokens_used": 150}

        result = await executor.execute(task_150_tokens, "test_task")

        assert len(result.attempts) == 1
        assert result.attempts[0].tokens_used == 150


# ============================================================================
# Test AC-2: Raise TokenBudgetExceeded when budget limit is hit
# ============================================================================

class TestAC2_TokenBudgetExceeded:
    """Tests that TokenBudgetExceeded is raised when budget is exceeded."""

    @pytest.mark.asyncio
    async def test_budget_exceeded_triggers_bankrupt(self):
        """Exceeding budget should return BANKRUPT status."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 50  # Low budget

        executor = PersonaExecutor(config=config, persona_id="test")

        async def task_100_tokens():
            return {"tokens_used": 100}  # Exceeds 50 budget

        result = await executor.execute(task_100_tokens, "expensive_task")

        assert result.final_status == ExecutionStatus.BANKRUPT

    @pytest.mark.asyncio
    async def test_budget_exceeded_message(self):
        """Budget exceeded should include correct error details."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 50

        executor = PersonaExecutor(config=config, persona_id="budget_test")

        async def expensive_task():
            return {"tokens_used": 100}

        result = await executor.execute(expensive_task, "expensive_task")

        assert result.failure_report is not None
        assert result.failure_report.error_category == "TOKEN_BUDGET"
        assert "budget_test" in result.failure_report.failed_persona

    @pytest.mark.asyncio
    async def test_budget_not_enforced_skips_check(self):
        """When enforce_budget is False, budget check should be skipped."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = False  # Disabled
        config.tokens.max_tokens_per_persona = 50

        executor = PersonaExecutor(config=config, persona_id="test")

        async def expensive_task():
            return {"tokens_used": 1000}  # Way over budget

        result = await executor.execute(expensive_task, "should_pass")

        # Should succeed because budget is not enforced
        assert result.final_status == ExecutionStatus.SUCCESS


# ============================================================================
# Test AC-3: Handle exceeded budget gracefully (BANKRUPT status, save progress)
# ============================================================================

class TestAC3_GracefulBankruptcy:
    """Tests graceful handling of token budget exceeded."""

    @pytest.mark.asyncio
    async def test_bankrupt_status_set_correctly(self):
        """BANKRUPT status should be set on attempt and result."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 20

        executor = PersonaExecutor(config=config, persona_id="test")

        async def expensive_task():
            return {"tokens_used": 50}

        result = await executor.execute(expensive_task, "test_task")

        # Check both attempt and final status
        assert result.final_status == ExecutionStatus.BANKRUPT
        assert result.attempts[-1].status == ExecutionStatus.BANKRUPT

    @pytest.mark.asyncio
    async def test_bankrupt_preserves_output(self):
        """Bankrupt task should still have output preserved."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 10

        executor = PersonaExecutor(config=config, persona_id="test")

        async def expensive_task():
            return {"tokens_used": 100, "result": "some_value"}

        result = await executor.execute(expensive_task, "test_task")

        # Output should be captured even though it went bankrupt
        assert result.attempts[0].output is not None
        assert result.attempts[0].output["result"] == "some_value"

    @pytest.mark.asyncio
    async def test_bankrupt_failure_report_complete(self):
        """Bankrupt result should have complete failure report."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 25

        executor = PersonaExecutor(config=config, persona_id="report_test")

        async def expensive_task():
            return {"tokens_used": 100}

        result = await executor.execute(expensive_task, "test_task")

        assert result.failure_report is not None
        assert result.failure_report.failed_persona == "report_test"
        assert result.failure_report.error_category == "TOKEN_BUDGET"
        assert result.failure_report.recoverable == False
        assert len(result.failure_report.context) > 0

    @pytest.mark.asyncio
    async def test_bankrupt_tracks_duration(self):
        """Bankrupt result should still track duration."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 10

        executor = PersonaExecutor(config=config, persona_id="test")

        async def expensive_task():
            await asyncio.sleep(0.1)  # Small delay
            return {"tokens_used": 50}

        result = await executor.execute(expensive_task, "test_task")

        assert result.total_duration_seconds >= 0.1


# ============================================================================
# Test AC-4: Add token usage to execution metrics/reports
# ============================================================================

class TestAC4_TokenMetrics:
    """Tests token usage tracking in metrics and reports."""

    @pytest.mark.asyncio
    async def test_total_tokens_in_result(self):
        """ExecutionResult should track total_tokens_used."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 1000

        executor = PersonaExecutor(config=config, persona_id="test")

        async def task_200_tokens():
            return {"tokens_used": 200}

        result = await executor.execute(task_200_tokens, "test_task")

        assert result.total_tokens_used == 200

    @pytest.mark.asyncio
    async def test_attempt_tokens_tracked(self):
        """Each ExecutionAttempt should have tokens_used."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 1000

        executor = PersonaExecutor(config=config, persona_id="test")

        async def task():
            return {"tokens_used": 75}

        result = await executor.execute(task, "test_task")

        for attempt in result.attempts:
            assert hasattr(attempt, "tokens_used")

    @pytest.mark.asyncio
    async def test_bankrupt_metrics_include_budget_info(self):
        """Bankrupt attempt metrics should include budget details."""
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 30

        executor = PersonaExecutor(config=config, persona_id="test")

        async def expensive_task():
            return {"tokens_used": 100}

        result = await executor.execute(expensive_task, "test_task")

        last_attempt = result.attempts[-1]
        assert "tokens_at_bankruptcy" in last_attempt.metrics
        assert "budget_limit" in last_attempt.metrics
        assert last_attempt.metrics["budget_limit"] == 30


# ============================================================================
# Test Token Extraction from Various Output Formats
# ============================================================================

class TestTokenExtraction:
    """Tests for _extract_tokens_from_output method."""

    def test_extract_from_dict_tokens_used(self):
        """Extract tokens from dict with tokens_used key."""
        config = ExecutionConfig()
        executor = PersonaExecutor(config=config, persona_id="test")

        output = {"tokens_used": 150}
        assert executor._extract_tokens_from_output(output) == 150

    def test_extract_from_dict_token_count(self):
        """Extract tokens from dict with token_count key."""
        config = ExecutionConfig()
        executor = PersonaExecutor(config=config, persona_id="test")

        output = {"token_count": 200}
        assert executor._extract_tokens_from_output(output) == 200

    def test_extract_from_nested_usage(self):
        """Extract tokens from nested usage dict (OpenAI format)."""
        config = ExecutionConfig()
        executor = PersonaExecutor(config=config, persona_id="test")

        output = {"usage": {"prompt_tokens": 50, "completion_tokens": 75}}
        assert executor._extract_tokens_from_output(output) == 125

    def test_extract_from_string_estimate(self):
        """Estimate tokens from string length."""
        config = ExecutionConfig()
        executor = PersonaExecutor(config=config, persona_id="test")

        # 400 chars / 4 = 100 tokens
        output = "x" * 400
        assert executor._extract_tokens_from_output(output) == 100

    def test_extract_from_none(self):
        """Return 0 for None output."""
        config = ExecutionConfig()
        executor = PersonaExecutor(config=config, persona_id="test")

        assert executor._extract_tokens_from_output(None) == 0


# ============================================================================
# Test Helper Methods
# ============================================================================

class TestTokenBudgetHelpers:
    """Tests for reset_token_usage and get_token_usage."""

    def test_reset_token_usage(self):
        """reset_token_usage should clear counter."""
        config = ExecutionConfig()
        executor = PersonaExecutor(config=config, persona_id="test")

        executor._tokens_used = 500
        executor.reset_token_usage()

        assert executor.get_token_usage() == 0

    def test_get_token_usage(self):
        """get_token_usage should return current count."""
        config = ExecutionConfig()
        executor = PersonaExecutor(config=config, persona_id="test")

        executor._tokens_used = 350

        assert executor.get_token_usage() == 350


# ============================================================================
# Integration Test - JIRA Acceptance Criteria Scenario
# ============================================================================

class TestJiraAcceptanceScenario:
    """
    Test the exact scenario from JIRA:
    - Configure an agent with a low budget ($0.01 ~ 100 tokens)
    - Run a task that requires $0.05 ~ 500 tokens
    - Verify the agent halts execution before completion with BANKRUPT status
    """

    @pytest.mark.asyncio
    async def test_jira_scenario_low_budget_bankrupt(self):
        """
        Scenario: Agent with low budget goes bankrupt on expensive task.

        This tests the exact acceptance criteria from JIRA:
        "Configure an agent with a low budget ($0.01 ~ 100 tokens).
        Run a task that requires $0.05 ~ 500 tokens.
        Verify the agent halts execution before completion with a specific error message."
        """
        # Configure with low budget (~$0.01 worth of tokens)
        config = ExecutionConfig()
        config.tokens.enforce_budget = True
        config.tokens.max_tokens_per_persona = 100  # Low budget

        executor = PersonaExecutor(config=config, persona_id="low_budget_agent")

        # Task that requires more tokens than budget allows (~$0.05)
        async def expensive_llm_call():
            # Simulates an LLM response that uses 500 tokens
            return {
                "response": "Generated code here...",
                "tokens_used": 500  # Way over 100 token budget
            }

        result = await executor.execute(expensive_llm_call, "code_generation")

        # Verify BANKRUPT status
        assert result.final_status == ExecutionStatus.BANKRUPT, \
            f"Expected BANKRUPT, got {result.final_status}"

        # Verify specific error message
        assert result.failure_report is not None
        assert "TOKEN_BUDGET" in result.failure_report.error_category
        assert "low_budget_agent" in result.failure_report.failed_persona

        # Verify tokens tracked (500 used, exceeded 100 budget)
        assert result.total_tokens_used == 500

        print("JIRA Acceptance Scenario: PASS")
        print(f"  Budget: 100 tokens")
        print(f"  Task required: 500 tokens")
        print(f"  Status: {result.final_status.value}")
        print(f"  Error: {result.failure_report.details}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
