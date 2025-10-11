#!/usr/bin/env python3
"""
Feature Mapper - Week 7-8 Requirements Traceability

Maps PRD features to implemented code features and identifies gaps.
Uses multiple matching strategies for robustness.

Key Features:
- Keyword-based matching (simple, always works)
- Evidence-based matching (endpoint names, file names)
- Semantic similarity matching (when available)
- Confidence scoring for matches
- Gap detection (PRD but not implemented)
- Extra detection (implemented but not in PRD)

NOTE: Future Enhancement - PRD features should be generated as structured metadata
during document creation by personas, rather than parsed after the fact.
"""

import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum

from code_feature_analyzer import CodeFeature
from prd_feature_extractor import PRDFeature

logger = logging.getLogger(__name__)


class MappingStatus(Enum):
    """Status of feature mapping"""
    FULLY_IMPLEMENTED = "fully_implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_IN_PRD = "not_in_prd"


@dataclass
class FeatureMapping:
    """Represents a mapping between PRD and code feature"""
    prd_feature: Optional[PRDFeature]
    code_feature: Optional[CodeFeature]
    match_confidence: float  # 0.0 - 1.0
    status: MappingStatus
    coverage: float  # 0.0 - 1.0 (for partially implemented)
    gaps: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "prd_feature": self.prd_feature.to_dict() if self.prd_feature else None,
            "code_feature": self.code_feature.to_dict() if self.code_feature else None,
            "match_confidence": self.match_confidence,
            "status": self.status.value,
            "coverage": self.coverage,
            "gaps": self.gaps,
            "evidence": self.evidence
        }


@dataclass
class TraceabilityMatrix:
    """Complete traceability matrix"""
    mappings: List[FeatureMapping]
    unmapped_prd: List[PRDFeature]  # PRD features with no implementation
    unmapped_code: List[CodeFeature]  # Code features not in PRD
    coverage_percentage: float
    total_prd_features: int
    total_code_features: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "mappings": [m.to_dict() for m in self.mappings],
            "unmapped_prd": [f.to_dict() for f in self.unmapped_prd],
            "unmapped_code": [f.to_dict() for f in self.unmapped_code],
            "coverage_percentage": self.coverage_percentage,
            "total_prd_features": self.total_prd_features,
            "total_code_features": self.total_code_features,
            "summary": {
                "fully_implemented": sum(1 for m in self.mappings if m.status == MappingStatus.FULLY_IMPLEMENTED),
                "partially_implemented": sum(1 for m in self.mappings if m.status == MappingStatus.PARTIALLY_IMPLEMENTED),
                "not_implemented": len(self.unmapped_prd),
                "not_in_prd": len(self.unmapped_code)
            }
        }


