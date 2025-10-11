#!/usr/bin/env python3
"""
Persona Executor V2 - Contract-Aware Execution Engine

This module executes individual personas with contract awareness:
- Loads persona definitions (WHO they are)
- Receives contract specifications (WHAT to deliver)
- Generates mocks from contracts for parallel work
- Validates deliverables against contracts
- Produces quality scores

Key Innovation: Clean separation of Identity (persona) and Obligation (contract)

Architecture:
    PersonaExecutor
        ├── load_persona() - Get persona definition
        ├── prepare_contract() - Parse contract and setup
        ├── generate_mock() - Create mock from contract (for parallel work)
        ├── execute() - Run persona with contract
        └── validate_deliverables() - Check contract fulfillment

Usage:
    executor = PersonaExecutor(persona_id="backend_developer")
    result = await executor.execute(
        requirement="Build REST API",
        contract=api_contract,
        context={"can_use_mock": True}
    )
"""

import asyncio
import sys
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid
import shutil

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

# Persona definitions
from personas import SDLCPersonas

# Claude Code API Layer - Standalone package
try:
    import sys
    sys.path.insert(0, '/home/ec2-user/projects/maestro-platform')
    from claude_code_api_layer import ClaudeCLIClient
    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    logging.warning("claude_code_api_layer not available")

# RAG Template Client for template recommendations
try:
    from rag_template_client import TemplateRAGClient, TemplateContent
    RAG_CLIENT_AVAILABLE = True
except ImportError:
    RAG_CLIENT_AVAILABLE = False
    TemplateRAGClient = None
    TemplateContent = None
    logging.warning("RAG template client not available")

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class MockGeneration:
    """Mock generated from contract"""
    mock_type: str  # api_server, data_stub, interface_mock
    artifacts: List[str]  # Files created
    endpoint: Optional[str] = None  # For API mocks
    usage_instructions: str = ""
    quality_score: float = 0.0


@dataclass
class PersonaExecutionResult:
    """Result of executing a persona"""
    persona_id: str
    contract_id: Optional[str]
    success: bool
    
    # Deliverables
    files_created: List[str]
    deliverables: Dict[str, List[str]]  # By category
    
    # Contract validation
    contract_fulfilled: bool = True
    fulfillment_score: float = 1.0
    missing_deliverables: List[str] = field(default_factory=list)
    
    # Quality
    quality_score: float = 0.0
    completeness_score: float = 0.0
    quality_issues: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timing
    duration_seconds: float = 0.0
    parallel_execution: bool = False
    used_mock: bool = False
    
    # AI insights
    ai_feedback: str = ""
    recommendations: List[str] = field(default_factory=list)
    risks_identified: List[str] = field(default_factory=list)
    
    # Metadata
    executed_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# PERSONA EXECUTOR V2
# =============================================================================

