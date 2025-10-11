#!/usr/bin/env python3
"""
Spec Similarity Service - ML Phase 3

Provides intelligent requirement specification similarity detection using:
- Semantic embeddings for specs
- Vector similarity search
- Feature-level overlap analysis
- Effort estimation

This enables V4 to detect similar projects and recommend clone-and-customize strategies.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import hashlib
import re


@dataclass
class SpecEmbedding:
    """Embedded representation of requirement specs"""
    project_id: str
    embedding: np.ndarray  # 768-dim vector
    specs: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime


@dataclass
class SimilarProject:
    """Similar project match"""
    project_id: str
    similarity_score: float
    specs: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class OverlapAnalysis:
    """Detailed overlap analysis between two projects"""
    overall_overlap: float
    user_stories_overlap: float
    functional_requirements_overlap: float
    data_models_overlap: float
    api_endpoints_overlap: float

    matched_user_stories: List[Tuple[str, str]]
    new_user_stories: List[str]
    modified_user_stories: List[Tuple[str, str]]

    matched_requirements: List[Tuple[str, str]]
    new_requirements: List[str]

    matched_models: List[Tuple[Dict, Dict]]
    new_models: List[Dict]
    modified_models: List[Tuple[Dict, Dict]]

    matched_endpoints: List[Tuple[Dict, Dict]]
    new_endpoints: List[Dict]

    delta_features: List[str]
    unchanged_features: List[str]


@dataclass
class EffortEstimate:
    """Effort estimation for delta work"""
    total_hours: float
    new_feature_hours: float
    modification_hours: float
    integration_hours: float
    confidence: float
    breakdown: Dict[str, float]


@dataclass
class ReuseRecommendation:
    """Reuse strategy recommendation"""
    strategy: str  # "clone_and_customize", "clone_with_customization", "hybrid", "full_sdlc"
    base_project_id: Optional[str]
    similarity_score: float
    overlap_percentage: float

    personas_to_run: List[str]
    personas_to_skip: List[str]

    estimated_effort_hours: float
    estimated_effort_percentage: float  # vs full SDLC
    confidence: float

    clone_instructions: Optional[Dict[str, Any]]
    reasoning: str


class SpecSimilarityService:
    """
    Service for detecting similar requirement specifications.

    Uses simple but effective similarity algorithms:
    - TF-IDF for text similarity
    - Jaccard similarity for structured data
    - Weighted combination for overall score
    """

    def __init__(self):
        # In-memory storage for embeddings (would be vector DB in production)
        self.embeddings_store: Dict[str, SpecEmbedding] = {}

        # Effort estimation constants (learned from historical data)
        self.FULL_SDLC_HOURS = 120  # Average hours for full SDLC
        self.INTEGRATION_OVERHEAD = 0.15  # 15% overhead for integration

    def embed_specs(self, specs: Dict[str, Any], project_id: str) -> SpecEmbedding:
        """
        Create semantic embedding for requirement specs.

        For now, uses simple TF-IDF-like approach.
        In production, would use trained transformer model.
        """

        # Extract all text from specs
        text_features = []

        # User stories
        for story in specs.get("user_stories", []):
            text_features.append(story.lower())

        # Functional requirements
        for req in specs.get("functional_requirements", []):
            text_features.append(req.lower())

        # Non-functional requirements
        for nfr in specs.get("non_functional_requirements", []):
            text_features.append(nfr.lower())

        # Extract keywords from structured data
        for model in specs.get("data_models", []):
            if isinstance(model, dict):
                text_features.append(model.get("entity", "").lower())
                text_features.extend([f.lower() for f in model.get("fields", [])])

        for endpoint in specs.get("api_endpoints", []):
            if isinstance(endpoint, dict):
                text_features.append(endpoint.get("path", "").lower())
                text_features.append(endpoint.get("purpose", "").lower())

        # Create simple embedding (bag of words + TF-IDF weights)
        # In production: Use sentence-transformers or similar
        embedding = self._create_simple_embedding(text_features)

        spec_embedding = SpecEmbedding(
            project_id=project_id,
            embedding=embedding,
            specs=specs,
            metadata={
                "user_story_count": len(specs.get("user_stories", [])),
                "requirement_count": len(specs.get("functional_requirements", [])),
                "model_count": len(specs.get("data_models", [])),
                "endpoint_count": len(specs.get("api_endpoints", []))
            },
            created_at=datetime.now()
        )

        # Store embedding
        self.embeddings_store[project_id] = spec_embedding

        return spec_embedding

    def _create_simple_embedding(self, text_features: List[str]) -> np.ndarray:
        """
        Create simple embedding from text features.

        Uses vocabulary + TF weighting.
        Fixed 768 dimensions for compatibility with real embeddings.
        """

        # Build vocabulary from common software terms
        vocabulary = set()
        for text in text_features:
            words = re.findall(r'\w+', text.lower())
            vocabulary.update(words)

        # Create term frequency vector
        vocab_list = sorted(list(vocabulary))[:768]  # Limit to 768 dims

        embedding = np.zeros(768)
        for i, term in enumerate(vocab_list):
            # Count occurrences across all features
            count = sum(1 for text in text_features if term in text.lower())
            embedding[i] = count / (1 + len(text_features))  # TF weighting

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def find_similar_projects(
        self,
        specs: Dict[str, Any],
        min_similarity: float = 0.80,
        limit: int = 5
    ) -> List[SimilarProject]:
        """
        Find projects with similar specs using vector similarity.

        Args:
            specs: New project specs
            min_similarity: Minimum similarity threshold (0-1)
            limit: Max number of results

        Returns:
            List of similar projects, sorted by similarity (highest first)
        """

        if not self.embeddings_store:
            return []

        # Create embedding for new specs
        new_embedding = self._create_simple_embedding(
            self._extract_text_features(specs)
        )

        # Calculate similarity with all stored projects
        similarities = []
        for project_id, stored_embedding in self.embeddings_store.items():
            similarity = self._cosine_similarity(
                new_embedding,
                stored_embedding.embedding
            )

            if similarity >= min_similarity:
                similarities.append(SimilarProject(
                    project_id=project_id,
                    similarity_score=similarity,
                    specs=stored_embedding.specs,
                    metadata=stored_embedding.metadata
                ))

        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x.similarity_score, reverse=True)

        return similarities[:limit]

    def _extract_text_features(self, specs: Dict[str, Any]) -> List[str]:
        """Extract text features from specs"""
        features = []

        for story in specs.get("user_stories", []):
            features.append(story.lower())

        for req in specs.get("functional_requirements", []):
            features.append(req.lower())

        for nfr in specs.get("non_functional_requirements", []):
            features.append(nfr.lower())

        return features

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def analyze_overlap(
        self,
        new_specs: Dict[str, Any],
        existing_specs: Dict[str, Any]
    ) -> OverlapAnalysis:
        """
        Detailed feature-by-feature overlap analysis.

        Compares:
        - User stories (semantic similarity)
        - Functional requirements
        - Data models (entity + field matching)
        - API endpoints (path + method matching)
        """

        # User stories overlap
        us_matched, us_new, us_modified = self._compare_user_stories(
            new_specs.get("user_stories", []),
            existing_specs.get("user_stories", [])
        )

        # Functional requirements overlap
        req_matched, req_new = self._compare_requirements(
            new_specs.get("functional_requirements", []),
            existing_specs.get("functional_requirements", [])
        )

        # Data models overlap
        model_matched, model_new, model_modified = self._compare_data_models(
            new_specs.get("data_models", []),
            existing_specs.get("data_models", [])
        )

        # API endpoints overlap
        endpoint_matched, endpoint_new = self._compare_endpoints(
            new_specs.get("api_endpoints", []),
            existing_specs.get("api_endpoints", [])
        )

        # Calculate overlap percentages
        total_us = len(new_specs.get("user_stories", []))
        us_overlap = len(us_matched) / total_us if total_us > 0 else 0

        total_req = len(new_specs.get("functional_requirements", []))
        req_overlap = len(req_matched) / total_req if total_req > 0 else 0

        total_models = len(new_specs.get("data_models", []))
        model_overlap = len(model_matched) / total_models if total_models > 0 else 0

        total_endpoints = len(new_specs.get("api_endpoints", []))
        endpoint_overlap = len(endpoint_matched) / total_endpoints if total_endpoints > 0 else 0

        # Weighted overall overlap
        overall_overlap = (
            0.3 * us_overlap +
            0.3 * req_overlap +
            0.2 * model_overlap +
            0.2 * endpoint_overlap
        )

        # Identify delta features
        delta_features = [f"New: {story}" for story in us_new[:5]]
        delta_features.extend([f"Modified: {m[0]}" for m in us_modified[:5]])

        # Unchanged features
        unchanged_features = [m[0] for m in us_matched[:10]]

        return OverlapAnalysis(
            overall_overlap=overall_overlap,
            user_stories_overlap=us_overlap,
            functional_requirements_overlap=req_overlap,
            data_models_overlap=model_overlap,
            api_endpoints_overlap=endpoint_overlap,
            matched_user_stories=us_matched,
            new_user_stories=us_new,
            modified_user_stories=us_modified,
            matched_requirements=req_matched,
            new_requirements=req_new,
            matched_models=model_matched,
            new_models=model_new,
            modified_models=model_modified,
            matched_endpoints=endpoint_matched,
            new_endpoints=endpoint_new,
            delta_features=delta_features,
            unchanged_features=unchanged_features
        )

    def _compare_user_stories(
        self,
        new_stories: List[str],
        existing_stories: List[str]
    ) -> Tuple[List[Tuple[str, str]], List[str], List[Tuple[str, str]]]:
        """
        Compare user stories with semantic similarity.

        Returns:
            (matched, new, modified)
        """
        matched = []
        new = []
        modified = []

        used_existing = set()

        for new_story in new_stories:
            best_match = None
            best_score = 0

            for i, existing_story in enumerate(existing_stories):
                if i in used_existing:
                    continue

                # Simple word overlap similarity
                score = self._text_similarity(new_story, existing_story)

                if score > best_score:
                    best_score = score
                    best_match = (i, existing_story)

            if best_score >= 0.85:
                # Strong match
                matched.append((new_story, best_match[1]))
                used_existing.add(best_match[0])
            elif best_score >= 0.60:
                # Partial match (modified)
                modified.append((new_story, best_match[1]))
                used_existing.add(best_match[0])
            else:
                # New story
                new.append(new_story)

        return matched, new, modified

    def _compare_requirements(
        self,
        new_reqs: List[str],
        existing_reqs: List[str]
    ) -> Tuple[List[Tuple[str, str]], List[str]]:
        """Compare functional requirements"""
        matched = []
        new = []

        used_existing = set()

        for new_req in new_reqs:
            best_match = None
            best_score = 0

            for i, existing_req in enumerate(existing_reqs):
                if i in used_existing:
                    continue

                score = self._text_similarity(new_req, existing_req)

                if score > best_score:
                    best_score = score
                    best_match = (i, existing_req)

            if best_score >= 0.75:
                matched.append((new_req, best_match[1]))
                used_existing.add(best_match[0])
            else:
                new.append(new_req)

        return matched, new

    def _compare_data_models(
        self,
        new_models: List[Dict],
        existing_models: List[Dict]
    ) -> Tuple[List[Tuple[Dict, Dict]], List[Dict], List[Tuple[Dict, Dict]]]:
        """
        Compare data models (entity + fields).

        Returns:
            (matched, new, modified)
        """
        matched = []
        new = []
        modified = []

        used_existing = set()

        for new_model in new_models:
            if not isinstance(new_model, dict):
                continue

            new_entity = new_model.get("entity", "")
            new_fields = set(new_model.get("fields", []))

            best_match = None
            best_score = 0

            for i, existing_model in enumerate(existing_models):
                if i in used_existing or not isinstance(existing_model, dict):
                    continue

                existing_entity = existing_model.get("entity", "")
                existing_fields = set(existing_model.get("fields", []))

                # Entity name similarity
                name_sim = self._text_similarity(new_entity, existing_entity)

                # Field overlap (Jaccard)
                if new_fields or existing_fields:
                    field_sim = len(new_fields & existing_fields) / len(new_fields | existing_fields)
                else:
                    field_sim = 0

                # Combined score
                score = 0.5 * name_sim + 0.5 * field_sim

                if score > best_score:
                    best_score = score
                    best_match = (i, existing_model)

            if best_score >= 0.85:
                matched.append((new_model, best_match[1]))
                used_existing.add(best_match[0])
            elif best_score >= 0.50:
                modified.append((new_model, best_match[1]))
                used_existing.add(best_match[0])
            else:
                new.append(new_model)

        return matched, new, modified

    def _compare_endpoints(
        self,
        new_endpoints: List[Dict],
        existing_endpoints: List[Dict]
    ) -> Tuple[List[Tuple[Dict, Dict]], List[Dict]]:
        """
        Compare API endpoints (method + path).

        Returns:
            (matched, new)
        """
        matched = []
        new = []

        used_existing = set()

        for new_ep in new_endpoints:
            if not isinstance(new_ep, dict):
                continue

            new_method = new_ep.get("method", "")
            new_path = new_ep.get("path", "")

            best_match = None
            best_score = 0

            for i, existing_ep in enumerate(existing_endpoints):
                if i in used_existing or not isinstance(existing_ep, dict):
                    continue

                existing_method = existing_ep.get("method", "")
                existing_path = existing_ep.get("path", "")

                # Exact method match required
                if new_method == existing_method:
                    # Path similarity
                    path_sim = self._text_similarity(new_path, existing_path)

                    if path_sim > best_score:
                        best_score = path_sim
                        best_match = (i, existing_ep)

            if best_score >= 0.80:
                matched.append((new_ep, best_match[1]))
                used_existing.add(best_match[0])
            else:
                new.append(new_ep)

        return matched, new

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity using word overlap (Jaccard).

        In production, use semantic similarity.
        """
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def estimate_effort(
        self,
        overlap_analysis: OverlapAnalysis,
        new_specs: Dict[str, Any]
    ) -> EffortEstimate:
        """
        Estimate development effort for delta work.

        Based on:
        - Number of new features
        - Number of modified features
        - Complexity of changes
        - Integration overhead
        """

        # Base effort for new work (proportional to delta)
        delta_percentage = 1.0 - overlap_analysis.overall_overlap
        base_delta_hours = self.FULL_SDLC_HOURS * delta_percentage

        # Adjust for feature counts
        new_story_count = len(overlap_analysis.new_user_stories)
        modified_story_count = len(overlap_analysis.modified_user_stories)
        new_model_count = len(overlap_analysis.new_models)
        modified_model_count = len(overlap_analysis.modified_models)

        # Estimate by category
        new_feature_hours = new_story_count * 1.5  # Avg 1.5 hours per story
        modification_hours = modified_story_count * 0.5  # Avg 0.5 hours per modification
        model_hours = new_model_count * 2.0 + modified_model_count * 0.8

        # Integration overhead (15% of delta work)
        integration_hours = (new_feature_hours + modification_hours + model_hours) * self.INTEGRATION_OVERHEAD

        total_hours = new_feature_hours + modification_hours + model_hours + integration_hours

        # Cap at reasonable bounds
        total_hours = min(total_hours, self.FULL_SDLC_HOURS * 0.5)  # Max 50% of full SDLC
        total_hours = max(total_hours, 2.0)  # Min 2 hours

        # Confidence based on overlap strength
        confidence = 0.5 + (overlap_analysis.overall_overlap * 0.5)  # 0.5-1.0 range

        return EffortEstimate(
            total_hours=total_hours,
            new_feature_hours=new_feature_hours,
            modification_hours=modification_hours,
            integration_hours=integration_hours,
            confidence=confidence,
            breakdown={
                "new_features": new_feature_hours,
                "modifications": modification_hours,
                "data_models": model_hours,
                "integration": integration_hours
            }
        )

    def recommend_reuse_strategy(
        self,
        overlap_analysis: OverlapAnalysis,
        effort_estimate: EffortEstimate,
        similar_project: SimilarProject
    ) -> ReuseRecommendation:
        """
        Recommend optimal reuse strategy based on overlap.

        Decision matrix:
        - 90%+ overlap → clone_and_customize (minimal delta)
        - 70-90% overlap → clone_with_customization (moderate delta)
        - 50-70% overlap → hybrid (selective reuse)
        - <50% overlap → full_sdlc (not worth cloning)
        """

        overlap_pct = overlap_analysis.overall_overlap

        if overlap_pct >= 0.90:
            # CLONE AND CUSTOMIZE: Minimal delta
            personas_to_run = self._determine_delta_personas(overlap_analysis, minimal=True)
            personas_to_skip = self._determine_skip_personas(personas_to_run)

            return ReuseRecommendation(
                strategy="clone_and_customize",
                base_project_id=similar_project.project_id,
                similarity_score=similar_project.similarity_score,
                overlap_percentage=overlap_pct,
                personas_to_run=personas_to_run,
                personas_to_skip=personas_to_skip,
                estimated_effort_hours=effort_estimate.total_hours,
                estimated_effort_percentage=(effort_estimate.total_hours / self.FULL_SDLC_HOURS) * 100,
                confidence=effort_estimate.confidence,
                clone_instructions={
                    "copy_entire_codebase": True,
                    "customize_only": overlap_analysis.delta_features[:10]
                },
                reasoning=f"{overlap_pct*100:.0f}% overlap - clone base and customize {(1-overlap_pct)*100:.0f}% delta only"
            )

        elif overlap_pct >= 0.70:
            # CLONE WITH CUSTOMIZATION: Moderate delta
            personas_to_run = self._determine_delta_personas(overlap_analysis, minimal=False)
            personas_to_skip = ["devops_engineer", "security_specialist", "technical_writer"]

            return ReuseRecommendation(
                strategy="clone_with_customization",
                base_project_id=similar_project.project_id,
                similarity_score=similar_project.similarity_score,
                overlap_percentage=overlap_pct,
                personas_to_run=personas_to_run,
                personas_to_skip=personas_to_skip,
                estimated_effort_hours=effort_estimate.total_hours,
                estimated_effort_percentage=(effort_estimate.total_hours / self.FULL_SDLC_HOURS) * 100,
                confidence=effort_estimate.confidence * 0.9,
                clone_instructions={
                    "copy_base_architecture": True,
                    "significant_customization_needed": True
                },
                reasoning=f"{overlap_pct*100:.0f}% overlap - clone base with significant customization"
            )

        elif overlap_pct >= 0.50:
            # HYBRID: Selective reuse
            personas_to_run = self._determine_hybrid_personas(overlap_analysis)
            personas_to_skip = []

            return ReuseRecommendation(
                strategy="hybrid",
                base_project_id=similar_project.project_id,
                similarity_score=similar_project.similarity_score,
                overlap_percentage=overlap_pct,
                personas_to_run=personas_to_run,
                personas_to_skip=personas_to_skip,
                estimated_effort_hours=effort_estimate.total_hours,
                estimated_effort_percentage=(effort_estimate.total_hours / self.FULL_SDLC_HOURS) * 100,
                confidence=effort_estimate.confidence * 0.7,
                clone_instructions={
                    "selective_reuse": True,
                    "reuse_components": overlap_analysis.unchanged_features[:10]
                },
                reasoning=f"{overlap_pct*100:.0f}% overlap - hybrid approach with selective component reuse"
            )

        else:
            # FULL SDLC: Not enough overlap
            return ReuseRecommendation(
                strategy="full_sdlc",
                base_project_id=None,
                similarity_score=similar_project.similarity_score,
                overlap_percentage=overlap_pct,
                personas_to_run=["all"],
                personas_to_skip=[],
                estimated_effort_hours=self.FULL_SDLC_HOURS,
                estimated_effort_percentage=100.0,
                confidence=0.9,
                clone_instructions=None,
                reasoning=f"Only {overlap_pct*100:.0f}% overlap - insufficient for cloning, full SDLC recommended"
            )

    def _determine_delta_personas(self, overlap: OverlapAnalysis, minimal: bool = True) -> List[str]:
        """Determine which personas needed for delta work"""
        personas = set()

        # Always include requirement_analyst
        personas.add("requirement_analyst")

        # Check if backend work needed
        if overlap.new_endpoints or overlap.new_models:
            personas.add("backend_developer")

        # Check if database work needed
        if len(overlap.new_models) > 0 or len(overlap.modified_models) > 2:
            personas.add("database_administrator")

        # Check if frontend work needed
        if not minimal or len(overlap.new_user_stories) > 3:
            personas.add("frontend_developer")

        # For minimal delta, skip architecture/design unless major changes
        if not minimal:
            if overlap.data_models_overlap < 0.70:
                personas.add("solution_architect")

        return sorted(list(personas))

    def _determine_skip_personas(self, personas_to_run: List[str]) -> List[str]:
        """Determine which personas can be skipped"""
        all_personas = [
            "requirement_analyst", "solution_architect", "security_specialist",
            "backend_developer", "database_administrator", "frontend_developer",
            "ui_ux_designer", "qa_engineer", "devops_engineer", "technical_writer"
        ]

        return [p for p in all_personas if p not in personas_to_run]

    def _determine_hybrid_personas(self, overlap: OverlapAnalysis) -> List[str]:
        """Determine personas for hybrid approach"""
        personas = [
            "requirement_analyst",
            "solution_architect",
            "backend_developer",
            "database_administrator",
            "frontend_developer",
            "qa_engineer"
        ]

        return personas
