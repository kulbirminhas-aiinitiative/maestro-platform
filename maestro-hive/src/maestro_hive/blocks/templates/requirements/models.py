"""
Document Template Models

Core data models for document templates supporting:
- Sections with prompts and variables (AC-2)
- Persona mapping (AC-3)
- Quality scoring metadata (AC-4)

Reference: MD-2515 Document Templates - Requirements Phase
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime
import re


class PersonaRole(Enum):
    """Persona roles for document lifecycle management (AC-3)."""
    CREATOR = "creator"
    REVIEWER = "reviewer"
    APPROVER = "approver"


@dataclass
class TemplateVariable:
    """
    Template variable definition (AC-2).

    Variables are placeholders that get populated during document generation.
    """
    name: str
    description: str
    var_type: str = "string"  # string, list, dict, date, number
    required: bool = True
    default_value: Optional[Any] = None
    validation_pattern: Optional[str] = None

    def validate(self, value: Any) -> bool:
        """Validate a value against this variable's constraints."""
        if value is None:
            return not self.required

        if self.var_type == "string" and self.validation_pattern:
            return bool(re.match(self.validation_pattern, str(value)))

        if self.var_type == "number":
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False

        if self.var_type == "list":
            return isinstance(value, (list, tuple))

        if self.var_type == "dict":
            return isinstance(value, dict)

        return True

    def get_placeholder(self) -> str:
        """Get the placeholder string for this variable."""
        return f"{{{{{self.name}}}}}"


@dataclass
class TemplatePrompt:
    """
    AI generation prompt for a template section (AC-2).

    Prompts guide AI assistants in generating content for each section.
    """
    prompt_id: str
    text: str
    context_variables: List[str] = field(default_factory=list)
    output_format: str = "markdown"  # markdown, plain, json
    max_tokens: int = 1000
    temperature: float = 0.7

    def render(self, variables: Dict[str, Any]) -> str:
        """Render the prompt with variable substitution."""
        rendered = self.text
        for var_name in self.context_variables:
            if var_name in variables:
                placeholder = f"{{{{{var_name}}}}}"
                rendered = rendered.replace(placeholder, str(variables[var_name]))
        return rendered


@dataclass
class TemplateSection:
    """
    Document section definition (AC-2).

    Sections define the structure of a document template.
    """
    section_id: str
    title: str
    description: str
    required: bool = True
    order: int = 0
    prompts: List[TemplatePrompt] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    subsections: List["TemplateSection"] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)

    def get_required_variables(self) -> List[str]:
        """Get all variables required by this section and subsections."""
        all_vars = list(self.variables)
        for prompt in self.prompts:
            all_vars.extend(prompt.context_variables)
        for subsection in self.subsections:
            all_vars.extend(subsection.get_required_variables())
        return list(set(all_vars))


@dataclass
class PersonaMapping:
    """
    Persona role mapping for document lifecycle (AC-3).

    Maps standard persona roles to specific job titles/functions.
    """
    role: PersonaRole
    title: str
    responsibilities: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    approval_weight: float = 1.0  # Weight in approval decisions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "role": self.role.value,
            "title": self.title,
            "responsibilities": self.responsibilities,
            "required_skills": self.required_skills,
            "approval_weight": self.approval_weight,
        }


@dataclass
class QualityScore:
    """
    Quality score for a single category (AC-4).
    """
    category: str
    score: float
    max_score: float
    details: str = ""
    issues: List[str] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        """Get score as percentage."""
        return (self.score / self.max_score * 100) if self.max_score > 0 else 0

    @property
    def passed(self) -> bool:
        """Check if score meets minimum threshold (70%)."""
        return self.percentage >= 70


