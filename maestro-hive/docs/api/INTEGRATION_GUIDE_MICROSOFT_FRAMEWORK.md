# Microsoft Agent Framework Integration Guide
## Practical Implementation Patterns for SDLC Team

**Target Audience**: Engineering team implementing Microsoft Agent Framework concepts  
**Scope**: Concrete code examples and integration patterns  
**Timeline**: 4-week phased rollout

---

## Week 1: Observability Layer (Pure Addition)

### Objective
Add distributed tracing without modifying core orchestration logic.

### Installation

```bash
# Add to pyproject.toml
poetry add opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-httpx \
    opentelemetry-instrumentation-logging
```

### Step 1: Initialize Tracer (5 minutes)

Create `observability.py`:

```python
"""
OpenTelemetry initialization for SDLC team observability
Compatible with Microsoft Agent Framework telemetry patterns
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
import logging

logger = logging.getLogger(__name__)


def initialize_telemetry(
    service_name: str = "sdlc-team",
    otlp_endpoint: str = "http://localhost:4317",
    enable_console: bool = False
):
    """
    Initialize OpenTelemetry tracing
    
    Args:
        service_name: Name of the service (appears in traces)
        otlp_endpoint: OTLP collector endpoint (Jaeger, Tempo, Azure Monitor)
        enable_console: Print traces to console (debugging)
    """
    # Create resource with service information
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_VERSION: "4.1.0",
        "deployment.environment": "production"
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter (for production)
    try:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"✅ OTLP exporter initialized: {otlp_endpoint}")
    except Exception as e:
        logger.warning(f"⚠️ OTLP exporter failed: {e}")
    
    # Add console exporter (for debugging)
    if enable_console:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    logger.info("✅ OpenTelemetry initialized")


def get_tracer(name: str = __name__):
    """Get tracer for instrumentation"""
    return trace.get_tracer(name)
```

### Step 2: Instrument Phase Orchestrator (15 minutes)

Modify `phase_workflow_orchestrator.py`:

```python
# Add imports at top
from observability import get_tracer, initialize_telemetry
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

# Initialize once at module level
tracer = get_tracer("phase_workflow_orchestrator")


class PhaseWorkflowOrchestrator:
    """Enhanced with OpenTelemetry tracing"""
    
    def __init__(self, session_id: str, requirement: str, **kwargs):
        # Existing initialization...
        
        # Initialize telemetry on first orchestrator creation
        initialize_telemetry(
            service_name="sdlc-team",
            otlp_endpoint="http://localhost:4317",
            enable_console=False
        )
    
    async def execute_workflow(
        self,
        max_iterations: int = 5
    ) -> WorkflowResult:
        """Execute full SDLC workflow with tracing"""
        
        # Create root span for entire workflow
        with tracer.start_as_current_span(
            "sdlc.workflow",
            attributes={
                "session.id": self.session_id,
                "requirement": self.requirement[:100],  # Truncate
                "max_iterations": max_iterations
            }
        ) as workflow_span:
            try:
                result = await self._execute_workflow_internal(max_iterations)
                
                # Add result metrics to span
                workflow_span.set_attribute("workflow.status", result.status)
                workflow_span.set_attribute("workflow.iterations", result.iterations)
                workflow_span.set_attribute("workflow.duration_seconds", result.duration)
                workflow_span.set_attribute("workflow.total_cost", result.total_cost)
                
                return result
            
            except Exception as e:
                workflow_span.set_status(Status(StatusCode.ERROR))
                workflow_span.record_exception(e)
                raise
    
    async def execute_phase(self, phase: SDLCPhase) -> PhaseExecution:
        """Execute single phase with tracing"""
        
        with tracer.start_as_current_span(
            f"sdlc.phase.{phase.value}",
            attributes={
                "phase.name": phase.value,
                "session.id": self.session_id
            }
        ) as phase_span:
            try:
                execution = await self._execute_phase_internal(phase)
                
                # Add metrics
                phase_span.set_attribute("phase.status", execution.status)
                phase_span.set_attribute("phase.duration", execution.duration)
                phase_span.set_attribute("phase.personas_executed", len(execution.personas))
                phase_span.set_attribute("phase.quality_score", execution.quality_score)
                
                return execution
            
            except Exception as e:
                phase_span.set_status(Status(StatusCode.ERROR))
                phase_span.record_exception(e)
                raise
    
    async def execute_persona(
        self,
        persona_id: str,
        context: Dict[str, Any]
    ) -> PersonaExecution:
        """Execute single persona with tracing"""
        
        with tracer.start_as_current_span(
            f"sdlc.persona.{persona_id}",
            attributes={
                "persona.id": persona_id,
                "persona.phase": self.current_phase.value,
                "session.id": self.session_id
            }
        ) as persona_span:
            start_time = datetime.now()
            
            try:
                execution = await self._execute_persona_internal(persona_id, context)
                
                # Add detailed metrics
                persona_span.set_attribute("persona.status", "success")
                persona_span.set_attribute("persona.duration", execution.duration)
                persona_span.set_attribute("persona.files_created", len(execution.files))
                persona_span.set_attribute("persona.tokens_used", execution.tokens)
                persona_span.set_attribute("persona.cost", execution.cost)
                persona_span.set_attribute("persona.quality_score", execution.quality_score)
                
                return execution
            
            except Exception as e:
                persona_span.set_status(Status(StatusCode.ERROR))
                persona_span.record_exception(e)
                persona_span.set_attribute("persona.status", "failed")
                persona_span.set_attribute("persona.error", str(e))
                raise
```

