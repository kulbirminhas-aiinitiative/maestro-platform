"""
User Simulator Agent (MD-3127)

Simulates user behavior for exam scenarios.
Replaces the vague "Ghost Users" concept with a concrete, scriptable component.

AC-3: An agent can take a "Python 101" exam in the simulator
"""

from __future__ import annotations

import logging
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScenarioStep:
    """A single step in an exam scenario."""
    step_id: int
    user_input: str  # What the "user" says/requests
    expected_behavior: str  # What the agent should do
    success_criteria: List[str]  # How to evaluate success
    timeout_seconds: int = 300
    hints: List[str] = field(default_factory=list)


@dataclass
class ExamScenario:
    """Complete exam scenario definition."""
    scenario_id: str
    name: str
    description: str
    difficulty: str  # easy, medium, hard, expert
    steps: List[ScenarioStep]
    max_total_time_minutes: int
    passing_score: float = 0.8


class UserSimulatorAgent:
    """
    Simulates user behavior for exam scenarios (AC-3).

    Consumes scenario YAML files and generates natural language prompts
    to test the student agent in a controlled environment.
    """

    def __init__(self, scenario_path: Optional[str] = None, scenario_data: Optional[Dict[str, Any]] = None):
        """
        Initialize with a scenario file or data.

        Args:
            scenario_path: Path to scenario YAML file
            scenario_data: Scenario data dict (alternative to file)
        """
        if scenario_path:
            with open(scenario_path, 'r') as f:
                data = yaml.safe_load(f)
        elif scenario_data:
            data = scenario_data
        else:
            raise ValueError("Either scenario_path or scenario_data must be provided")

        self.scenario = self._parse_scenario(data)
        self.current_step = 0
        self.start_time: Optional[datetime] = None
        self.step_results: List[Dict[str, Any]] = []

    def _parse_scenario(self, data: Dict[str, Any]) -> ExamScenario:
        """Parse scenario data into ExamScenario."""
        scenario_data = data.get('scenario', data)
        return ExamScenario(
            scenario_id=scenario_data.get('id', 'unknown'),
            name=scenario_data.get('name', 'Unnamed Scenario'),
            description=scenario_data.get('description', ''),
            difficulty=scenario_data.get('difficulty', 'medium'),
            max_total_time_minutes=scenario_data.get('max_time_minutes', 60),
            passing_score=scenario_data.get('passing_score', 0.8),
            steps=[
                ScenarioStep(
                    step_id=i,
                    user_input=step.get('user_input', ''),
                    expected_behavior=step.get('expected_behavior', ''),
                    success_criteria=step.get('success_criteria', []),
                    timeout_seconds=step.get('timeout_seconds', 300),
                    hints=step.get('hints', [])
                )
                for i, step in enumerate(scenario_data.get('steps', []))
            ]
        )

    def start_exam(self) -> str:
        """Start the exam and return the first prompt."""
        self.start_time = datetime.utcnow()
        self.current_step = 0
        self.step_results = []
        logger.info(f"Started exam: {self.scenario.name}")
        return self.get_current_prompt()

    def get_current_prompt(self) -> str:
        """Get the current step's user prompt."""
        if self.current_step >= len(self.scenario.steps):
            return "[EXAM COMPLETE]"
        return self.scenario.steps[self.current_step].user_input

    def get_current_step_info(self) -> Optional[ScenarioStep]:
        """Get current step information."""
        if self.current_step >= len(self.scenario.steps):
            return None
        return self.scenario.steps[self.current_step]

    def evaluate_response(self, agent_response: str, score: Optional[float] = None) -> Dict[str, Any]:
        """
        Evaluate the agent's response against success criteria (AC-4).

        In production, this would use an LLM to evaluate against criteria.
        For now, returns the provided score or a default.

        Args:
            agent_response: The agent's response to evaluate
            score: Optional score override (for testing)

        Returns:
            Dict with 'passed', 'score', 'feedback' keys
        """
        if self.current_step >= len(self.scenario.steps):
            return {
                'step_id': -1,
                'passed': False,
                'score': 0.0,
                'feedback': 'Exam already complete',
                'criteria_met': []
            }

        step = self.scenario.steps[self.current_step]

        # In real implementation, use LLM to evaluate against criteria
        # For now, use provided score or check for basic criteria
        if score is not None:
            calculated_score = score
        else:
            # Basic evaluation: check if response contains expected keywords
            calculated_score = self._basic_evaluate(agent_response, step)

        passed = calculated_score >= self.scenario.passing_score

        result = {
            'step_id': self.current_step,
            'passed': passed,
            'score': calculated_score,
            'feedback': f"Step {self.current_step + 1} {'passed' if passed else 'failed'}",
            'criteria_met': step.success_criteria if passed else [],
            'expected_behavior': step.expected_behavior,
        }
        self.step_results.append(result)
        return result

    def _basic_evaluate(self, response: str, step: ScenarioStep) -> float:
        """Basic evaluation based on response content."""
        if not response:
            return 0.0

        # Check if response addresses any success criteria
        matches = 0
        total_criteria = len(step.success_criteria) or 1

        for criterion in step.success_criteria:
            # Simple keyword matching
            keywords = criterion.lower().split()
            if any(kw in response.lower() for kw in keywords if len(kw) > 3):
                matches += 1

        return matches / total_criteria if total_criteria > 0 else 0.5

    def advance_step(self) -> bool:
        """Move to next step. Returns False if exam is complete."""
        self.current_step += 1
        at_end = self.current_step >= len(self.scenario.steps)
        if at_end:
            logger.info(f"Exam complete: {self.scenario.name}")
        return not at_end

    def get_final_score(self) -> float:
        """Calculate final exam score (AC-4: weighted average)."""
        if not self.step_results:
            return 0.0

        # Weight scores by step position (later steps worth more)
        total_weight = 0
        weighted_sum = 0

        for i, result in enumerate(self.step_results):
            weight = 1.0 + (i * 0.1)  # Increasing weight for later steps
            weighted_sum += result['score'] * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def has_passed(self) -> bool:
        """Check if agent passed the exam."""
        return self.get_final_score() >= self.scenario.passing_score

    def get_exam_summary(self) -> Dict[str, Any]:
        """Get comprehensive exam summary (AC-4)."""
        return {
            'scenario_id': self.scenario.scenario_id,
            'scenario_name': self.scenario.name,
            'difficulty': self.scenario.difficulty,
            'total_steps': len(self.scenario.steps),
            'steps_completed': len(self.step_results),
            'final_score': self.get_final_score(),
            'passed': self.has_passed(),
            'passing_threshold': self.scenario.passing_score,
            'step_results': self.step_results,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': datetime.utcnow().isoformat(),
        }
