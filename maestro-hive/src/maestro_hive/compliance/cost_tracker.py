#!/usr/bin/env python3
"""
Cost Tracker: Token and API cost tracking for LLM usage.

Tracks token usage across models, calculates costs, and enforces budgets.
Supports multiple LLM providers (OpenAI, Anthropic, Azure).

EU AI Act Article 13: Transparency on resource usage.
SOC2 CC5.3: Logical and physical access controls.
"""

import json
import threading
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from collections import defaultdict

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE = "azure"
    GOOGLE = "google"
    BEDROCK = "bedrock"
    LOCAL = "local"


# Token pricing per 1M tokens (as of 2025)
MODEL_PRICING = {
    # OpenAI
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "provider": "openai"},
    "gpt-4": {"input": 30.00, "output": 60.00, "provider": "openai"},
    "gpt-4o": {"input": 2.50, "output": 10.00, "provider": "openai"},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "provider": "openai"},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "provider": "openai"},

    # Anthropic
    "claude-3-opus": {"input": 15.00, "output": 75.00, "provider": "anthropic"},
    "claude-3-sonnet": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-3-haiku": {"input": 0.25, "output": 1.25, "provider": "anthropic"},
    "claude-3.5-sonnet": {"input": 3.00, "output": 15.00, "provider": "anthropic"},
    "claude-opus-4": {"input": 15.00, "output": 75.00, "provider": "anthropic"},

    # Google
    "gemini-pro": {"input": 0.50, "output": 1.50, "provider": "google"},
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50, "provider": "google"},

    # Default for unknown models
    "default": {"input": 1.00, "output": 3.00, "provider": "unknown"}
}


