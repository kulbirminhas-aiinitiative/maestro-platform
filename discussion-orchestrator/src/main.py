"""
Main FastAPI application for the Discussion Orchestrator service.

Provides REST API endpoints and WebSocket support for managing
multi-agent discussions with human participants.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .context import SharedContext, redis_manager
from .models import (
    DiscussionRequest,
    DiscussionResponse,
    DiscussionSession,
    Message,
    MessageRequest,
    Participant,
    ParticipantType,
    DiscussionStatus,
    HealthResponse,
    MessageType
)
from .agent_factory import AgentFactory
from .discussion_manager import DiscussionManager

# Configure logging
settings.configure_logging()
logger = logging.getLogger(__name__)


# WebSocket connection manager
class ConnectionManager:
    """Manages WebSocket connections for discussion sessions."""

    def __init__(self):
        """Initialize connection manager with empty connections dict."""
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, discussion_id: str, websocket: WebSocket):
        """
        Accept and register a new WebSocket connection.

        Args:
            discussion_id: Discussion session ID
            websocket: WebSocket connection to register
        """
        await websocket.accept()
        if discussion_id not in self.active_connections:
            self.active_connections[discussion_id] = []
        self.active_connections[discussion_id].append(websocket)
        logger.info(f"WebSocket connected to discussion {discussion_id}")

    def disconnect(self, discussion_id: str, websocket: WebSocket):
        """
        Unregister a WebSocket connection.

        Args:
            discussion_id: Discussion session ID
            websocket: WebSocket connection to unregister
        """
        if discussion_id in self.active_connections:
            self.active_connections[discussion_id].remove(websocket)
            if not self.active_connections[discussion_id]:
                del self.active_connections[discussion_id]
        logger.info(f"WebSocket disconnected from discussion {discussion_id}")

    async def broadcast(self, discussion_id: str, message: dict):
        """
        Broadcast a message to all connected clients for a discussion.

        Args:
            discussion_id: Discussion session ID
            message: Message data to broadcast
        """
        if discussion_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[discussion_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message: {e}")
                    dead_connections.append(connection)

            # Clean up dead connections
            for dead_conn in dead_connections:
                self.disconnect(discussion_id, dead_conn)


# Global instances
ws_manager = ConnectionManager()
agent_factory = AgentFactory()
discussion_manager: Optional[DiscussionManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan events.

    Handles startup and shutdown tasks like connecting/disconnecting from Redis.
    """
    global discussion_manager

    # Startup
    logger.info(f"Starting {settings.service_name} service...")
    try:
        await redis_manager.connect()
        redis_client = await redis_manager.get_client()
        shared_context = SharedContext(redis_client)

        # Initialize discussion manager
        discussion_manager = DiscussionManager(agent_factory, shared_context)

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application...")
    try:
        await redis_manager.disconnect()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Discussion Orchestrator",
    description="Orchestrates multi-agent discussions with human participants",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency to get SharedContext