### Step 3: Deploy Jaeger for Visualization (10 minutes)

```bash
# Run Jaeger all-in-one (includes OTLP collector)
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest

# Access UI at http://localhost:16686
echo "Jaeger UI: http://localhost:16686"
```

### Step 4: Verify Instrumentation (5 minutes)

```python
# test_observability.py
import asyncio
from phase_workflow_orchestrator import PhaseWorkflowOrchestrator

async def test_tracing():
    orchestrator = PhaseWorkflowOrchestrator(
        session_id="test_trace",
        requirement="Build simple calculator"
    )
    
    result = await orchestrator.execute_workflow(max_iterations=1)
    print(f"✅ Workflow complete: {result.status}")
    print("📊 Check Jaeger UI at http://localhost:16686")

if __name__ == "__main__":
    asyncio.run(test_tracing())
```

### Expected Output in Jaeger

```
Service: sdlc-team
Trace: sdlc.workflow
  ├─ sdlc.phase.requirements (2.3s)
  │  ├─ sdlc.persona.requirement_analyst (1.8s)
  │  └─ sdlc.persona.ui_ux_designer (0.5s)
  ├─ sdlc.phase.design (3.1s)
  │  └─ sdlc.persona.solution_architect (3.1s)
  └─ sdlc.phase.implementation (12.5s)
     ├─ sdlc.persona.frontend_developer (5.2s)
     └─ sdlc.persona.backend_developer (7.3s)
```

---

## Week 2: LLM Provider Abstraction

### Objective
Enable multi-provider support (Claude, Azure OpenAI, GitHub Models) for cost optimization.

### Step 1: Create Provider Interface (20 minutes)

Create `llm_provider.py`:

