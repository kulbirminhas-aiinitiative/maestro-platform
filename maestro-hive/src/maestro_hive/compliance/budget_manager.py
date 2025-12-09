#!/usr/bin/env python3
"""
Budget Manager: Budget limits, alerts, and enforcement for LLM costs.

Manages budget allocation across teams and projects with configurable limits,
alerts, and enforcement policies.

SOC2 CC5.3: Cost management controls.
EU AI Act Article 13: Resource transparency.
"""

import json
import threading
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class BudgetPeriod(Enum):
    """Budget period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EXCEEDED = "exceeded"


class EnforcementAction(Enum):
    """Actions to take when budget exceeded."""
    ALLOW = "allow"  # Allow but log
    WARN = "warn"    # Allow but alert
    BLOCK = "block"  # Block the request
    THROTTLE = "throttle"  # Slow down requests


@dataclass
class Budget:
    """A budget allocation."""
    id: str
    name: str
    entity_type: str  # team, project, user
    entity_id: str
    limit_usd: float
    period: BudgetPeriod
    alert_thresholds: List[float] = field(default_factory=lambda: [0.5, 0.75, 0.9])
    enforcement: EnforcementAction = EnforcementAction.WARN
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['period'] = self.period.value
        data['enforcement'] = self.enforcement.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Budget':
        data = dict(data)
        data['period'] = BudgetPeriod(data['period'])
        data['enforcement'] = EnforcementAction(data['enforcement'])
        return cls(**data)


@dataclass
class BudgetAlert:
    """A budget alert event."""
    id: str
    budget_id: str
    level: AlertLevel
    utilization: float
    spent: float
    limit: float
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['level'] = self.level.value
        return data


@dataclass
class BudgetStatus:
    """Current status of a budget."""
    budget_id: str
    budget_name: str
    entity_type: str
    entity_id: str
    period: BudgetPeriod
    period_start: str
    period_end: str
    limit_usd: float
    spent_usd: float
    remaining_usd: float
    utilization: float
    status: str
    enforcement: EnforcementAction
    requests_count: int = 0
    active_alerts: List[BudgetAlert] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['period'] = self.period.value
        data['enforcement'] = self.enforcement.value
        data['active_alerts'] = [a.to_dict() for a in self.active_alerts]
        return data


class BudgetManager:
    """
    Manages budgets for cost control.

    Features:
    - Multi-level budgets (team, project, user)
    - Configurable periods and limits
    - Alert system with thresholds
    - Enforcement policies
    """

    _instance: Optional['BudgetManager'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        default_limit: float = 1000.0,
        alert_handlers: Optional[List[Callable]] = None
    ):
        """
        Initialize budget manager.

        Args:
            storage_dir: Directory for budget configurations
            default_limit: Default budget limit in USD
            alert_handlers: Callbacks for alerts
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'budgets'
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.default_limit = default_limit
        self.alert_handlers = alert_handlers or []

        self._budgets: Dict[str, Budget] = {}
        self._alerts: List[BudgetAlert] = []
        self._spending: Dict[str, float] = {}  # budget_id -> current period spending
        self._data_lock = threading.RLock()
        self._alert_counter = 0

        self._load_budgets()

        self._initialized = True
        logger.info(f"BudgetManager initialized: {self.storage_dir}")

    def create_budget(
        self,
        name: str,
        entity_type: str,
        entity_id: str,
        limit_usd: float,
        period: BudgetPeriod = BudgetPeriod.MONTHLY,
        alert_thresholds: Optional[List[float]] = None,
        enforcement: EnforcementAction = EnforcementAction.WARN,
        **metadata
    ) -> Budget:
        """
        Create a new budget.

        Args:
            name: Budget name
            entity_type: 'team', 'project', or 'user'
            entity_id: Entity identifier
            limit_usd: Budget limit in USD
            period: Budget period
            alert_thresholds: List of thresholds (0.0-1.0)
            enforcement: Action on budget exceeded

        Returns:
            Created Budget
        """
        budget_id = f"BUD-{entity_type[:3].upper()}-{entity_id}-{period.value[:3].upper()}"

        budget = Budget(
            id=budget_id,
            name=name,
            entity_type=entity_type,
            entity_id=entity_id,
            limit_usd=limit_usd,
            period=period,
            alert_thresholds=alert_thresholds or [0.5, 0.75, 0.9],
            enforcement=enforcement,
            metadata=metadata
        )

        with self._data_lock:
            self._budgets[budget_id] = budget
            self._spending[budget_id] = 0.0
            self._save_budget(budget)

        logger.info(f"Created budget: {budget_id} - ${limit_usd} {period.value}")

        return budget

    def update_budget(
        self,
        budget_id: str,
        limit_usd: Optional[float] = None,
        alert_thresholds: Optional[List[float]] = None,
        enforcement: Optional[EnforcementAction] = None
    ) -> Optional[Budget]:
        """Update an existing budget."""
        with self._data_lock:
            budget = self._budgets.get(budget_id)
            if not budget:
                return None

            if limit_usd is not None:
                budget.limit_usd = limit_usd
            if alert_thresholds is not None:
                budget.alert_thresholds = alert_thresholds
            if enforcement is not None:
                budget.enforcement = enforcement

            budget.updated_at = datetime.utcnow().isoformat()
            self._save_budget(budget)

        return budget

    def delete_budget(self, budget_id: str) -> bool:
        """Delete a budget."""
        with self._data_lock:
            if budget_id in self._budgets:
                del self._budgets[budget_id]
                if budget_id in self._spending:
                    del self._spending[budget_id]

                # Remove file
                file_path = self.storage_dir / f"{budget_id}.json"
                if file_path.exists():
                    file_path.unlink()

                return True
        return False

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """Get a budget by ID."""
        return self._budgets.get(budget_id)

    def get_budgets(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> List[Budget]:
        """Get budgets with optional filters."""
        budgets = list(self._budgets.values())

        if entity_type:
            budgets = [b for b in budgets if b.entity_type == entity_type]
        if entity_id:
            budgets = [b for b in budgets if b.entity_id == entity_id]

        return budgets

    def record_spending(
        self,
        entity_type: str,
        entity_id: str,
        amount_usd: float
    ) -> Dict[str, Any]:
        """
        Record spending against budgets.

        Args:
            entity_type: 'team', 'project', or 'user'
            entity_id: Entity identifier
            amount_usd: Amount spent

        Returns:
            Dictionary with check results for each affected budget
        """
        results = {}

        with self._data_lock:
            # Find applicable budgets
            for budget_id, budget in self._budgets.items():
                if budget.entity_type == entity_type and budget.entity_id == entity_id:
                    # Update spending
                    current = self._spending.get(budget_id, 0.0)
                    new_total = current + amount_usd
                    self._spending[budget_id] = new_total

                    # Calculate utilization
                    utilization = new_total / budget.limit_usd if budget.limit_usd > 0 else 0.0

                    # Check thresholds
                    for threshold in budget.alert_thresholds:
                        if current / budget.limit_usd < threshold <= utilization:
                            self._create_alert(budget, utilization, new_total, threshold)

                    # Determine enforcement action
                    action = self._determine_action(budget, utilization)

                    results[budget_id] = {
                        'budget_name': budget.name,
                        'spent': new_total,
                        'limit': budget.limit_usd,
                        'utilization': utilization,
                        'action': action.value,
                        'allowed': action != EnforcementAction.BLOCK
                    }

        return results

    def check_budget(
        self,
        entity_type: str,
        entity_id: str,
        amount_usd: float = 0.0
    ) -> Dict[str, Any]:
        """
        Check if spending is within budget (without recording).

        Args:
            entity_type: Entity type
            entity_id: Entity identifier
            amount_usd: Amount to check

        Returns:
            Check result
        """
        result = {
            'allowed': True,
            'budgets': [],
            'enforcement': EnforcementAction.ALLOW.value
        }

        with self._data_lock:
            for budget_id, budget in self._budgets.items():
                if budget.entity_type == entity_type and budget.entity_id == entity_id:
                    current = self._spending.get(budget_id, 0.0)
                    projected = current + amount_usd
                    utilization = projected / budget.limit_usd if budget.limit_usd > 0 else 0.0

                    action = self._determine_action(budget, utilization)

                    budget_check = {
                        'budget_id': budget_id,
                        'budget_name': budget.name,
                        'current_spent': current,
                        'projected_spent': projected,
                        'limit': budget.limit_usd,
                        'utilization': utilization,
                        'action': action.value,
                        'allowed': action != EnforcementAction.BLOCK
                    }

                    result['budgets'].append(budget_check)

                    if action == EnforcementAction.BLOCK:
                        result['allowed'] = False
                        result['enforcement'] = action.value

        return result

    def get_status(self, budget_id: str) -> Optional[BudgetStatus]:
        """Get current status of a budget."""
        budget = self._budgets.get(budget_id)
        if not budget:
            return None

        period_start, period_end = self._get_period_bounds(budget.period)
        spent = self._spending.get(budget_id, 0.0)
        remaining = max(0, budget.limit_usd - spent)
        utilization = spent / budget.limit_usd if budget.limit_usd > 0 else 0.0

        # Get active alerts
        active_alerts = [
            a for a in self._alerts
            if a.budget_id == budget_id and not a.acknowledged
        ]

        return BudgetStatus(
            budget_id=budget_id,
            budget_name=budget.name,
            entity_type=budget.entity_type,
            entity_id=budget.entity_id,
            period=budget.period,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            limit_usd=budget.limit_usd,
            spent_usd=spent,
            remaining_usd=remaining,
            utilization=utilization,
            status=self._get_status_string(utilization),
            enforcement=budget.enforcement,
            active_alerts=active_alerts
        )

    def acknowledge_alert(
        self,
        alert_id: str,
        user: str
    ) -> bool:
        """Acknowledge an alert."""
        for alert in self._alerts:
            if alert.id == alert_id and not alert.acknowledged:
                alert.acknowledged = True
                alert.acknowledged_by = user
                alert.acknowledged_at = datetime.utcnow().isoformat()
                return True
        return False

    def reset_period(self, budget_id: str) -> bool:
        """Reset spending for a budget period."""
        if budget_id in self._spending:
            self._spending[budget_id] = 0.0
            return True
        return False

    def emergency_override(
        self,
        budget_id: str,
        new_limit: float,
        reason: str,
        approver: str
    ) -> Optional[Budget]:
        """
        Emergency budget override.

        Args:
            budget_id: Budget to override
            new_limit: New limit
            reason: Reason for override
            approver: Who approved the override

        Returns:
            Updated budget
        """
        budget = self.update_budget(budget_id, limit_usd=new_limit)

        if budget:
            # Log the override
            logger.warning(
                f"Budget override: {budget_id} -> ${new_limit} "
                f"(reason: {reason}, approver: {approver})"
            )

            # Create informational alert
            self._create_alert(
                budget,
                self._spending.get(budget_id, 0) / new_limit,
                self._spending.get(budget_id, 0),
                0.0,
                level=AlertLevel.INFO,
                message=f"Budget override: new limit ${new_limit} by {approver}"
            )

        return budget

    def _determine_action(
        self,
        budget: Budget,
        utilization: float
    ) -> EnforcementAction:
        """Determine enforcement action based on utilization."""
        if utilization >= 1.0:
            return budget.enforcement
        elif utilization >= 0.9:
            return EnforcementAction.WARN if budget.enforcement != EnforcementAction.ALLOW else EnforcementAction.ALLOW
        else:
            return EnforcementAction.ALLOW

    def _create_alert(
        self,
        budget: Budget,
        utilization: float,
        spent: float,
        threshold: float,
        level: Optional[AlertLevel] = None,
        message: Optional[str] = None
    ) -> BudgetAlert:
        """Create a budget alert."""
        self._alert_counter += 1
        alert_id = f"ALERT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._alert_counter:04d}"

        if level is None:
            if utilization >= 1.0:
                level = AlertLevel.EXCEEDED
            elif utilization >= 0.9:
                level = AlertLevel.CRITICAL
            elif utilization >= 0.75:
                level = AlertLevel.WARNING
            else:
                level = AlertLevel.INFO

        if message is None:
            message = f"Budget {budget.name} at {utilization:.1%} (${spent:.2f}/${budget.limit_usd:.2f})"

        alert = BudgetAlert(
            id=alert_id,
            budget_id=budget.id,
            level=level,
            utilization=utilization,
            spent=spent,
            limit=budget.limit_usd,
            message=message
        )

        self._alerts.append(alert)

        # Call alert handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

        logger.info(f"Alert: {alert.message}")

        return alert

    def _get_period_bounds(self, period: BudgetPeriod) -> tuple[datetime, datetime]:
        """Get start and end of current period."""
        now = datetime.utcnow()

        if period == BudgetPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)

        elif period == BudgetPeriod.WEEKLY:
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(weeks=1)

        elif period == BudgetPeriod.MONTHLY:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)

        elif period == BudgetPeriod.QUARTERLY:
            quarter = (now.month - 1) // 3
            start = now.replace(month=quarter * 3 + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(month=start.month + 3) if start.month <= 9 else start.replace(year=start.year + 1, month=1)

        else:  # ANNUAL
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=now.year + 1)

        return start, end

    def _get_status_string(self, utilization: float) -> str:
        """Get status string from utilization."""
        if utilization >= 1.0:
            return 'exceeded'
        elif utilization >= 0.9:
            return 'critical'
        elif utilization >= 0.75:
            return 'warning'
        elif utilization >= 0.5:
            return 'moderate'
        else:
            return 'healthy'

    def _save_budget(self, budget: Budget) -> None:
        """Save budget to storage."""
        file_path = self.storage_dir / f"{budget.id}.json"
        with open(file_path, 'w') as f:
            json.dump(budget.to_dict(), f, indent=2)

    def _load_budgets(self) -> None:
        """Load budgets from storage."""
        for file_path in self.storage_dir.glob("BUD-*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    budget = Budget.from_dict(data)
                    self._budgets[budget.id] = budget
                    self._spending[budget.id] = 0.0
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"Loaded {len(self._budgets)} budgets")


def get_budget_manager(**kwargs) -> BudgetManager:
    """Get the singleton BudgetManager instance."""
    return BudgetManager(**kwargs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = BudgetManager()

    # Create example budget
    budget = manager.create_budget(
        name="Engineering Team Monthly",
        entity_type="team",
        entity_id="engineering",
        limit_usd=5000.0,
        period=BudgetPeriod.MONTHLY
    )

    # Record some spending
    result = manager.record_spending("team", "engineering", 100.0)
    print(json.dumps(result, indent=2))

    # Get status
    status = manager.get_status(budget.id)
    if status:
        print(json.dumps(status.to_dict(), indent=2))