async def get_context() -> SharedContext:
    """
    Get SharedContext instance with Redis client.

    Returns:
        SharedContext instance
    """
    redis_client = await redis_manager.get_client()
    return SharedContext(redis_client)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and dependency health information.
    """
    try:
        redis_client = await redis_manager.get_client()
        await redis_client.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"

    return HealthResponse(
        status="healthy" if redis_status == "healthy" else "degraded",
        service=settings.service_name,
        version="0.1.0",
        timestamp=datetime.utcnow(),
        dependencies={
            "redis": redis_status,
            "execution_platform": "not_implemented"
        }
    )


@app.post(
    "/v1/discussions",
    response_model=DiscussionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Discussions"]
)
async def create_discussion(request: DiscussionRequest):
    """
    Create a new discussion session using DiscussionManager.

    Creates a discussion with specified agents and human participants,
    initializes AutoGen agents via execution-platform, and returns session details.

    Args:
        request: DiscussionRequest with topic, agents, humans, and protocol

    Returns:
        DiscussionResponse with created session details

    Raises:
        HTTPException: If session creation fails
    """
    try:
        if discussion_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Discussion manager not initialized"
            )

        # Create discussion using manager
        session = await discussion_manager.create_discussion(request)

        logger.info(f"Created discussion session: {session.id}")

        return DiscussionResponse(
            session=session,
            message="Discussion session created successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create discussion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create discussion: {str(e)}"
        )


@app.get(
    "/v1/discussions/{discussion_id}",
    response_model=DiscussionSession,
    tags=["Discussions"]
)
async def get_discussion(discussion_id: str):
    """
    Get discussion session details.

    Retrieves full session information including participants and metadata.

    Args:
        discussion_id: Discussion session ID

    Returns:
        DiscussionSession object

    Raises:
        HTTPException: If discussion not found
    """
    try:
        context = await get_context()
        session = await context.get_session(discussion_id)

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discussion {discussion_id} not found"
            )

        # Load messages into session
        messages = await context.get_history(discussion_id)
        session.messages = messages

        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get discussion {discussion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve discussion: {str(e)}"
        )


@app.get(
    "/v1/discussions/{discussion_id}/messages",
    response_model=List[Message],
    tags=["Discussions"]
)
async def get_messages(
    discussion_id: str,
    limit: Optional[int] = None,
    offset: int = 0
):
    """
    Get discussion message history.

    Args:
        discussion_id: Discussion session ID
        limit: Maximum number of messages to retrieve
        offset: Number of messages to skip

    Returns:
        List of Message objects

    Raises:
        HTTPException: If discussion not found
    """
    try:
        context = await get_context()

        # Verify discussion exists
        session = await context.get_session(discussion_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discussion {discussion_id} not found"
            )

        messages = await context.get_history(discussion_id, limit, offset)
        return messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages for {discussion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}"
        )


@app.post(
    "/v1/discussions/{discussion_id}/start",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Discussions"]
)
async def start_discussion(discussion_id: str, initial_message: str = "Let's begin the discussion."):
    """
    Start a discussion with AutoGen agents.

    Initiates the multi-agent discussion using the configured protocol.
    Messages will be streamed to WebSocket clients in real-time.

    Args:
        discussion_id: Discussion session ID
        initial_message: Initial message to start the discussion

    Returns:
        Acceptance response

    Raises:
        HTTPException: If discussion not found or cannot be started
    """
    try:
        if discussion_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Discussion manager not initialized"
            )

        # Define callback to broadcast messages via WebSocket
        async def broadcast_message(message: Message):
            await ws_manager.broadcast(discussion_id, {
                "type": "message",
                "data": message.model_dump(mode="json")
            })

        # Start discussion in background task
        async def run_discussion():
            try:
                async for message in discussion_manager.start_discussion(
                    discussion_id,
                    initial_message,
                    message_callback=broadcast_message
                ):
                    # Messages are automatically broadcasted via callback
                    logger.debug(f"Discussion {discussion_id}: {message.participant_name} - {message.content[:50]}")
            except Exception as e:
                logger.error(f"Error in discussion {discussion_id}: {e}", exc_info=True)
                await ws_manager.broadcast(discussion_id, {
                    "type": "error",
                    "data": {"message": str(e)}
                })

        # Start discussion as background task
        import asyncio
        asyncio.create_task(run_discussion())

        return {
            "status": "started",
            "message": "Discussion started. Connect to WebSocket for real-time updates.",
            "websocket_url": f"/v1/discussions/{discussion_id}/stream"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start discussion: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start discussion: {str(e)}"
        )


@app.post(
    "/v1/discussions/{discussion_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
    tags=["Discussions"]
)
async def send_message(discussion_id: str, message_request: MessageRequest):
    """
    Send a human message to a discussion.

    This allows human participants to inject messages into the discussion.
    The message will be broadcasted to all WebSocket clients.

    Args:
        discussion_id: Discussion session ID
        message_request: Message data

    Returns:
        Created Message object

    Raises:
        HTTPException: If discussion not found or message send fails
    """
    try:
        if discussion_manager is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Discussion manager not initialized"
            )

        # Add human message via discussion manager
        message = await discussion_manager.add_human_message(
            session_id=discussion_id,
            user_id=message_request.participant_id,
            message=message_request.content
        )

        # Broadcast to WebSocket clients
        await ws_manager.broadcast(discussion_id, {
            "type": "message",
            "data": message.model_dump(mode="json")
        })

        return message

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message to {discussion_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )


@app.websocket("/v1/discussions/{discussion_id}/stream")
async def discussion_stream(websocket: WebSocket, discussion_id: str):
    """
    WebSocket endpoint for real-time discussion updates.

    Streams messages and events for a discussion session in real-time.

    Args:
        websocket: WebSocket connection
        discussion_id: Discussion session ID
    """
    context = await get_context()

    # Verify discussion exists
    session = await context.get_session(discussion_id)
    if not session:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Connect WebSocket
    await ws_manager.connect(discussion_id, websocket)

    try:
        # Send initial state
        messages = await context.get_history(discussion_id)
        await websocket.send_json({
            "type": "init",
            "data": {
                "session": session.model_dump(mode="json"),
                "messages": [m.model_dump(mode="json") for m in messages]
            }
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_json()

                # Handle ping/pong
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                # Handle client messages (optional)
                # Could add support for sending messages via WebSocket here

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected from discussion {discussion_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error for {discussion_id}: {e}")
                break

    finally:
        ws_manager.disconnect(discussion_id, websocket)


@app.delete(
    "/v1/discussions/{discussion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Discussions"]
)
async def delete_discussion(discussion_id: str):
    """
    Delete a discussion session.

    Removes the session and all associated data from storage.

    Args:
        discussion_id: Discussion session ID

    Raises:
        HTTPException: If deletion fails
    """
    try:
        context = await get_context()
        success = await context.delete_session(discussion_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discussion {discussion_id} not found"
            )

        logger.info(f"Deleted discussion: {discussion_id}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete discussion {discussion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete discussion: {str(e)}"
        )


@app.get("/v1/discussions", response_model=List[str], tags=["Discussions"])
async def list_discussions():
    """
    List all active discussion IDs.

    Returns:
        List of discussion session IDs
    """
    try:
        context = await get_context()
        discussion_ids = await context.get_active_discussions()
        return discussion_ids

    except Exception as e:
        logger.error(f"Failed to list discussions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list discussions: {str(e)}"
        )


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