@dataclass
class UsageRecord:
    """A single usage record."""
    id: str
    timestamp: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    team_id: Optional[str] = None
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CostSummary:
    """Cost summary for a period."""
    period_start: str
    period_end: str
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_requests: int
    by_model: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    by_team: Dict[str, float] = field(default_factory=dict)
    by_project: Dict[str, float] = field(default_factory=dict)
    by_user: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostTracker:
    """
    Tracks token usage and costs for LLM operations.

    Features:
    - Real-time cost tracking
    - Multi-dimensional reporting (team, project, user)
    - Budget enforcement hooks
    - Export capabilities
    """

    _instance: Optional['CostTracker'] = None
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
        pricing: Optional[Dict[str, Dict]] = None,
        budget_hooks: Optional[List[Callable]] = None
    ):
        """
        Initialize cost tracker.

        Args:
            storage_dir: Directory for storing usage records
            pricing: Custom pricing dictionary
            budget_hooks: Callbacks for budget checks
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'cost_tracking'
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.pricing = pricing or MODEL_PRICING.copy()
        self.budget_hooks = budget_hooks or []

        self._records: List[UsageRecord] = []
        self._record_lock = threading.RLock()
        self._record_counter = 0

        # Load existing records
        self._load_records()

        self._initialized = True
        logger.info(f"CostTracker initialized: {self.storage_dir}")

    def track(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        team_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **metadata
    ) -> UsageRecord:
        """
        Track a usage event.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            team_id: Team identifier
            project_id: Project identifier
            user_id: User identifier
            session_id: Session identifier
            correlation_id: Correlation ID for tracing
            **metadata: Additional metadata

        Returns:
            UsageRecord with calculated cost
        """
        # Calculate cost
        pricing = self.pricing.get(model, self.pricing['default'])
        provider = pricing.get('provider', 'unknown')

        input_cost = Decimal(str(input_tokens)) * Decimal(str(pricing['input'])) / Decimal('1000000')
        output_cost = Decimal(str(output_tokens)) * Decimal(str(pricing['output'])) / Decimal('1000000')
        total_cost = float((input_cost + output_cost).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))

        with self._record_lock:
            self._record_counter += 1
            record_id = f"COST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._record_counter:06d}"

        record = UsageRecord(
            id=record_id,
            timestamp=datetime.utcnow().isoformat(),
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=total_cost,
            team_id=team_id,
            project_id=project_id,
            user_id=user_id,
            session_id=session_id,
            correlation_id=correlation_id,
            metadata=metadata
        )

        with self._record_lock:
            self._records.append(record)
            self._persist_record(record)

        # Check budget hooks
        for hook in self.budget_hooks:
            try:
                hook(record)
            except Exception as e:
                logger.error(f"Budget hook error: {e}")

        logger.debug(f"Tracked usage: {record_id} - {model} - ${total_cost:.6f}")

        return record

    def get_summary(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        team_id: Optional[str] = None,
        project_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> CostSummary:
        """
        Get cost summary for a period.

        Args:
            since: Start time (ISO format or relative like '1d', '7d', '30d')
            until: End time
            team_id: Filter by team
            project_id: Filter by project
            user_id: Filter by user

        Returns:
            CostSummary with aggregated data
        """
        # Parse time filters
        since_dt = self._parse_time(since) if since else datetime.min
        until_dt = self._parse_time(until) if until else datetime.utcnow()

        # Filter records
        filtered = []
        for r in self._records:
            record_dt = datetime.fromisoformat(r.timestamp.replace('Z', '+00:00').replace('+00:00', ''))

            if record_dt < since_dt or record_dt > until_dt:
                continue
            if team_id and r.team_id != team_id:
                continue
            if project_id and r.project_id != project_id:
                continue
            if user_id and r.user_id != user_id:
                continue

            filtered.append(r)

        # Aggregate
        summary = CostSummary(
            period_start=since_dt.isoformat() if since_dt != datetime.min else "all",
            period_end=until_dt.isoformat(),
            total_cost_usd=0.0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_requests=len(filtered)
        )

        by_model: Dict[str, Dict] = defaultdict(lambda: {
            'cost': 0.0, 'input_tokens': 0, 'output_tokens': 0, 'requests': 0
        })
        by_team: Dict[str, float] = defaultdict(float)
        by_project: Dict[str, float] = defaultdict(float)
        by_user: Dict[str, float] = defaultdict(float)

        for r in filtered:
            summary.total_cost_usd += r.cost_usd
            summary.total_input_tokens += r.input_tokens
            summary.total_output_tokens += r.output_tokens

            by_model[r.model]['cost'] += r.cost_usd
            by_model[r.model]['input_tokens'] += r.input_tokens
            by_model[r.model]['output_tokens'] += r.output_tokens
            by_model[r.model]['requests'] += 1

            if r.team_id:
                by_team[r.team_id] += r.cost_usd
            if r.project_id:
                by_project[r.project_id] += r.cost_usd
            if r.user_id:
                by_user[r.user_id] += r.cost_usd

        summary.by_model = dict(by_model)
        summary.by_team = dict(by_team)
        summary.by_project = dict(by_project)
        summary.by_user = dict(by_user)

        return summary

    def get_budget_utilization(
        self,
        team_id: Optional[str] = None,
        project_id: Optional[str] = None,
        period: str = '30d',
        budget_limit: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Get budget utilization for a team or project.

        Args:
            team_id: Team identifier
            project_id: Project identifier
            period: Time period
            budget_limit: Budget limit in USD

        Returns:
            Dictionary with utilization data
        """
        summary = self.get_summary(
            since=period,
            team_id=team_id,
            project_id=project_id
        )

        spent = summary.total_cost_usd
        remaining = max(0, budget_limit - spent)
        utilization = (spent / budget_limit) if budget_limit > 0 else 0.0

        return {
            'team_id': team_id,
            'project_id': project_id,
            'period': period,
            'budget_limit': budget_limit,
            'spent': spent,
            'remaining': remaining,
            'utilization': utilization,
            'status': self._get_budget_status(utilization),
            'total_requests': summary.total_requests,
            'total_tokens': summary.total_input_tokens + summary.total_output_tokens
        }

    def _get_budget_status(self, utilization: float) -> str:
        """Get budget status based on utilization."""
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

    def export(
        self,
        format: str = 'json',
        since: Optional[str] = None,
        until: Optional[str] = None,
        **filters
    ) -> bytes:
        """
        Export usage records.

        Args:
            format: Export format ('json', 'csv')
            since: Start time
            until: End time
            **filters: Additional filters

        Returns:
            Exported data as bytes
        """
        summary = self.get_summary(since=since, until=until, **filters)

        if format == 'json':
            return json.dumps(summary.to_dict(), indent=2).encode()

        elif format == 'csv':
            lines = ['timestamp,model,input_tokens,output_tokens,cost_usd,team_id,project_id']

            for r in self._records:
                lines.append(
                    f'{r.timestamp},{r.model},{r.input_tokens},{r.output_tokens},'
                    f'{r.cost_usd},{r.team_id or ""},{r.project_id or ""}'
                )

            return '\n'.join(lines).encode()

        else:
            raise ValueError(f"Unknown format: {format}")

    def add_budget_hook(self, hook: Callable[[UsageRecord], None]) -> None:
        """Add a budget check hook."""
        self.budget_hooks.append(hook)

    def _persist_record(self, record: UsageRecord) -> None:
        """Persist a record to storage."""
        # Write to daily file
        date_str = record.timestamp[:10]
        file_path = self.storage_dir / f"usage_{date_str}.jsonl"

        with open(file_path, 'a') as f:
            f.write(json.dumps(record.to_dict()) + '\n')

    def _load_records(self) -> None:
        """Load existing records from storage."""
        for file_path in sorted(self.storage_dir.glob("usage_*.jsonl")):
            try:
                with open(file_path, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        self._records.append(UsageRecord(**data))
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"Loaded {len(self._records)} usage records")

    def _parse_time(self, time_str: str) -> datetime:
        """Parse time string."""
        import re

        # Check for relative time
        match = re.match(r'^(\d+)([hdwm])$', time_str)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            deltas = {
                'h': timedelta(hours=value),
                'd': timedelta(days=value),
                'w': timedelta(weeks=value),
                'm': timedelta(days=value * 30)
            }
            return datetime.utcnow() - deltas[unit]

        return datetime.fromisoformat(time_str.replace('Z', '+00:00').replace('+00:00', ''))


def get_cost_tracker(**kwargs) -> CostTracker:
    """Get the singleton CostTracker instance."""
    return CostTracker(**kwargs)


# Token counting utilities
def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count tokens in text.

    Uses tiktoken for OpenAI models, approximation for others.
    """
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except ImportError:
        # Fallback: approximate 4 chars per token
        return len(text) // 4
    except Exception:
        return len(text) // 4


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    tracker = CostTracker()

    # Example usage
    record = tracker.track(
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        team_id="engineering",
        project_id="maestro"
    )

    print(f"Tracked: {record.id} - ${record.cost_usd:.6f}")

    summary = tracker.get_summary(since='7d')
    print(json.dumps(summary.to_dict(), indent=2))
