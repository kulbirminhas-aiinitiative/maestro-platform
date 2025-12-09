#!/usr/bin/env python3
"""
Requirements Analyzer: Analyzes requirements for quality, completeness, and feasibility.

This module handles:
- Ambiguity detection in requirements text
- Feasibility checking against constraints
- Prioritization of requirements
- Acceptance criteria extraction and validation
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

logger = logging.getLogger(__name__)


class AmbiguityType(Enum):
    """Types of ambiguity in requirements."""
    VAGUE_TERMS = "vague_terms"           # Words like "fast", "user-friendly"
    INCOMPLETE = "incomplete"              # Missing details
    INCONSISTENT = "inconsistent"          # Contradicting statements
    UNMEASURABLE = "unmeasurable"          # No success criteria
    IMPLICIT = "implicit"                  # Assumed knowledge


class FeasibilityStatus(Enum):
    """Feasibility check result."""
    FEASIBLE = "feasible"
    NEEDS_CLARIFICATION = "needs_clarification"
    HIGH_RISK = "high_risk"
    INFEASIBLE = "infeasible"


class PriorityLevel(Enum):
    """Priority levels for requirements."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    NICE_TO_HAVE = 5


@dataclass
class AmbiguityIssue:
    """An identified ambiguity in a requirement."""
    issue_id: str
    ambiguity_type: AmbiguityType
    location: str  # Where in the requirement
    description: str
    suggestion: str
    severity: str = "medium"  # low, medium, high


@dataclass
class FeasibilityCheck:
    """Result of a feasibility check."""
    check_id: str
    status: FeasibilityStatus
    factors: List[Dict[str, Any]]
    risks: List[str]
    recommendations: List[str]
    confidence: float  # 0.0 to 1.0


@dataclass
class AcceptanceCriterion:
    """A parsed acceptance criterion."""
    criterion_id: str
    text: str
    testable: bool
    given: Optional[str] = None
    when: Optional[str] = None
    then: Optional[str] = None
    validation_method: str = "manual"


@dataclass
class RequirementAnalysis:
    """Complete analysis of a requirement."""
    req_id: str
    title: str
    complexity: str  # low, medium, high, critical
    ambiguities: List[AmbiguityIssue]
    feasibility: FeasibilityCheck
    acceptance_criteria: List[AcceptanceCriterion]
    priority: PriorityLevel
    estimated_effort: str
    quality_score: float  # 0.0 to 1.0
    dependencies: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


