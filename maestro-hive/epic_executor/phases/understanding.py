"""
Phase 1: Understanding

Parse EPIC, extract acceptance criteria, plan work.
This is the first phase of EPIC execution.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    AcceptanceCriterion,
    ACStatus,
    EpicInfo,
    ExecutionPhase,
    PhaseResult,
)
from ..jira.epic_updater import EpicUpdater, JiraConfig


@dataclass
class UnderstandingResult:
    """Result from the understanding phase."""
    epic_info: EpicInfo
    acceptance_criteria: List[AcceptanceCriterion]
    child_tasks_created: Dict[str, str]  # AC ID -> Task key
    requirement_type: str  # e.g., "feature", "bug", "refactor"
    estimated_complexity: str  # "low", "medium", "high"
    recommended_team_composition: List[str]  # Agent roles needed


class UnderstandingPhase:
    """
    Phase 1: EPIC Understanding & Planning

    Responsibilities:
    1. Fetch EPIC details from JIRA
    2. Extract or infer acceptance criteria
    3. Classify the requirement type
    4. Determine required team composition
    5. Create child tasks for each AC
    """

    def __init__(self, jira_config: JiraConfig):
        """
        Initialize the understanding phase.

        Args:
            jira_config: JIRA API configuration
        """
        self.jira_config = jira_config
        self.epic_updater = EpicUpdater(jira_config)

    async def execute(
        self,
        epic_key: str,
        create_child_tasks: bool = True,
    ) -> Tuple[PhaseResult, Optional[UnderstandingResult]]:
        """
        Execute the understanding phase.

        Args:
            epic_key: EPIC key to process
            create_child_tasks: Whether to create JIRA tasks for each AC

        Returns:
            Tuple of (PhaseResult, UnderstandingResult or None if failed)
        """
        started_at = datetime.now()
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []

        try:
            # Step 1: Fetch EPIC details
            epic_info = await self.epic_updater.fetch_epic(epic_key)
            artifacts.append(f"Fetched EPIC {epic_key}")

            # Step 2: Validate and enhance acceptance criteria
            acceptance_criteria = epic_info.acceptance_criteria

            if not acceptance_criteria:
                # Try to infer from EPIC description and summary
                acceptance_criteria = await self._infer_acceptance_criteria(epic_info)
                warnings.append(
                    f"No explicit ACs found, inferred {len(acceptance_criteria)} from description"
                )

            if not acceptance_criteria:
                # Create minimal placeholder AC
                acceptance_criteria = [
                    AcceptanceCriterion(
                        id="AC-1",
                        description=f"Implement {epic_info.summary}",
                        status=ACStatus.PENDING
                    )
                ]
                warnings.append("No ACs could be inferred, created placeholder AC")

            # Update epic_info with final ACs
            epic_info.acceptance_criteria = acceptance_criteria
            artifacts.append(f"Extracted {len(acceptance_criteria)} acceptance criteria")

            # Step 3: Classify requirement type
            requirement_type = self._classify_requirement(epic_info)
            artifacts.append(f"Classified as: {requirement_type}")

            # Step 4: Estimate complexity
            complexity = self._estimate_complexity(epic_info, acceptance_criteria)
            artifacts.append(f"Complexity: {complexity}")

            # Step 5: Recommend team composition
            team_composition = self._recommend_team(requirement_type, complexity, acceptance_criteria)
            artifacts.append(f"Recommended team: {', '.join(team_composition)}")

            # Step 6: Create child tasks (optional)
            child_tasks_created: Dict[str, str] = {}
            if create_child_tasks:
                existing_tasks = set(epic_info.child_tasks)
                if not existing_tasks:
                    child_tasks_created = await self.epic_updater.create_ac_tasks(
                        epic_key, acceptance_criteria
                    )
                    artifacts.append(f"Created {len(child_tasks_created)} child tasks")
                else:
                    warnings.append(f"EPIC already has {len(existing_tasks)} child tasks, skipping creation")

            # Build result
            understanding_result = UnderstandingResult(
                epic_info=epic_info,
                acceptance_criteria=acceptance_criteria,
                child_tasks_created=child_tasks_created,
                requirement_type=requirement_type,
                estimated_complexity=complexity,
                recommended_team_composition=team_composition,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.UNDERSTANDING,
                success=True,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
                metrics={
                    "acs_extracted": len(acceptance_criteria),
                    "child_tasks_created": len(child_tasks_created),
                    "requirement_type": requirement_type,
                    "complexity": complexity,
                }
            )

            return phase_result, understanding_result

        except Exception as e:
            errors.append(str(e))
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.UNDERSTANDING,
                success=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
            )

            return phase_result, None

    async def _infer_acceptance_criteria(
        self,
        epic_info: EpicInfo
    ) -> List[AcceptanceCriterion]:
        """
        Infer acceptance criteria from EPIC content.

        Uses keyword analysis and structure detection to generate ACs.
        """
        criteria = []
        description = epic_info.description.lower()

        # Common action keywords that suggest requirements
        action_keywords = {
            "implement": "Implementation",
            "create": "Creation",
            "add": "Addition",
            "update": "Update",
            "fix": "Fix",
            "remove": "Removal",
            "migrate": "Migration",
            "integrate": "Integration",
            "test": "Testing",
            "document": "Documentation",
            "optimize": "Optimization",
            "refactor": "Refactoring",
        }

        # Look for action keywords in description
        ac_count = 0
        for keyword, action_type in action_keywords.items():
            if keyword in description:
                # Try to extract context around keyword
                import re
                pattern = rf'{keyword}\s+[\w\s]{{10,50}}'
                matches = re.findall(pattern, description)
                for match in matches[:2]:  # Limit to 2 per keyword
                    ac_count += 1
                    criteria.append(AcceptanceCriterion(
                        id=f"AC-{ac_count}",
                        description=f"{action_type}: {match.strip().capitalize()}",
                        status=ACStatus.PENDING
                    ))

        # If still no criteria, generate from summary
        if not criteria:
            summary = epic_info.summary
            criteria.append(AcceptanceCriterion(
                id="AC-1",
                description=f"Complete implementation of: {summary}",
                status=ACStatus.PENDING
            ))

            # Add standard quality criteria
            criteria.append(AcceptanceCriterion(
                id="AC-2",
                description="Unit tests covering core functionality",
                status=ACStatus.PENDING
            ))
            criteria.append(AcceptanceCriterion(
                id="AC-3",
                description="Technical documentation in Confluence",
                status=ACStatus.PENDING
            ))

        return criteria[:8]  # Limit to 8 ACs

    def _classify_requirement(self, epic_info: EpicInfo) -> str:
        """
        Classify the requirement type based on EPIC content.

        Returns:
            One of: "feature", "bug", "refactor", "infrastructure", "documentation"
        """
        description = epic_info.description.lower()
        summary = epic_info.summary.lower()
        labels = [l.lower() for l in epic_info.labels]
        combined = f"{description} {summary} {' '.join(labels)}"

        # Priority-based classification
        classifiers = [
            (["bug", "fix", "error", "issue", "broken"], "bug"),
            (["refactor", "cleanup", "technical debt", "improve code"], "refactor"),
            (["docs", "documentation", "readme", "guide"], "documentation"),
            (["infra", "infrastructure", "deploy", "ci/cd", "devops"], "infrastructure"),
            (["feature", "implement", "add", "create", "new"], "feature"),
        ]

        for keywords, req_type in classifiers:
            if any(kw in combined for kw in keywords):
                return req_type

        return "feature"  # Default

    def _estimate_complexity(
        self,
        epic_info: EpicInfo,
        acceptance_criteria: List[AcceptanceCriterion]
    ) -> str:
        """
        Estimate implementation complexity.

        Returns:
            One of: "low", "medium", "high"
        """
        # Factors affecting complexity
        score = 0

        # Number of ACs
        ac_count = len(acceptance_criteria)
        if ac_count <= 3:
            score += 1
        elif ac_count <= 6:
            score += 2
        else:
            score += 3

        # Description length (proxy for scope)
        desc_len = len(epic_info.description)
        if desc_len < 500:
            score += 1
        elif desc_len < 1500:
            score += 2
        else:
            score += 3

        # Keywords indicating complexity
        complex_keywords = ["integration", "migrate", "architecture", "security", "performance"]
        if any(kw in epic_info.description.lower() for kw in complex_keywords):
            score += 2

        # Simple keywords
        simple_keywords = ["update", "fix", "typo", "config"]
        if any(kw in epic_info.description.lower() for kw in simple_keywords):
            score -= 1

        # Map score to complexity
        if score <= 3:
            return "low"
        elif score <= 6:
            return "medium"
        else:
            return "high"

    def _recommend_team(
        self,
        requirement_type: str,
        complexity: str,
        acceptance_criteria: List[AcceptanceCriterion]
    ) -> List[str]:
        """
        Recommend team composition for the EPIC.

        Returns:
            List of recommended agent roles
        """
        # Base team by requirement type
        base_teams = {
            "feature": ["architect", "developer", "tester"],
            "bug": ["developer", "tester"],
            "refactor": ["architect", "developer"],
            "infrastructure": ["devops", "developer"],
            "documentation": ["tech_writer", "developer"],
        }

        team = list(base_teams.get(requirement_type, ["developer"]))

        # Add roles based on complexity
        if complexity == "high":
            if "architect" not in team:
                team.insert(0, "architect")
            if "reviewer" not in team:
                team.append("reviewer")

        # Add roles based on AC content
        ac_text = " ".join(ac.description.lower() for ac in acceptance_criteria)

        if "api" in ac_text or "endpoint" in ac_text:
            if "api_designer" not in team:
                team.append("api_designer")

        if "test" in ac_text or "coverage" in ac_text:
            if "tester" not in team:
                team.append("tester")

        if "security" in ac_text or "auth" in ac_text:
            if "security_engineer" not in team:
                team.append("security_engineer")

        if "frontend" in ac_text or "ui" in ac_text:
            if "frontend_developer" not in team:
                team.append("frontend_developer")

        return team