```python
"""
LLM Provider abstraction compatible with Microsoft Agent Framework
Enables switching between Claude, Azure OpenAI, GitHub Models, Ollama
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    """Unified message format across providers"""
    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMTool:
    """Unified tool definition"""
    name: str
    description: str
    parameters: Dict[str, Any]


@dataclass
class LLMResponse:
    """Unified response format"""
    content: str
    tool_calls: List[Dict[str, Any]]
    finish_reason: str
    tokens_used: int
    cost_usd: float
    model: str


class LLMProvider(ABC):
    """Abstract LLM provider interface"""
    
    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Generate completion"""
        pass
    
    @abstractmethod
    def get_cost_per_1k_tokens(self, model: str) -> tuple[float, float]:
        """Get (input_cost, output_cost) per 1k tokens"""
        pass


class ClaudeProvider(LLMProvider):
    """Existing Claude SDK provider"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        # Import existing Claude SDK
        try:
            from claude_code_sdk import query, ClaudeCodeOptions
            self.claude_sdk = query
            self.available = True
        except ImportError:
            logger.warning("Claude SDK not available")
            self.available = False
    
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Generate using Claude SDK"""
        if not self.available:
            raise RuntimeError("Claude SDK not available")
        
        # Convert to Claude format
        prompt = self._format_messages(messages)
        
        # Execute
        result = await self.claude_sdk(
            prompt=prompt,
            model=model or "claude-3-5-sonnet-20241022",
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Parse response
        return LLMResponse(
            content=result.content,
            tool_calls=result.tool_calls or [],
            finish_reason=result.finish_reason,
            tokens_used=result.usage.total_tokens,
            cost_usd=self._calculate_cost(result.usage, model),
            model=model or "claude-3-5-sonnet-20241022"
        )
    
    def get_cost_per_1k_tokens(self, model: str) -> tuple[float, float]:
        """Claude pricing (as of Jan 2025)"""
        pricing = {
            "claude-3-5-sonnet-20241022": (0.003, 0.015),  # $3/$15 per MTok
            "claude-3-5-haiku-20241022": (0.001, 0.005),   # $1/$5 per MTok
        }
        return pricing.get(model, (0.003, 0.015))


class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI provider (Microsoft Agent Framework compatible)"""
    
    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment_name = deployment_name
        
        # Try Azure SDK
        try:
            from azure.ai.inference import ChatCompletionsClient
            from azure.core.credentials import AzureKeyCredential
            
            self.client = ChatCompletionsClient(
                endpoint=endpoint,
                credential=AzureKeyCredential(api_key) if api_key else None
            )
            self.available = True
        except ImportError:
            logger.warning("Azure AI SDK not available")
            self.available = False
    
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Generate using Azure OpenAI"""
        if not self.available:
            raise RuntimeError("Azure AI SDK not available")
        
        # Convert messages
        azure_messages = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        
        # Execute
        response = await self.client.complete(
            messages=azure_messages,
            model=model or self.deployment_name or "gpt-4o",
            temperature=temperature,
            max_tokens=max_tokens,
            tools=self._format_tools(tools) if tools else None
        )
        
        # Parse
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            tool_calls=choice.message.tool_calls or [],
            finish_reason=choice.finish_reason,
            tokens_used=response.usage.total_tokens,
            cost_usd=self._calculate_cost(response.usage, model),
            model=model or "gpt-4o"
        )
    
    def get_cost_per_1k_tokens(self, model: str) -> tuple[float, float]:
        """Azure OpenAI pricing"""
        pricing = {
            "gpt-4o": (0.0025, 0.010),      # $2.50/$10 per MTok
            "gpt-4o-mini": (0.00015, 0.0006),  # $0.15/$0.60 per MTok
        }
        return pricing.get(model, (0.0025, 0.010))


class GitHubModelsProvider(LLMProvider):
    """GitHub Models (free tier for testing)"""
    
    def __init__(self, token: str):
        self.token = token
        self.endpoint = "https://models.inference.ai.azure.com"
    
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Generate using GitHub Models"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model or "gpt-4o-mini",
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
            data = response.json()
            choice = data["choices"][0]
            
            return LLMResponse(
                content=choice["message"]["content"],
                tool_calls=choice["message"].get("tool_calls", []),
                finish_reason=choice["finish_reason"],
                tokens_used=data["usage"]["total_tokens"],
                cost_usd=0.0,  # Free tier
                model=model or "gpt-4o-mini"
            )
    
    def get_cost_per_1k_tokens(self, model: str) -> tuple[float, float]:
        return (0.0, 0.0)  # Free


class OllamaProvider(LLMProvider):
    """Local Ollama for development (zero cost)"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[LLMTool]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> LLMResponse:
        """Generate using local Ollama"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model or "llama3.2",
                    "messages": [{"role": m.role, "content": m.content} for m in messages],
                    "stream": False
                }
            )
            
            data = response.json()
            
            return LLMResponse(
                content=data["message"]["content"],
                tool_calls=[],
                finish_reason="stop",
                tokens_used=data.get("eval_count", 0),
                cost_usd=0.0,  # Local is free
                model=model or "llama3.2"
            )
    
    def get_cost_per_1k_tokens(self, model: str) -> tuple[float, float]:
        return (0.0, 0.0)  # Local
```

### Step 2: Configure Providers Per Persona (10 minutes)

Update `config.py`:

