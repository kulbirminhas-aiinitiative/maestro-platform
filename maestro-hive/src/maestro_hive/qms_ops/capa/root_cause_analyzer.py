"""
AI-Powered Root Cause Analyzer Module
======================================

Provides intelligent root cause analysis using multiple methodologies.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class AnalysisMethod(Enum):
    """Root cause analysis methodologies."""
    FIVE_WHYS = "five_whys"
    FISHBONE = "fishbone"
    PARETO = "pareto"
    FMEA = "fmea"
    FAULT_TREE = "fault_tree"
    AI_ASSISTED = "ai_assisted"


class CauseCategory(Enum):
    """Fishbone/Ishikawa categories."""
    PEOPLE = "people"
    PROCESS = "process"
    EQUIPMENT = "equipment"
    MATERIALS = "materials"
    ENVIRONMENT = "environment"
    MEASUREMENT = "measurement"


@dataclass
class CauseNode:
    """Node in a cause tree."""
    id: str
    description: str
    category: CauseCategory
    level: int
    parent_id: Optional[str] = None
    is_root_cause: bool = False
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)


@dataclass
class FiveWhyStep:
    """Single step in Five Whys analysis."""
    level: int
    why_question: str
    answer: str
    is_root: bool = False
    confidence: float = 0.0


@dataclass
class FishboneCause:
    """Cause in Fishbone diagram."""
    category: CauseCategory
    primary_causes: List[str]
    secondary_causes: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class RootCauseResult:
    """Result of root cause analysis."""
    id: str
    method: AnalysisMethod
    problem_statement: str
    root_causes: List[str]
    contributing_factors: List[str]
    confidence_score: float
    analysis_data: Dict[str, Any]
    recommendations: List[str]
    analyzed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def primary_root_cause(self) -> Optional[str]:
        """Get the primary (highest confidence) root cause."""
        if self.root_causes:
            return self.root_causes[0]
        return None


class FiveWhysAnalyzer:
    """Performs Five Whys analysis."""

    def __init__(self, max_depth: int = 5):
        self.max_depth = max_depth

    def analyze(
        self,
        problem: str,
        answers: List[str],
        context: Dict[str, Any] = None
    ) -> List[FiveWhyStep]:
        """
        Perform Five Whys analysis.

        Args:
            problem: The initial problem statement
            answers: List of answers to each "Why?"
            context: Optional context data

        Returns:
            List of FiveWhyStep objects
        """
        steps = []
        current_problem = problem

        for i, answer in enumerate(answers[:self.max_depth]):
            step = FiveWhyStep(
                level=i + 1,
                why_question=f"Why {i + 1}: Why does {current_problem}?",
                answer=answer,
                is_root=i == len(answers) - 1,
                confidence=0.9 - (i * 0.1)  # Confidence decreases with depth
            )
            steps.append(step)
            current_problem = answer.lower()

        return steps

    def suggest_next_why(
        self,
        steps: List[FiveWhyStep],
        context: Dict[str, Any] = None
    ) -> str:
        """AI-assisted suggestion for next Why question."""
        if not steps:
            return "Why did this problem occur?"

        last_answer = steps[-1].answer
        # Simple heuristic-based suggestion
        suggestions = {
            "training": "Why was the training inadequate or missing?",
            "process": "Why did the process fail to prevent this?",
            "equipment": "Why did the equipment malfunction?",
            "material": "Why was the material defective or unsuitable?",
            "human": "Why did the human error occur?",
            "communication": "Why was communication ineffective?",
        }

        for keyword, suggestion in suggestions.items():
            if keyword in last_answer.lower():
                return suggestion

        return f"Why did '{last_answer}' occur?"


class FishboneAnalyzer:
    """Performs Fishbone (Ishikawa) diagram analysis."""

    def analyze(
        self,
        problem: str,
        causes_by_category: Dict[CauseCategory, List[str]],
        context: Dict[str, Any] = None
    ) -> List[FishboneCause]:
        """
        Perform Fishbone analysis.

        Args:
            problem: The effect/problem to analyze
            causes_by_category: Causes organized by category
            context: Optional context data

        Returns:
            List of FishboneCause objects
        """
        fishbone_causes = []

        for category in CauseCategory:
            causes = causes_by_category.get(category, [])
            if causes:
                fishbone_cause = FishboneCause(
                    category=category,
                    primary_causes=causes,
                    secondary_causes={}
                )
                fishbone_causes.append(fishbone_cause)

        return fishbone_causes

    def identify_likely_categories(
        self,
        problem: str,
        context: Dict[str, Any] = None
    ) -> List[Tuple[CauseCategory, float]]:
        """
        AI-assisted identification of likely cause categories.

        Returns:
            List of (category, probability) tuples
        """
        # Keyword-based category identification
        category_keywords = {
            CauseCategory.PEOPLE: ["operator", "training", "skill", "human", "staff", "personnel"],
            CauseCategory.PROCESS: ["procedure", "method", "workflow", "step", "sop"],
            CauseCategory.EQUIPMENT: ["machine", "tool", "equipment", "device", "calibration"],
            CauseCategory.MATERIALS: ["material", "component", "part", "supply", "raw"],
            CauseCategory.ENVIRONMENT: ["temperature", "humidity", "contamination", "clean", "environment"],
            CauseCategory.MEASUREMENT: ["measure", "test", "inspection", "gauge", "accuracy"],
        }

        scores = []
        problem_lower = problem.lower()

        for category, keywords in category_keywords.items():
            score = sum(1 for kw in keywords if kw in problem_lower)
            probability = min(0.9, 0.3 + (score * 0.15))
            scores.append((category, probability))

        # Sort by probability descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores


class AIRootCauseEngine:
    """
    AI-powered root cause analysis engine.

    Combines multiple methodologies and provides intelligent suggestions.
    """

    def __init__(self):
        self.five_whys = FiveWhysAnalyzer()
        self.fishbone = FishboneAnalyzer()
        self.logger = logging.getLogger("qms-rca")

    def analyze_problem(
        self,
        problem: str,
        symptoms: List[str],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Perform AI-assisted initial analysis.

        Args:
            problem: Problem statement
            symptoms: Observable symptoms
            context: Additional context

        Returns:
            Analysis suggestions and probable causes
        """
        context = context or {}

        # Identify likely cause categories
        category_scores = self.fishbone.identify_likely_categories(problem, context)

        # Generate analysis suggestions
        suggestions = {
            "primary_categories": [c.value for c, _ in category_scores[:3]],
            "recommended_methods": self._recommend_methods(problem, symptoms),
            "initial_questions": self._generate_initial_questions(problem, symptoms),
            "similar_patterns": self._find_similar_patterns(problem, context),
        }

        return suggestions

    def _recommend_methods(
        self,
        problem: str,
        symptoms: List[str]
    ) -> List[Dict[str, Any]]:
        """Recommend analysis methods based on problem characteristics."""
        recommendations = []

        # Five Whys for focused, single-cause problems
        if len(symptoms) <= 3:
            recommendations.append({
                "method": AnalysisMethod.FIVE_WHYS.value,
                "rationale": "Best for focused problems with apparent causal chain",
                "priority": 1
            })

        # Fishbone for complex, multi-factor problems
        if len(symptoms) > 3:
            recommendations.append({
                "method": AnalysisMethod.FISHBONE.value,
                "rationale": "Best for complex problems with multiple potential causes",
                "priority": 1
            })

        # Always suggest AI-assisted for comprehensive analysis
        recommendations.append({
            "method": AnalysisMethod.AI_ASSISTED.value,
            "rationale": "Combines multiple methods with pattern recognition",
            "priority": 2
        })

        return recommendations

    def _generate_initial_questions(
        self,
        problem: str,
        symptoms: List[str]
    ) -> List[str]:
        """Generate initial investigation questions."""
        questions = [
            "When did this problem first occur?",
            "Has anything changed recently (process, equipment, materials, personnel)?",
            "Is this problem intermittent or constant?",
            "What is the scope of the problem (how many units/processes affected)?",
            "Have similar problems occurred before?",
        ]

        # Add symptom-specific questions
        for symptom in symptoms[:3]:
            questions.append(f"What conditions exist when '{symptom}' is observed?")

        return questions

    def _find_similar_patterns(
        self,
        problem: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find similar historical patterns (placeholder for ML integration)."""
        # In a real implementation, this would query a historical database
        return []


class RootCauseAnalyzer:
    """
    Main root cause analysis interface.

    Provides unified access to multiple RCA methodologies with AI assistance.
    """

    def __init__(self):
        self.ai_engine = AIRootCauseEngine()
        self.results: Dict[str, RootCauseResult] = {}
        self.logger = logging.getLogger("qms-rca")
        self._configure_logger()

    def _configure_logger(self) -> None:
        """Configure logger."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def analyze(
        self,
        problem_statement: str,
        method: AnalysisMethod,
        analysis_data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> RootCauseResult:
        """
        Perform root cause analysis.

        Args:
            problem_statement: Clear statement of the problem
            method: Analysis methodology to use
            analysis_data: Method-specific analysis data
            context: Additional context

        Returns:
            RootCauseResult with findings
        """
        import uuid

        result_id = f"RCA-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        if method == AnalysisMethod.FIVE_WHYS:
            result = self._analyze_five_whys(result_id, problem_statement, analysis_data)
        elif method == AnalysisMethod.FISHBONE:
            result = self._analyze_fishbone(result_id, problem_statement, analysis_data)
        elif method == AnalysisMethod.AI_ASSISTED:
            result = self._analyze_ai_assisted(result_id, problem_statement, analysis_data, context)
        else:
            # Default analysis
            result = RootCauseResult(
                id=result_id,
                method=method,
                problem_statement=problem_statement,
                root_causes=[],
                contributing_factors=[],
                confidence_score=0.5,
                analysis_data=analysis_data,
                recommendations=[],
                analyzed_at=datetime.utcnow()
            )

        self.results[result_id] = result
        self.logger.info(
            f"RCA_COMPLETE | id={result_id} | method={method.value} | "
            f"root_causes={len(result.root_causes)} | confidence={result.confidence_score:.2f}"
        )

        return result

    def _analyze_five_whys(
        self,
        result_id: str,
        problem: str,
        data: Dict[str, Any]
    ) -> RootCauseResult:
        """Perform Five Whys analysis."""
        answers = data.get("answers", [])
        steps = self.ai_engine.five_whys.analyze(problem, answers)

        root_causes = [s.answer for s in steps if s.is_root]
        contributing_factors = [s.answer for s in steps if not s.is_root]

        # Calculate confidence based on depth and consistency
        confidence = 0.9 if len(steps) >= 4 else 0.7

        recommendations = [
            f"Address root cause: {rc}" for rc in root_causes
        ]
        recommendations.append("Verify root cause through testing before implementing solutions")

        return RootCauseResult(
            id=result_id,
            method=AnalysisMethod.FIVE_WHYS,
            problem_statement=problem,
            root_causes=root_causes,
            contributing_factors=contributing_factors,
            confidence_score=confidence,
            analysis_data={"steps": [{"level": s.level, "question": s.why_question, "answer": s.answer} for s in steps]},
            recommendations=recommendations,
            analyzed_at=datetime.utcnow()
        )

    def _analyze_fishbone(
        self,
        result_id: str,
        problem: str,
        data: Dict[str, Any]
    ) -> RootCauseResult:
        """Perform Fishbone analysis."""
        causes_by_category = {}
        for cat_name, causes in data.get("causes", {}).items():
            try:
                category = CauseCategory(cat_name.lower())
                causes_by_category[category] = causes
            except ValueError:
                continue

        fishbone_causes = self.ai_engine.fishbone.analyze(problem, causes_by_category)

        # Identify most likely root causes (categories with most causes)
        root_causes = []
        contributing_factors = []

        for fc in fishbone_causes:
            if len(fc.primary_causes) >= 2:
                root_causes.extend(fc.primary_causes[:1])
            contributing_factors.extend(fc.primary_causes[1:])

        confidence = min(0.85, 0.5 + (len(fishbone_causes) * 0.1))

        recommendations = [
            f"Investigate {fc.category.value}: {', '.join(fc.primary_causes[:2])}"
            for fc in fishbone_causes if fc.primary_causes
        ]

        return RootCauseResult(
            id=result_id,
            method=AnalysisMethod.FISHBONE,
            problem_statement=problem,
            root_causes=root_causes,
            contributing_factors=contributing_factors,
            confidence_score=confidence,
            analysis_data={
                "fishbone": [
                    {"category": fc.category.value, "causes": fc.primary_causes}
                    for fc in fishbone_causes
                ]
            },
            recommendations=recommendations,
            analyzed_at=datetime.utcnow()
        )

    def _analyze_ai_assisted(
        self,
        result_id: str,
        problem: str,
        data: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> RootCauseResult:
        """Perform AI-assisted comprehensive analysis."""
        symptoms = data.get("symptoms", [])

        # Get AI suggestions
        suggestions = self.ai_engine.analyze_problem(problem, symptoms, context)

        # Combine with provided analysis
        root_causes = data.get("identified_causes", [])
        if not root_causes and suggestions["primary_categories"]:
            root_causes = [f"Likely related to {cat}" for cat in suggestions["primary_categories"][:2]]

        contributing_factors = data.get("contributing_factors", [])

        # Generate recommendations
        recommendations = [
            f"Investigate: {q}" for q in suggestions["initial_questions"][:3]
        ]
        recommendations.extend([
            f"Use {m['method']} analysis: {m['rationale']}"
            for m in suggestions["recommended_methods"][:2]
        ])

        return RootCauseResult(
            id=result_id,
            method=AnalysisMethod.AI_ASSISTED,
            problem_statement=problem,
            root_causes=root_causes,
            contributing_factors=contributing_factors,
            confidence_score=0.75,
            analysis_data={
                "symptoms": symptoms,
                "ai_suggestions": suggestions,
                "provided_data": data
            },
            recommendations=recommendations,
            analyzed_at=datetime.utcnow()
        )

    def get_result(self, result_id: str) -> Optional[RootCauseResult]:
        """Get analysis result by ID."""
        return self.results.get(result_id)

    def suggest_analysis(
        self,
        problem: str,
        symptoms: List[str],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Get AI suggestions for root cause analysis."""
        return self.ai_engine.analyze_problem(problem, symptoms, context)
