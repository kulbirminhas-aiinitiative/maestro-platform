# Implementation Guide: Team Execution Enhancements
## Step-by-Step Technical Implementation

**Version:** 1.0
**Date:** 2025
**Target:** team_execution.py + contract_manager.py integration

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Phase 1: Blueprint Integration](#phase-1-blueprint-integration)
3. [Phase 2: Contract-Persona Separation](#phase-2-contract-persona-separation)
4. [Phase 3: Enhanced Contract Management](#phase-3-enhanced-contract-management)
5. [Testing Strategy](#testing-strategy)
6. [Migration Path](#migration-path)

---

## Quick Start

### Prerequisites

```bash
# Ensure both repositories are accessible
cd /home/ec2-user/projects/maestro-platform

# Verify synth blueprint system
python -c "from synth.maestro_ml.modules.teams.blueprints import BLUEPRINT_REGISTRY; print(f'Blueprints available: {len(BLUEPRINT_REGISTRY.blueprints)}')"

# Verify maestro-hive is functional
cd maestro-hive
python -c "from personas import SDLCPersonas; print(f'Personas loaded: {len(SDLCPersonas.get_all_personas())}')"
```

### Installation

```python
# Add synth to Python path in team_execution.py
import sys
from pathlib import Path

SYNTH_PATH = Path(__file__).parent.parent.parent / "synth"
if str(SYNTH_PATH) not in sys.path:
    sys.path.insert(0, str(SYNTH_PATH))
```

---

## Phase 1: Blueprint Integration

### Step 1.1: Import Blueprint System

**File:** `team_execution.py` (add to imports section)

```python
# ============================================================================
# NEW: Blueprint System Integration
# ============================================================================

try:
    from maestro_ml.modules.teams.blueprints import (
        create_team_from_blueprint,
        search_blueprints,
        get_blueprint_by_id,
        list_all_blueprints,
        BLUEPRINT_REGISTRY
    )
    from maestro_ml.modules.teams.archetypes import (
        TeamArchetype,
        ExecutionMode,
        CoordinationMode,
        ScalingStrategy
    )
    BLUEPRINTS_AVAILABLE = True
    logger.info("✅ Blueprint system loaded successfully")
except ImportError as e:
    BLUEPRINTS_AVAILABLE = False
    logger.warning(f"⚠️  Blueprint system not available: {e}")
    logger.warning("   Install synth: pip install -e ../synth")
```

### Step 1.2: Add Blueprint Selector

**File:** `team_execution.py` (new class method)

```python
class AutonomousSDLCEngineV3_1_Resumable:
    """
    Enhanced with blueprint support
    """
    
    def __init__(self, ...):
        # ... existing init ...
        
        # NEW: Blueprint support
        self.use_blueprints = BLUEPRINTS_AVAILABLE and kwargs.get("use_blueprints", True)
        self.blueprint_id = kwargs.get("blueprint_id", None)
        self.auto_select_blueprint = kwargs.get("auto_select_blueprint", False)
        
    async def select_team_blueprint(
        self,
        requirement: str,
        project_type: Optional[str] = None
    ) -> Optional[str]:
        """
        Select optimal team blueprint based on requirements
        
        Args:
            requirement: Project requirements text
            project_type: Optional hint (web_app, mobile_app, api, ml_pipeline)
            
        Returns:
            Blueprint ID or None if not using blueprints
        """
        if not self.use_blueprints:
            return None
            
        if self.blueprint_id:
            # User specified blueprint
            return self.blueprint_id
            
        if not self.auto_select_blueprint:
            return None
            
        logger.info("🔍 Auto-selecting optimal team blueprint...")
        
        # Analyze requirements to determine characteristics
        characteristics = await self._analyze_requirements(requirement)
        
        # Determine execution mode from requirements
        execution_mode = self._determine_execution_mode(characteristics)
        
        # Determine scaling needs
        scaling = self._determine_scaling_needs(characteristics)
        
        # Search for matching blueprints
        candidates = search_blueprints(
            execution_mode=execution_mode,
            scaling=scaling,
            capabilities=characteristics.get("capabilities", [])
        )
        
        if not candidates:
            logger.warning(f"⚠️  No blueprints found for {execution_mode}/{scaling}")
            return None
            
        # Rank candidates by match score
        best_match = self._rank_blueprint_candidates(
            candidates,
            characteristics
        )
        
        logger.info(f"✅ Selected blueprint: {best_match['id']}")
        logger.info(f"   Execution: {best_match['archetype']['execution']}")
        logger.info(f"   Scaling: {best_match['archetype']['scaling']}")
        logger.info(f"   Personas: {len(best_match['personas'])}")
        
        return best_match['id']
        
    async def _analyze_requirements(
        self,
        requirement: str
    ) -> Dict[str, Any]:
        """
        Analyze requirements to extract characteristics
        
        Uses AI to understand project complexity, parallelizability, etc.
        """
        # Simple rule-based analysis (can be enhanced with ML)
        characteristics = {
            "complexity": "medium",
            "parallel_work": False,
            "real_time": False,
            "scale": "small",
            "capabilities": []
        }
        
        req_lower = requirement.lower()
        
        # Complexity detection
        if any(word in req_lower for word in ["complex", "enterprise", "large-scale"]):
            characteristics["complexity"] = "high"
        elif any(word in req_lower for word in ["simple", "basic", "minimal"]):
            characteristics["complexity"] = "low"
            
        # Parallel work detection
        if any(word in req_lower for word in ["frontend", "backend", "api", "database"]):
            characteristics["parallel_work"] = True
            
        # Real-time detection
        if any(word in req_lower for word in ["real-time", "websocket", "streaming", "live"]):
            characteristics["real_time"] = True
            characteristics["capabilities"].append("real_time")
            
        # Performance requirements
        if any(word in req_lower for word in ["performance", "fast", "optimize", "scale"]):
            characteristics["capabilities"].append("performance_focused")
            
        # Security requirements
        if any(word in req_lower for word in ["secure", "auth", "encrypt", "compliance"]):
            characteristics["capabilities"].append("security_focused")
            
        return characteristics
        
    def _determine_execution_mode(
        self,
        characteristics: Dict[str, Any]
    ) -> str:
        """
        Determine optimal execution mode from characteristics
        """
        if characteristics.get("parallel_work"):
            return "parallel"
        elif characteristics.get("complexity") == "high":
            return "hybrid"
        else:
            return "sequential"
            
    def _determine_scaling_needs(
        self,
        characteristics: Dict[str, Any]
    ) -> str:
        """
        Determine scaling strategy from characteristics
        """
        if characteristics.get("complexity") == "high":
            return "elastic"
        elif characteristics.get("scale") == "large":
            return "elastic"
        else:
            return "static"
            
    def _rank_blueprint_candidates(
        self,
        candidates: List[Dict[str, Any]],
        characteristics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Rank blueprint candidates by match score
        """
        if not candidates:
            return None
            
        # Simple scoring (can be enhanced)
        def score_blueprint(blueprint):
            score = 0
            
            # Execution mode match
            if blueprint["archetype"]["execution"] == self._determine_execution_mode(characteristics):
                score += 10
                
            # Scaling match
            if blueprint["archetype"]["scaling"] == self._determine_scaling_needs(characteristics):
                score += 5
                
            # Capability matches
            blueprint_capabilities = blueprint["archetype"].get("capabilities", [])
            required_capabilities = characteristics.get("capabilities", [])
            
            for cap in required_capabilities:
                if cap in blueprint_capabilities:
                    score += 2
                    
            # Maturity bonus
            maturity_scores = {"stable": 3, "beta": 2, "experimental": 1}
            score += maturity_scores.get(blueprint.get("maturity", "beta"), 0)
            
            return score
            
        # Sort by score
        scored = [(bp, score_blueprint(bp)) for bp in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return scored[0][0]  # Return highest scored blueprint
```

### Step 1.3: Integrate Blueprint into Execute Method

**File:** `team_execution.py` (modify `execute` method)

```python
async def execute(
    self,
    requirement: str,
    session_id: Optional[str] = None,
    resume_session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute SDLC workflow with optional blueprint support
    """
    # ... existing session loading ...
    
    # NEW: Select team blueprint if enabled
    blueprint_id = await self.select_team_blueprint(requirement)
    
    if blueprint_id:
        logger.info(f"\n{'='*80}")
        logger.info(f"📋 Using Team Blueprint: {blueprint_id}")
        logger.info(f"{'='*80}\n")
        
        # Get personas from blueprint
        blueprint = get_blueprint_by_id(blueprint_id)
        if blueprint:
            # Override selected_personas with blueprint personas
            blueprint_personas = blueprint["personas"]
            
            # Filter to only include personas not yet completed
            if self.force_rerun:
                pending_personas = blueprint_personas
            else:
                pending_personas = [
                    p for p in blueprint_personas
                    if p not in session.completed_personas
                ]
                
            # Update execution order from blueprint coordination strategy
            execution_order = self._apply_blueprint_coordination(
                pending_personas,
                blueprint["archetype"]["coordination"]
            )
            
            logger.info(f"📝 Blueprint personas: {', '.join(blueprint_personas)}")
            logger.info(f"⏳ To execute: {', '.join(execution_order)}")
        else:
            # Fallback to original logic
            logger.warning(f"⚠️  Blueprint {blueprint_id} not found, using manual selection")
            pending_personas = self._determine_pending_personas(session)
            execution_order = self._determine_execution_order(pending_personas)
    else:
        # Original logic: manual persona selection
        pending_personas = self._determine_pending_personas(session)
        execution_order = self._determine_execution_order(pending_personas)
        
    # ... rest of execute method unchanged ...
    
def _apply_blueprint_coordination(
    self,
    personas: List[str],
    coordination_mode: str
) -> List[str]:
    """
    Apply blueprint's coordination strategy to determine execution order
    
    Coordination modes:
    - handoff: Sequential execution (A → B → C)
    - parallel: Concurrent execution where possible
    - consensus: Collaborative with group discussion
    - delegation: Hierarchical with reviews
    """
    if coordination_mode == "handoff":
        # Sequential: use standard execution order
        return self._determine_execution_order(personas)
        
    elif coordination_mode == "broadcast":
        # All personas get same input simultaneously
        # Still execute sequentially but with shared context
        return personas  # Order doesn't matter as much
        
    elif coordination_mode == "consensus":
        # Collaborative: intersperse with group discussions
        # For now, use standard order (enhance later with group chat)
        return self._determine_execution_order(personas)
        
    elif coordination_mode == "delegation":
        # Hierarchical: leaders first, then implementers
        leaders = ["requirement_analyst", "solution_architect", "tech_lead"]
        implementers = [p for p in personas if p not in leaders]
        reviewers = ["qa_engineer", "security_specialist"]
        
        ordered = []
        ordered.extend([p for p in leaders if p in personas])
        ordered.extend([p for p in implementers if p not in reviewers])
        ordered.extend([p for p in reviewers if p in personas])
        
        return ordered
        
    else:
        # Default: use standard execution order
        return self._determine_execution_order(personas)
```

### Step 1.4: Add Blueprint CLI Arguments

**File:** `team_execution.py` (modify `main()` function)

```python
async def main():
    """CLI entry point with blueprint support"""
    parser = argparse.ArgumentParser(...)
    
    # ... existing arguments ...
    
    # NEW: Blueprint arguments
    blueprint_group = parser.add_argument_group("Blueprint Options")
    blueprint_group.add_argument(
        "--blueprint",
        help="Specify blueprint ID (e.g., 'parallel-elastic', 'sequential-basic')"
    )
    blueprint_group.add_argument(
        "--auto-blueprint",
        action="store_true",
        help="Automatically select optimal blueprint based on requirements"
    )
    blueprint_group.add_argument(
        "--list-blueprints",
        action="store_true",
        help="List all available team blueprints"
    )
    blueprint_group.add_argument(
        "--no-blueprints",
        action="store_true",
        help="Disable blueprint system (use manual persona selection)"
    )
    
    args = parser.parse_args()
    
    # Handle blueprint listing
    if args.list_blueprints:
        print_available_blueprints()
        return
        
    # ... existing engine creation ...
    
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=args.personas if args.personas else [],
        output_dir=args.output,
        session_manager=session_manager,
        maestro_ml_url=args.maestro_ml_url,
        enable_persona_reuse=not args.disable_persona_reuse,
        force_rerun=args.force,
        # NEW: Blueprint options
        use_blueprints=not args.no_blueprints,
        blueprint_id=args.blueprint,
        auto_select_blueprint=args.auto_blueprint
    )
    
    # ... rest of main ...

def print_available_blueprints():
    """Print all available blueprints"""
    if not BLUEPRINTS_AVAILABLE:
        print("❌ Blueprint system not available")
        print("   Install synth: pip install -e ../synth")
        return
        
    blueprints = list_all_blueprints()
    
    print("\n" + "="*80)
    print("📋 AVAILABLE TEAM BLUEPRINTS")
    print("="*80 + "\n")
    
    by_category = {}
    for bp in blueprints:
        category = bp["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(bp)
        
    for category, bps in by_category.items():
        print(f"\n{category.upper()}:")
        for bp in bps:
            print(f"\n  📋 {bp['id']}")
            print(f"     Name: {bp['name']}")
            print(f"     Execution: {bp['archetype']['execution']}")
            print(f"     Scaling: {bp['archetype']['scaling']}")
            print(f"     Personas: {len(bp['personas'])}")
            print(f"     Maturity: {bp.get('maturity', 'beta')}")
            print(f"     Use cases: {', '.join(bp.get('use_cases', [])[:2])}")
            
    print("\n" + "="*80)
    print("\nUsage:")
    print("  python team_execution.py --blueprint parallel-elastic --requirement '...'")
    print("  python team_execution.py --auto-blueprint --requirement '...'")
    print("="*80 + "\n")
```

---

## Phase 2: Contract-Persona Separation

### Step 2.1: Create PersonaContract Model

**File:** `maestro-hive/models/persona_contract.py` (NEW FILE)

```python
"""
Persona Contract Models - Contracts as Add-Ons to Personas

Contracts are decoupled from persona execution logic.
They provide interface specifications that personas implement or consume.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum


class ContractRole(Enum):
    """Role of persona in contract"""
    PROVIDER = "provider"  # Persona implements this contract
    CONSUMER = "consumer"  # Persona uses this contract


class ContractType(Enum):
    """Type of contract"""
    REST_API = "REST_API"
    GRAPHQL = "GraphQL"
    GRPC = "gRPC"
    EVENT_STREAM = "EventStream"
    DATABASE_SCHEMA = "DatabaseSchema"
    MESSAGE_QUEUE = "MessageQueue"


@dataclass
class PersonaContract:
    """
    Contract attached to a persona
    
    Represents an interface specification that a persona either:
    - Implements (provider role)
    - Consumes (consumer role)
    
    Examples:
    - backend_developer PROVIDES BlogAPI (REST_API)
    - frontend_developer CONSUMES BlogAPI (REST_API with mock)
    - database_specialist PROVIDES UserSchema (DatabaseSchema)
    """
    
    contract_id: str  # e.g., "BlogAPI_v1"
    persona_id: str  # e.g., "backend_developer"
    role: ContractRole  # provider or consumer
    contract_type: ContractType  # REST_API, GraphQL, etc.
    specification: Dict[str, Any]  # Full contract spec (OpenAPI, GraphQL schema, etc.)
    
    # Optional: Mock implementation for consumers
    mock_endpoint: Optional[str] = None  # e.g., "http://localhost:3001/api"
    mock_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    version: str = "v0.1"
    description: str = ""
    dependencies: List[str] = field(default_factory=list)  # Other contracts this depends on
    
    def to_prompt_context(self) -> str:
        """
        Convert contract to prompt context for persona
        
        Returns formatted text to include in persona prompt
        """
        if self.role == ContractRole.PROVIDER:
            return self._provider_context()
        else:
            return self._consumer_context()
            
    def _provider_context(self) -> str:
        """Context for contract provider (implementer)"""
        ctx = f"### {self.contract_id} ({self.version})\n\n"
        ctx += f"**YOU IMPLEMENT THIS CONTRACT**\n\n"
        ctx += f"Type: {self.contract_type.value}\n"
        ctx += f"Description: {self.description}\n\n"
        ctx += f"Specification:\n```json\n{json.dumps(self.specification, indent=2)}\n```\n\n"
        
        if self.dependencies:
            ctx += f"Dependencies: {', '.join(self.dependencies)}\n\n"
            
        ctx += "Ensure your implementation strictly adheres to this contract.\n"
        ctx += "All endpoints, schemas, and behaviors must match the specification.\n"
        
        return ctx
        
    def _consumer_context(self) -> str:
        """Context for contract consumer (user)"""
        ctx = f"### {self.contract_id} ({self.version})\n\n"
        ctx += f"**YOU CONSUME THIS CONTRACT**\n\n"
        ctx += f"Type: {self.contract_type.value}\n"
        ctx += f"Description: {self.description}\n\n"
        
        if self.mock_endpoint:
            ctx += f"Mock Endpoint: {self.mock_endpoint}\n"
            ctx += f"Use this mock URL for development. The actual implementation will be integrated later.\n\n"
            
        if self.mock_data:
            ctx += f"Mock Data:\n```json\n{json.dumps(self.mock_data, indent=2)}\n```\n\n"
            
        ctx += f"Specification:\n```json\n{json.dumps(self.specification, indent=2)}\n```\n\n"
        ctx += "Integrate with this contract. Use mocks for now; real implementation will replace them.\n"
        
        return ctx
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "contract_id": self.contract_id,
            "persona_id": self.persona_id,
            "role": self.role.value,
            "contract_type": self.contract_type.value,
            "specification": self.specification,
            "mock_endpoint": self.mock_endpoint,
            "mock_data": self.mock_data,
            "version": self.version,
            "description": self.description,
            "dependencies": self.dependencies
        }


@dataclass
class PersonaContractRegistry:
    """
    Registry of contracts attached to personas
    
    Maps persona_id → List[PersonaContract]
    """
    
    contracts: Dict[str, List[PersonaContract]] = field(default_factory=dict)
    
    def add_contract(
        self,
        persona_id: str,
        contract: PersonaContract
    ):
        """Add contract to persona"""
        if persona_id not in self.contracts:
            self.contracts[persona_id] = []
            
        self.contracts[persona_id].append(contract)
        
    def get_contracts(
        self,
        persona_id: str,
        role: Optional[ContractRole] = None
    ) -> List[PersonaContract]:
        """Get contracts for persona, optionally filtered by role"""
        persona_contracts = self.contracts.get(persona_id, [])
        
        if role:
            return [c for c in persona_contracts if c.role == role]
            
        return persona_contracts
        
    def get_provider_contracts(self, persona_id: str) -> List[PersonaContract]:
        """Get contracts this persona provides (implements)"""
        return self.get_contracts(persona_id, ContractRole.PROVIDER)
        
    def get_consumer_contracts(self, persona_id: str) -> List[PersonaContract]:
        """Get contracts this persona consumes (uses)"""
        return self.get_contracts(persona_id, ContractRole.CONSUMER)
        
    def has_contracts(self, persona_id: str) -> bool:
        """Check if persona has any contracts"""
        return persona_id in self.contracts and len(self.contracts[persona_id]) > 0
        
    def to_prompt_context(self, persona_id: str) -> str:
        """
        Build complete contract context for persona's prompt
        
        Returns formatted text with all provider and consumer contracts
        """
        contracts = self.contracts.get(persona_id, [])
        
        if not contracts:
            return ""
            
        ctx = "\n\n" + "="*80 + "\n"
        ctx += "API CONTRACTS (Interface Specifications)\n"
        ctx += "="*80 + "\n\n"
        
        provider_contracts = [c for c in contracts if c.role == ContractRole.PROVIDER]
        consumer_contracts = [c for c in contracts if c.role == ContractRole.CONSUMER]
        
        if provider_contracts:
            ctx += "## CONTRACTS YOU IMPLEMENT\n\n"
            for contract in provider_contracts:
                ctx += contract.to_prompt_context() + "\n"
                
        if consumer_contracts:
            ctx += "## CONTRACTS YOU CONSUME\n\n"
            for contract in consumer_contracts:
                ctx += contract.to_prompt_context() + "\n"
                
        ctx += "="*80 + "\n"
        
        return ctx
```

### Step 2.2: Enhance Prompt Builder with Contract Context

**File:** `team_execution.py` (modify `_build_persona_prompt`)

```python
def _build_persona_prompt(
    self,
    persona_config: Dict[str, Any],
    requirement: str,
    expected_deliverables: List[str],
    session_context: str,
    persona_id: Optional[str] = None
) -> str:
    """Build prompt with session context, validation instructions, AND contracts"""
    persona_name = persona_config["name"]
    expertise = persona_config.get("expertise", [])
    
    # Base prompt (existing code)
    prompt = f"""You are the {persona_name} for this project.

TEAM CONVERSATION AND PREVIOUS WORK:
{session_context}

Your task is to build on the existing work and create your deliverables.

Your expertise areas:
{chr(10).join(f"- {exp}" for exp in expertise[:5])}

Expected deliverables for your role:
{chr(10).join(f"- {d}" for d in expected_deliverables)}
"""
    
    # NEW: Add contract context if available
    if hasattr(self, 'persona_contract_registry') and self.persona_contract_registry:
        contract_context = self.persona_contract_registry.to_prompt_context(persona_id)
        if contract_context:
            prompt += contract_context
            
            # Add contract-specific instructions
            provider_contracts = self.persona_contract_registry.get_provider_contracts(persona_id)
            consumer_contracts = self.persona_contract_registry.get_consumer_contracts(persona_id)
            
            if provider_contracts:
                prompt += "\n**IMPORTANT - Contract Implementation:**\n"
                prompt += "You are responsible for implementing the contracts listed above.\n"
                prompt += "Your implementation MUST strictly adhere to the specifications.\n"
                prompt += "All endpoints, schemas, and behaviors must match exactly.\n\n"
                
            if consumer_contracts:
                prompt += "\n**IMPORTANT - Contract Consumption:**\n"
                prompt += "You will consume the contracts listed above.\n"
                prompt += "Use the mock endpoints/data provided for now.\n"
                prompt += "Your code should work with both mocks and real implementations.\n\n"
    
    # ... rest of existing prompt (file creation rules, persona-specific instructions, etc.) ...
    
    return prompt
```

### Step 2.3: Initialize Contract Registry in Engine

**File:** `team_execution.py` (modify `__init__`)

```python
from models.persona_contract import PersonaContractRegistry, PersonaContract, ContractRole, ContractType

class AutonomousSDLCEngineV3_1_Resumable:
    def __init__(self, ...):
        # ... existing init ...
        
        # NEW: Contract registry
        self.persona_contract_registry = PersonaContractRegistry()
        self.enable_contracts = kwargs.get("enable_contracts", True)
```

---

## Phase 3: Enhanced Contract Management

### Step 3.1: Contract Extraction from Architecture

**File:** `team_execution.py` (new method)

```python
async def _extract_and_register_contracts(
    self,
    session: SDLCSession
) -> List[Dict[str, Any]]:
    """
    Extract contract specifications from architecture documents
    
    Called after architecture phase (requirement_analyst + solution_architect)
    to identify and register all contracts.
    
    Returns:
        List of extracted contracts
    """
    if not self.enable_contracts:
        return []
        
    logger.info("\n" + "="*80)
    logger.info("📜 EXTRACTING API CONTRACTS FROM ARCHITECTURE")
    logger.info("="*80)
    
    contracts = []
    
    # Read architecture documents
    arch_file = self.output_dir / "ARCHITECTURE.md"
    api_spec_file = self.output_dir / "API_SPECIFICATION.md"
    openapi_file = self.output_dir / "openapi.yaml"
    
    # Extract from ARCHITECTURE.md
    if arch_file.exists():
        content = arch_file.read_text()
        arch_contracts = await self._parse_architecture_contracts(content)
        contracts.extend(arch_contracts)
        logger.info(f"  📄 Found {len(arch_contracts)} contracts in ARCHITECTURE.md")
        
    # Extract from API_SPECIFICATION.md
    if api_spec_file.exists():
        content = api_spec_file.read_text()
        api_contracts = await self._parse_api_specification(content)
        contracts.extend(api_contracts)
        logger.info(f"  📄 Found {len(api_contracts)} contracts in API_SPECIFICATION.md")
        
    # Extract from OpenAPI spec
    if openapi_file.exists():
        import yaml
        spec = yaml.safe_load(openapi_file.read_text())
        openapi_contract = {
            "name": spec.get("info", {}).get("title", "API"),
            "type": "REST_API",
            "version": spec.get("info", {}).get("version", "v1"),
            "specification": spec,
            "description": spec.get("info", {}).get("description", "")
        }
        contracts.append(openapi_contract)
        logger.info(f"  📄 Found OpenAPI specification: {openapi_contract['name']}")
        
    # Register contracts in contract manager
    if hasattr(self, 'contract_manager'):
        for contract_spec in contracts:
            await self.contract_manager.create_contract(
                team_id=session.session_id,
                contract_name=contract_spec["name"],
                version=contract_spec["version"],
                contract_type=contract_spec["type"],
                specification=contract_spec["specification"],
                owner_role=contract_spec.get("owner_role", "backend_developer"),
                owner_agent=f"{contract_spec.get('owner_role', 'backend')}_001"
            )
            
    logger.info(f"\n✅ Extracted and registered {len(contracts)} contracts")
    logger.info("="*80 + "\n")
    
    return contracts
    
async def _parse_architecture_contracts(
    self,
    content: str
) -> List[Dict[str, Any]]:
    """
    Parse ARCHITECTURE.md to extract contract specifications
    
    Looks for sections like:
    - ## API Endpoints
    - ## REST API Design
    - ## GraphQL Schema
    - ## Database Schema
    """
    contracts = []
    
    # Simple regex-based extraction (can be enhanced with AI)
    import re
    
    # Look for API sections
    api_sections = re.finditer(
        r'##\s+(API|REST|GraphQL|gRPC).*?\n(.*?)(?=##|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    
    for match in api_sections:
        section_title = match.group(1)
        section_content = match.group(2)
        
        # Extract endpoints
        endpoints = re.findall(
            r'(GET|POST|PUT|DELETE|PATCH)\s+(/[\w/{}:-]+)',
            section_content
        )
        
        if endpoints:
            contracts.append({
                "name": f"{section_title}API",
                "type": "REST_API",
                "version": "v0.1",
                "specification": {
                    "endpoints": [
                        {"method": method, "path": path}
                        for method, path in endpoints
                    ]
                },
                "description": f"API extracted from architecture: {section_title}",
                "owner_role": "backend_developer"
            })
            
    # Look for database schemas
    db_sections = re.finditer(
        r'##\s+(Database|Schema|Data Model).*?\n(.*?)(?=##|\Z)',
        content,
        re.DOTALL | re.IGNORECASE
    )
    
    for match in db_sections:
        section_content = match.group(2)
        
        # Extract table names
        tables = re.findall(r'Table:\s*(\w+)', section_content, re.IGNORECASE)
        
        if tables:
            contracts.append({
                "name": "DatabaseSchema",
                "type": "DATABASE_SCHEMA",
                "version": "v0.1",
                "specification": {
                    "tables": tables
                },
                "description": "Database schema extracted from architecture",
                "owner_role": "database_specialist"
            })
            
    return contracts
    
async def _parse_api_specification(
    self,
    content: str
) -> List[Dict[str, Any]]:
    """Parse API_SPECIFICATION.md for detailed contract specs"""
    # Similar to _parse_architecture_contracts but more detailed
    # Implementation left as exercise (can enhance with AI parsing)
    return []
```

### Step 3.2: Map Contracts to Personas

**File:** `team_execution.py` (new method)

```python
async def _map_contracts_to_personas(
    self,
    contracts: List[Dict[str, Any]],
    personas: List[str]
) -> PersonaContractRegistry:
    """
    Map extracted contracts to personas
    
    Determines who provides (implements) and who consumes each contract
    
    Rules:
    - backend_developer provides REST/GraphQL/gRPC APIs
    - frontend_developer consumes REST/GraphQL APIs
    - database_specialist provides database schemas
    - backend_developer consumes database schemas
    - devops_engineer consumes all contracts (for deployment)
    """
    registry = PersonaContractRegistry()
    
    logger.info("🔗 Mapping contracts to personas...")
    
    for contract_spec in contracts:
        contract_type_str = contract_spec["type"]
        contract_name = contract_spec["name"]
        
        # Convert string to enum
        try:
            contract_type = ContractType[contract_type_str]
        except KeyError:
            logger.warning(f"⚠️  Unknown contract type: {contract_type_str}")
            continue
            
        # REST/GraphQL/gRPC APIs
        if contract_type in [ContractType.REST_API, ContractType.GRAPHQL, ContractType.GRPC]:
            # Backend provides
            if "backend_developer" in personas:
                provider_contract = PersonaContract(
                    contract_id=f"{contract_name}_{contract_spec['version']}",
                    persona_id="backend_developer",
                    role=ContractRole.PROVIDER,
                    contract_type=contract_type,
                    specification=contract_spec["specification"],
                    version=contract_spec["version"],
                    description=contract_spec.get("description", "")
                )
                registry.add_contract("backend_developer", provider_contract)
                logger.info(f"  ✓ backend_developer PROVIDES {contract_name}")
                
            # Frontend consumes
            if "frontend_developer" in personas:
                consumer_contract = PersonaContract(
                    contract_id=f"{contract_name}_{contract_spec['version']}",
                    persona_id="frontend_developer",
                    role=ContractRole.CONSUMER,
                    contract_type=contract_type,
                    specification=contract_spec["specification"],
                    mock_endpoint="http://localhost:3001/api",  # Mock for development
                    version=contract_spec["version"],
                    description=contract_spec.get("description", "")
                )
                registry.add_contract("frontend_developer", consumer_contract)
                logger.info(f"  ✓ frontend_developer CONSUMES {contract_name} (mock)")
                
        # Database schemas
        elif contract_type == ContractType.DATABASE_SCHEMA:
            # Database specialist provides
            if "database_specialist" in personas:
                provider_contract = PersonaContract(
                    contract_id=f"{contract_name}_{contract_spec['version']}",
                    persona_id="database_specialist",
                    role=ContractRole.PROVIDER,
                    contract_type=contract_type,
                    specification=contract_spec["specification"],
                    version=contract_spec["version"],
                    description=contract_spec.get("description", "")
                )
                registry.add_contract("database_specialist", provider_contract)
                logger.info(f"  ✓ database_specialist PROVIDES {contract_name}")
                
            # Backend consumes
            if "backend_developer" in personas:
                consumer_contract = PersonaContract(
                    contract_id=f"{contract_name}_{contract_spec['version']}",
                    persona_id="backend_developer",
                    role=ContractRole.CONSUMER,
                    contract_type=contract_type,
                    specification=contract_spec["specification"],
                    version=contract_spec["version"],
                    description=contract_spec.get("description", "")
                )
                registry.add_contract("backend_developer", consumer_contract)
                logger.info(f"  ✓ backend_developer CONSUMES {contract_name}")
                
    return registry
```

### Step 3.3: Integrate into Execute Workflow

**File:** `team_execution.py` (modify `execute` method)

```python
async def execute(
    self,
    requirement: str,
    session_id: Optional[str] = None,
    resume_session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute SDLC workflow with contracts
    """
    # ... existing session loading and blueprint selection ...
    
    # NEW: Separate architecture phase from implementation phase
    architecture_personas = [
        p for p in execution_order
        if p in ["requirement_analyst", "solution_architect"]
    ]
    
    implementation_personas = [
        p for p in execution_order
        if p not in architecture_personas
    ]
    
    # PHASE 1: Execute architecture personas (define contracts)
    if architecture_personas and self.enable_contracts:
        logger.info("\n" + "="*80)
        logger.info("🏗️  PHASE 1: ARCHITECTURE & CONTRACT DEFINITION")
        logger.info("="*80 + "\n")
        
        for persona_id in architecture_personas:
            persona_context = await self._execute_persona(
                persona_id,
                requirement,
                session
            )
            
            session.add_persona_execution(
                persona_id=persona_id,
                files_created=persona_context.files_created,
                deliverables=persona_context.deliverables,
                duration=persona_context.duration(),
                success=persona_context.success
            )
            
            self.session_manager.save_session(session)
            
        # Extract and register contracts
        contracts = await self._extract_and_register_contracts(session)
        
        # Map contracts to personas
        if contracts:
            self.persona_contract_registry = await self._map_contracts_to_personas(
                contracts,
                implementation_personas
            )
    else:
        implementation_personas = execution_order  # No separation
        
    # PHASE 2: Execute implementation personas with contract context
    if implementation_personas:
        logger.info("\n" + "="*80)
        logger.info("🔨 PHASE 2: IMPLEMENTATION WITH CONTRACTS")
        logger.info("="*80 + "\n")
        
        for persona_id in implementation_personas:
            # Check if persona has contracts
            has_contracts = (
                hasattr(self, 'persona_contract_registry') and
                self.persona_contract_registry.has_contracts(persona_id)
            )
            
            if has_contracts:
                provider_contracts = self.persona_contract_registry.get_provider_contracts(persona_id)
                consumer_contracts = self.persona_contract_registry.get_consumer_contracts(persona_id)
                
                logger.info(f"\n📜 {persona_id} contracts:")
                if provider_contracts:
                    logger.info(f"   PROVIDES: {', '.join(c.contract_id for c in provider_contracts)}")
                if consumer_contracts:
                    logger.info(f"   CONSUMES: {', '.join(c.contract_id for c in consumer_contracts)}")
                logger.info("")
                
            # Execute persona (contracts will be included in prompt via _build_persona_prompt)
            persona_context = await self._execute_persona(
                persona_id,
                requirement,
                session
            )
            
            # ... rest of execution (quality gates, validation, etc.) ...
            
    # ... rest of execute method (deployment validation, result building) ...
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_blueprint_integration.py

import pytest
from team_execution import AutonomousSDLCEngineV3_1_Resumable

@pytest.mark.asyncio
async def test_blueprint_selection():
    """Test automatic blueprint selection"""
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=[],
        auto_select_blueprint=True
    )
    
    # Simple requirement should select sequential
    blueprint_id = await engine.select_team_blueprint(
        "Create a simple calculator app"
    )
    assert blueprint_id in ["sequential-basic", "sequential-elastic"]
    
    # Complex requirement should select parallel
    blueprint_id = await engine.select_team_blueprint(
        "Build a complex e-commerce platform with frontend, backend, and database"
    )
    assert blueprint_id in ["parallel-basic", "parallel-elastic", "hybrid-full-sdlc"]

@pytest.mark.asyncio
async def test_contract_extraction():
    """Test contract extraction from architecture"""
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=["backend_developer"],
        enable_contracts=True
    )
    
    # Create mock ARCHITECTURE.md with API endpoints
    arch_content = """
    ## REST API Design
    
    GET /api/users
    POST /api/users
    GET /api/products
    """
    
    contracts = await engine._parse_architecture_contracts(arch_content)
    
    assert len(contracts) > 0
    assert contracts[0]["type"] == "REST_API"
    assert len(contracts[0]["specification"]["endpoints"]) == 3

@pytest.mark.asyncio
async def test_contract_persona_mapping():
    """Test contract-to-persona mapping"""
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=["backend_developer", "frontend_developer"],
        enable_contracts=True
    )
    
    contracts = [
        {
            "name": "UserAPI",
            "type": "REST_API",
            "version": "v1",
            "specification": {"endpoints": [{"method": "GET", "path": "/api/users"}]}
        }
    ]
    
    registry = await engine._map_contracts_to_personas(
        contracts,
        ["backend_developer", "frontend_developer"]
    )
    
    # Backend should provide
    backend_contracts = registry.get_provider_contracts("backend_developer")
    assert len(backend_contracts) == 1
    assert backend_contracts[0].contract_id == "UserAPI_v1"
    
    # Frontend should consume
    frontend_contracts = registry.get_consumer_contracts("frontend_developer")
    assert len(frontend_contracts) == 1
    assert frontend_contracts[0].mock_endpoint is not None
```

### Integration Tests

```python
# tests/test_full_workflow_with_contracts.py

@pytest.mark.asyncio
async def test_full_workflow_with_contracts():
    """Test complete workflow with blueprint and contracts"""
    engine = AutonomousSDLCEngineV3_1_Resumable(
        selected_personas=[],
        auto_select_blueprint=True,
        enable_contracts=True
    )
    
    result = await engine.execute(
        requirement="Build a blog platform with authentication and comments"
    )
    
    # Verify blueprint was used
    assert "blueprint_used" in result
    
    # Verify contracts were created
    assert "contracts" in result
    assert len(result["contracts"]) > 0
    
    # Verify personas received contracts
    # (check validation reports for contract context)
```

---

## Migration Path

### Week 1: Opt-In Blueprint Support
- Add `--blueprint` and `--auto-blueprint` flags
- Default to manual persona selection
- Users can opt-in to blueprints

### Week 2: Blueprint Default with Fallback
- Make blueprints default
- Keep `--no-blueprints` flag for fallback
- Monitor usage and issues

### Week 3: Contract System Rollout
- Enable contract extraction and mapping
- Add `--enable-contracts` flag (default: true)
- Test with existing projects

### Week 4: Full Integration
- Blueprints + contracts as default workflow
- Remove legacy flags
- Update documentation

---

## Next Steps

1. ✅ Review this implementation guide
2. ⏸️ Run unit tests to verify blueprint system is accessible
3. ⏸️ Implement Phase 1 (Blueprint Integration)
4. ⏸️ Test with sample projects
5. ⏸️ Implement Phase 2 (Contract-Persona Separation)
6. ⏸️ Implement Phase 3 (Enhanced Contract Management)
7. ⏸️ Full integration testing
8. ⏸️ Production rollout

---

**Questions or Issues?**

Refer to:
- Blueprint system: `synth/maestro_ml/modules/teams/`
- Proposal document: `TEAM_EXECUTION_ENHANCEMENT_PROPOSAL.md`
- Current implementation: `team_execution.py`, `contract_manager.py`, `personas.py`