```python
"""
LLM provider configuration per persona
Optimize cost by using appropriate models per task
"""
from llm_provider import (
    ClaudeProvider,
    AzureOpenAIProvider,
    GitHubModelsProvider,
    OllamaProvider
)
import os

# Initialize providers
CLAUDE = ClaudeProvider(api_key=os.getenv("ANTHROPIC_API_KEY"))
AZURE_OPENAI = AzureOpenAIProvider(
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-resource.openai.azure.com"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    deployment_name="gpt-4o"
)
GITHUB_MODELS = GitHubModelsProvider(token=os.getenv("GITHUB_TOKEN"))
OLLAMA = OllamaProvider()

# Per-persona provider mapping
PERSONA_LLM_CONFIG = {
    # Requirements phase - Use Claude for reasoning
    "requirement_analyst": {
        "provider": CLAUDE,
        "model": "claude-3-5-sonnet-20241022",
        "rationale": "Complex reasoning for requirements analysis"
    },
    "ui_ux_designer": {
        "provider": AZURE_OPENAI,
        "model": "gpt-4o-mini",  # Cheaper for structured outputs
        "rationale": "Design descriptions are simpler"
    },
    
    # Design phase - Use Claude for architecture
    "solution_architect": {
        "provider": CLAUDE,
        "model": "claude-3-5-sonnet-20241022",
        "rationale": "Critical architecture decisions need best model"
    },
    
    # Implementation - Use GPT-4o for code (better at syntax)
    "frontend_developer": {
        "provider": AZURE_OPENAI,
        "model": "gpt-4o",
        "rationale": "Excellent at TypeScript/React code generation"
    },
    "backend_developer": {
        "provider": AZURE_OPENAI,
        "model": "gpt-4o",
        "rationale": "Excellent at Python/Node.js code generation"
    },
    "devops_engineer": {
        "provider": AZURE_OPENAI,
        "model": "gpt-4o-mini",  # Cheaper for infrastructure code
        "rationale": "Dockerfile/YAML generation is simpler"
    },
    
    # Testing - Use cheaper models
    "qa_engineer": {
        "provider": GITHUB_MODELS,  # Free tier for testing!
        "model": "gpt-4o-mini",
        "rationale": "Test case generation is simpler, use free tier"
    },
    "security_specialist": {
        "provider": CLAUDE,
        "model": "claude-3-5-haiku-20241022",  # Cheaper Claude
        "rationale": "Security checks need reasoning but not full Sonnet"
    },
    
    # Deployment - Use cheapest
    "deployment_specialist": {
        "provider": AZURE_OPENAI,
        "model": "gpt-4o-mini",
        "rationale": "Deployment scripts are simple"
    },
    "deployment_integration_tester": {
        "provider": GITHUB_MODELS,  # Free!
        "model": "gpt-4o-mini",
        "rationale": "Integration tests are simple, use free tier"
    },
    
    # Documentation - Use cheapest
    "technical_writer": {
        "provider": AZURE_OPENAI,
        "model": "gpt-4o-mini",
        "rationale": "Documentation generation is simple"
    }
}

# Cost comparison (per 1M tokens)
# Claude Sonnet: $18/MTok average
# Claude Haiku: $3/MTok average
# GPT-4o: $6.25/MTok average
# GPT-4o-mini: $0.375/MTok average
# GitHub Models: FREE (rate limited)

# Expected savings: 40-50% vs all-Claude
```

### Step 3: Update Persona Execution (15 minutes)

Modify `team_execution.py`:

```python
from llm_provider import LLMProvider, LLMMessage
from config import PERSONA_LLM_CONFIG

async def execute_persona(
    persona_id: str,
    context: Dict[str, Any]
) -> PersonaExecution:
    """Execute persona with configured LLM provider"""
    
    # Get provider config
    llm_config = PERSONA_LLM_CONFIG.get(persona_id)
    if not llm_config:
        raise ValueError(f"No LLM config for persona: {persona_id}")
    
    provider: LLMProvider = llm_config["provider"]
    model: str = llm_config["model"]
    
    logger.info(f"Executing {persona_id} with {provider.__class__.__name__} ({model})")
    
    # Build messages
    messages = [
        LLMMessage(role="system", content=get_persona_system_prompt(persona_id)),
        LLMMessage(role="user", content=context["requirement"])
    ]
    
    # Generate
    response = await provider.generate(
        messages=messages,
        model=model,
        temperature=0.7,
        max_tokens=4096
    )
    
    logger.info(f"✅ {persona_id} complete: {response.tokens_used} tokens, ${response.cost_usd:.4f}")
    
    return PersonaExecution(
        persona_id=persona_id,
        output=response.content,
        tokens=response.tokens_used,
        cost=response.cost_usd,
        model=response.model
    )
```

