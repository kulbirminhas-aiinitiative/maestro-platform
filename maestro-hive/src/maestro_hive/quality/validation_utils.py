"""
Validation utilities for detecting incomplete implementations and measuring quality

Quality Focus:
- Completeness (not file count)
- Correctness (no stubs/placeholders)
- Context-aware (only validate what's expected for this project)
"""
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


def detect_stubs_and_placeholders(file_path: Path) -> Dict[str, Any]:
    """
    Detect if a file contains incomplete/placeholder implementations

    Focus: QUALITY indicators, not quantity

    Returns:
        {
            "is_stub": bool,
            "severity": "low" | "medium" | "high" | "critical",
            "issues": List[str],
            "completeness_score": float,  # 0.0 to 1.0
            "lines_of_code": int,  # For context only
            "substance_ratio": float  # Code vs comments/whitespace
        }
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        return {
            "is_stub": False,
            "severity": "low",
            "issues": [f"Could not read file: {e}"],
            "completeness_score": 1.0,
            "lines_of_code": 0,
            "substance_ratio": 0.0
        }

    issues = []
    severity_score = 0

    lines = content.split('\n')
    total_lines = len(lines)

    # Calculate substance ratio (actual code vs whitespace/comments)
    code_lines = [
        l for l in lines
        if l.strip() and not l.strip().startswith('//') and not l.strip().startswith('*')
    ]
    substance_ratio = len(code_lines) / max(total_lines, 1)

    # 1. CRITICAL: Placeholder text (blocks deployment)
    critical_patterns = [
        (r"coming\s+soon", "critical", "Contains 'Coming Soon' placeholder"),
        (r"not\s+implemented", "critical", "Marked as not implemented"),
        (r"@stub", "critical", "Marked as stub"),
        (r"implement\s+me", "critical", "Needs implementation"),
    ]

    for pattern, severity, message in critical_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            issues.append(f"{message} ({len(matches)} occurrences)")
            severity_score += 5

    # 2. HIGH: Incomplete implementations
    high_patterns = [
        (r"FIXME", "high", "Contains FIXME"),
        (r"under\s+construction", "high", "Under construction"),
        (r"temporary\s+implementation", "high", "Temporary implementation"),
    ]

    for pattern, severity, message in high_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            issues.append(f"{message} ({len(matches)} occurrences)")
            severity_score += 3

    # 3. MEDIUM: TODOs (acceptable in moderation)
    todo_matches = re.findall(r"TODO", content, re.IGNORECASE)
    if len(todo_matches) > 5:  # More than 5 TODOs is a problem
        issues.append(f"Excessive TODOs ({len(todo_matches)} occurrences)")
        severity_score += 2

    # 4. CRITICAL: Commented-out routes/functionality
    if file_path.suffix in ['.ts', '.js', '.tsx', '.jsx']:
        # Check for commented-out routes (critical for APIs)
        stub_routes = re.findall(
            r'//\s*router\.(get|post|put|delete|patch|use)',
            content,
            re.IGNORECASE
        )
        if stub_routes:
            issues.append(f"Commented-out routes: {len(stub_routes)}")
            severity_score += 5  # CRITICAL

        # Check for commented-out imports (indicates incomplete code)
        stub_imports = re.findall(r'//\s*import\s+', content)
        if len(stub_imports) > 2:
            issues.append(f"Commented-out imports: {len(stub_imports)}")
            severity_score += 2

    # 5. HIGH: Empty implementations
    empty_functions = re.findall(
        r'function\s+\w+\s*\([^)]*\)\s*\{\s*\}',
        content
    )
    if empty_functions:
        issues.append(f"Empty functions: {len(empty_functions)}")
        severity_score += 3

    # Empty React components
    empty_components = re.findall(
        r'const\s+\w+\s*=\s*\(\)\s*=>\s*\{\s*return\s+null;?\s*\}',
        content
    )
    if empty_components:
        issues.append(f"Empty components returning null: {len(empty_components)}")
        severity_score += 3

    # 6. MEDIUM: Placeholder UI text
    if file_path.suffix in ['.tsx', '.jsx', '.html']:
        ui_placeholders = re.findall(
            r'<.*?>Coming Soon<.*?>|placeholder.*?text|Lorem ipsum',
            content,
            re.IGNORECASE
        )
        if ui_placeholders:
            issues.append(f"UI placeholders: {len(ui_placeholders)}")
            severity_score += 2

    # 7. LOW: Very small files (might be stubs)
    if substance_ratio < 0.1 and total_lines < 10:
        issues.append(f"Suspiciously small file ({total_lines} lines, {substance_ratio:.0%} substance)")
        severity_score += 1

    # Calculate completeness score (quality-focused)
    # Penalize heavily for critical issues, lightly for minor ones
    completeness_score = max(0.0, 1.0 - (severity_score * 0.08))

    # Boost score if file has substance (not just comments)
    if substance_ratio > 0.5:
        completeness_score = min(1.0, completeness_score + 0.1)

    # Determine overall severity
    is_stub = severity_score >= 5  # Threshold for "stub" classification

    if severity_score >= 10:
        severity = "critical"
    elif severity_score >= 6:
        severity = "high"
    elif severity_score >= 3:
        severity = "medium"
    else:
        severity = "low"

    return {
        "is_stub": is_stub,
        "severity": severity,
        "issues": issues,
        "completeness_score": completeness_score,
        "severity_score": severity_score,
        "lines_of_code": total_lines,
        "substance_ratio": substance_ratio
    }


def analyze_implementation_quality(
    file_path: Path,
    expected_patterns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Analyze implementation quality beyond stub detection

    Checks:
    - Test coverage indicators
    - Error handling presence
    - Documentation quality
    - Security patterns

    Returns quality metrics, not file counts
    """
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return {"quality_score": 0.0, "issues": ["Cannot read file"]}

    quality_indicators = {
        "has_error_handling": 0,
        "has_documentation": 0,
        "has_validation": 0,
        "has_tests": 0,
        "has_security_checks": 0
    }

    issues = []

    # Check for error handling
    if re.search(r'try\s*{|catch\s*\(', content):
        quality_indicators["has_error_handling"] = 1
    else:
        issues.append("No error handling detected")

    # Check for documentation
    doc_patterns = [r'\/\*\*', r'^\s*#', r'"""', r"'''"]
    if any(re.search(pattern, content, re.MULTILINE) for pattern in doc_patterns):
        quality_indicators["has_documentation"] = 1
    else:
        issues.append("Minimal documentation")

    # Check for validation
    validation_patterns = [r'validate', r'schema', r'zod', r'joi', r'yup']
    if any(re.search(pattern, content, re.IGNORECASE) for pattern in validation_patterns):
        quality_indicators["has_validation"] = 1
    else:
        issues.append("No input validation detected")

    # Check if this is a test file
    if re.search(r'(test|spec|describe|it\()', content, re.IGNORECASE):
        quality_indicators["has_tests"] = 1

    # Check for security patterns
    security_patterns = [r'sanitize', r'escape', r'authenticate', r'authorize', r'hash']
    if any(re.search(pattern, content, re.IGNORECASE) for pattern in security_patterns):
        quality_indicators["has_security_checks"] = 1

    quality_score = sum(quality_indicators.values()) / len(quality_indicators)

    return {
        "quality_score": quality_score,
        "quality_indicators": quality_indicators,
        "issues": issues
    }


