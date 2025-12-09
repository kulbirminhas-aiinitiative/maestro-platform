"""
Self-Reflection Module: Self-Healing Platform Capabilities

This module provides the self-improvement loop for the Maestro platform:

1. GapDetector (MD-2501): Static analysis gap detection
   - Scans workspace against registry for missing files/capabilities
   - Creates Gap objects for remediation

2. GapToJira (MD-2501): Administrative feedback loop
   - Converts detected gaps to JIRA tickets
   - Tracks resolution status

3. FailureDetector (MD-2533): Runtime failure detection
   - Parses pytest output, logs, execution history
   - Creates Failure objects for auto-remediation

4. RefactoringEngine (MD-2533): Auto-fix generation
   - Uses RAG to find similar past fixes
   - Generates fixes via LLM
   - Applies and validates patches

5. SelfHealingEngine (MD-2533): Complete feedback loop
   - Orchestrates detect -> fix -> test -> approve cycle
   - Falls back to JIRA for unfixable issues

6. FeedbackCollector (MD-2533): User feedback integration
   - Collects approval/rejection feedback
   - Learns from feedback to improve fixes

Target: Enable Self-Reflection capability (15% -> 80%)
"""

from .gap_detector import GapDetector, Gap
from .gap_to_jira import GapToJira, JiraConfig
from .failure_detector import FailureDetector, Failure, FailureType, Severity
from .refactoring_engine import RefactoringEngine, Fix, FixStatus
from .self_healing_engine import SelfHealingEngine, HealingResult, HealingStatus
from .feedback_collector import FeedbackCollector, FeedbackType, FeedbackRecord

__all__ = [
    # Gap Detection (MD-2501)
    'GapDetector',
    'Gap',
    'GapToJira',
    'JiraConfig',

    # Failure Detection (MD-2533)
    'FailureDetector',
    'Failure',
    'FailureType',
    'Severity',

    # Refactoring (MD-2533)
    'RefactoringEngine',
    'Fix',
    'FixStatus',

    # Self-Healing (MD-2533)
    'SelfHealingEngine',
    'HealingResult',
    'HealingStatus',

    # Feedback (MD-2533)
    'FeedbackCollector',
    'FeedbackType',
    'FeedbackRecord',
]