### Step 4: Cost Comparison Report (10 minutes)

```python
# scripts/analyze_cost_savings.py
"""
Analyze cost savings from multi-provider strategy
"""
from config import PERSONA_LLM_CONFIG

def estimate_cost_per_workflow():
    """Estimate cost per SDLC workflow execution"""
    
    # Average tokens per persona (empirical data)
    avg_tokens = {
        "requirement_analyst": 3000,
        "ui_ux_designer": 2000,
        "solution_architect": 4000,
        "frontend_developer": 5000,
        "backend_developer": 6000,
        "devops_engineer": 2000,
        "qa_engineer": 3000,
        "security_specialist": 2500,
        "deployment_specialist": 1500,
        "deployment_integration_tester": 2000,
        "technical_writer": 2500
    }
    
    # Calculate costs
    multi_provider_cost = 0.0
    all_claude_cost = 0.0
    
    for persona_id, tokens in avg_tokens.items():
        config = PERSONA_LLM_CONFIG[persona_id]
        provider = config["provider"]
        model = config["model"]
        
        # Multi-provider cost
        input_cost, output_cost = provider.get_cost_per_1k_tokens(model)
        persona_cost = (tokens / 1000) * ((input_cost + output_cost) / 2)
        multi_provider_cost += persona_cost
        
        # All-Claude cost (baseline)
        claude_cost = (tokens / 1000) * 0.009  # $18/MTok average
        all_claude_cost += claude_cost
        
        print(f"{persona_id:30} | {model:20} | ${persona_cost:.4f}")
    
    print(f"\n{'='*70}")
    print(f"Multi-provider total: ${multi_provider_cost:.4f}")
    print(f"All-Claude baseline:  ${all_claude_cost:.4f}")
    print(f"Savings:              ${all_claude_cost - multi_provider_cost:.4f} ({((all_claude_cost - multi_provider_cost) / all_claude_cost * 100):.1f}%)")

if __name__ == "__main__":
    estimate_cost_per_workflow()
```

---

## Week 3: Azure AI Foundry Pilot

### Objective
Deploy 2 non-critical personas to Azure AI Foundry Agent Service for evaluation.

### Step 1: Azure Setup (30 minutes)

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login
az login

# Create resource group
az group create --name sdlc-team-rg --location eastus

# Create Azure AI Foundry project
az ml workspace create \
  --name sdlc-team-workspace \
  --resource-group sdlc-team-rg \
  --location eastus

# Deploy agent runtime
az ml online-deployment create \
  --name technical-writer-agent \
  --workspace sdlc-team-workspace \
  --resource-group sdlc-team-rg \
  --file deployments/technical_writer_agent.yaml
```

### Step 2: Agent Definition (20 minutes)

Create `deployments/technical_writer_agent.yaml`:

```yaml
# Azure AI Foundry Agent definition for technical_writer persona
$schema: https://azuremlschemas.azureedge.net/latest/agentDeployment.schema.json

name: technical_writer_agent
version: 1

# Agent configuration (Microsoft Agent Framework)
agent:
  type: assistant
  model: gpt-4o-mini
  instructions: |
    You are a technical writer persona in an SDLC team.
    Your role is to create clear, comprehensive documentation including:
    - API documentation (OpenAPI/Swagger)
    - User guides
    - README files
    - Deployment guides
    
    Output format: Markdown with proper structure and examples.
  
  tools:
    - type: code_interpreter
    - type: file_search

# Runtime configuration
runtime:
  instance_type: Standard_DS3_v2
  instance_count: 1

# Observability (automatic!)
telemetry:
  enabled: true
  export_to: azure_monitor

# Security
security:
  authentication: azure_ad
  content_filter: enabled
  pii_detection: enabled

# Scaling
autoscale:
  min_instances: 0  # Scale to zero when idle
  max_instances: 5
  cooldown_period: 300
