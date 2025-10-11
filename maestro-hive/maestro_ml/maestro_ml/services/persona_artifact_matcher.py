#!/usr/bin/env python3
"""
Persona-Level Artifact Matching Service

Enables granular, component-level reuse by matching individual persona
artifacts rather than entire projects.

Key Innovation:
- Even if overall project similarity is 50%, individual personas may have
  90-100% matches and can be reused independently
- Generic framework - not hardcoded to specific personas
- Each persona's domain is analyzed separately

Example:
    Overall project match: 50%
    - system_architect: 100% match → reuse architecture
    - frontend_engineer: 90% match → reuse UI components
    - backend_engineer: 30% match → build fresh
    - Result: Fast-track 2 personas, run 8 = 20% time savings
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PersonaDomainSpec:
    """Specification extracted for a specific persona's domain"""
    persona_id: str
    domain: str  # e.g., "architecture", "frontend", "backend"
    specs: Dict[str, Any]
    extracted_from: str  # Source file/artifact
    confidence: float  # How confident we are in extraction (0-1)


@dataclass
class PersonaMatchResult:
    """Match result for a specific persona"""
    persona_id: str
    similarity_score: float  # 0-1
    should_reuse: bool
    source_project_id: Optional[str]
    source_artifacts: List[str]  # Artifact IDs to reuse
    match_details: Dict[str, Any]  # Detailed breakdown
    rationale: str


@dataclass
class PersonaReuseMap:
    """Complete reuse decision map across all personas"""
    overall_similarity: float
    persona_matches: Dict[str, PersonaMatchResult]  # persona_id -> match
    personas_to_reuse: List[str]
    personas_to_execute: List[str]
    estimated_time_savings_percent: float


