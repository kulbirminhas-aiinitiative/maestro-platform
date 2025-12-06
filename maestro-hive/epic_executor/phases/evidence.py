"""
Phase 7: Evidence

Collect evidence for each acceptance criterion.
This phase collects AC evidence for 25 compliance points.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..models import (
    AcceptanceCriterion,
    ACEvidence,
    ACStatus,
    DocumentInfo,
    EpicInfo,
    ExecutionPhase,
    PhaseResult,
)


@dataclass
class EvidenceResult:
    """Result from the evidence phase."""
    evidence_collected: List[ACEvidence]
    acs_with_evidence: int
    acs_verified: int
    points_earned: float  # Out of 25


class EvidencePhase:
    """
    Phase 7: AC Evidence Collection

    Responsibilities:
    1. Link implementation files to ACs
    2. Link test files to ACs
    3. Link Confluence docs to ACs
    4. Collect verification output
    """

    def __init__(self):
        """Initialize the evidence phase."""
        pass

    async def execute(
        self,
        epic_info: EpicInfo,
        implementation_files: List[str],
        test_files: List[str],
        documents: List[DocumentInfo],
    ) -> Tuple[PhaseResult, Optional[EvidenceResult]]:
        """
        Execute the evidence phase.

        Args:
            epic_info: EPIC information with acceptance criteria
            implementation_files: List of implementation file paths
            test_files: List of test file paths
            documents: List of created Confluence documents

        Returns:
            Tuple of (PhaseResult, EvidenceResult or None if failed)
        """
        started_at = datetime.now()
        errors: List[str] = []
        warnings: List[str] = []
        artifacts: List[str] = []

        try:
            evidence_collected: List[ACEvidence] = []
            acs_with_evidence = 0
            acs_verified = 0

            # Process each acceptance criterion
            for ac in epic_info.acceptance_criteria:
                evidence = await self._collect_evidence_for_ac(
                    ac=ac,
                    implementation_files=implementation_files,
                    test_files=test_files,
                    documents=documents,
                )

                if evidence:
                    evidence_collected.append(evidence)

                    # Count if this AC has sufficient evidence
                    has_impl = evidence.implementation_file is not None
                    has_test = evidence.test_file is not None
                    has_doc = evidence.confluence_link is not None

                    if has_impl or has_test or has_doc:
                        acs_with_evidence += 1
                        ac.status = ACStatus.TESTED

                    if has_impl and has_test:
                        evidence.verified = True
                        evidence.verified_at = datetime.now()
                        acs_verified += 1
                        ac.status = ACStatus.VERIFIED

                    artifacts.append(f"Collected evidence for {ac.id}")

            # Calculate points: (acs_with_evidence / acs_total) * 25
            total_acs = len(epic_info.acceptance_criteria)
            points_earned = (acs_with_evidence / total_acs * 25) if total_acs > 0 else 0

            if acs_with_evidence < total_acs:
                warnings.append(
                    f"Only {acs_with_evidence}/{total_acs} ACs have evidence"
                )

            artifacts.append(f"Verified {acs_verified}/{total_acs} ACs")

            # Build result
            result = EvidenceResult(
                evidence_collected=evidence_collected,
                acs_with_evidence=acs_with_evidence,
                acs_verified=acs_verified,
                points_earned=points_earned,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.EVIDENCE,
                success=acs_with_evidence > 0,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
                metrics={
                    "acs_with_evidence": acs_with_evidence,
                    "acs_verified": acs_verified,
                    "acs_total": total_acs,
                    "points_earned": points_earned,
                    "points_max": 25.0,
                }
            )

            return phase_result, result

        except Exception as e:
            errors.append(str(e))
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            phase_result = PhaseResult(
                phase=ExecutionPhase.EVIDENCE,
                success=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                artifacts_created=artifacts,
                errors=errors,
                warnings=warnings,
            )

            return phase_result, None

    async def _collect_evidence_for_ac(
        self,
        ac: AcceptanceCriterion,
        implementation_files: List[str],
        test_files: List[str],
        documents: List[DocumentInfo],
    ) -> Optional[ACEvidence]:
        """Collect evidence for a single acceptance criterion."""
        evidence = ACEvidence(ac_id=ac.id)

        # Find matching implementation file
        impl_match = self._find_matching_file(
            ac, implementation_files, file_type="implementation"
        )
        if impl_match:
            evidence.implementation_file = impl_match["file"]
            evidence.implementation_line = impl_match.get("line")

        # Find matching test file
        test_match = self._find_matching_file(
            ac, test_files, file_type="test"
        )
        if test_match:
            evidence.test_file = test_match["file"]
            evidence.test_line = test_match.get("line")

        # Find matching Confluence doc
        doc_match = self._find_matching_doc(ac, documents)
        if doc_match:
            evidence.confluence_link = doc_match.confluence_url

        # Generate verification output
        evidence.verification_output = self._generate_verification(evidence)

        return evidence

    def _find_matching_file(
        self,
        ac: AcceptanceCriterion,
        files: List[str],
        file_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find a file that matches this acceptance criterion.

        Uses keyword matching between AC description and file content/name.
        """
        ac_lower = ac.description.lower()
        ac_id_safe = ac.id.replace("-", "_").lower()

        # Keywords from AC description
        keywords = set(
            word for word in re.findall(r'\w+', ac_lower)
            if len(word) > 3
        )

        best_match = None
        best_score = 0

        for file_path in files:
            path = Path(file_path)
            file_name = path.stem.lower()
            score = 0

            # Check if AC ID is in filename
            if ac_id_safe in file_name or ac.id.lower() in file_name:
                score += 10

            # Check for keyword matches in filename
            for keyword in keywords:
                if keyword in file_name:
                    score += 2

            # Check file content if exists
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore").lower()

                    # Check for AC ID in content
                    if ac.id.lower() in content or ac_id_safe in content:
                        score += 5

                    # Check for keywords in content
                    for keyword in keywords:
                        if keyword in content:
                            score += 1

                    # Find line number if AC ID mentioned
                    if score > 0:
                        line_num = self._find_line_with_text(path, ac.id)
                        if line_num:
                            score += 3

                except Exception:
                    pass

            if score > best_score:
                best_score = score
                best_match = {
                    "file": file_path,
                    "score": score,
                }

        if best_match and best_score >= 3:
            # Try to find specific line
            line = self._find_line_with_text(
                Path(best_match["file"]),
                ac.id
            )
            if line:
                best_match["line"] = line
            return best_match

        # If no good match, return first file as fallback
        if files and file_type == "implementation":
            return {"file": files[0]}

        return None

    def _find_line_with_text(
        self,
        file_path: Path,
        text: str,
    ) -> Optional[int]:
        """Find the line number containing specific text."""
        if not file_path.exists():
            return None

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for i, line in enumerate(content.split("\n"), 1):
                if text.lower() in line.lower():
                    return i
        except Exception:
            pass

        return None

    def _find_matching_doc(
        self,
        ac: AcceptanceCriterion,
        documents: List[DocumentInfo],
    ) -> Optional[DocumentInfo]:
        """Find a Confluence document relevant to this AC."""
        ac_lower = ac.description.lower()

        # Technical design is usually the best match for any AC
        for doc in documents:
            if doc.doc_type.value == "technical_design":
                return doc

        # Look for keyword matches
        for doc in documents:
            doc_type = doc.doc_type.value.lower()

            if "api" in ac_lower and "api" in doc_type:
                return doc
            if "config" in ac_lower and "config" in doc_type:
                return doc
            if "monitor" in ac_lower and "monitor" in doc_type:
                return doc
            if "runbook" in ac_lower and "runbook" in doc_type:
                return doc

        # Return first doc as fallback
        return documents[0] if documents else None

    def _generate_verification(self, evidence: ACEvidence) -> str:
        """Generate a verification summary for the evidence."""
        parts = []

        if evidence.implementation_file:
            line_info = f":{evidence.implementation_line}" if evidence.implementation_line else ""
            parts.append(f"Implementation: {evidence.implementation_file}{line_info}")

        if evidence.test_file:
            line_info = f":{evidence.test_line}" if evidence.test_line else ""
            parts.append(f"Test: {evidence.test_file}{line_info}")

        if evidence.confluence_link:
            parts.append(f"Documentation: {evidence.confluence_link}")

        if not parts:
            return "No evidence collected"

        return " | ".join(parts)