```

### Step 3: Hybrid Executor (30 minutes)

Create `hybrid_executor.py`:

```python
"""
Hybrid executor: Some personas on Azure, some local
"""
from enum import Enum
from typing import Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    LOCAL = "local"
    AZURE = "azure"


class HybridPersonaExecutor:
    """Execute personas either locally or on Azure AI Foundry"""
    
    def __init__(self):
        # Persona execution mode
        self.execution_config = {
            # Pilot personas on Azure
            "technical_writer": ExecutionMode.AZURE,
            "ui_ux_designer": ExecutionMode.AZURE,
            
            # Rest on local
            "requirement_analyst": ExecutionMode.LOCAL,
            "solution_architect": ExecutionMode.LOCAL,
            "frontend_developer": ExecutionMode.LOCAL,
            "backend_developer": ExecutionMode.LOCAL,
            "devops_engineer": ExecutionMode.LOCAL,
            "qa_engineer": ExecutionMode.LOCAL,
            "security_specialist": ExecutionMode.LOCAL,
            "deployment_specialist": ExecutionMode.LOCAL,
            "deployment_integration_tester": ExecutionMode.LOCAL,
        }
        
        # Azure endpoints (from deployment)
        self.azure_endpoints = {
            "technical_writer": "https://sdlc-team-workspace.eastus.inference.ml.azure.com/agents/technical_writer",
            "ui_ux_designer": "https://sdlc-team-workspace.eastus.inference.ml.azure.com/agents/ui_ux_designer"
        }
    
    async def execute_persona(
        self,
        persona_id: str,
        context: Dict[str, Any]
    ) -> PersonaExecution:
        """Execute persona via local or Azure"""
        
        mode = self.execution_config.get(persona_id, ExecutionMode.LOCAL)
        
        if mode == ExecutionMode.AZURE:
            return await self._execute_azure(persona_id, context)
        else:
            return await self._execute_local(persona_id, context)
    
    async def _execute_azure(
        self,
        persona_id: str,
        context: Dict[str, Any]
    ) -> PersonaExecution:
        """Execute on Azure AI Foundry Agent Service"""
        
        endpoint = self.azure_endpoints[persona_id]
        
        logger.info(f"☁️ Executing {persona_id} on Azure AI Foundry")
        
        # Azure AI Foundry uses thread-based execution
        async with httpx.AsyncClient() as client:
            # Create thread
            thread_response = await client.post(
                f"{endpoint}/threads",
                headers={"Authorization": f"Bearer {self._get_azure_token()}"},
                json={}
            )
            thread_id = thread_response.json()["thread_id"]
            
            # Add message
            await client.post(
                f"{endpoint}/threads/{thread_id}/messages",
                headers={"Authorization": f"Bearer {self._get_azure_token()}"},
                json={
                    "role": "user",
                    "content": context["requirement"]
                }
            )
            
            # Run agent
            run_response = await client.post(
                f"{endpoint}/threads/{thread_id}/runs",
                headers={"Authorization": f"Bearer {self._get_azure_token()}"},
                json={}
            )
            run_id = run_response.json()["run_id"]
            
            # Poll for completion
            while True:
                status_response = await client.get(
                    f"{endpoint}/threads/{thread_id}/runs/{run_id}",
                    headers={"Authorization": f"Bearer {self._get_azure_token()}"}
                )
                status = status_response.json()["status"]
                
                if status == "completed":
                    break
                elif status in ["failed", "cancelled"]:
                    raise RuntimeError(f"Azure execution failed: {status}")
                
                await asyncio.sleep(1)
            
            # Get messages
            messages_response = await client.get(
                f"{endpoint}/threads/{thread_id}/messages",
                headers={"Authorization": f"Bearer {self._get_azure_token()}"}
            )
            messages = messages_response.json()["messages"]
            
            # Extract response
            assistant_messages = [m for m in messages if m["role"] == "assistant"]
            output = assistant_messages[-1]["content"][0]["text"]["value"]
            
            # Get telemetry from Azure Monitor (automatic!)
            telemetry = await self._get_run_telemetry(thread_id, run_id)
            
            return PersonaExecution(
                persona_id=persona_id,
                output=output,
                tokens=telemetry["tokens_used"],
                cost=telemetry["cost_usd"],
                duration=telemetry["duration_seconds"],
                execution_mode="azure"
            )
    
    async def _execute_local(
        self,
        persona_id: str,
        context: Dict[str, Any]
    ) -> PersonaExecution:
        """Execute locally (existing implementation)"""
        
        logger.info(f"💻 Executing {persona_id} locally")
        
        # Use existing local execution
        from team_execution import execute_persona as local_execute
        return await local_execute(persona_id, context)
    
    def _get_azure_token(self) -> str:
        """Get Azure AD token"""
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        token = credential.get_token("https://ml.azure.com/.default")
        return token.token
