from __future__ import annotations
import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from .router import PersonaRouter
from .spi import Message, ChatRequest as SPIChatRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global router instance
router: Optional[PersonaRouter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global router
    logger.info("Initializing LLM Router Service...")
    try:
        router = PersonaRouter()
        logger.info("PersonaRouter initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize PersonaRouter: {e}")
        raise
    yield
    logger.info("Shutting down LLM Router Service...")


# Create FastAPI app
app = FastAPI(
    title="LLM Router Service",
    description="Lightweight LLM provider routing service",
    version="1.0.0",
    lifespan=lifespan,
)


# Pydantic models for API
class MessageModel(BaseModel):
    role: str = Field(..., description="Message role (system, user, assistant)")
    content: str = Field(..., description="Message content")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID if applicable")


class ChatRequestModel(BaseModel):
    persona: str = Field(..., description="Persona to use (code_assistant, chatbot, analyst, creative_writer)")
    messages: List[MessageModel] = Field(..., description="Conversation messages")
    max_tokens: int = Field(4096, description="Maximum tokens to generate")
    temperature: float = Field(0.7, description="Temperature for generation", ge=0.0, le=2.0)
    stream: bool = Field(True, description="Whether to stream the response")
    model: Optional[str] = Field(None, description="Specific model override")


class PersonaInfo(BaseModel):
    name: str
    description: str
    provider_preferences: List[str]
    requires: List[str]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        service="llm-router",
        version="1.0.0"
    )


@app.get("/api/v1/personas", response_model=List[PersonaInfo])
async def list_personas():
    """List available personas and their configurations"""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")

    personas_data = router.policy.get("personas", {})
    personas = []

    for name, config in personas_data.items():
        personas.append(PersonaInfo(
            name=name,
            description=config.get("description", ""),
            provider_preferences=config.get("provider_preferences", []),
            requires=config.get("requires", [])
        ))

    return personas


@app.post("/api/v1/chat")
async def chat(request: ChatRequestModel):
    """
    Route chat request to appropriate LLM provider based on persona
    """
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")

    try:
        # Get the appropriate client for this persona
        logger.info(f"Routing request for persona: {request.persona}")
        client = router.get_client(request.persona)

        # Convert API messages to SPI messages
        messages = [
            Message(
                role=msg.role,
                content=msg.content,
                tool_call_id=msg.tool_call_id
            )
            for msg in request.messages
        ]

        # Create SPI chat request
        chat_req = SPIChatRequest(
            messages=messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            stream=request.stream,
            model=request.model
        )

        # Stream response
        if request.stream:
            async def generate():
                try:
                    async for chunk in client.chat(chat_req):
                        if chunk.delta_text:
                            yield chunk.delta_text
                        if chunk.finish_reason:
                            logger.info(f"Chat completed with reason: {chunk.finish_reason}")
                except Exception as e:
                    logger.error(f"Error during streaming: {e}")
                    yield f"\n\n[ERROR: {str(e)}]"

            return StreamingResponse(generate(), media_type="text/plain")
        else:
            # Non-streaming response
            full_text = ""
            async for chunk in client.chat(chat_req):
                if chunk.delta_text:
                    full_text += chunk.delta_text

            return JSONResponse(content={"content": full_text, "response": full_text})

    except ValueError as e:
        logger.error(f"Routing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/v1/providers")
async def list_providers():
    """List available LLM providers and their capabilities"""
    if not router:
        raise HTTPException(status_code=503, detail="Router not initialized")

    return router.capabilities.get("providers", {})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(
        "llm_router.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