class FeatureMapper:
    """Maps PRD features to code features"""

    def __init__(self):
        self.mappings: List[FeatureMapping] = []

    async def map_features(
        self,
        prd_features: List[PRDFeature],
        code_features: List[CodeFeature]
    ) -> TraceabilityMatrix:
        """Map PRD features to code features"""
        logger.info(f"🔗 Mapping {len(prd_features)} PRD features to {len(code_features)} code features")

        # Handle case where no PRD exists
        if not prd_features:
            logger.info("  No PRD features - reporting all code features as implemented")
            return self._create_matrix_without_prd(code_features)

        # Handle case where no code exists
        if not code_features:
            logger.info("  No code features - reporting all PRD features as not implemented")
            return self._create_matrix_without_code(prd_features)

        # Perform mapping
        mapped_prd = set()
        mapped_code = set()

        # Find best matches for each PRD feature
        for prd_feature in prd_features:
            best_match = None
            best_confidence = 0.0

            for code_feature in code_features:
                # Skip already mapped code features
                if code_feature.id in mapped_code:
                    continue

                # Calculate match confidence
                confidence = self._calculate_match_confidence(prd_feature, code_feature)

                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = code_feature

            # Create mapping if confidence is above threshold
            if best_match and best_confidence >= 0.5:  # 50% threshold
                mapping = self._create_mapping(prd_feature, best_match, best_confidence)
                self.mappings.append(mapping)
                mapped_prd.add(prd_feature.id)
                mapped_code.add(best_match.id)
            else:
                # PRD feature not implemented
                mapping = FeatureMapping(
                    prd_feature=prd_feature,
                    code_feature=None,
                    match_confidence=0.0,
                    status=MappingStatus.NOT_IMPLEMENTED,
                    coverage=0.0,
                    gaps=[f"No implementation found for '{prd_feature.title}'"]
                )
                self.mappings.append(mapping)
                mapped_prd.add(prd_feature.id)

        # Identify unmapped PRD features
        unmapped_prd = [f for f in prd_features if f.id not in mapped_prd]

        # Identify unmapped code features (not in PRD)
        unmapped_code = [f for f in code_features if f.id not in mapped_code]

        # Calculate coverage
        coverage = self._calculate_coverage(prd_features, self.mappings)

        matrix = TraceabilityMatrix(
            mappings=self.mappings,
            unmapped_prd=unmapped_prd,
            unmapped_code=unmapped_code,
            coverage_percentage=coverage,
            total_prd_features=len(prd_features),
            total_code_features=len(code_features)
        )

        logger.info(f"✅ Mapped {len(self.mappings)} features")
        logger.info(f"  Coverage: {coverage:.0%}")
        logger.info(f"  Unmapped PRD: {len(unmapped_prd)}")
        logger.info(f"  Extra code features: {len(unmapped_code)}")

        return matrix

    def _calculate_match_confidence(
        self,
        prd_feature: PRDFeature,
        code_feature: CodeFeature
    ) -> float:
        """Calculate confidence that PRD and code features match"""
        confidence = 0.0

        # Strategy 1: Keyword matching (30%)
        keyword_score = self._keyword_similarity(
            prd_feature.title + " " + prd_feature.description,
            code_feature.name
        )
        confidence += keyword_score * 0.3

        # Strategy 2: Category matching (20%)
        if prd_feature.category:
            category_score = self._category_similarity(prd_feature.category, code_feature.category.value)
            confidence += category_score * 0.2

        # Strategy 3: Evidence matching (50%)
        evidence_score = self._evidence_similarity(prd_feature, code_feature)
        confidence += evidence_score * 0.5

        return min(confidence, 1.0)

    def _keyword_similarity(self, text1: str, text2: str) -> float:
        """Calculate keyword similarity between two texts"""
        # Extract keywords (words longer than 3 characters, lowercase)
        def extract_keywords(text: str) -> Set[str]:
            words = re.findall(r'\b\w{4,}\b', text.lower())
            # Remove common words
            stop_words = {'that', 'this', 'with', 'from', 'have', 'been', 'will', 'your', 'what', 'when', 'where'}
            return set(w for w in words if w not in stop_words)

        keywords1 = extract_keywords(text1)
        keywords2 = extract_keywords(text2)

        if not keywords1 or not keywords2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = keywords1 & keywords2
        union = keywords1 | keywords2

        return len(intersection) / len(union) if union else 0.0

    def _category_similarity(self, category1: str, category2: str) -> float:
        """Calculate category similarity"""
        if category1.lower() == category2.lower():
            return 1.0

        # Check if one category name contains the other
        if category1.lower() in category2.lower() or category2.lower() in category1.lower():
            return 0.7

        return 0.0

    def _evidence_similarity(self, prd_feature: PRDFeature, code_feature: CodeFeature) -> float:
        """Calculate evidence-based similarity"""
        score = 0.0

        # Extract keywords from PRD feature
        prd_keywords = set(re.findall(r'\b\w{4,}\b', prd_feature.title.lower()))

        # Check endpoint paths
        if code_feature.endpoints:
            for endpoint in code_feature.endpoints:
                path_keywords = set(re.findall(r'\b\w{4,}\b', endpoint.path.lower()))
                if prd_keywords & path_keywords:
                    score += 0.3
                    break

        # Check model names
        if code_feature.models:
            for model in code_feature.models:
                if any(keyword in model.name.lower() for keyword in prd_keywords):
                    score += 0.3
                    break

        # Check component names
        if code_feature.components:
            for component in code_feature.components:
                if any(keyword in component.name.lower() for keyword in prd_keywords):
                    score += 0.2
                    break

        # Check file names
        all_files = [e.file for e in code_feature.endpoints] + \
                   [m.file for m in code_feature.models] + \
                   [c.file for c in code_feature.components]

        for file_path in all_files:
            if any(keyword in file_path.lower() for keyword in prd_keywords):
                score += 0.2
                break

        return min(score, 1.0)

    def _create_mapping(
        self,
        prd_feature: PRDFeature,
        code_feature: CodeFeature,
        confidence: float
    ) -> FeatureMapping:
        """Create a feature mapping with status and gaps"""
        # Determine status and coverage
        if code_feature.completeness >= 0.8:
            status = MappingStatus.FULLY_IMPLEMENTED
            coverage = 1.0
            gaps = []
        elif code_feature.completeness >= 0.5:
            status = MappingStatus.PARTIALLY_IMPLEMENTED
            coverage = code_feature.completeness
            gaps = self._identify_gaps(prd_feature, code_feature)
        else:
            status = MappingStatus.PARTIALLY_IMPLEMENTED
            coverage = code_feature.completeness
            gaps = self._identify_gaps(prd_feature, code_feature)

        # Collect evidence
        evidence = {
            "endpoints": len(code_feature.endpoints),
            "models": len(code_feature.models),
            "components": len(code_feature.components),
            "has_tests": code_feature.has_tests,
            "completeness": code_feature.completeness
        }

        return FeatureMapping(
            prd_feature=prd_feature,
            code_feature=code_feature,
            match_confidence=confidence,
            status=status,
            coverage=coverage,
            gaps=gaps,
            evidence=evidence
        )

    def _identify_gaps(self, prd_feature: PRDFeature, code_feature: CodeFeature) -> List[str]:
        """Identify gaps between PRD and implementation"""
        gaps = []

        # Check completeness
        if code_feature.completeness < 0.8:
            gaps.append(f"Implementation incomplete ({code_feature.completeness:.0%})")

        # Check tests
        if not code_feature.has_tests:
            gaps.append("No tests found")

        # Check acceptance criteria (if PRD has them)
        if prd_feature.acceptance_criteria:
            # For now, just note if there are acceptance criteria
            # In future, could try to match specific criteria to code
            gaps.append(f"{len(prd_feature.acceptance_criteria)} acceptance criteria need verification")

        return gaps

    def _calculate_coverage(
        self,
        prd_features: List[PRDFeature],
        mappings: List[FeatureMapping]
    ) -> float:
        """Calculate PRD feature coverage percentage"""
        if not prd_features:
            return 1.0

        # Count fully and partially implemented features
        implemented = sum(
            1 for m in mappings
            if m.status in [MappingStatus.FULLY_IMPLEMENTED, MappingStatus.PARTIALLY_IMPLEMENTED]
        )

        return implemented / len(prd_features)

    def _create_matrix_without_prd(self, code_features: List[CodeFeature]) -> TraceabilityMatrix:
        """Create matrix when no PRD exists - report all code as implemented"""
        mappings = [
            FeatureMapping(
                prd_feature=None,
                code_feature=code_feature,
                match_confidence=1.0,
                status=MappingStatus.NOT_IN_PRD,
                coverage=code_feature.completeness,
                gaps=[],
                evidence={"note": "No PRD to compare against"}
            )
            for code_feature in code_features
        ]

        return TraceabilityMatrix(
            mappings=mappings,
            unmapped_prd=[],
            unmapped_code=[],
            coverage_percentage=1.0,  # 100% since no PRD to compare
            total_prd_features=0,
            total_code_features=len(code_features)
        )

    def _create_matrix_without_code(self, prd_features: List[PRDFeature]) -> TraceabilityMatrix:
        """Create matrix when no code exists - report all PRD as not implemented"""
        mappings = [
            FeatureMapping(
                prd_feature=prd_feature,
                code_feature=None,
                match_confidence=0.0,
                status=MappingStatus.NOT_IMPLEMENTED,
                coverage=0.0,
                gaps=[f"Feature '{prd_feature.title}' not implemented"],
                evidence={}
            )
            for prd_feature in prd_features
        ]

        return TraceabilityMatrix(
            mappings=mappings,
            unmapped_prd=prd_features,
            unmapped_code=[],
            coverage_percentage=0.0,
            total_prd_features=len(prd_features),
            total_code_features=0
        )