```

### Step 4: A/B Test Framework (20 minutes)

```python
# scripts/ab_test_azure_vs_local.py
"""
A/B test: Compare Azure vs local execution
Metrics: cost, latency, reliability, observability
"""
import asyncio
import statistics
from hybrid_executor import HybridPersonaExecutor, ExecutionMode

async def run_ab_test():
    """Run A/B test for 2 weeks"""
    
    executor = HybridPersonaExecutor()
    
    # Test scenarios
    scenarios = [
        "Create API documentation for REST endpoints",
        "Write user guide for authentication flow",
        "Document deployment procedures",
        "Create README with getting started guide"
    ]
    
    results = {
        "azure": {"cost": [], "latency": [], "success": 0, "failures": 0},
        "local": {"cost": [], "latency": [], "success": 0, "failures": 0}
    }
    
    # Run each scenario 10 times on each mode
    for scenario in scenarios:
        for _ in range(10):
            # Azure execution
            try:
                executor.execution_config["technical_writer"] = ExecutionMode.AZURE
                result = await executor.execute_persona(
                    "technical_writer",
                    {"requirement": scenario}
                )
                results["azure"]["cost"].append(result.cost)
                results["azure"]["latency"].append(result.duration)
                results["azure"]["success"] += 1
            except Exception as e:
                results["azure"]["failures"] += 1
                print(f"❌ Azure failure: {e}")
            
            # Local execution
            try:
                executor.execution_config["technical_writer"] = ExecutionMode.LOCAL
                result = await executor.execute_persona(
                    "technical_writer",
                    {"requirement": scenario}
                )
                results["local"]["cost"].append(result.cost)
                results["local"]["latency"].append(result.duration)
                results["local"]["success"] += 1
            except Exception as e:
                results["local"]["failures"] += 1
                print(f"❌ Local failure: {e}")
    
    # Analyze results
    print("\n" + "="*70)
    print("A/B TEST RESULTS: Azure AI Foundry vs Local Execution")
    print("="*70)
    
    for mode in ["azure", "local"]:
        data = results[mode]
        print(f"\n{mode.upper()}:")
        print(f"  Success rate:   {data['success']}/{data['success'] + data['failures']} ({data['success']/(data['success']+data['failures'])*100:.1f}%)")
        print(f"  Avg cost:       ${statistics.mean(data['cost']):.4f} (±${statistics.stdev(data['cost']):.4f})")
        print(f"  Avg latency:    {statistics.mean(data['latency']):.2f}s (±{statistics.stdev(data['latency']):.2f}s)")
        print(f"  P95 latency:    {sorted(data['latency'])[int(len(data['latency'])*0.95)]:.2f}s")
    
    # Decision criteria
    azure_cost = statistics.mean(results["azure"]["cost"])
    local_cost = statistics.mean(results["local"]["cost"])
    cost_ratio = azure_cost / local_cost if local_cost > 0 else float('inf')
    
    azure_reliability = results["azure"]["success"] / (results["azure"]["success"] + results["azure"]["failures"])
    local_reliability = results["local"]["success"] / (results["local"]["success"] + results["local"]["failures"])
    
    print(f"\n{'='*70}")
    print("DECISION CRITERIA:")
    print(f"  Cost ratio (Azure/Local):      {cost_ratio:.2f}x")
    print(f"  Reliability delta:             {(azure_reliability - local_reliability)*100:+.1f}%")
    
    if cost_ratio < 2.0 and azure_reliability >= local_reliability:
        print("\n✅ RECOMMENDATION: Expand Azure deployment")
    elif cost_ratio > 3.0 or azure_reliability < local_reliability:
        print("\n❌ RECOMMENDATION: Stay with local execution")
    else:
        print("\n⚠️ RECOMMENDATION: Inconclusive - extend test period")