class RequirementAnalyzer:
    """
    Analyzes requirements for quality and completeness.

    Implements:
    - ambiguity_detection: Find unclear or vague language
    - feasibility_check: Assess technical feasibility
    - prioritization: Rank requirements by importance
    - acceptance_criteria: Extract and validate ACs
    """

    # Vague terms that indicate ambiguity
    VAGUE_TERMS = {
        'fast', 'quick', 'user-friendly', 'easy', 'simple', 'flexible',
        'scalable', 'efficient', 'intuitive', 'robust', 'seamless',
        'appropriate', 'adequate', 'reasonable', 'as needed', 'etc',
        'various', 'some', 'several', 'many', 'few', 'lots'
    }

    # Technical constraint keywords
    TECHNICAL_KEYWORDS = {
        'api', 'database', 'authentication', 'authorization', 'encryption',
        'real-time', 'concurrent', 'distributed', 'microservice', 'kubernetes',
        'ml', 'ai', 'machine learning', 'neural', 'gpu'
    }

    def __init__(self):
        """Initialize the analyzer."""
        self._analyses: Dict[str, RequirementAnalysis] = {}

    def analyze(
        self,
        req_id: str,
        title: str,
        description: str,
        acceptance_criteria: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None
    ) -> RequirementAnalysis:
        """
        Perform full analysis on a requirement.

        Args:
            req_id: Requirement identifier
            title: Requirement title
            description: Full description text
            acceptance_criteria: List of AC strings
            constraints: Technical/business constraints

        Returns:
            Complete RequirementAnalysis
        """
        logger.info(f"Analyzing requirement {req_id}")

        acceptance_criteria = acceptance_criteria or []
        constraints = constraints or {}

        # Detect ambiguities
        ambiguities = self.detect_ambiguity(title, description)

        # Check feasibility
        feasibility = self.check_feasibility(description, constraints)

        # Extract and parse acceptance criteria
        parsed_acs = self.extract_acceptance_criteria(acceptance_criteria)

        # Calculate priority
        priority = self.calculate_priority(
            title, description, constraints.get('priority_factors', {})
        )

        # Estimate complexity
        complexity = self._estimate_complexity(description, parsed_acs)

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            ambiguities, feasibility, parsed_acs
        )

        # Extract dependencies
        dependencies = self._extract_dependencies(description)

        analysis = RequirementAnalysis(
            req_id=req_id,
            title=title,
            complexity=complexity,
            ambiguities=ambiguities,
            feasibility=feasibility,
            acceptance_criteria=parsed_acs,
            priority=priority,
            estimated_effort=self._estimate_effort(complexity),
            quality_score=quality_score,
            dependencies=dependencies
        )

        self._analyses[req_id] = analysis

        logger.info(
            f"Analysis complete for {req_id}: "
            f"complexity={complexity}, quality={quality_score:.2f}"
        )

        return analysis

    def detect_ambiguity(
        self,
        title: str,
        description: str
    ) -> List[AmbiguityIssue]:
        """
        Detect ambiguities in requirement text.

        Implements ambiguity_detection to find unclear language.
        """
        issues = []
        combined_text = f"{title} {description}".lower()
        words = combined_text.split()

        # Check for vague terms
        for term in self.VAGUE_TERMS:
            if term in combined_text:
                issues.append(AmbiguityIssue(
                    issue_id=str(uuid.uuid4()),
                    ambiguity_type=AmbiguityType.VAGUE_TERMS,
                    location=f"Found: '{term}'",
                    description=f"Vague term '{term}' lacks specific criteria",
                    suggestion=f"Replace '{term}' with measurable criteria",
                    severity="medium"
                ))

        # Check for incomplete sentences
        if description and len(description) < 50:
            issues.append(AmbiguityIssue(
                issue_id=str(uuid.uuid4()),
                ambiguity_type=AmbiguityType.INCOMPLETE,
                location="Description",
                description="Description seems too brief for a complete requirement",
                suggestion="Expand description with more context and details",
                severity="high"
            ))

        # Check for missing actors
        actor_patterns = ['user', 'admin', 'system', 'service', 'customer']
        has_actor = any(actor in combined_text for actor in actor_patterns)
        if not has_actor:
            issues.append(AmbiguityIssue(
                issue_id=str(uuid.uuid4()),
                ambiguity_type=AmbiguityType.IMPLICIT,
                location="Actor",
                description="No clear actor/user role specified",
                suggestion="Specify who will use or be affected by this feature",
                severity="medium"
            ))

        # Check for unmeasurable success criteria
        measurement_patterns = [
            r'\d+%', r'\d+\s*(second|minute|hour|ms)',
            r'(increase|decrease|reduce)\s+by',
            r'at least', r'no more than'
        ]
        has_measurement = any(
            re.search(p, combined_text) for p in measurement_patterns
        )
        if not has_measurement and len(description) > 100:
            issues.append(AmbiguityIssue(
                issue_id=str(uuid.uuid4()),
                ambiguity_type=AmbiguityType.UNMEASURABLE,
                location="Success criteria",
                description="No measurable success criteria found",
                suggestion="Add specific metrics (e.g., '< 200ms response time')",
                severity="high"
            ))

        return issues

    def check_feasibility(
        self,
        description: str,
        constraints: Dict[str, Any]
    ) -> FeasibilityCheck:
        """
        Check technical and business feasibility.

        Implements feasibility_check against constraints.
        """
        factors = []
        risks = []
        recommendations = []
        desc_lower = description.lower()

        # Check for complex technical requirements
        tech_complexity = sum(
            1 for kw in self.TECHNICAL_KEYWORDS if kw in desc_lower
        )

        if tech_complexity > 3:
            factors.append({
                "factor": "technical_complexity",
                "level": "high",
                "detail": f"Found {tech_complexity} complex technical elements"
            })
            risks.append("High technical complexity may require specialist skills")

        # Check against resource constraints
        budget = constraints.get('budget')
        if budget and tech_complexity > 2:
            factors.append({
                "factor": "budget_risk",
                "level": "medium",
                "detail": "Complex requirements may exceed budget"
            })
            risks.append("Budget may be insufficient for full scope")
            recommendations.append("Consider phased implementation")

        # Check timeline constraints
        deadline = constraints.get('deadline')
        if deadline and tech_complexity > 3:
            factors.append({
                "factor": "timeline_risk",
                "level": "high",
                "detail": "Complex requirements may miss deadline"
            })
            risks.append("Timeline risk due to complexity")
            recommendations.append("Prioritize MVP features first")

        # Check for integration requirements
        if any(term in desc_lower for term in ['integrate', 'connect', 'sync', 'api']):
            factors.append({
                "factor": "integration_dependency",
                "level": "medium",
                "detail": "External integration required"
            })
            risks.append("Integration may depend on external systems")
            recommendations.append("Validate external API availability early")

        # Determine overall status
        high_risk_count = sum(1 for f in factors if f.get('level') == 'high')
        if high_risk_count >= 2:
            status = FeasibilityStatus.HIGH_RISK
            confidence = 0.5
        elif high_risk_count == 1:
            status = FeasibilityStatus.NEEDS_CLARIFICATION
            confidence = 0.7
        elif len(factors) > 0:
            status = FeasibilityStatus.FEASIBLE
            confidence = 0.8
        else:
            status = FeasibilityStatus.FEASIBLE
            confidence = 0.9

        return FeasibilityCheck(
            check_id=str(uuid.uuid4()),
            status=status,
            factors=factors,
            risks=risks,
            recommendations=recommendations,
            confidence=confidence
        )

    def extract_acceptance_criteria(
        self,
        criteria_list: List[str]
    ) -> List[AcceptanceCriterion]:
        """
        Extract and parse acceptance criteria.

        Implements acceptance_criteria extraction with Gherkin support.
        """
        parsed = []

        for i, criterion in enumerate(criteria_list, 1):
            ac = self._parse_single_criterion(f"AC-{i}", criterion)
            parsed.append(ac)

        return parsed

    def _parse_single_criterion(
        self,
        criterion_id: str,
        text: str
    ) -> AcceptanceCriterion:
        """Parse a single acceptance criterion."""
        # Try to parse Gherkin format
        given = when = then = None
        text_lower = text.lower()

        given_match = re.search(r'given\s+(.+?)(?=when|$)', text_lower)
        when_match = re.search(r'when\s+(.+?)(?=then|$)', text_lower)
        then_match = re.search(r'then\s+(.+?)$', text_lower)

        if given_match:
            given = given_match.group(1).strip()
        if when_match:
            when = when_match.group(1).strip()
        if then_match:
            then = then_match.group(1).strip()

        # Determine if testable
        testable = self._is_testable_criterion(text)

        # Determine validation method
        if any(word in text_lower for word in ['api', 'endpoint', 'response']):
            validation = "automated_api"
        elif any(word in text_lower for word in ['ui', 'screen', 'button', 'display']):
            validation = "automated_ui"
        elif then or testable:
            validation = "automated"
        else:
            validation = "manual"

        return AcceptanceCriterion(
            criterion_id=criterion_id,
            text=text,
            testable=testable,
            given=given,
            when=when,
            then=then,
            validation_method=validation
        )

    def _is_testable_criterion(self, text: str) -> bool:
        """Check if a criterion is testable."""
        # Testable indicators
        testable_patterns = [
            r'\d+',                    # Numbers
            r'(must|should|shall)',    # Modal verbs
            r'(display|show|return)',  # Observable actions
            r'(error|success|fail)',   # Expected outcomes
            r'given|when|then',        # Gherkin
        ]
        return any(re.search(p, text.lower()) for p in testable_patterns)

    def calculate_priority(
        self,
        title: str,
        description: str,
        factors: Dict[str, Any]
    ) -> PriorityLevel:
        """
        Calculate requirement priority.

        Implements prioritization based on multiple factors.
        """
        score = 3  # Start at medium

        combined = f"{title} {description}".lower()

        # Check for urgency indicators
        if any(word in combined for word in ['critical', 'urgent', 'blocking', 'security']):
            score -= 2

        if any(word in combined for word in ['important', 'required', 'must']):
            score -= 1

        if any(word in combined for word in ['nice to have', 'optional', 'future']):
            score += 1

        # Apply external factors
        business_value = factors.get('business_value', 5)
        if business_value >= 8:
            score -= 1
        elif business_value <= 3:
            score += 1

        user_impact = factors.get('user_impact', 5)
        if user_impact >= 8:
            score -= 1

        # Clamp to valid range
        score = max(1, min(5, score))

        return PriorityLevel(score)

    def _estimate_complexity(
        self,
        description: str,
        acs: List[AcceptanceCriterion]
    ) -> str:
        """Estimate requirement complexity."""
        # Word count factor
        word_count = len(description.split())

        # AC count factor
        ac_count = len(acs)

        # Technical terms factor
        tech_count = sum(
            1 for kw in self.TECHNICAL_KEYWORDS
            if kw in description.lower()
        )

        # Calculate score
        score = (word_count / 50) + (ac_count * 0.5) + (tech_count * 2)

        if score <= 3:
            return "low"
        elif score <= 6:
            return "medium"
        elif score <= 10:
            return "high"
        else:
            return "critical"

    def _estimate_effort(self, complexity: str) -> str:
        """Estimate effort based on complexity."""
        effort_map = {
            "low": "1-2 days",
            "medium": "3-5 days",
            "high": "1-2 weeks",
            "critical": "2-4 weeks"
        }
        return effort_map.get(complexity, "unknown")

    def _calculate_quality_score(
        self,
        ambiguities: List[AmbiguityIssue],
        feasibility: FeasibilityCheck,
        acs: List[AcceptanceCriterion]
    ) -> float:
        """Calculate overall quality score for the requirement."""
        score = 1.0

        # Deduct for ambiguities
        for amb in ambiguities:
            if amb.severity == "high":
                score -= 0.15
            elif amb.severity == "medium":
                score -= 0.08
            else:
                score -= 0.03

        # Adjust for feasibility
        score *= feasibility.confidence

        # Bonus for testable ACs
        if acs:
            testable_ratio = sum(1 for ac in acs if ac.testable) / len(acs)
            score *= (0.7 + 0.3 * testable_ratio)

        return max(0.0, min(1.0, score))

    def _extract_dependencies(self, description: str) -> List[str]:
        """Extract mentioned dependencies from description."""
        dependencies = []

        # Look for issue references
        issue_refs = re.findall(r'[A-Z]+-\d+', description)
        dependencies.extend(issue_refs)

        # Look for "depends on" phrases
        depends_matches = re.findall(
            r'depends?\s+on\s+["\']?([^"\'.,]+)["\']?',
            description.lower()
        )
        dependencies.extend(depends_matches)

        return list(set(dependencies))

    def get_analysis(self, req_id: str) -> Optional[RequirementAnalysis]:
        """Get stored analysis for a requirement."""
        return self._analyses.get(req_id)

    def get_all_analyses(self) -> Dict[str, RequirementAnalysis]:
        """Get all stored analyses."""
        return self._analyses.copy()


# Factory function
def create_requirement_analyzer() -> RequirementAnalyzer:
    """Create a new RequirementAnalyzer instance."""
    return RequirementAnalyzer()
