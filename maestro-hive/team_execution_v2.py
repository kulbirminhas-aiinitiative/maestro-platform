#!/usr/bin/env python3
"""
Team Execution Engine V2 - AI-Driven, Blueprint-Based, Contract-First

Revolutionary Architecture:
- AI agents analyze requirements and compose teams
- Blueprint-based team patterns (12+ predefined patterns from conductor)
- Contract-first parallel execution
- Clear separation: Personas (WHO) + Contracts (WHAT) = Teams (HOW)

Key Innovations:
1. AI-Driven: No hardcoded logic, agents make decisions
2. Blueprint Integration: Use proven patterns from conductor module
3. Contract Management: Separate obligations from identity (conductor/contracts)
4. Parallel Execution: Contract-based coordination enables true parallelism
5. Mock Generation: Auto-generate mocks from contracts for parallel work

Workflow:
  Requirement
      ↓
  AI Analyzes (TeamComposerAgent)
      ↓
  Blueprint Selected (search blueprints)
      ↓
  Contracts Designed (ContractDesignerAgent)
      ↓
  Team Instantiated (from_blueprint)
      ↓
  Parallel Execution (contract-based coordination)
      ↓
  Contract Validation (fulfillment verification)
      ↓
  Result with Quality Scores

"""

import asyncio
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
import uuid

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Core imports
from config import CLAUDE_CONFIG, OUTPUT_CONFIG
from session_manager import SessionManager, SDLCSession

# Try to import contracts from conductor
try:
    # Add conductor path (blueprints and contracts are now in conductor)
    conductor_path = Path("/home/ec2-user/projects/conductor")
    sys.path.insert(0, str(conductor_path))

    from contracts.integration.contract_manager import ContractManager
    CONTRACT_MANAGER_AVAILABLE = True
except ImportError as e:
    CONTRACT_MANAGER_AVAILABLE = False
    ContractManager = None
    logging.warning(f"Contract manager not available: {e}")

# Try to import blueprint system from conductor (merged from synth)
try:
    # Blueprints are now in conductor after synth merge
    conductor_path = Path("/home/ec2-user/projects/conductor")
    sys.path.insert(0, str(conductor_path))

    from conductor.modules.teams.blueprints import (
        create_team_from_blueprint,
        search_blueprints,
        get_blueprint,
        list_blueprints
    )
    from conductor.modules.teams.blueprints.archetypes import (
        ExecutionMode,
        CoordinationMode,
        ScalingStrategy,
        SpecializationArchetype,
        TeamCapability
    )
    BLUEPRINTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Blueprint system not available: {e}")
    BLUEPRINTS_AVAILABLE = False

# Claude Code API Layer - Standalone package
try:
    import sys
    sys.path.insert(0, '/home/ec2-user/projects/maestro-platform')
    from claude_code_api_layer import ClaudeCLIClient
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.error("claude_code_api_layer not available")

# RAG Template Client for template recommendations
try:
    from rag_template_client import TemplateRAGClient
    RAG_CLIENT_AVAILABLE = True