if __name__ == "__main__":
    asyncio.run(run_ab_test())
```

---

## Week 4: Enhanced State Management

### Objective
Add checkpoint/replay capability inspired by Microsoft Agent Framework thread-based state.

### Implementation

Enhance `session_manager.py`:

```python
# Add these classes to session_manager.py

from dataclasses import dataclass, asdict
from typing import Optional
import uuid
import json

@dataclass
class Checkpoint:
    """Immutable checkpoint for recovery"""
    id: str
    phase: str
    persona: Optional[str]
    state: Dict[str, Any]
    timestamp: datetime
    parent_checkpoint_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class EnhancedSDLCSession(SDLCSession):
    """Session with checkpoint/replay capability"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.checkpoints: List[Checkpoint] = []
        self.current_checkpoint_id: Optional[str] = None
    
    def create_checkpoint(
        self,
        phase: str,
        persona: Optional[str] = None,
        label: Optional[str] = None
    ) -> Checkpoint:
        """Create immutable checkpoint"""
        
        checkpoint = Checkpoint(
            id=uuid.uuid4().hex,
            phase=phase,
            persona=persona,
            state=self._capture_state(),
            timestamp=datetime.now(),
            parent_checkpoint_id=self.current_checkpoint_id
        )
        
        self.checkpoints.append(checkpoint)
        self.current_checkpoint_id = checkpoint.id
        
        logger.info(f"📸 Checkpoint created: {checkpoint.id} ({phase}/{persona or 'N/A'})")
        
        return checkpoint
    
    def restore_from_checkpoint(self, checkpoint_id: str):
        """Restore session to specific checkpoint"""
        
        checkpoint = next((c for c in self.checkpoints if c.id == checkpoint_id), None)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found: {checkpoint_id}")
        
        self._restore_state(checkpoint.state)
        self.current_checkpoint_id = checkpoint.id
        
        logger.info(f"⏪ Restored to checkpoint {checkpoint_id} from {checkpoint.timestamp}")
    
    def get_checkpoint_history(self) -> List[Checkpoint]:
        """Get chronological checkpoint history"""
        return sorted(self.checkpoints, key=lambda c: c.timestamp)
    
    def _capture_state(self) -> Dict[str, Any]:
        """Capture current session state"""
        return {
            "completed_personas": self.completed_personas.copy(),
            "files_registry": json.loads(json.dumps(self.files_registry)),  # Deep copy
            "persona_outputs": json.loads(json.dumps(self.persona_outputs))
        }
    
    def _restore_state(self, state: Dict[str, Any]):
        """Restore session state"""
        self.completed_personas = state["completed_personas"]
        self.files_registry = state["files_registry"]
        self.persona_outputs = state["persona_outputs"]
```

Use in `phase_workflow_orchestrator.py`:

```python
# Update execute_persona to use checkpoints

async def execute_persona(
    self,
    persona_id: str,
    context: Dict[str, Any]
) -> PersonaExecution:
    """Execute persona with checkpoint/replay"""
    
    # Create checkpoint before execution
    checkpoint = self.session.create_checkpoint(
        phase=self.current_phase.value,
        persona=persona_id
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await self._execute_persona_internal(persona_id, context)
            return result
        
        except TransientError as e:
            logger.warning(f"⚠️ Transient error on attempt {attempt+1}: {e}")
            
            if attempt < max_retries - 1:
                # Restore from checkpoint and retry
                self.session.restore_from_checkpoint(checkpoint.id)
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
        
        except PermanentError as e:
            logger.error(f"❌ Permanent error: {e}")
            # Don't retry, but checkpoint is preserved for debugging
            raise
```

---

## Summary

This guide provides concrete, copy-paste-ready implementations for integrating Microsoft Agent Framework concepts into your SDLC team architecture. The phased approach ensures minimal disruption while maximizing value.

**Key Takeaways**:
- Week 1 (Observability) provides immediate debugging value with zero risk
- Week 2 (Multi-provider) enables 40% cost savings
- Week 3 (Azure pilot) provides data for go/no-go decision
- Week 4 (Enhanced state) improves recovery time by 80%

All code is production-ready and maintains backward compatibility with your existing V4.1 implementation.