class PersonaArtifactMatcher:
    """
    Generic framework for persona-level artifact matching.

    Not hardcoded - uses configurable extractors and matchers
    for each persona's domain.
    """

    def __init__(self):
        # Configurable: Define what each persona cares about
        self.persona_domains = self._initialize_persona_domains()

        # Configurable: Reuse thresholds per persona
        self.reuse_thresholds = self._initialize_reuse_thresholds()

    def _initialize_persona_domains(self) -> Dict[str, Dict[str, Any]]:
        """
        Define what each persona's domain includes.

        This is configurable and extensible - not hardcoded.
        """
        return {
            "system_architect": {
                "domain": "architecture",
                "extract_from": ["REQUIREMENTS.md", "ARCHITECTURE.md"],
                "key_aspects": [
                    "architecture_patterns",  # e.g., microservices, monolith
                    "tech_stack",             # e.g., React, FastAPI, PostgreSQL
                    "scalability_requirements",
                    "system_components",
                    "integration_patterns"
                ],
                "similarity_weights": {
                    "architecture_patterns": 0.35,
                    "tech_stack": 0.25,
                    "scalability_requirements": 0.15,
                    "system_components": 0.15,
                    "integration_patterns": 0.10
                }
            },

            "frontend_engineer": {
                "domain": "frontend",
                "extract_from": ["REQUIREMENTS.md", "UI_SPECS.md"],
                "key_aspects": [
                    "ui_components",          # e.g., login form, dashboard
                    "user_flows",             # e.g., signup flow, checkout
                    "state_management",       # e.g., Redux, Context API
                    "ui_framework",           # e.g., React, Vue, Angular
                    "styling_approach"        # e.g., CSS-in-JS, Tailwind
                ],
                "similarity_weights": {
                    "ui_components": 0.30,
                    "user_flows": 0.25,
                    "state_management": 0.20,
                    "ui_framework": 0.15,
                    "styling_approach": 0.10
                }
            },

            "backend_engineer": {
                "domain": "backend",
                "extract_from": ["REQUIREMENTS.md", "API_SPECS.md"],
                "key_aspects": [
                    "business_logic",         # Core algorithms/rules
                    "data_flow",              # How data moves through system
                    "api_patterns",           # REST, GraphQL, gRPC
                    "backend_framework",      # FastAPI, Django, Express
                    "async_patterns"          # Task queues, event handling
                ],
                "similarity_weights": {
                    "business_logic": 0.35,
                    "data_flow": 0.25,
                    "api_patterns": 0.20,
                    "backend_framework": 0.12,
                    "async_patterns": 0.08
                }
            },

            "database_engineer": {
                "domain": "database",
                "extract_from": ["REQUIREMENTS.md", "DATA_MODELS.md"],
                "key_aspects": [
                    "data_models",            # Entities and fields
                    "relationships",          # Foreign keys, associations
                    "indexes",                # Performance indexes
                    "database_type",          # PostgreSQL, MongoDB, etc.
                    "normalization_level"     # 1NF, 2NF, 3NF
                ],
                "similarity_weights": {
                    "data_models": 0.40,
                    "relationships": 0.30,
                    "indexes": 0.15,
                    "database_type": 0.10,
                    "normalization_level": 0.05
                }
            },

            "api_engineer": {
                "domain": "api",
                "extract_from": ["REQUIREMENTS.md", "API_SPECS.md"],
                "key_aspects": [
                    "api_endpoints",          # Endpoint paths and methods
                    "request_formats",        # Request schemas
                    "response_formats",       # Response schemas
                    "api_style",              # REST, GraphQL, gRPC
                    "versioning_strategy"     # v1, v2, header-based
                ],
                "similarity_weights": {
                    "api_endpoints": 0.35,
                    "request_formats": 0.25,
                    "response_formats": 0.25,
                    "api_style": 0.10,
                    "versioning_strategy": 0.05
                }
            },

            "security_engineer": {
                "domain": "security",
                "extract_from": ["REQUIREMENTS.md", "SECURITY_REQUIREMENTS.md"],
                "key_aspects": [
                    "auth_mechanism",         # JWT, OAuth, sessions
                    "authorization_model",    # RBAC, ABAC, ACL
                    "security_requirements",  # Encryption, HTTPS, etc.
                    "compliance_needs",       # GDPR, HIPAA, SOC2
                    "threat_model"            # Security threats to address
                ],
                "similarity_weights": {
                    "auth_mechanism": 0.30,
                    "authorization_model": 0.30,
                    "security_requirements": 0.20,
                    "compliance_needs": 0.12,
                    "threat_model": 0.08
                }
            },

            "testing_engineer": {
                "domain": "testing",
                "extract_from": ["REQUIREMENTS.md", "TEST_PLAN.md"],
                "key_aspects": [
                    "test_scenarios",         # What to test
                    "coverage_requirements",  # % coverage needed
                    "testing_frameworks",     # Jest, Pytest, etc.
                    "test_types",             # Unit, integration, e2e
                    "ci_integration"          # CI/CD test automation
                ],
                "similarity_weights": {
                    "test_scenarios": 0.35,
                    "coverage_requirements": 0.25,
                    "testing_frameworks": 0.15,
                    "test_types": 0.15,
                    "ci_integration": 0.10
                }
            },

            "devops_engineer": {
                "domain": "devops",
                "extract_from": ["REQUIREMENTS.md", "INFRASTRUCTURE.md"],
                "key_aspects": [
                    "infrastructure",         # AWS, GCP, Azure, on-prem
                    "containerization",       # Docker, Kubernetes
                    "ci_cd_pipeline",         # GitHub Actions, Jenkins
                    "monitoring",             # Prometheus, Datadog
                    "scaling_strategy"        # Auto-scaling, load balancing
                ],
                "similarity_weights": {
                    "infrastructure": 0.30,
                    "containerization": 0.25,
                    "ci_cd_pipeline": 0.20,
                    "monitoring": 0.15,
                    "scaling_strategy": 0.10
                }
            },

            "deployment_engineer": {
                "domain": "deployment",
                "extract_from": ["REQUIREMENTS.md", "DEPLOYMENT_PLAN.md"],
                "key_aspects": [
                    "deployment_strategy",    # Blue-green, canary, rolling
                    "environments",           # dev, staging, prod
                    "rollout_plan",           # Phased vs all-at-once
                    "rollback_strategy",      # How to undo deployments
                    "deployment_automation"   # Scripts, tools
                ],
                "similarity_weights": {
                    "deployment_strategy": 0.30,
                    "environments": 0.25,
                    "rollout_plan": 0.20,
                    "rollback_strategy": 0.15,
                    "deployment_automation": 0.10
                }
            }
        }

    def _initialize_reuse_thresholds(self) -> Dict[str, float]:
        """
        Define reuse thresholds for each persona.

        Configurable - some personas may need higher confidence to reuse.
        """
        return {
            # High-leverage, stable personas (can reuse with lower threshold)
            "system_architect": 0.85,      # 85%+ match → reuse architecture
            "security_engineer": 0.90,     # 90%+ match → reuse security (critical)
            "devops_engineer": 0.85,       # 85%+ match → reuse infrastructure
            "deployment_engineer": 0.85,   # 85%+ match → reuse deployment

            # Implementation personas (need higher match for reuse)
            "frontend_engineer": 0.88,     # 88%+ match → reuse frontend
            "backend_engineer": 0.88,      # 88%+ match → reuse backend
            "database_engineer": 0.90,     # 90%+ match → reuse DB (schema critical)
            "api_engineer": 0.87,          # 87%+ match → reuse API

            # Testing (can adapt easily, lower threshold)
            "testing_engineer": 0.80       # 80%+ match → reuse tests
        }

    def extract_persona_specs(
        self,
        persona_id: str,
        requirements_md: str,
        additional_artifacts: Optional[Dict[str, str]] = None
    ) -> PersonaDomainSpec:
        """
        Extract specs for a specific persona's domain.

        Generic extraction - reads from persona domain config.

        Args:
            persona_id: Persona to extract for
            requirements_md: REQUIREMENTS.md content
            additional_artifacts: Optional additional documents

        Returns:
            PersonaDomainSpec with extracted information
        """

        if persona_id not in self.persona_domains:
            raise ValueError(f"Unknown persona: {persona_id}")

        domain_config = self.persona_domains[persona_id]

        # Extract specs based on key aspects
        extracted_specs = {}
        for aspect in domain_config["key_aspects"]:
            extracted_specs[aspect] = self._extract_aspect(
                aspect,
                requirements_md,
                additional_artifacts or {}
            )

        # Calculate extraction confidence
        confidence = self._calculate_extraction_confidence(extracted_specs)

        return PersonaDomainSpec(
            persona_id=persona_id,
            domain=domain_config["domain"],
            specs=extracted_specs,
            extracted_from="REQUIREMENTS.md",
            confidence=confidence
        )

    def _extract_aspect(
        self,
        aspect: str,
        requirements_md: str,
        additional_artifacts: Dict[str, str]
    ) -> Any:
        """
        Extract a specific aspect from documents.

        Generic extraction using patterns and heuristics.
        """

        # Architecture patterns
        if aspect == "architecture_patterns":
            return self._extract_architecture_patterns(requirements_md)

        # Tech stack
        elif aspect == "tech_stack":
            return self._extract_tech_stack(requirements_md)

        # UI components
        elif aspect == "ui_components":
            return self._extract_ui_components(requirements_md)

        # User flows
        elif aspect == "user_flows":
            return self._extract_user_flows(requirements_md)

        # Business logic
        elif aspect == "business_logic":
            return self._extract_business_logic(requirements_md)

        # Data models (already handled by SpecExtractor, reuse)
        elif aspect == "data_models":
            from .spec_extractor import SpecExtractor
            extractor = SpecExtractor()
            specs = extractor.extract_from_text(requirements_md)
            return specs.get("data_models", [])

        # API endpoints (already handled, reuse)
        elif aspect == "api_endpoints":
            from .spec_extractor import SpecExtractor
            extractor = SpecExtractor()
            specs = extractor.extract_from_text(requirements_md)
            return specs.get("api_endpoints", [])

        # Auth mechanism
        elif aspect == "auth_mechanism":
            return self._extract_auth_mechanism(requirements_md)

        # Authorization model
        elif aspect == "authorization_model":
            return self._extract_authorization_model(requirements_md)

        # Infrastructure
        elif aspect == "infrastructure":
            return self._extract_infrastructure(requirements_md)

        # Generic fallback
        else:
            return self._extract_generic(aspect, requirements_md)

    def _extract_architecture_patterns(self, content: str) -> List[str]:
        """Extract architecture patterns mentioned"""
        patterns = []

        keywords = {
            "microservices": r"microservices?",
            "monolith": r"monolith(?:ic)?",
            "serverless": r"serverless",
            "event-driven": r"event[- ]driven",
            "layered": r"layered|n-tier",
            "mvc": r"\bmvc\b|model[- ]view[- ]controller",
            "hexagonal": r"hexagonal|ports[- ]and[- ]adapters",
            "clean": r"clean architecture"
        }

        for pattern_name, regex in keywords.items():
            if re.search(regex, content, re.IGNORECASE):
                patterns.append(pattern_name)

        return patterns

    def _extract_tech_stack(self, content: str) -> Dict[str, List[str]]:
        """Extract technology stack"""
        stack = {
            "frontend": [],
            "backend": [],
            "database": [],
            "infrastructure": []
        }

        # Frontend technologies
        frontend_techs = {
            "React": r"\bReact(?:JS)?\b",
            "Vue": r"\bVue(?:\.js)?\b",
            "Angular": r"\bAngular\b",
            "Svelte": r"\bSvelte\b",
            "Next.js": r"\bNext(?:\.js)?\b"
        }
        for tech, regex in frontend_techs.items():
            if re.search(regex, content, re.IGNORECASE):
                stack["frontend"].append(tech)

        # Backend technologies
        backend_techs = {
            "FastAPI": r"\bFastAPI\b",
            "Django": r"\bDjango\b",
            "Flask": r"\bFlask\b",
            "Express": r"\bExpress(?:\.js)?\b",
            "Node.js": r"\bNode(?:\.js)?\b",
            "Spring": r"\bSpring(?:Boot)?\b"
        }
        for tech, regex in backend_techs.items():
            if re.search(regex, content, re.IGNORECASE):
                stack["backend"].append(tech)

        # Database technologies
        db_techs = {
            "PostgreSQL": r"\bPostgreSQL\b|\bPostgres\b",
            "MySQL": r"\bMySQL\b",
            "MongoDB": r"\bMongoDB\b|\bMongo\b",
            "Redis": r"\bRedis\b",
            "Elasticsearch": r"\bElasticsearch\b"
        }
        for tech, regex in db_techs.items():
            if re.search(regex, content, re.IGNORECASE):
                stack["database"].append(tech)

        return stack

    def _extract_ui_components(self, content: str) -> List[str]:
        """Extract UI components mentioned"""
        components = []

        # Pattern: Look for component-like terms
        component_patterns = [
            r"(?:login|signup|registration)\s+(?:form|page|screen)",
            r"dashboard",
            r"navigation\s+(?:bar|menu)",
            r"(?:data|table)\s+grid",
            r"(?:search|filter)\s+(?:bar|component)",
            r"modal|dialog|popup",
            r"(?:user|profile)\s+(?:card|widget)",
            r"chart|graph|visualization"
        ]

        for pattern in component_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            components.extend([m.lower() for m in matches])

        return list(set(components))[:50]  # Unique, max 50

    def _extract_user_flows(self, content: str) -> List[str]:
        """Extract user flows/journeys"""
        flows = []

        # Pattern: "User can ... " or "Users should be able to ..."
        flow_patterns = [
            r"(?:user|users?)\s+(?:can|should|must|will)\s+(.+?)(?:\.|,|\n)",
            r"(?:allow|enable)\s+users?\s+to\s+(.+?)(?:\.|,|\n)"
        ]

        for pattern in flow_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            flows.extend([m.strip() for m in matches])

        return flows[:30]  # Max 30 flows

    def _extract_business_logic(self, content: str) -> List[str]:
        """Extract business logic/rules"""
        rules = []

        # Pattern: "The system shall calculate/validate/process ..."
        logic_patterns = [
            r"(?:calculate|compute|determine)\s+(.+?)(?:\.|,|\n)",
            r"(?:validate|verify|check)\s+(.+?)(?:\.|,|\n)",
            r"(?:process|handle|manage)\s+(.+?)(?:\.|,|\n)"
        ]

        for pattern in logic_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            rules.extend([m.strip() for m in matches])

        return rules[:40]  # Max 40 rules

    def _extract_auth_mechanism(self, content: str) -> List[str]:
        """Extract authentication mechanisms"""
        mechanisms = []

        auth_keywords = {
            "JWT": r"\bJWT\b|JSON Web Token",
            "OAuth": r"\bOAuth\b",
            "SAML": r"\bSAML\b",
            "Session": r"session[- ]based",
            "API Key": r"API[- ]key",
            "Basic Auth": r"basic auth"
        }

        for mechanism, regex in auth_keywords.items():
            if re.search(regex, content, re.IGNORECASE):
                mechanisms.append(mechanism)

        return mechanisms

    def _extract_authorization_model(self, content: str) -> List[str]:
        """Extract authorization models"""
        models = []

        authz_keywords = {
            "RBAC": r"\bRBAC\b|role[- ]based access",
            "ABAC": r"\bABAC\b|attribute[- ]based access",
            "ACL": r"\bACL\b|access control list",
            "Permission-based": r"permission[- ]based"
        }

        for model, regex in authz_keywords.items():
            if re.search(regex, content, re.IGNORECASE):
                models.append(model)

        return models

    def _extract_infrastructure(self, content: str) -> List[str]:
        """Extract infrastructure providers"""
        providers = []

        infra_keywords = {
            "AWS": r"\bAWS\b|Amazon Web Services",
            "GCP": r"\bGCP\b|Google Cloud",
            "Azure": r"\bAzure\b|Microsoft Azure",
            "Docker": r"\bDocker\b",
            "Kubernetes": r"\bKubernetes\b|\bK8s\b"
        }

        for provider, regex in infra_keywords.items():
            if re.search(regex, content, re.IGNORECASE):
                providers.append(provider)

        return providers

    def _extract_generic(self, aspect: str, content: str) -> Any:
        """Generic extraction for unknown aspects"""
        # Look for section matching aspect name
        section_pattern = rf"##\s+{re.escape(aspect)}\s*\n(.+?)(?=\n##|\Z)"
        match = re.search(section_pattern, content, re.IGNORECASE | re.DOTALL)

        if match:
            return match.group(1).strip()

        return None

    def _calculate_extraction_confidence(self, specs: Dict[str, Any]) -> float:
        """Calculate confidence in extraction quality"""
        total_aspects = len(specs)
        non_empty_aspects = sum(1 for v in specs.values() if v)

        return non_empty_aspects / total_aspects if total_aspects > 0 else 0.0

    def match_persona_artifacts(
        self,
        new_persona_specs: PersonaDomainSpec,
        existing_persona_specs: PersonaDomainSpec
    ) -> PersonaMatchResult:
        """
        Match artifacts for a specific persona between new and existing projects.

        Generic matching based on persona domain configuration.

        Args:
            new_persona_specs: Specs for new project
            existing_persona_specs: Specs from existing project

        Returns:
            PersonaMatchResult with similarity score and reuse decision
        """

        persona_id = new_persona_specs.persona_id

        if persona_id not in self.persona_domains:
            raise ValueError(f"Unknown persona: {persona_id}")

        domain_config = self.persona_domains[persona_id]
        weights = domain_config["similarity_weights"]

        # Calculate weighted similarity across all aspects
        aspect_similarities = {}
        weighted_sum = 0.0

        for aspect, weight in weights.items():
            new_val = new_persona_specs.specs.get(aspect)
            existing_val = existing_persona_specs.specs.get(aspect)

            similarity = self._compare_aspect(aspect, new_val, existing_val)
            aspect_similarities[aspect] = similarity
            weighted_sum += similarity * weight

        overall_similarity = weighted_sum

        # Decide if we should reuse
        threshold = self.reuse_thresholds.get(persona_id, 0.85)
        should_reuse = overall_similarity >= threshold

        # Build rationale
        rationale = self._build_rationale(
            persona_id,
            overall_similarity,
            aspect_similarities,
            should_reuse,
            threshold
        )

        return PersonaMatchResult(
            persona_id=persona_id,
            similarity_score=overall_similarity,
            should_reuse=should_reuse,
            source_project_id=existing_persona_specs.specs.get("project_id") if should_reuse else None,
            source_artifacts=[],  # Will be populated by executor
            match_details=aspect_similarities,
            rationale=rationale
        )

    def _compare_aspect(self, aspect: str, new_val: Any, existing_val: Any) -> float:
        """Compare specific aspect between new and existing"""

        if new_val is None or existing_val is None:
            return 0.0

        # List comparison (e.g., architecture patterns, tech stack)
        if isinstance(new_val, list) and isinstance(existing_val, list):
            return self._list_similarity(new_val, existing_val)

        # Dict comparison (e.g., tech stack with categories)
        elif isinstance(new_val, dict) and isinstance(existing_val, dict):
            return self._dict_similarity(new_val, existing_val)

        # String comparison
        elif isinstance(new_val, str) and isinstance(existing_val, str):
            return self._text_similarity(new_val, existing_val)

        # Fallback
        else:
            return 1.0 if new_val == existing_val else 0.0

    def _list_similarity(self, list1: List, list2: List) -> float:
        """Calculate similarity between two lists using Jaccard"""
        if not list1 or not list2:
            return 0.0

        set1 = set(str(x).lower() for x in list1)
        set2 = set(str(x).lower() for x in list2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0

    def _dict_similarity(self, dict1: Dict, dict2: Dict) -> float:
        """Calculate similarity between two dicts"""
        if not dict1 or not dict2:
            return 0.0

        # Compare keys
        keys1 = set(dict1.keys())
        keys2 = set(dict2.keys())
        common_keys = keys1 & keys2

        if not common_keys:
            return 0.0

        # Compare values for common keys
        similarities = []
        for key in common_keys:
            val1 = dict1[key]
            val2 = dict2[key]

            if isinstance(val1, list) and isinstance(val2, list):
                similarities.append(self._list_similarity(val1, val2))
            else:
                similarities.append(1.0 if val1 == val2 else 0.0)

        return sum(similarities) / len(similarities) if similarities else 0.0

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple token overlap"""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def _build_rationale(
        self,
        persona_id: str,
        overall_similarity: float,
        aspect_similarities: Dict[str, float],
        should_reuse: bool,
        threshold: float
    ) -> str:
        """Build human-readable rationale for reuse decision"""

        if should_reuse:
            # Find top matching aspects
            top_aspects = sorted(
                aspect_similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]

            top_matches = ", ".join([
                f"{aspect}: {sim:.0%}"
                for aspect, sim in top_aspects
            ])

            return (
                f"{persona_id} has {overall_similarity:.0%} match "
                f"(threshold: {threshold:.0%}). "
                f"Strong matches: {top_matches}. "
                f"Recommendation: Reuse existing artifacts."
            )
        else:
            # Find low matching aspects
            low_aspects = sorted(
                aspect_similarities.items(),
                key=lambda x: x[1]
            )[:3]

            low_matches = ", ".join([
                f"{aspect}: {sim:.0%}"
                for aspect, sim in low_aspects
            ])

            return (
                f"{persona_id} has {overall_similarity:.0%} match "
                f"(threshold: {threshold:.0%}). "
                f"Low matches: {low_matches}. "
                f"Recommendation: Execute fresh."
            )

    def build_persona_reuse_map(
        self,
        new_project_requirements: str,
        existing_project_requirements: str,
        persona_ids: List[str]
    ) -> PersonaReuseMap:
        """
        Build complete reuse map across all personas.

        Analyzes each persona independently and builds a decision map.

        Args:
            new_project_requirements: New project REQUIREMENTS.md
            existing_project_requirements: Existing project REQUIREMENTS.md
            persona_ids: List of personas to analyze

        Returns:
            PersonaReuseMap with per-persona decisions
        """

        persona_matches = {}
        personas_to_reuse = []
        personas_to_execute = []

        # Analyze each persona independently
        for persona_id in persona_ids:
            if persona_id == "requirement_analyst":
                # requirement_analyst always runs first
                personas_to_execute.append(persona_id)
                continue

            # Extract specs for this persona's domain
            new_specs = self.extract_persona_specs(persona_id, new_project_requirements)
            existing_specs = self.extract_persona_specs(persona_id, existing_project_requirements)

            # Match artifacts
            match_result = self.match_persona_artifacts(new_specs, existing_specs)
            persona_matches[persona_id] = match_result

            if match_result.should_reuse:
                personas_to_reuse.append(persona_id)
            else:
                personas_to_execute.append(persona_id)

        # Calculate overall similarity (weighted by persona importance)
        if persona_matches:
            overall_similarity = sum(
                m.similarity_score for m in persona_matches.values()
            ) / len(persona_matches)
        else:
            overall_similarity = 0.0

        # Estimate time savings
        total_personas = len(persona_ids)
        reused_personas = len(personas_to_reuse)
        time_savings_percent = (reused_personas / total_personas * 100) if total_personas > 0 else 0

        return PersonaReuseMap(
            overall_similarity=overall_similarity,
            persona_matches=persona_matches,
            personas_to_reuse=personas_to_reuse,
            personas_to_execute=personas_to_execute,
            estimated_time_savings_percent=time_savings_percent
        )