async def map_prd_to_code(
    prd_features: List[PRDFeature],
    code_features: List[CodeFeature]
) -> TraceabilityMatrix:
    """Main entry point for feature mapping"""
    mapper = FeatureMapper()
    matrix = await mapper.map_features(prd_features, code_features)
    return matrix


if __name__ == "__main__":
    # Test feature mapper
    import asyncio
    import json

    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

    async def main():
        from code_feature_analyzer import analyze_code_features
        from prd_feature_extractor import extract_prd_features
        from pathlib import Path

        workflow_dir = Path("/tmp/maestro_workflow/wf-1760076571-6b932a66")
        impl_dir = workflow_dir / "implementation"
        requirements_dir = workflow_dir / "requirements"

        print("=" * 80)
        print("FEATURE MAPPER - TEST RUN")
        print("=" * 80)
        print(f"Workflow: {workflow_dir.name}\n")

        # Extract features
        print("Step 1: Extracting PRD features...")
        prd_features = await extract_prd_features(requirements_dir)
        print(f"  Found {len(prd_features)} PRD features")

        print("\nStep 2: Analyzing code features...")
        code_features = await analyze_code_features(impl_dir)
        print(f"  Found {len(code_features)} code features")

        print("\nStep 3: Mapping features...")
        matrix = await map_prd_to_code(prd_features, code_features)

        print("\n" + "=" * 80)
        print("MAPPING COMPLETE")
        print("=" * 80)

        print(f"\n📊 Summary:")
        print(f"  PRD Features: {matrix.total_prd_features}")
        print(f"  Code Features: {matrix.total_code_features}")
        print(f"  Coverage: {matrix.coverage_percentage:.0%}")
        print(f"  Mappings: {len(matrix.mappings)}")
        print(f"  Unmapped PRD: {len(matrix.unmapped_prd)}")
        print(f"  Extra Code: {len(matrix.unmapped_code)}")

        summary = matrix.to_dict()['summary']
        print(f"\n📋 Status Breakdown:")
        print(f"  Fully Implemented: {summary['fully_implemented']}")
        print(f"  Partially Implemented: {summary['partially_implemented']}")
        print(f"  Not Implemented: {summary['not_implemented']}")
        print(f"  Not in PRD: {summary['not_in_prd']}")

        # Save result
        output_file = workflow_dir / "TRACEABILITY_MATRIX.json"
        output_file.write_text(json.dumps(matrix.to_dict(), indent=2))
        print(f"\n📄 Saved traceability matrix to {output_file}")

        # Show some example mappings
        if matrix.mappings:
            print(f"\n✅ Example Mappings:")
            for mapping in matrix.mappings[:3]:
                if mapping.code_feature:
                    print(f"\n  Code Feature: {mapping.code_feature.name}")
                    print(f"    Status: {mapping.status.value}")
                    print(f"    Confidence: {mapping.match_confidence:.0%}")
                    print(f"    Coverage: {mapping.coverage:.0%}")
                    if mapping.prd_feature:
                        print(f"    Mapped to PRD: {mapping.prd_feature.title}")
                    else:
                        print(f"    Not in PRD (implemented anyway)")

    asyncio.run(main())