def validate_persona_deliverables(
    persona_id: str,
    expected_deliverables: List[str],
    deliverables_found: Dict[str, List[str]],
    output_dir: Path,
    project_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate that persona created expected deliverables with quality focus

    CRITICAL CHANGE: Context-aware validation
    - Only validate deliverables relevant to this project type
    - Measure quality, not quantity

    Args:
        persona_id: ID of persona being validated
        expected_deliverables: Deliverables expected for this persona
        deliverables_found: Mapping of deliverable -> files
        output_dir: Project output directory
        project_context: Optional context (e.g., {"type": "backend_only"})

    Returns:
        {
            "complete": bool,
            "missing": List[str],
            "found": List[str],
            "partial": List[str],  # Found but likely stubs
            "completeness_percentage": float,
            "quality_score": float,  # NEW: Average quality of deliverables
            "quality_issues": List[Dict],
            "context_adjusted": bool  # Whether context affected validation
        }
    """
    missing = []
    found = []
    partial = []
    quality_issues = []
    quality_scores = []

    context_adjusted = False

    # Context-aware filtering of expected deliverables
    if project_context:
        project_type = project_context.get("type", "full_stack")

        # Filter out irrelevant deliverables based on project type
        if project_type == "backend_only":
            # Backend project doesn't need frontend deliverables
            frontend_deliverables = [
                "frontend_code", "components", "frontend_tests",
                "responsive_design", "wireframes", "mockups", "design_system"
            ]
            expected_deliverables = [
                d for d in expected_deliverables
                if d not in frontend_deliverables
            ]
            context_adjusted = True
            logger.info(f"📋 Context-aware: Backend-only project, skipping frontend deliverables")

        elif project_type == "frontend_only":
            # Frontend project doesn't need backend deliverables
            backend_deliverables = [
                "backend_code", "api_implementation", "database_schema", "backend_tests"
            ]
            expected_deliverables = [
                d for d in expected_deliverables
                if d not in backend_deliverables
            ]
            context_adjusted = True
            logger.info(f"📋 Context-aware: Frontend-only project, skipping backend deliverables")

    for deliverable in expected_deliverables:
        if deliverable in deliverables_found:
            found.append(deliverable)

            # Analyze quality of each file in this deliverable
            deliverable_quality_scores = []

            for file_path in deliverables_found[deliverable]:
                full_path = output_dir / file_path
                if full_path.exists():
                    # Stub detection
                    stub_check = detect_stubs_and_placeholders(full_path)
                    deliverable_quality_scores.append(stub_check["completeness_score"])

                    if stub_check["is_stub"]:
                        partial.append(deliverable)
                        quality_issues.append({
                            "file": file_path,
                            "deliverable": deliverable,
                            "severity": stub_check["severity"],
                            "issues": stub_check["issues"],
                            "completeness_score": stub_check["completeness_score"],
                            "substance_ratio": stub_check["substance_ratio"]
                        })

                    # Additional quality analysis for code files
                    if full_path.suffix in ['.ts', '.tsx', '.js', '.jsx', '.py']:
                        quality_analysis = analyze_implementation_quality(full_path)
                        deliverable_quality_scores.append(quality_analysis["quality_score"])

                        if quality_analysis["quality_score"] < 0.4:  # Low quality threshold
                            quality_issues.append({
                                "file": file_path,
                                "deliverable": deliverable,
                                "severity": "medium",
                                "issues": quality_analysis["issues"],
                                "quality_score": quality_analysis["quality_score"]
                            })

            # Average quality for this deliverable
            if deliverable_quality_scores:
                quality_scores.append(sum(deliverable_quality_scores) / len(deliverable_quality_scores))
        else:
            missing.append(deliverable)

    total = len(expected_deliverables)
    complete_count = len(found) - len(set(partial))  # Remove duplicates from partial
    completeness_percentage = (complete_count / total * 100) if total > 0 else 0

    # Calculate overall quality score (average across all deliverables)
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
    else:
        avg_quality = 0.0 if missing else 1.0  # 0 if missing everything, 1.0 if nothing expected

    # Combined metric: completeness × quality
    combined_score = (completeness_percentage / 100) * avg_quality

    return {
        "complete": len(missing) == 0 and len(partial) == 0,
        "missing": missing,
        "found": found,
        "partial": list(set(partial)),  # Deduplicate
        "completeness_percentage": completeness_percentage,
        "quality_score": avg_quality,  # Quality of what was created
        "combined_score": combined_score,  # Completeness × Quality
        "quality_issues": quality_issues,
        "context_adjusted": context_adjusted,
        "deliverable_count": len(found),  # For informational purposes only
        "expected_count": len(expected_deliverables)
    }


def detect_project_type(output_dir: Path) -> Dict[str, Any]:
    """
    Detect project type from requirements and artifacts

    Returns context for validation
    """
    context = {
        "type": "full_stack",  # Default
        "has_backend": False,
        "has_frontend": False,
        "has_mobile": False,
        "has_database": False,
        "primary_language": None
    }

    # Check for backend indicators
    backend_patterns = [
        "backend/**/*",
        "api/**/*",
        "server/**/*",
        "src/**/routes/**/*"
    ]

    for pattern in backend_patterns:
        if list(output_dir.glob(pattern)):
            context["has_backend"] = True
            break

    # Check for frontend indicators
    frontend_patterns = [
        "frontend/**/*",
        "client/**/*",
        "src/**/*.tsx",
        "src/**/*.jsx"
    ]

    for pattern in frontend_patterns:
        if list(output_dir.glob(pattern)):
            context["has_frontend"] = True
            break

    # Determine project type
    if context["has_backend"] and not context["has_frontend"]:
        context["type"] = "backend_only"
    elif context["has_frontend"] and not context["has_backend"]:
        context["type"] = "frontend_only"
    elif context["has_backend"] and context["has_frontend"]:
        context["type"] = "full_stack"

    return context
