
from dataclasses import dataclass
from .exceptions import TokenBudgetExceeded


@dataclass
class TokenBudget:
    total_limit: int
    current_usage: int = 0

    def check_budget(self, estimated_cost: int) -> bool:
        if self.current_usage + estimated_cost > self.total_limit:
            return False
        return True

    def deduct(self, cost: int):
        self.current_usage += cost


def check_budget(budget: TokenBudget, estimated_cost: int):
    if not budget.check_budget(estimated_cost):
        raise TokenBudgetExceeded(
            message="Budget exceeded",
            persona_id="unknown",
            tokens_used=budget.current_usage,
            budget_limit=budget.total_limit
        )