class PersonaExecutorV2:
    """
    Execute a persona with contract awareness.
    
    This replaces the simple persona execution with contract-based,
    validated, quality-assured execution.
    """
    
    def __init__(
        self,
        persona_id: str,
        output_dir: Path,
        model: str = "claude-3-5-sonnet-20241022",
        rag_client: Optional['TemplateRAGClient'] = None
    ):
        self.persona_id = persona_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = model
        self.rag_client = rag_client

        # Load persona definition
        try:
            all_personas = SDLCPersonas.get_all_personas()
            if persona_id not in all_personas:
                raise ValueError(f"Persona '{persona_id}' not found")
            self.persona_def = all_personas[persona_id]
        except Exception as e:
            logger.error(f"Failed to load persona {persona_id}: {e}")
            # Create minimal fallback
            self.persona_def = {
                "id": persona_id,
                "name": persona_id.replace("_", " ").title(),
                "role": "Software Developer",
                "expertise": ["software_development"],
                "responsibilities": ["Deliver software"],
                "deliverables": ["code"]
            }

        logger.info(f"✅ PersonaExecutor initialized: {self.persona_def['name']}")
    
    async def generate_mock_from_contract(
        self,
        contract: Dict[str, Any]
    ) -> MockGeneration:
        """
        Generate mock implementation from contract specification.
        
        This enables parallel work - consumers can work against mock
        while provider builds real implementation.
        
        Contract: Must generate usable mock that matches contract interface
        """
        logger.info(f"🎭 Generating mock for contract: {contract.get('name', 'Unknown')}")
        
        contract_type = contract.get("contract_type", "Deliverable")
        artifacts = []
        endpoint = None
        
        if contract_type == "REST_API":
            # Generate OpenAPI spec and mock server
            mock_result = await self._generate_api_mock(contract)
            artifacts = mock_result["artifacts"]
            endpoint = mock_result.get("endpoint")
            instructions = mock_result.get("instructions", "")
        
        elif contract_type == "GraphQL":
            # Generate GraphQL schema and mock
            mock_result = await self._generate_graphql_mock(contract)
            artifacts = mock_result["artifacts"]
            endpoint = mock_result.get("endpoint")
            instructions = mock_result.get("instructions", "")
        
        else:
            # Generate data stubs or interface mocks
            mock_result = await self._generate_interface_mock(contract)
            artifacts = mock_result["artifacts"]
            instructions = mock_result.get("instructions", "")
        
        mock = MockGeneration(
            mock_type=contract_type,
            artifacts=artifacts,
            endpoint=endpoint,
            usage_instructions=instructions,
            quality_score=0.9  # Mocks are reliable
        )
        
        logger.info(f"  ✅ Mock generated: {len(artifacts)} artifact(s)")
        if endpoint:
            logger.info(f"     Endpoint: {endpoint}")
        
        return mock
    
    async def _generate_api_mock(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Generate REST API mock with OpenAPI spec"""
        contract_name = contract.get("name", "api").lower().replace(" ", "_")
        
        # Extract interface spec if available
        interface_spec = contract.get("interface_spec", {})
        deliverables = contract.get("deliverables", [])
        
        # Generate OpenAPI specification
        openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": contract.get("name", "API"),
                "version": contract.get("version", "1.0.0"),
                "description": f"Generated from contract: {contract.get('id', 'N/A')}"
            },
            "paths": {},
            "components": {
                "schemas": {}
            }
        }
        
        # Add endpoints from deliverables
        for deliverable in deliverables:
            if deliverable.get("name") == "api_specification":
                # Use provided spec details
                pass
            
            # Default endpoints for common patterns
            openapi_spec["paths"]["/api/items"] = {
                "get": {
                    "summary": "List items",
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Item"}
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create item",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ItemCreate"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Item"}
                                }
                            }
                        }
                    }
                }
            }
        
        # Add schemas
        openapi_spec["components"]["schemas"]["Item"] = {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"}
            }
        }
        openapi_spec["components"]["schemas"]["ItemCreate"] = {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"}
            }
        }
        
        # Write spec file
        contracts_dir = self.output_dir / "contracts"
        contracts_dir.mkdir(parents=True, exist_ok=True)
        
        spec_file = contracts_dir / f"{contract_name}_spec.yaml"
        with open(spec_file, "w") as f:
            yaml.dump(openapi_spec, f, default_flow_style=False, sort_keys=False)
        
        # Generate mock server implementation (simple Node.js/Express)
        mock_server_code = self._generate_mock_server_code(openapi_spec, contract_name)
        mock_file = contracts_dir / f"{contract_name}_mock_server.js"
        with open(mock_file, "w") as f:
            f.write(mock_server_code)
        
        # Generate README
        readme_content = f"""# Mock API Server - {contract.get('name', 'API')}

## Overview
This is a mock implementation generated from contract: `{contract.get('id', 'N/A')}`

## Usage

### 1. Install dependencies:
```bash
npm install express cors body-parser
```

### 2. Start mock server:
```bash
node {mock_file.name}
```

### 3. Access API:
- Base URL: http://localhost:3001
- OpenAPI Spec: {spec_file.name}

## Endpoints
- GET /api/items - List items
- POST /api/items - Create item
- GET /api/health - Health check

## Note
This is a MOCK server for parallel development.
Replace with real implementation from backend team.
"""
        
        readme_file = contracts_dir / f"{contract_name}_README.md"
        with open(readme_file, "w") as f:
            f.write(readme_content)
        
        return {
            "artifacts": [str(spec_file), str(mock_file), str(readme_file)],
            "endpoint": "http://localhost:3001",
            "instructions": f"Run: node {mock_file}"
        }
    
    def _generate_mock_server_code(self, openapi_spec: Dict, name: str) -> str:
        """Generate simple Express mock server"""
        return f"""// Mock API Server - {name}
// Auto-generated from contract specification

const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3001;

// Middleware
app.use(cors());
app.use(bodyParser.json());

// In-memory storage
let items = [
    {{ id: '1', name: 'Sample Item 1', created_at: new Date().toISOString() }},
    {{ id: '2', name: 'Sample Item 2', created_at: new Date().toISOString() }}
];

// Routes
app.get('/api/health', (req, res) => {{
    res.json({{ status: 'ok', message: 'Mock server running' }});
}});

app.get('/api/items', (req, res) => {{
    console.log('GET /api/items');
    res.json(items);
}});

app.post('/api/items', (req, res) => {{
    console.log('POST /api/items', req.body);
    const newItem = {{
        id: String(items.length + 1),
        name: req.body.name,
        created_at: new Date().toISOString()
    }};
    items.push(newItem);
    res.status(201).json(newItem);
}});

app.get('/api/items/:id', (req, res) => {{
    console.log('GET /api/items/:id', req.params.id);
    const item = items.find(i => i.id === req.params.id);
    if (item) {{
        res.json(item);
    }} else {{
        res.status(404).json({{ error: 'Not found' }});
    }}
}});

// Start server
app.listen(PORT, () => {{
    console.log(`Mock API server running on http://localhost:${{PORT}}`);
    console.log('Endpoints:');
    console.log('  GET  /api/health');
    console.log('  GET  /api/items');
    console.log('  POST /api/items');
    console.log('  GET  /api/items/:id');
}});
"""
    
    async def _generate_graphql_mock(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GraphQL mock"""
        # Simplified GraphQL mock generation
        contract_name = contract.get("name", "graphql").lower().replace(" ", "_")
        contracts_dir = self.output_dir / "contracts"
        contracts_dir.mkdir(parents=True, exist_ok=True)
        
        schema_file = contracts_dir / f"{contract_name}_schema.graphql"
        with open(schema_file, "w") as f:
            f.write("""
type Query {
  items: [Item!]!
  item(id: ID!): Item
}

type Mutation {
  createItem(name: String!): Item!
}

type Item {
  id: ID!
  name: String!
  createdAt: String!
}
""")
        
        return {
            "artifacts": [str(schema_file)],
            "endpoint": "http://localhost:4000/graphql",
            "instructions": "Use Apollo Server to serve this schema"
        }
    
    async def _generate_interface_mock(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """Generate interface or data mocks"""
        contract_name = contract.get("name", "interface").lower().replace(" ", "_")
        contracts_dir = self.output_dir / "contracts"
        contracts_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate contract summary file
        contract_file = contracts_dir / f"{contract_name}_contract.json"
        with open(contract_file, "w") as f:
            json.dump(contract, f, indent=2, default=str)
        
        return {
            "artifacts": [str(contract_file)],
            "instructions": "See contract specification for deliverables"
        }
    
    async def execute(
        self,
        requirement: str,
        contract: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        use_mock: bool = False
    ) -> PersonaExecutionResult:
        """
        Execute persona with contract.
        
        Args:
            requirement: The overall requirement
            contract: Contract specification (WHAT to deliver)
            context: Additional context (dependencies, etc.)
            use_mock: Whether to use mock for dependencies
        
        Returns:
            PersonaExecutionResult with deliverables and validation
        """
        start_time = datetime.now()
        context = context or {}
        
        logger.info("="*70)
        logger.info(f"🎭 Executing Persona: {self.persona_def['name']}")
        logger.info("="*70)
        
        if contract:
            logger.info(f"📝 Contract: {contract.get('name', 'N/A')}")
            logger.info(f"   Type: {contract.get('contract_type', 'N/A')}")
            logger.info(f"   Provider: {contract.get('provider_persona_id', 'N/A')}")
        
        if use_mock:
            logger.info("🎭 Using MOCK for dependencies (parallel work)")

        # Persona-Level RAG: Search for relevant templates
        recommended_templates = []
        if self.rag_client:
            logger.info("🔍 Searching for relevant templates...")
            try:
                recommended_templates = await self.rag_client.search_templates_for_persona(
                    persona_id=self.persona_id,
                    requirement=requirement,
                    context=context or {}
                )

                if recommended_templates:
                    logger.info(f"  ✅ Found {len(recommended_templates)} relevant template(s)")
                    for template in recommended_templates[:3]:  # Show top 3
                        logger.info(f"     • {template.metadata.name} (relevance: {template.relevance_score:.0%})")
                else:
                    logger.info("  ℹ️  No matching templates found")
            except Exception as e:
                logger.warning(f"  ⚠️  Template search failed: {e}")
                recommended_templates = []

        # Build prompt for persona
        prompt = self._build_persona_prompt(
            requirement,
            contract,
            context,
            use_mock,
            recommended_templates
        )
        
        # Execute with AI
        files_created = []
        deliverables = {}
        ai_response = ""
        
        try:
            if CLAUDE_SDK_AVAILABLE:
                logger.info("🤖 Executing with AI...")

                # Use ClaudeCLIClient
                client = ClaudeCLIClient(cwd=self.output_dir)

                # Build full prompt with system context
                full_prompt = f"{self._build_system_prompt()}\n\n{prompt}"

                # Execute query
                result = client.query(
                    prompt=full_prompt,
                    skip_permissions=True,  # Auto-accept for automation
                    allowed_tools=["Write", "Edit", "Read", "Bash"],
                    timeout=600  # 10 minutes
                )

                if result.get('success'):
                    ai_response = result.get('output', '')

                    # Find created files
                    if self.output_dir.exists():
                        for file_path in self.output_dir.rglob("*"):
                            if file_path.is_file():
                                files_created.append(str(file_path))

                    # Categorize deliverables
                    deliverables = self._categorize_deliverables(files_created)

                    logger.info(f"✅ Execution complete: {len(files_created)} file(s) created")
                else:
                    logger.error(f"AI execution failed: {result.get('error')}")
                    raise Exception(result.get('error', 'Unknown error'))

            else:
                logger.warning("⚠️  Claude SDK not available, using fallback")
                # Create placeholder files
                files_created, deliverables = await self._fallback_execution(
                    requirement,
                    contract
                )
        
        except Exception as e:
            logger.error(f"❌ Execution failed: {e}")
            return PersonaExecutionResult(
                persona_id=self.persona_id,
                contract_id=contract.get("id") if contract else None,
                success=False,
                files_created=[],
                deliverables={},
                contract_fulfilled=False,
                fulfillment_score=0.0,
                duration_seconds=(datetime.now() - start_time).total_seconds()
            )
        
        # Validate against contract
        validation_result = await self._validate_contract_fulfillment(
            contract,
            files_created,
            deliverables
        )
        
        # Calculate quality scores
        quality_score = await self._calculate_quality_score(
            files_created,
            deliverables,
            validation_result
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        result = PersonaExecutionResult(
            persona_id=self.persona_id,
            contract_id=contract.get("id") if contract else None,
            success=True,
            files_created=files_created,
            deliverables=deliverables,
            contract_fulfilled=validation_result["fulfilled"],
            fulfillment_score=validation_result["score"],
            missing_deliverables=validation_result["missing"],
            quality_score=quality_score,
            completeness_score=validation_result["score"],
            quality_issues=validation_result.get("issues", []),
            duration_seconds=duration,
            parallel_execution=use_mock,
            used_mock=use_mock,
            ai_feedback=ai_response[:500] if ai_response else "",
            recommendations=validation_result.get("recommendations", []),
            executed_at=datetime.now()
        )
        
        logger.info("="*70)
        logger.info("✅ Persona Execution Complete")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"   Files: {len(files_created)}")
        logger.info(f"   Contract fulfilled: {result.contract_fulfilled}")
        logger.info(f"   Quality: {result.quality_score:.0%}")
        logger.info("="*70)
        
        return result
    
    def _build_system_prompt(self) -> str:
        """Build system prompt from persona definition"""
        persona = self.persona_def
        
        return f"""You are {persona['name']}, a {persona.get('role', 'Software Professional')}.

Your expertise: {', '.join(persona.get('expertise', []))}

Your responsibilities:
{chr(10).join(f"- {r}" for r in persona.get('responsibilities', []))}

Your typical deliverables:
{chr(10).join(f"- {d}" for d in persona.get('deliverables', []))}

Always deliver high-quality work that meets professional standards.
Follow best practices for your role.
Document your work clearly.
"""
    
    def _build_persona_prompt(
        self,
        requirement: str,
        contract: Optional[Dict[str, Any]],
        context: Dict[str, Any],
        use_mock: bool,
        recommended_templates: Optional[List['TemplateContent']] = None
    ) -> str:
        """Build execution prompt for persona"""
        prompt_parts = [
            f"# Task: {requirement}\n",
            f"## Your Role: {self.persona_def['name']}\n"
        ]

        # Add recommended templates if available
        if recommended_templates and len(recommended_templates) > 0:
            prompt_parts.append("\n## 📚 Recommended Templates\n\n")
            prompt_parts.append("You have access to the following production-tested templates that may help with this task:\n\n")

            for i, template in enumerate(recommended_templates[:5], 1):  # Show top 5
                relevance = template.relevance_score
                metadata = template.metadata

                prompt_parts.append(f"### Template {i}: {metadata.name}\n")
                prompt_parts.append(f"- **Relevance**: {relevance:.0%}\n")
                prompt_parts.append(f"- **Category**: {metadata.category}\n")
                prompt_parts.append(f"- **Quality**: {metadata.quality_score:.0%}\n")

                if metadata.description:
                    prompt_parts.append(f"- **Description**: {metadata.description}\n")

                if metadata.tech_stack:
                    prompt_parts.append(f"- **Tech Stack**: {', '.join(metadata.tech_stack)}\n")

                # Include full template code for high-relevance templates (using config thresholds)
                try:
                    from config import RAG_CONFIG
                    high_threshold = RAG_CONFIG['high_relevance_threshold']
                    medium_threshold = RAG_CONFIG['medium_relevance_threshold']
                    include_code = RAG_CONFIG.get('include_template_code', True)
                except:
                    high_threshold = 0.80
                    medium_threshold = 0.60
                    include_code = True

                if relevance >= high_threshold and template.content and include_code:
                    prompt_parts.append(f"\n**Template Code** (relevance {relevance:.0%} - recommended for direct use):\n")
                    prompt_parts.append(f"```\n{template.content}\n```\n")
                elif relevance >= medium_threshold:
                    prompt_parts.append(f"\n**Note**: This template (relevance {relevance:.0%}) can be used as inspiration or adapted to your needs.\n")
                else:
                    prompt_parts.append(f"\n**Note**: Lower relevance ({relevance:.0%}), consider as reference only.\n")

                if template.selection_reasoning:
                    prompt_parts.append(f"\n**Why recommended**: {template.selection_reasoning}\n")

                prompt_parts.append("\n")

            # Add guidance for using templates (using config thresholds)
            try:
                from config import RAG_CONFIG
                high_threshold = int(RAG_CONFIG['high_relevance_threshold'] * 100)
                medium_threshold = int(RAG_CONFIG['medium_relevance_threshold'] * 100)
            except:
                high_threshold = 80
                medium_threshold = 60

            prompt_parts.append("\n**Template Usage Guidelines**:\n")
            prompt_parts.append(f"- **High relevance (>{high_threshold}%)**: Use template directly with minor customization\n")
            prompt_parts.append(f"- **Medium relevance ({medium_threshold}-{high_threshold}%)**: Use as inspiration, adapt patterns\n")
            prompt_parts.append(f"- **Low relevance (<{medium_threshold}%)**: Consider for reference only, build custom solution\n")
            prompt_parts.append("- You may choose to build from scratch if templates don't fully fit\n")
            prompt_parts.append("- Document your decision (used template, adapted, or custom) in your deliverables\n\n")

        # ✅ NEW: Add comprehensive previous phase context
        if "previous_phase_outputs" in context and context["previous_phase_outputs"]:
            prompt_parts.append("\n## 📦 Work from Previous Phases\n\n")
            prompt_parts.append("You are building upon completed work from previous team members. ")
            prompt_parts.append("All deliverables and specifications below are ALREADY COMPLETE and available for your use.\n\n")

            for phase_name, outputs in context["previous_phase_outputs"].items():
                prompt_parts.append(f"### {phase_name.upper()} Phase:\n\n")

                # Show deliverables by category
                if "deliverables" in outputs:
                    prompt_parts.append("**Deliverables Created:**\n")
                    for deliverable_type, files in outputs.get("deliverables", {}).items():
                        prompt_parts.append(f"- **{deliverable_type.title()}:**\n")
                        for file_path in files:
                            prompt_parts.append(f"  - `{file_path}`\n")
                    prompt_parts.append("\n")

                # Show full output data
                if "phase" in outputs or "execution_summary" in outputs:
                    prompt_parts.append("**Detailed Output:**\n")
                    prompt_parts.append("```json\n")
                    prompt_parts.append(json.dumps(outputs, indent=2))  # ✅ FULL output
                    prompt_parts.append("\n```\n\n")

        # ✅ NEW: Add available artifacts from all phases
        if "available_artifacts" in context and context["available_artifacts"]:
            prompt_parts.append("\n## 📄 Available Artifacts\n\n")
            prompt_parts.append("The following files have been created by previous team members and are available in the project:\n\n")

            # Group by phase
            artifacts_by_phase = {}
            for artifact in context["available_artifacts"]:
                phase = artifact.get("created_by_phase", "unknown")
                if phase not in artifacts_by_phase:
                    artifacts_by_phase[phase] = []
                artifacts_by_phase[phase].append(artifact)

            for phase, artifacts in artifacts_by_phase.items():
                prompt_parts.append(f"**From {phase.title()} Phase:**\n")
                for artifact in artifacts:
                    prompt_parts.append(f"- `{artifact['name']}`")
                    if artifact.get('created_at'):
                        prompt_parts.append(f" (created {artifact['created_at']})")
                    prompt_parts.append("\n")
                prompt_parts.append("\n")

        # ✅ NEW: Add specific instructions based on role and context
        if self.persona_id == "frontend_developer":
            # Frontend gets special guidance to use backend specs
            if "previous_phase_outputs" in context:
                prompt_parts.append("\n## 🎯 Frontend Development Guidelines\n\n")
                prompt_parts.append("1. Review the API specification from the design/backend phase\n")
                prompt_parts.append("2. Use the exact endpoints, request/response formats specified\n")
                prompt_parts.append("3. Implement error handling for all API responses\n")
                prompt_parts.append("4. Follow the state management design from architecture phase\n")
                prompt_parts.append("5. If mock API is available, develop against mock then integrate with real API\n\n")

        elif self.persona_id == "qa_engineer":
            prompt_parts.append("\n## 🎯 QA Testing Guidelines\n\n")
            prompt_parts.append("1. Review ALL deliverables from implementation phase\n")
            prompt_parts.append("2. Create tests for EVERY endpoint in the API specification\n")
            prompt_parts.append("3. Test frontend against the ACTUAL implemented features\n")
            prompt_parts.append("4. Verify against acceptance criteria from requirements phase\n\n")

        if contract:
            prompt_parts.append("## Contract Obligations:\n")
            prompt_parts.append(f"Contract: {contract.get('name', 'N/A')}\n")
            prompt_parts.append(f"Type: {contract.get('contract_type', 'N/A')}\n\n")

            prompt_parts.append("### Deliverables Required:\n")
            for deliverable in contract.get("deliverables", []):
                prompt_parts.append(f"**{deliverable.get('name', 'Deliverable')}**\n")
                prompt_parts.append(f"- Description: {deliverable.get('description', 'N/A')}\n")
                prompt_parts.append(f"- Artifacts: {', '.join(deliverable.get('artifacts', []))}\n")
                if deliverable.get('acceptance_criteria'):
                    prompt_parts.append("- Acceptance Criteria:\n")
                    for criterion in deliverable['acceptance_criteria']:
                        prompt_parts.append(f"  - {criterion}\n")
                prompt_parts.append("\n")

        if use_mock:
            prompt_parts.append("## ⚠️  Working with Mock Dependencies\n")
            prompt_parts.append("You are working in PARALLEL with other team members.\n")
            prompt_parts.append("Dependencies are MOCKED - use the mock endpoints/interfaces provided.\n")
            prompt_parts.append("Your work will be integrated with real implementations later.\n\n")

        if context:
            prompt_parts.append("## Context:\n")
            prompt_parts.append(json.dumps(context, indent=2))
            prompt_parts.append("\n")

        prompt_parts.append(f"\n## Output Directory:\n{self.output_dir}\n")
        prompt_parts.append("\nDeliver production-quality work that fulfills the contract.\n")

        return "".join(prompt_parts)
    
    async def _fallback_execution(
        self,
        requirement: str,
        contract: Optional[Dict[str, Any]]
    ) -> tuple[List[str], Dict[str, List[str]]]:
        """Fallback execution when Claude SDK unavailable"""
        logger.info("📝 Creating placeholder deliverables...")
        
        files_created = []
        deliverables = {}
        
        # Create persona-specific directory
        persona_dir = self.output_dir / self.persona_id
        persona_dir.mkdir(parents=True, exist_ok=True)
        
        # Create placeholder based on contract or persona type
        if contract:
            for deliverable in contract.get("deliverables", []):
                artifacts = deliverable.get("artifacts", [])
                for artifact_pattern in artifacts:
                    # Create file from pattern
                    file_path = persona_dir / Path(artifact_pattern).name
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(file_path, "w") as f:
                        f.write(f"# {deliverable.get('name', 'Deliverable')}\n\n")
                        f.write(f"Generated by: {self.persona_def['name']}\n")
                        f.write(f"Requirement: {requirement[:100]}\n\n")
                        f.write(f"Description: {deliverable.get('description', 'N/A')}\n\n")
                        f.write("# TODO: Implement this deliverable\n")
                    
                    files_created.append(str(file_path))
        else:
            # Generic deliverable
            readme_file = persona_dir / "README.md"
            with open(readme_file, "w") as f:
                f.write(f"# {self.persona_def['name']} Deliverables\n\n")
                f.write(f"Requirement: {requirement}\n\n")
                f.write("## Work completed\n\n")
                f.write("(Placeholder - AI execution not available)\n")
            
            files_created.append(str(readme_file))
        
        deliverables = self._categorize_deliverables(files_created)
        
        return files_created, deliverables
    
    def _categorize_deliverables(self, files: List[str]) -> Dict[str, List[str]]:
        """Categorize files into deliverable types"""
        categories = {
            "documentation": [],
            "code": [],
            "tests": [],
            "configuration": [],
            "contracts": [],
            "other": []
        }
        
        for file_path in files:
            path = Path(file_path)
            
            if path.suffix in [".md", ".txt", ".doc", ".pdf"]:
                categories["documentation"].append(file_path)
            elif path.suffix in [".py", ".js", ".ts", ".java", ".go", ".rs"]:
                if "test" in path.name.lower():
                    categories["tests"].append(file_path)
                else:
                    categories["code"].append(file_path)
            elif path.suffix in [".yaml", ".yml", ".json", ".toml", ".ini"]:
                if "contract" in path.name.lower():
                    categories["contracts"].append(file_path)
                else:
                    categories["configuration"].append(file_path)
            else:
                categories["other"].append(file_path)
        
        # Remove empty categories
        return {k: v for k, v in categories.items() if v}
    
    async def _validate_contract_fulfillment(
        self,
        contract: Optional[Dict[str, Any]],
        files_created: List[str],
        deliverables: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Validate that deliverables fulfill contract"""
        if not contract:
            return {
                "fulfilled": True,
                "score": 1.0,
                "missing": [],
                "issues": [],
                "recommendations": []
            }
        
        missing = []
        issues = []
        recommendations = []
        
        required_deliverables = contract.get("deliverables", [])
        total_required = len(required_deliverables)
        fulfilled_count = 0
        
        for required in required_deliverables:
            name = required.get("name", "")
            artifacts = required.get("artifacts", [])
            
            # Check if artifacts exist
            artifacts_found = []
            for artifact_pattern in artifacts:
                # Simple pattern matching
                pattern_name = Path(artifact_pattern).name
                for created_file in files_created:
                    if pattern_name in created_file or artifact_pattern in created_file:
                        artifacts_found.append(created_file)
                        break
            
            if artifacts_found:
                fulfilled_count += 1
            else:
                missing.append(name)
                issues.append({
                    "type": "missing_deliverable",
                    "severity": "high",
                    "deliverable": name,
                    "expected_artifacts": artifacts
                })
        
        # Calculate fulfillment score
        score = fulfilled_count / total_required if total_required > 0 else 1.0
        
        # Generate recommendations
        if missing:
            recommendations.append(f"Complete missing deliverables: {', '.join(missing)}")
        
        if score >= 0.8:
            recommendations.append("Consider adding additional documentation")
        
        return {
            "fulfilled": score >= 0.8,  # 80% threshold
            "score": score,
            "missing": missing,
            "issues": issues,
            "recommendations": recommendations
        }
    
    async def _calculate_quality_score(
        self,
        files_created: List[str],
        deliverables: Dict[str, List[str]],
        validation: Dict[str, Any]
    ) -> float:
        """Calculate overall quality score"""
        scores = []
        
        # Contract fulfillment score (40%)
        scores.append(validation["score"] * 0.4)
        
        # Completeness score (30%)
        expected_categories = {"documentation", "code"}
        found_categories = set(deliverables.keys())
        completeness = len(expected_categories & found_categories) / len(expected_categories)
        scores.append(completeness * 0.3)
        
        # File count score (20%)
        file_score = min(len(files_created) / 5, 1.0)  # Expect at least 5 files
        scores.append(file_score * 0.2)
        
        # Issues penalty (10%)
        issues = validation.get("issues", [])
        issue_score = max(0, 1.0 - len(issues) * 0.2)
        scores.append(issue_score * 0.1)
        
        return sum(scores)


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

async def main():
    """CLI entry point for testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Persona Executor V2 - Contract-Aware Execution")
    parser.add_argument("--persona-id", required=True, help="Persona ID to execute")
    parser.add_argument("--requirement", required=True, help="Requirement to fulfill")
    parser.add_argument("--contract", help="Contract JSON file")
    parser.add_argument("--output", default="./generated_project", help="Output directory")
    parser.add_argument("--use-mock", action="store_true", help="Use mock for dependencies")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    # Load contract if provided
    contract = None
    if args.contract:
        with open(args.contract) as f:
            contract = json.load(f)
    
    # Create executor
    executor = PersonaExecutorV2(
        persona_id=args.persona_id,
        output_dir=Path(args.output)
    )
    
    # Execute
    result = await executor.execute(
        requirement=args.requirement,
        contract=contract,
        use_mock=args.use_mock
    )
    
    # Print result
    print("\n" + "="*70)
    print("📊 EXECUTION RESULT")
    print("="*70)
    print(f"Success: {result.success}")
    print(f"Files created: {len(result.files_created)}")
    print(f"Contract fulfilled: {result.contract_fulfilled} ({result.fulfillment_score:.0%})")
    print(f"Quality score: {result.quality_score:.0%}")
    print(f"Duration: {result.duration_seconds:.2f}s")
    
    if result.missing_deliverables:
        print(f"\n⚠️  Missing: {', '.join(result.missing_deliverables)}")
    
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