@dataclass
class QualityScoringConfig:
    """
    Quality scoring configuration for a template (AC-4).

    Defines how documents are scored for quality validation.
    """
    completeness_weight: float = 25.0
    consistency_weight: float = 25.0
    clarity_weight: float = 25.0
    traceability_weight: float = 25.0
    pass_threshold: float = 70.0
    required_sections: List[str] = field(default_factory=list)
    terminology_glossary: Dict[str, str] = field(default_factory=dict)

    @property
    def total_weight(self) -> float:
        """Get total weight across all categories."""
        return (
            self.completeness_weight +
            self.consistency_weight +
            self.clarity_weight +
            self.traceability_weight
        )

    def normalize_weights(self) -> None:
        """Normalize weights to sum to 100."""
        total = self.total_weight
        if total > 0:
            factor = 100 / total
            self.completeness_weight *= factor
            self.consistency_weight *= factor
            self.clarity_weight *= factor
            self.traceability_weight *= factor


@dataclass
class ValidationResult:
    """
    Result of document validation against template rules.
    """
    valid: bool
    total_score: float
    max_score: float = 100.0
    category_scores: Dict[str, QualityScore] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def passed(self) -> bool:
        """Check if validation passed quality gate."""
        return self.valid and self.total_score >= 70

    def add_category_score(self, score: QualityScore) -> None:
        """Add a category score to the result."""
        self.category_scores[score.category] = score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "valid": self.valid,
            "passed": self.passed,
            "total_score": self.total_score,
            "max_score": self.max_score,
            "category_scores": {
                k: {
                    "score": v.score,
                    "max": v.max_score,
                    "percentage": v.percentage,
                    "details": v.details,
                }
                for k, v in self.category_scores.items()
            },
            "errors": self.errors,
            "warnings": self.warnings,
            "validated_at": self.validated_at.isoformat(),
        }


@dataclass
class RenderedDocument:
    """
    A fully rendered document from a template.
    """
    template_id: str
    template_name: str
    content: str
    variables_used: Dict[str, Any] = field(default_factory=dict)
    sections_rendered: List[str] = field(default_factory=list)
    rendered_at: datetime = field(default_factory=datetime.utcnow)
    format: str = "markdown"
    validation_result: Optional[ValidationResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "content": self.content,
            "variables_used": self.variables_used,
            "sections_rendered": self.sections_rendered,
            "rendered_at": self.rendered_at.isoformat(),
            "format": self.format,
            "validation": self.validation_result.to_dict() if self.validation_result else None,
        }