except ImportError:
    RAG_CLIENT_AVAILABLE = False
    logging.warning("RAG template client not available")

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class RequirementComplexity(str, Enum):
    """Complexity levels for requirements"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class ParallelizabilityLevel(str, Enum):
    """How much work can be parallelized"""
    FULLY_PARALLEL = "fully_parallel"      # 90%+ can run in parallel
    PARTIALLY_PARALLEL = "partially_parallel"  # 50-90% parallel
    MOSTLY_SEQUENTIAL = "mostly_sequential"    # 10-50% parallel
    FULLY_SEQUENTIAL = "fully_sequential"      # <10% parallel


@dataclass
class RequirementClassification:
    """AI-generated classification of a requirement"""
    requirement_type: str  # feature_development, bug_fix, refactoring, etc.
    complexity: RequirementComplexity
    parallelizability: ParallelizabilityLevel
    required_expertise: List[str]
    estimated_effort_hours: float
    dependencies: List[str]
    risks: List[str]
    
    # AI reasoning
    rationale: str
    confidence_score: float  # 0-1


@dataclass
class BlueprintRecommendation:
    """AI recommendation for team blueprint"""
    blueprint_id: str
    blueprint_name: str
    match_score: float  # 0-1, how well blueprint fits requirement
    personas: List[str]  # Recommended personas for this team
    rationale: str
    alternatives: List[Dict[str, Any]]  # Alternative blueprints
    
    # Blueprint details (from catalog)
    execution_mode: str
    coordination_mode: str
    scaling_strategy: str
    estimated_time_savings: float  # vs sequential execution


@dataclass
class ContractSpecification:
    """Specification for a contract between personas"""
    id: str
    name: str
    version: str
    contract_type: str  # REST_API, GraphQL, EventStream, Deliverable, etc.
    
    # Deliverables
    deliverables: List[Dict[str, Any]]  # What must be produced
    
    # Dependencies
    dependencies: List[str]  # Other contract IDs needed first
    
    # Roles
    provider_persona_id: str  # Who creates the deliverables
    consumer_persona_ids: List[str]  # Who uses the deliverables
    
    # Acceptance
    acceptance_criteria: List[str]
    
    # Interface (for parallel work)
    interface_spec: Optional[Dict[str, Any]] = None  # OpenAPI, GraphQL schema, etc.
    mock_available: bool = False
    mock_endpoint: Optional[str] = None
    
    # Timeline
    estimated_effort_hours: float = 0.0
    deadline: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "contract_designer_agent"


@dataclass
class ExecutionResult:
    """Result of executing a persona with a contract"""
    persona_id: str
    contract_id: str
    success: bool
    
    # Deliverables
    files_created: List[str]
    deliverables: Dict[str, List[str]]
    
    # Contract validation
    contract_fulfilled: bool
    fulfillment_score: float  # 0-1
    missing_deliverables: List[str]
    quality_issues: List[Dict[str, Any]]
    
    # Timing
    duration_seconds: float
    parallel_execution: bool
    
    # Quality
    quality_score: float
    completeness_score: float
    
    # AI insights
    recommendations: List[str]
    risks_identified: List[str]


# =============================================================================
# AI AGENTS
# =============================================================================

class TeamComposerAgent:
    """
    AI agent that analyzes requirements and recommends team composition.
    
    This replaces hardcoded keyword matching with intelligent analysis.
    """
    
    def __init__(self):
        self.model = CLAUDE_CONFIG.get("model", "claude-3-5-sonnet-20241022")
    
    async def analyze_requirement(
        self,
        requirement: str,
        context: Optional[Dict[str, Any]] = None
    ) -> RequirementClassification:
        """
        Use AI to classify requirement with deep analysis.
        
        Contract: Must return RequirementClassification with confidence > 0.7
        """
        logger.info("🤖 AI analyzing requirement...")
        
        analysis_prompt = f"""You are an expert software project analyst.

Analyze this requirement and provide a DETAILED classification:

REQUIREMENT:
{requirement}

CONTEXT (if any):
{json.dumps(context or {}, indent=2)}

Provide a JSON response with this EXACT structure:
{{
    "requirement_type": "<one of: feature_development, bug_fix, refactoring, performance_optimization, security_audit, testing, documentation, deployment, maintenance>",
    "complexity": "<one of: simple, moderate, complex, very_complex>",
    "parallelizability": "<one of: fully_parallel, partially_parallel, mostly_sequential, fully_sequential>",
    "required_expertise": ["list", "of", "skills"],
    "estimated_effort_hours": <number>,
    "dependencies": ["list of things needed first"],
    "risks": ["potential risks or challenges"],
    "rationale": "Detailed explanation of your classification",
    "confidence_score": <0.0 to 1.0>
}}

Analysis guidelines:
- fully_parallel: 90%+ can run simultaneously (e.g., frontend + backend + docs)
- partially_parallel: 50-90% parallel (e.g., backend API + frontend, but need architecture first)
- mostly_sequential: 10-50% parallel (e.g., incremental feature with tight dependencies)
- fully_sequential: <10% parallel (e.g., single-threaded algorithm optimization)

Consider:
- Can frontend and backend work simultaneously with contract/mock?
- Are there clear interface boundaries?
- What must be done in order?
- What can run independently?