@dataclass
class DocumentTemplate:
    """
    Base document template class (AC-1, AC-2, AC-3, AC-4).

    Provides the foundation for all document templates with:
    - Sections and prompts
    - Variable management
    - Persona mappings
    - Quality scoring
    """
    template_id: str
    name: str
    description: str
    phase: str = "requirements"
    version: str = "1.0.0"
    sections: List[TemplateSection] = field(default_factory=list)
    variables: List[TemplateVariable] = field(default_factory=list)
    personas: Dict[PersonaRole, PersonaMapping] = field(default_factory=dict)
    quality_config: QualityScoringConfig = field(default_factory=QualityScoringConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_variable(self, name: str) -> Optional[TemplateVariable]:
        """Get a variable by name."""
        for var in self.variables:
            if var.name == name:
                return var
        return None

    def get_required_variables(self) -> List[TemplateVariable]:
        """Get all required variables."""
        return [v for v in self.variables if v.required]

    def get_persona(self, role: PersonaRole) -> Optional[PersonaMapping]:
        """Get persona mapping for a role."""
        return self.personas.get(role)

    def validate_variables(self, values: Dict[str, Any]) -> List[str]:
        """Validate variable values, returning list of errors."""
        errors = []
        for var in self.variables:
            if var.required and var.name not in values:
                errors.append(f"Required variable '{var.name}' is missing")
            elif var.name in values and not var.validate(values[var.name]):
                errors.append(f"Variable '{var.name}' failed validation")
        return errors

    def render(self, variables: Dict[str, Any]) -> RenderedDocument:
        """
        Render the template with provided variables.

        Returns a RenderedDocument with the generated content.
        """
        # Validate variables first
        errors = self.validate_variables(variables)
        if errors:
            # Return document with validation errors
            return RenderedDocument(
                template_id=self.template_id,
                template_name=self.name,
                content="",
                variables_used=variables,
                validation_result=ValidationResult(
                    valid=False,
                    total_score=0,
                    errors=errors,
                ),
            )

        # Build document content
        content_parts = []
        sections_rendered = []

        # Add header
        content_parts.append(f"# {self.name}")
        content_parts.append("")
        content_parts.append(f"**Version:** {variables.get('version', '1.0')}")
        content_parts.append(f"**Project:** {variables.get('project_name', 'Unknown')}")
        content_parts.append(f"**Generated:** {datetime.utcnow().isoformat()}")
        content_parts.append("")
        content_parts.append("---")
        content_parts.append("")

        # Render each section
        for section in sorted(self.sections, key=lambda s: s.order):
            section_content = self._render_section(section, variables)
            content_parts.append(section_content)
            sections_rendered.append(section.section_id)

        return RenderedDocument(
            template_id=self.template_id,
            template_name=self.name,
            content="\n".join(content_parts),
            variables_used=variables,
            sections_rendered=sections_rendered,
            format="markdown",
        )

    def _render_section(
        self,
        section: TemplateSection,
        variables: Dict[str, Any],
        depth: int = 2
    ) -> str:
        """Render a single section with variable substitution."""
        parts = []

        # Section header
        header_prefix = "#" * depth
        parts.append(f"{header_prefix} {section.title}")
        parts.append("")

        # Section description with variable substitution
        desc = section.description
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            if placeholder in desc:
                desc = desc.replace(placeholder, str(var_value))
        parts.append(desc)
        parts.append("")

        # Render subsections
        for subsection in sorted(section.subsections, key=lambda s: s.order):
            parts.append(self._render_section(subsection, variables, depth + 1))

        return "\n".join(parts)

    def validate(self, document: RenderedDocument) -> ValidationResult:
        """
        Validate a rendered document against quality rules (AC-4).

        Returns ValidationResult with scores and issues.
        """
        result = ValidationResult(valid=True, total_score=0)

        # Completeness check
        completeness = self._check_completeness(document)
        result.add_category_score(completeness)

        # Consistency check
        consistency = self._check_consistency(document)
        result.add_category_score(consistency)

        # Clarity check
        clarity = self._check_clarity(document)
        result.add_category_score(clarity)

        # Traceability check
        traceability = self._check_traceability(document)
        result.add_category_score(traceability)

        # Calculate total score
        result.total_score = sum(s.score for s in result.category_scores.values())
        result.valid = result.total_score >= self.quality_config.pass_threshold

        return result

    def _check_completeness(self, document: RenderedDocument) -> QualityScore:
        """Check document completeness."""
        max_score = self.quality_config.completeness_weight
        issues = []

        # Check required sections
        required = set(self.quality_config.required_sections)
        rendered = set(document.sections_rendered)
        missing = required - rendered

        if missing:
            issues.extend([f"Missing section: {s}" for s in missing])

        # Check for empty placeholders
        placeholder_pattern = r'\{\{[^}]+\}\}'
        if re.search(placeholder_pattern, document.content):
            issues.append("Document contains unresolved placeholders")

        # Calculate score
        section_score = (1 - len(missing) / max(len(required), 1)) if required else 1
        placeholder_penalty = 0.2 if re.search(placeholder_pattern, document.content) else 0
        score = max_score * (section_score - placeholder_penalty)

        return QualityScore(
            category="completeness",
            score=max(0, score),
            max_score=max_score,
            details=f"{len(rendered)}/{len(required)} required sections present",
            issues=issues,
        )

    def _check_consistency(self, document: RenderedDocument) -> QualityScore:
        """Check document consistency."""
        max_score = self.quality_config.consistency_weight
        issues = []

        # Check terminology consistency
        glossary = self.quality_config.terminology_glossary
        inconsistent_terms = []

        for term, preferred in glossary.items():
            if term.lower() != preferred.lower():
                pattern = rf'\b{re.escape(term)}\b'
                if re.search(pattern, document.content, re.IGNORECASE):
                    if not re.search(rf'\b{re.escape(preferred)}\b', document.content, re.IGNORECASE):
                        inconsistent_terms.append(f"'{term}' should be '{preferred}'")

        if inconsistent_terms:
            issues.extend(inconsistent_terms)

        # Calculate score based on issues
        penalty = min(len(issues) * 0.1, 0.5)
        score = max_score * (1 - penalty)

        return QualityScore(
            category="consistency",
            score=max(0, score),
            max_score=max_score,
            details=f"{len(issues)} consistency issues found",
            issues=issues,
        )

    def _check_clarity(self, document: RenderedDocument) -> QualityScore:
        """Check document clarity."""
        max_score = self.quality_config.clarity_weight
        issues = []

        # Check for overly long sentences
        sentences = re.split(r'[.!?]', document.content)
        long_sentences = [s for s in sentences if len(s.split()) > 40]
        if long_sentences:
            issues.append(f"{len(long_sentences)} sentences exceed 40 words")

        # Check for passive voice indicators (simplified)
        passive_patterns = [r'\bwas\s+\w+ed\b', r'\bwere\s+\w+ed\b', r'\bis\s+being\b']
        passive_count = sum(
            len(re.findall(p, document.content, re.IGNORECASE))
            for p in passive_patterns
        )
        if passive_count > 5:
            issues.append(f"High passive voice usage ({passive_count} instances)")

        # Calculate score
        sentence_penalty = min(len(long_sentences) * 0.05, 0.25)
        passive_penalty = min(passive_count * 0.02, 0.25)
        score = max_score * (1 - sentence_penalty - passive_penalty)

        return QualityScore(
            category="clarity",
            score=max(0, score),
            max_score=max_score,
            details=f"Readability analysis complete",
            issues=issues,
        )

    def _check_traceability(self, document: RenderedDocument) -> QualityScore:
        """Check document traceability."""
        max_score = self.quality_config.traceability_weight
        issues = []

        # Check for requirement references
        req_pattern = r'\b(REQ|US|AC|FR|NFR)-?\d+\b'
        req_refs = re.findall(req_pattern, document.content, re.IGNORECASE)

        if not req_refs:
            issues.append("No requirement references found")

        # Check for version history
        if "version" not in document.content.lower():
            issues.append("No version information found")

        # Calculate score
        ref_score = min(len(req_refs) * 0.1, 0.5)
        version_score = 0.25 if "version" in document.content.lower() else 0
        base_score = 0.25  # Base score for having a rendered document

        score = max_score * (base_score + ref_score + version_score)

        return QualityScore(
            category="traceability",
            score=min(score, max_score),
            max_score=max_score,
            details=f"{len(req_refs)} requirement references found",
            issues=issues,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary representation."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "phase": self.phase,
            "version": self.version,
            "sections": [
                {
                    "section_id": s.section_id,
                    "title": s.title,
                    "description": s.description,
                    "required": s.required,
                    "order": s.order,
                }
                for s in self.sections
            ],
            "variables": [
                {
                    "name": v.name,
                    "description": v.description,
                    "type": v.var_type,
                    "required": v.required,
                }
                for v in self.variables
            ],
            "personas": {
                role.value: mapping.to_dict()
                for role, mapping in self.personas.items()
            },
            "quality_config": {
                "pass_threshold": self.quality_config.pass_threshold,
                "weights": {
                    "completeness": self.quality_config.completeness_weight,
                    "consistency": self.quality_config.consistency_weight,
                    "clarity": self.quality_config.clarity_weight,
                    "traceability": self.quality_config.traceability_weight,
                },
            },
        }