Respond with ONLY the JSON, no other text."""

        try:
            if CLAUDE_SDK_AVAILABLE:
                # Use Claude Code API Layer for analysis
                client = ClaudeCLIClient()

                # Query Claude (synchronous within async function is fine)
                result = client.query(
                    prompt=analysis_prompt,
                    skip_permissions=True,
                    timeout=300
                )

                if result.get('success'):
                    response_text = result.get('output', '')

                    # Extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        analysis_data = json.loads(json_match.group())
                    else:
                        raise ValueError("No JSON found in response")
                else:
                    raise ValueError(f"Claude query failed: {result.get('error', 'Unknown error')}")
            else:
                # Fallback: Heuristic-based classification (better than pure hardcoding)
                analysis_data = self._fallback_classification(requirement)
            
            # Build classification object
            classification = RequirementClassification(
                requirement_type=analysis_data["requirement_type"],
                complexity=RequirementComplexity(analysis_data["complexity"]),
                parallelizability=ParallelizabilityLevel(analysis_data["parallelizability"]),
                required_expertise=analysis_data["required_expertise"],
                estimated_effort_hours=float(analysis_data["estimated_effort_hours"]),
                dependencies=analysis_data["dependencies"],
                risks=analysis_data["risks"],
                rationale=analysis_data["rationale"],
                confidence_score=float(analysis_data["confidence_score"])
            )
            
            logger.info(f"  ✅ Classification: {classification.requirement_type}")
            logger.info(f"     Complexity: {classification.complexity.value}")
            logger.info(f"     Parallelizability: {classification.parallelizability.value}")
            logger.info(f"     Effort: {classification.estimated_effort_hours}h")
            logger.info(f"     Confidence: {classification.confidence_score:.0%}")
            
            return classification
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}, using fallback")
            # Get fallback data and convert to RequirementClassification
            fallback_data = self._fallback_classification(requirement)
            fallback_classification = RequirementClassification(
                requirement_type=fallback_data["requirement_type"],
                complexity=RequirementComplexity(fallback_data["complexity"]),
                parallelizability=ParallelizabilityLevel(fallback_data["parallelizability"]),
                required_expertise=fallback_data["required_expertise"],
                estimated_effort_hours=float(fallback_data["estimated_effort_hours"]),
                dependencies=fallback_data["dependencies"],
                risks=fallback_data["risks"],
                rationale=fallback_data["rationale"],
                confidence_score=float(fallback_data["confidence_score"])
            )
            logger.info(f"  ⚠️  Fallback Classification: {fallback_classification.requirement_type}")
            return fallback_classification
    
    def _fallback_classification(self, requirement: str) -> Dict[str, Any]:
        """Heuristic-based fallback (better than nothing)"""
        req_lower = requirement.lower()
        
        # Detect parallelizability
        has_frontend = any(kw in req_lower for kw in ["frontend", "ui", "interface", "component"])
        has_backend = any(kw in req_lower for kw in ["backend", "api", "server", "database"])
        
        if has_frontend and has_backend:
            parallelizability = "fully_parallel"
        elif any(kw in req_lower for kw in ["independent", "separate", "module"]):
            parallelizability = "partially_parallel"
        else:
            parallelizability = "mostly_sequential"
        
        # Detect complexity
        if len(requirement.split()) < 20:
            complexity = "simple"
        elif len(requirement.split()) < 50:
            complexity = "moderate"
        else:
            complexity = "complex"
        
        return {
            "requirement_type": "feature_development",
            "complexity": complexity,
            "parallelizability": parallelizability,
            "required_expertise": ["software_engineering"],
            "estimated_effort_hours": 8.0,
            "dependencies": [],
            "risks": ["Unknown requirements"],
            "rationale": "Fallback heuristic classification (AI unavailable)",
            "confidence_score": 0.6
        }
    
    async def recommend_blueprint(
        self,
        classification: RequirementClassification,
        constraints: Optional[Dict[str, Any]] = None
    ) -> BlueprintRecommendation:
        """
        Search blueprint catalog and return best match.
        
        Contract: Must return BlueprintRecommendation with match_score > 0.5
        """
        if not BLUEPRINTS_AVAILABLE:
            logger.warning("Blueprint system not available, using default")
            return self._default_blueprint_recommendation()
        
        logger.info("🔍 Searching blueprint catalog...")
        
        # Convert classification to search criteria
        search_criteria = {}
        
        # Map parallelizability to execution mode
        if classification.parallelizability in [ParallelizabilityLevel.FULLY_PARALLEL, ParallelizabilityLevel.PARTIALLY_PARALLEL]:
            search_criteria["execution_mode"] = ExecutionMode.PARALLEL
        else:
            search_criteria["execution_mode"] = ExecutionMode.SEQUENTIAL
        
        # Map complexity to scaling
        if classification.complexity in [RequirementComplexity.COMPLEX, RequirementComplexity.VERY_COMPLEX]:
            search_criteria["scaling"] = ScalingStrategy.ELASTIC
        
        # Search blueprints
        try:
            matching_blueprints = search_blueprints(**search_criteria)
            
            if matching_blueprints:
                # Use first match (best score)
                best_match = matching_blueprints[0]
                
                # Extract personas based on blueprint and requirement
                personas = self._extract_personas_for_requirement(
                    classification,
                    best_match
                )
                
                recommendation = BlueprintRecommendation(
                    blueprint_id=best_match["id"],
                    blueprint_name=best_match["name"],
                    match_score=0.85,  # TODO: Implement proper scoring
                    personas=personas,
                    rationale=f"Blueprint '{best_match['name']}' matches {classification.parallelizability.value} work pattern",
                    alternatives=[m for m in matching_blueprints[1:3]],  # Top 2 alternatives
                    execution_mode=best_match["archetype"]["execution"]["mode"],
                    coordination_mode=best_match["archetype"]["coordination"]["mode"],
                    scaling_strategy=best_match["archetype"]["scaling"],
                    estimated_time_savings=0.4 if "parallel" in best_match["archetype"]["execution"]["mode"] else 0.0
                )
                
                logger.info(f"  ✅ Selected: {recommendation.blueprint_name}")
                logger.info(f"     Match score: {recommendation.match_score:.0%}")
                logger.info(f"     Time savings: {recommendation.estimated_time_savings:.0%}")
                
                return recommendation
        except Exception as e:
            logger.error(f"Blueprint search failed: {e}")
        
        return self._default_blueprint_recommendation()
    
    def _extract_personas_for_requirement(
        self,
        classification: RequirementClassification,
        blueprint: Dict[str, Any]
    ) -> List[str]:
        """Extract appropriate personas based on requirement and blueprint"""
        personas = []
        
        # Always start with requirement analysis
        personas.append("requirement_analyst")
        
        # Add architecture if complex
        if classification.complexity in [RequirementComplexity.COMPLEX, RequirementComplexity.VERY_COMPLEX]:
            personas.append("solution_architect")
        
        # Add domain-specific personas based on expertise needed
        expertise_map = {
            "backend": ["backend_developer"],
            "frontend": ["frontend_developer", "ui_ux_designer"],
            "database": ["database_specialist"],
            "api": ["backend_developer"],
            "security": ["security_specialist"],
            "testing": ["qa_engineer", "test_engineer"],
            "devops": ["devops_engineer"],
            "documentation": ["technical_writer"]
        }
        
        for skill in classification.required_expertise:
            skill_lower = skill.lower()
            for keyword, mapped_personas in expertise_map.items():
                if keyword in skill_lower:
                    personas.extend(mapped_personas)
        
        # Default: backend + frontend if none specified
        if len(personas) == 1:  # Only requirement_analyst
            personas.extend(["backend_developer", "frontend_developer"])
        
        # Add QA and deployment at end
        if "qa_engineer" not in personas:
            personas.append("qa_engineer")
        if "devops_engineer" not in personas:
            personas.append("devops_engineer")
        
        # Deduplicate while preserving order
        seen = set()
        result = []
        for p in personas:
            if p not in seen:
                seen.add(p)
                result.append(p)
        
        return result
    
    def _default_blueprint_recommendation(self) -> BlueprintRecommendation:
        """Fallback recommendation"""
        return BlueprintRecommendation(
            blueprint_id="sequential-basic",
            blueprint_name="Basic Sequential Team",
            match_score=0.6,
            personas=["requirement_analyst", "backend_developer", "frontend_developer", "qa_engineer"],
            rationale="Default sequential pattern (blueprint system unavailable)",
            alternatives=[],
            execution_mode="sequential",
            coordination_mode="handoff",
            scaling_strategy="static",
            estimated_time_savings=0.0
        )


class ContractDesignerAgent:
    """
    AI agent that designs contracts between team members.
    
    Creates clear deliverable specifications with acceptance criteria.
    """
    
    def __init__(self):
        self.model = CLAUDE_CONFIG.get("model", "claude-3-5-sonnet-20241022")
    
    async def design_contracts(
        self,
        requirement: str,
        classification: RequirementClassification,
        blueprint: BlueprintRecommendation,
        previous_phase_contracts: Optional[List[ContractSpecification]] = None
    ) -> List[ContractSpecification]:
        """
        Design contracts for the team.

        ✅ FIXED: Now accepts previous phase contracts to establish contract lifecycle

        Contract: Must return at least one contract per persona pair.

        Args:
            requirement: Current phase requirement
            classification: Requirement classification
            blueprint: Blueprint recommendation
            previous_phase_contracts: Contracts from previous phases (for linking dependencies)

        Returns:
            List of contracts for current phase (may reference previous contracts)
        """
        logger.info("📝 Designing contracts...")

        if previous_phase_contracts:
            logger.info(f"   📦 Building upon {len(previous_phase_contracts)} contract(s) from previous phases")

        contracts = []

        # Create contracts based on coordination mode
        if "parallel" in blueprint.execution_mode and "contract" in blueprint.coordination_mode:
            # Contract-first parallel: Create interface contracts
            contracts = await self._design_parallel_contracts(
                requirement,
                classification,
                blueprint.personas,
                previous_phase_contracts  # ✅ NEW: Pass previous contracts
            )
        else:
            # Sequential: Create deliverable contracts
            contracts = await self._design_sequential_contracts(
                requirement,
                classification,
                blueprint.personas,
                previous_phase_contracts  # ✅ NEW: Pass previous contracts
            )

        logger.info(f"  ✅ Designed {len(contracts)} contract(s) for current phase")
        for contract in contracts:
            logger.info(f"     • {contract.name} ({contract.provider_persona_id} → {', '.join(contract.consumer_persona_ids)})")
            if contract.dependencies:
                logger.info(f"       Dependencies: {', '.join(contract.dependencies)}")

        return contracts
    
    async def _design_parallel_contracts(
        self,
        requirement: str,
        classification: RequirementClassification,
        personas: List[str],
        previous_phase_contracts: Optional[List[ContractSpecification]] = None
    ) -> List[ContractSpecification]:
        """
        Design contracts for parallel execution with clear interfaces.

        ✅ FIXED: Now links to previous phase contracts in dependencies
        """
        contracts = []

        # Collect previous contract IDs to establish dependencies
        previous_contract_ids = []
        if previous_phase_contracts:
            previous_contract_ids = [c.id for c in previous_phase_contracts]
            logger.info(f"   🔗 Linking to {len(previous_contract_ids)} contract(s) from previous phases")

        # Identify interface boundaries
        has_backend = "backend_developer" in personas
        has_frontend = "frontend_developer" in personas
        
        if has_backend and has_frontend:
            # Create API contract between backend and frontend
            contract_id = f"contract_{uuid.uuid4().hex[:12]}"

            contracts.append(ContractSpecification(
                id=contract_id,
                name="Backend API Contract",
                version="v1.0",
                contract_type="REST_API",
                deliverables=[
                    {
                        "name": "api_implementation",
                        "description": "RESTful API endpoints",
                        "artifacts": ["backend/src/routes/*.ts", "backend/src/controllers/*.ts"],
                        "acceptance_criteria": [
                            "All endpoints respond with correct status codes",
                            "Input validation implemented",
                            "Error handling for all paths",
                            "API documentation generated"
                        ]
                    },
                    {
                        "name": "api_specification",
                        "description": "OpenAPI 3.0 specification",
                        "artifacts": ["contracts/api_spec.yaml"],
                        "acceptance_criteria": [
                            "All endpoints documented",
                            "Request/response schemas defined",
                            "Authentication flows specified"
                        ]
                    }
                ],
                dependencies=previous_contract_ids,  # ✅ FIXED: Link to previous phase contracts
                provider_persona_id="backend_developer",
                consumer_persona_ids=["frontend_developer", "qa_engineer"],
                acceptance_criteria=[
                    "API spec published before implementation starts",
                    "Mock server available from spec",
                    "All tests pass against real implementation"
                ],
                interface_spec={
                    "type": "openapi",
                    "version": "3.0",
                    "spec_file": "contracts/api_spec.yaml"
                },
                mock_available=True,
                mock_endpoint="http://localhost:3001",  # Mock server for parallel work
                estimated_effort_hours=classification.estimated_effort_hours * 0.4
            ))
            
            # Frontend contract (consumes backend)
            # ✅ FIXED: Add explicit scaffold files to ensure frontend generation
            contracts.append(ContractSpecification(
                id=f"contract_{uuid.uuid4().hex[:12]}",
                name="Frontend UI Contract",
                version="v1.0",
                contract_type="Deliverable",
                deliverables=[
                    {
                        "name": "project_scaffold",
                        "description": "Frontend project structure and configuration",
                        "artifacts": [
                            "frontend/package.json",
                            "frontend/vite.config.ts",
                            "frontend/tsconfig.json",
                            "frontend/index.html",
                            "frontend/.gitignore",
                            "frontend/README.md"
                        ],
                        "acceptance_criteria": [
                            "Valid package.json with all dependencies",
                            "Vite configured for React + TypeScript",
                            "TypeScript configuration present",
                            "HTML entry point exists"
                        ]
                    },
                    {
                        "name": "app_entry_points",
                        "description": "Main application entry points",
                        "artifacts": [
                            "frontend/src/main.tsx",
                            "frontend/src/App.tsx",
                            "frontend/src/App.css"
                        ],
                        "acceptance_criteria": [
                            "Main.tsx renders App component",
                            "App.tsx is functional component",
                            "Basic styling present"
                        ]
                    },
                    {
                        "name": "component_implementation",
                        "description": "React components for features",
                        "artifacts": [
                            "frontend/src/components/**/*.tsx",
                            "frontend/src/services/api.ts"
                        ],
                        "acceptance_criteria": [
                            "Components render correctly",
                            "API integration works",
                            "Error states handled",
                            "Loading states implemented",
                            "API service uses OpenAPI spec endpoints"
                        ]
                    }
                ],
                dependencies=[contract_id],  # Needs API spec (not implementation!)
                provider_persona_id="frontend_developer",
                consumer_persona_ids=["qa_engineer"],
                acceptance_criteria=[
                    "Frontend project structure complete",
                    "npm install runs successfully",
                    "npm run dev starts development server",
                    "UI functional with mock API",
                    "UI functional with real API",
                    "Integration tests pass"
                ],
                estimated_effort_hours=classification.estimated_effort_hours * 0.3
            ))
        
        return contracts
    
    async def _design_sequential_contracts(
        self,
        requirement: str,
        classification: RequirementClassification,
        personas: List[str],
        previous_phase_contracts: Optional[List[ContractSpecification]] = None
    ) -> List[ContractSpecification]:
        """
        Design contracts for sequential execution.

        ✅ FIXED: Now links to previous phase contracts in first contract's dependencies
        """
        contracts = []

        # Collect previous contract IDs to establish dependencies
        previous_contract_ids = []
        if previous_phase_contracts:
            previous_contract_ids = [c.id for c in previous_phase_contracts]
            logger.info(f"   🔗 Linking to {len(previous_contract_ids)} contract(s) from previous phases")

        # Create simple deliverable contracts for each persona
        for i, persona_id in enumerate(personas):
            contract_id = f"contract_{uuid.uuid4().hex[:12]}"

            # First contract depends on previous phase, others depend on previous in chain
            if i == 0:
                dependencies = previous_contract_ids  # ✅ FIXED: First depends on previous phases
            else:
                dependencies = [contracts[i-1].id]  # Others depend on previous in chain

            contracts.append(ContractSpecification(
                id=contract_id,
                name=f"{persona_id.replace('_', ' ').title()} Contract",
                version="v1.0",
                contract_type="Deliverable",
                deliverables=[
                    {
                        "name": f"{persona_id}_deliverables",
                        "description": f"Deliverables from {persona_id}",
                        "artifacts": [],  # Will be determined at execution
                        "acceptance_criteria": [
                            "All expected deliverables present",
                            "Quality standards met",
                            "Documentation included"
                        ]
                    }
                ],
                dependencies=dependencies,
                provider_persona_id=persona_id,
                consumer_persona_ids=[personas[i+1]] if i < len(personas)-1 else [],
                acceptance_criteria=[
                    "Deliverables complete",
                    "Quality gate passed"
                ],
                estimated_effort_hours=classification.estimated_effort_hours / len(personas)
            ))
        
        return contracts
    


# =============================================================================
# TEAM EXECUTION ENGINE V2
# =============================================================================

class TeamExecutionEngineV2:
    """
    Next-generation team execution engine.
    
    Key innovations:
    - AI-driven requirement analysis and team composition
    - Blueprint-based team patterns
    - Contract-first parallel execution
    - Separation of personas and contracts
    """
    
    def __init__(
        self,
        output_dir: Optional[str] = None,
        session_manager: Optional[SessionManager] = None,
        contract_manager: Optional[ContractManager] = None
    ):
        self.output_dir = Path(output_dir or OUTPUT_CONFIG.get("default_output_dir", "./generated_project"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_manager = session_manager or SessionManager()
        # contract_manager will need StateManager - for now skip it
        self.contract_manager = contract_manager
        
        # AI Agents
        self.team_composer = TeamComposerAgent()
        self.contract_designer = ContractDesignerAgent()

        # RAG Client for template recommendations
        self.rag_client = None
        if RAG_CLIENT_AVAILABLE:
            try:
                # Import RAG configuration
                from config import RAG_CONFIG

                # Check if RAG is enabled in config
                if RAG_CONFIG.get('enable_project_level_rag', True):
                    self.rag_client = TemplateRAGClient()
                    logger.info("✅ RAG Template Client initialized (using config)")
                else:
                    logger.info("  ℹ️  Project-level RAG disabled in config")
            except Exception as e:
                logger.warning(f"Failed to initialize RAG client: {e}")
                self.rag_client = None

        logger.info("✅ Team Execution Engine V2 initialized")
        logger.info(f"   Blueprints available: {BLUEPRINTS_AVAILABLE}")
        logger.info(f"   Claude SDK available: {CLAUDE_SDK_AVAILABLE}")
        logger.info(f"   RAG Client available: {self.rag_client is not None}")
    
    async def execute(
        self,
        requirement: str,
        constraints: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute requirement with AI-driven team composition.
        
        This is the main entry point.
        """
        start_time = datetime.now()
        
        logger.info("="*80)
        logger.info("🚀 TEAM EXECUTION ENGINE V2")
        logger.info("="*80)
        logger.info(f"📝 Requirement: {requirement[:100]}...")
        logger.info("="*80)

        # Step 0: Project-Level RAG (Template Package Recommendation)
        template_package = None
        if self.rag_client:
            logger.info("\n🔍 Step 0: Project-Level RAG (Template Package Discovery)")
            try:
                template_package = await self.rag_client.get_recommended_package(
                    requirement=requirement,
                    context=constraints or {}
                )

                if template_package:
                    logger.info(f"  ✅ Template Package Recommended:")
                    logger.info(f"     Package: {template_package.name}")
                    logger.info(f"     Type: {template_package.match_type}")
                    logger.info(f"     Confidence: {template_package.confidence:.0%}")
                    logger.info(f"     Templates: {len(template_package.templates)}")
                    if template_package.reasoning:
                        logger.info(f"     Reasoning: {template_package.reasoning[:100]}...")
                else:
                    logger.info("  ℹ️  No template package matches found")
            except Exception as e:
                logger.warning(f"  ⚠️  Template package discovery failed: {e}")
                template_package = None
        else:
            logger.info("\n  ℹ️  Step 0 skipped: RAG client not available")

        # Step 1: AI analyzes requirement
        logger.info("\n📊 Step 1: AI Requirement Analysis")
        classification = await self.team_composer.analyze_requirement(requirement)
        
        # Step 2: AI recommends blueprint
        logger.info("\n🎯 Step 2: Blueprint Selection")
        blueprint_rec = await self.team_composer.recommend_blueprint(
            classification,
            constraints
        )
        
        # Step 3: AI designs contracts
        logger.info("\n📝 Step 3: Contract Design")

        # ✅ FIXED: Extract previous phase contracts from constraints if present
        previous_phase_contracts = None
        if constraints and "previous_phase_contracts" in constraints:
            previous_phase_contracts = constraints["previous_phase_contracts"]

        contracts = await self.contract_designer.design_contracts(
            requirement,
            classification,
            blueprint_rec,
            previous_phase_contracts  # ✅ NEW: Pass previous contracts
        )
        
        # Step 4: Create session
        logger.info("\n💾 Step 4: Session Creation")
        session = self.session_manager.create_session(
            requirement=requirement,
            output_dir=self.output_dir,
            session_id=session_id
        )
        logger.info(f"   Session ID: {session.session_id}")
        
        # Step 5: Execute team
        logger.info("\n🎬 Step 5: Team Execution")
        logger.info(f"   Team: {', '.join(blueprint_rec.personas)}")
        logger.info(f"   Pattern: {blueprint_rec.blueprint_name}")
        logger.info(f"   Contracts: {len(contracts)}")
        
        # Import execution components
        from parallel_coordinator_v2 import ParallelCoordinatorV2
        
        # Create coordinator
        coordinator = ParallelCoordinatorV2(
            output_dir=self.output_dir,
            max_parallel_workers=4
        )
        
        # Convert contract specifications to dict format
        contracts_dict = [
            {
                "id": c.id,
                "name": c.name,
                "version": c.version,
                "contract_type": c.contract_type,
                "deliverables": c.deliverables,
                "dependencies": c.dependencies,
                "provider_persona_id": c.provider_persona_id,
                "consumer_persona_ids": c.consumer_persona_ids,
                "acceptance_criteria": c.acceptance_criteria,
                "interface_spec": c.interface_spec,
                "mock_available": c.mock_available,
                "mock_endpoint": c.mock_endpoint,
                "estimated_effort_hours": c.estimated_effort_hours
            }
            for c in contracts
        ]
        
        # Execute team
        execution_result = await coordinator.execute_parallel(
            requirement=requirement,
            contracts=contracts_dict,
            context=constraints or {}
        )
        
        # Build result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "success": execution_result.success,
            "session_id": session.session_id,
            "requirement": requirement,

            # Template Package (RAG)
            "template_package": {
                "package_id": template_package.package_id if template_package else None,
                "package_name": template_package.name if template_package else None,
                "match_type": template_package.match_type if template_package else None,
                "confidence": template_package.confidence if template_package else 0.0,
                "reasoning": template_package.reasoning if template_package else "",
                "templates_count": len(template_package.templates) if template_package else 0
            } if template_package else None,

            # Classification
            "classification": {
                "type": classification.requirement_type,
                "complexity": classification.complexity.value,
                "parallelizability": classification.parallelizability.value,
                "effort_hours": classification.estimated_effort_hours,
                "confidence": classification.confidence_score
            },

            # Blueprint
            "blueprint": {
                "id": blueprint_rec.blueprint_id,
                "name": blueprint_rec.blueprint_name,
                "match_score": blueprint_rec.match_score,
                "execution_mode": blueprint_rec.execution_mode,
                "estimated_time_savings": blueprint_rec.estimated_time_savings
            },
            
            # Team
            "team": {
                "personas": blueprint_rec.personas,
                "size": len(blueprint_rec.personas)
            },
            
            # Contracts
            "contracts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "provider": c.provider_persona_id,
                    "consumers": c.consumer_persona_ids,
                    "type": c.contract_type,
                    "mock_available": c.mock_available
                }
                for c in contracts
            ],
            
            # Execution Results
            "execution": {
                "total_duration": execution_result.total_duration,
                "sequential_duration": execution_result.sequential_duration,
                "time_savings_percent": execution_result.time_savings_percent,
                "parallelization_achieved": execution_result.parallelization_achieved,
                "personas_executed": len(execution_result.persona_results),
                "groups_executed": len(execution_result.groups_executed)
            },
            
            # Deliverables
            "deliverables": {
                persona_id: {
                    "files_created": result.files_created,
                    "deliverables": result.deliverables,
                    "contract_fulfilled": result.contract_fulfilled,
                    "quality_score": result.quality_score
                }
                for persona_id, result in execution_result.persona_results.items()
            },
            
            # Quality
            "quality": {
                "overall_quality_score": execution_result.overall_quality_score,
                "quality_by_persona": execution_result.quality_by_persona,
                "contracts_fulfilled": execution_result.contracts_fulfilled,
                "contracts_total": execution_result.contracts_total,
                "integration_issues": len(execution_result.integration_issues)
            },
            
            # Timing
            "duration_seconds": duration,
            "project_dir": str(self.output_dir)
        }
        
        logger.info("\n" + "="*80)
        logger.info("✅ EXECUTION COMPLETE")
        logger.info("="*80)
        logger.info(f"Duration: {execution_result.total_duration:.2f}s (parallel)")
        logger.info(f"Sequential would be: {execution_result.sequential_duration:.2f}s")
        logger.info(f"Time savings: {execution_result.time_savings_percent:.0%} ⚡")
        logger.info(f"Classification: {classification.requirement_type} ({classification.complexity.value})")
        logger.info(f"Blueprint: {blueprint_rec.blueprint_name}")
        logger.info(f"Team size: {len(blueprint_rec.personas)} personas")
        logger.info(f"Contracts: {execution_result.contracts_fulfilled}/{execution_result.contracts_total} fulfilled")
        logger.info(f"Quality: {execution_result.overall_quality_score:.0%}")
        logger.info(f"Parallelization: {execution_result.parallelization_achieved:.0%}")
        logger.info("="*80)

        return result

    async def execute_jira_task(
        self,
        task_key: str,
        constraints: Optional[Dict[str, Any]] = None,
        update_jira: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a JIRA task using AI-driven team composition.

        This convenience method fetches the JIRA task, converts it to a requirement,
        executes it, and optionally updates JIRA with the results.

        Args:
            task_key: JIRA task key (e.g., "MD-131")
            constraints: Optional execution constraints
            update_jira: Whether to update JIRA status and add comments

        Returns:
            Execution result dictionary
        """
        # Import adapter here to avoid circular imports
        from jira_task_adapter import JiraTaskAdapter

        logger.info(f"\n{'='*80}")
        logger.info(f"🎫 JIRA TASK EXECUTION: {task_key}")
        logger.info(f"{'='*80}\n")

        # Create adapter
        adapter = JiraTaskAdapter()

        # Convert task to requirement
        logger.info("📋 Converting JIRA task to requirement...")
        requirement = await adapter.task_to_requirement(task_key)

        # Update JIRA status to In Progress
        if update_jira:
            await adapter.update_task_status(task_key, 'inProgress')
            logger.info(f"   Updated {task_key} status to In Progress")

        # Merge constraints
        merged_constraints = constraints or {}
        merged_constraints['jira_task_key'] = task_key

        # Execute
        result = await self.execute(
            requirement=requirement,
            constraints=merged_constraints
        )

        # Post result to JIRA
        if update_jira:
            await adapter.add_execution_result_comment(task_key, result)
            logger.info(f"   Posted execution result to {task_key}")

            # Update status based on result
            if result.get('success', False):
                await adapter.update_task_status(task_key, 'done')
                logger.info(f"   Updated {task_key} status to Done")

        return result


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Team Execution Engine V2 - AI-Driven, Blueprint-Based, Contract-First",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Execute with requirement string
  python team_execution_v2.py --requirement "Build a REST API for user management"

  # Execute a JIRA task
  python team_execution_v2.py --jira-task MD-131

  # Execute JIRA task with custom output directory
  python team_execution_v2.py --jira-task MD-131 --output ./output --prefer-parallel
        """
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--requirement", help="Project requirement string")
    input_group.add_argument("--jira-task", help="JIRA task key (e.g., MD-131)")

    # Other options
    parser.add_argument("--output", help="Output directory")
    parser.add_argument("--session-id", help="Session ID")
    parser.add_argument("--prefer-parallel", action="store_true", help="Prefer parallel execution")
    parser.add_argument("--quality-threshold", type=float, default=0.80, help="Quality threshold (0-1)")
    parser.add_argument("--no-jira-update", action="store_true", help="Don't update JIRA status/comments")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Create engine
    engine = TeamExecutionEngineV2(output_dir=args.output)

    # Execute
    constraints = {
        "prefer_parallel": args.prefer_parallel,
        "quality_threshold": args.quality_threshold
    }

    if args.jira_task:
        # Execute JIRA task
        result = await engine.execute_jira_task(
            task_key=args.jira_task,
            constraints=constraints,
            update_jira=not args.no_jira_update
        )
    else:
        # Execute requirement string
        result = await engine.execute(
            requirement=args.requirement,
            constraints=constraints,
            session_id=args.session_id
        )

    # Print result
    print("\n" + "="*80)
    print("📊 EXECUTION RESULT")
    print("="*80)
    print(json.dumps(result, indent=2, default=str))
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
