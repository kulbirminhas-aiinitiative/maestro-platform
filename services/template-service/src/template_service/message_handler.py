"""
Maestro Template Service - Redis Streams Message Handler

Handles asynchronous template operations via Redis Streams.
Consumes messages from template:requests stream and publishes results to template:results stream.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

import redis.asyncio as redis
from pydantic import BaseModel, Field

# Configure logging
logger = logging.getLogger(__name__)


class TemplateRequest(BaseModel):
    """Template operation request message"""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    template_id: Optional[str] = None
    operation: str  # retrieve, create, update, delete, search
    tenant_id: str
    user_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TemplateResult(BaseModel):
    """Template operation result message"""

    request_id: str
    template_id: Optional[str] = None
    status: str  # success, error
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TemplateUsageEvent(BaseModel):
    """Template usage tracking event"""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    template_id: str
    tenant_id: str
    user_id: str
    operation: str
    success: bool
    duration_ms: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TemplateMessageHandler:
    """
    Redis Streams message handler for template operations.

    Consumes messages from template:requests stream and processes them asynchronously.
    Publishes results to template:results stream and usage events to template:usage stream.
    """

    def __init__(
        self,
        redis_url: str,
        stream_requests: str = "maestro:streams:templates:requests",
        stream_results: str = "maestro:streams:templates:results",
        stream_usage: str = "maestro:streams:templates:usage",
        consumer_group: str = "maestro-template-workers",
        consumer_name: str = "worker-1"
    ):
        """
        Initialize message handler.

        Args:
            redis_url: Redis connection URL
            stream_requests: Stream name for incoming requests
            stream_results: Stream name for operation results
            stream_usage: Stream name for usage tracking
            consumer_group: Consumer group name
            consumer_name: Consumer name within group
        """
        self.redis_url = redis_url
        self.stream_requests = stream_requests
        self.stream_results = stream_results
        self.stream_usage = stream_usage
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name

        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False
        self._consumer_task: Optional[asyncio.Task] = None

        logger.info(
            f"Initialized TemplateMessageHandler: "
            f"group={consumer_group}, consumer={consumer_name}"
        )

    async def start(self):
        """Start the message handler and begin consuming messages."""
        try:
            # Connect to Redis
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                encoding="utf-8"
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis successfully")

            # Create consumer group if it doesn't exist
            await self._create_consumer_group()

            # Start consuming messages
            self.is_running = True
            self._consumer_task = asyncio.create_task(self._consume_requests())

            logger.info("TemplateMessageHandler started successfully")

        except Exception as e:
            logger.error(f"Failed to start TemplateMessageHandler: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the message handler gracefully."""
        logger.info("Stopping TemplateMessageHandler...")

        self.is_running = False

        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

        if self.redis_client:
            await self.redis_client.close()

        logger.info("TemplateMessageHandler stopped")

    async def _create_consumer_group(self):
        """Create consumer group for the requests stream if it doesn't exist."""
        try:
            await self.redis_client.xgroup_create(
                name=self.stream_requests,
                groupname=self.consumer_group,
                id="0",
                mkstream=True
            )
            logger.info(f"Created consumer group: {self.consumer_group}")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group already exists: {self.consumer_group}")
            else:
                raise

    async def _consume_requests(self):
        """Main consumer loop for processing template requests."""
        logger.info(f"Starting to consume from stream: {self.stream_requests}")

        while self.is_running:
            try:
                # Read messages from stream
                messages = await self.redis_client.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_requests: ">"},
                    count=5,
                    block=5000  # Block for 5 seconds
                )

                for stream_name, message_list in messages:
                    for message_id, data in message_list:
                        await self._process_request(message_id, data)

                        # Acknowledge message
                        await self.redis_client.xack(
                            self.stream_requests,
                            self.consumer_group,
                            message_id
                        )

            except asyncio.CancelledError:
                logger.info("Consumer task cancelled")
                break
            except Exception as e:
                logger.error(f"Error consuming messages: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

    async def _process_request(self, message_id: str, data: Dict[str, str]):
        """
        Process a template operation request.

        Args:
            message_id: Redis message ID
            data: Message data from stream
        """
        start_time = datetime.utcnow()

        try:
            # Parse request
            request_data = json.loads(data.get("data", "{}"))
            request = TemplateRequest(**request_data)

            logger.info(
                f"Processing request: id={request.request_id}, "
                f"operation={request.operation}, template_id={request.template_id}"
            )

            # Process based on operation type
            result = await self._execute_operation(request)

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Create result message
            result_message = TemplateResult(
                request_id=request.request_id,
                template_id=request.template_id,
                status="success",
                result=result,
                duration_ms=duration_ms
            )

            # Publish result
            await self._publish_result(result_message)

            # Track usage
            await self._track_usage(request, success=True, duration_ms=duration_ms)

            logger.info(
                f"Successfully processed request: id={request.request_id}, "
                f"duration={duration_ms}ms"
            )

        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)

            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            # Create error result
            error_result = TemplateResult(
                request_id=request.request_id if 'request' in locals() else "unknown",
                template_id=request.template_id if 'request' in locals() else None,
                status="error",
                error=str(e),
                duration_ms=duration_ms
            )

            # Publish error result
            await self._publish_result(error_result)

            # Track usage (failure)
            if 'request' in locals():
                await self._track_usage(request, success=False, duration_ms=duration_ms)

    async def _execute_operation(self, request: TemplateRequest) -> Dict[str, Any]:
        """
        Execute the requested template operation.

        Args:
            request: Template operation request

        Returns:
            Operation result data
        """
        operation = request.operation

        # TODO: Implement actual template operations
        # For now, return mock responses

        if operation == "retrieve":
            return {
                "template_id": request.template_id,
                "name": f"Template {request.template_id}",
                "category": "backend_developer",
                "version": "1.0.0"
            }

        elif operation == "search":
            return {
                "results": [
                    {
                        "template_id": "template-1",
                        "name": "Backend API Template",
                        "category": "backend_developer"
                    },
                    {
                        "template_id": "template-2",
                        "name": "Frontend Component Template",
                        "category": "frontend_developer"
                    }
                ],
                "total": 2
            }

        elif operation == "create":
            return {
                "template_id": str(uuid4()),
                "status": "created",
                "message": "Template created successfully"
            }

        elif operation == "update":
            return {
                "template_id": request.template_id,
                "status": "updated",
                "message": "Template updated successfully"
            }

        elif operation == "delete":
            return {
                "template_id": request.template_id,
                "status": "deleted",
                "message": "Template deleted successfully"
            }

        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _publish_result(self, result: TemplateResult):
        """
        Publish operation result to results stream.

        Args:
            result: Template operation result
        """
        try:
            await self.redis_client.xadd(
                name=self.stream_results,
                fields={
                    "data": result.model_dump_json()
                }
            )
            logger.debug(f"Published result for request: {result.request_id}")
        except Exception as e:
            logger.error(f"Failed to publish result: {e}", exc_info=True)

    async def _track_usage(
        self,
        request: TemplateRequest,
        success: bool,
        duration_ms: int
    ):
        """
        Track template usage event.

        Args:
            request: Original template request
            success: Whether operation succeeded
            duration_ms: Operation duration in milliseconds
        """
        try:
            usage_event = TemplateUsageEvent(
                template_id=request.template_id or "unknown",
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                operation=request.operation,
                success=success,
                duration_ms=duration_ms
            )

            await self.redis_client.xadd(
                name=self.stream_usage,
                fields={
                    "data": usage_event.model_dump_json()
                }
            )
            logger.debug(f"Tracked usage event: {usage_event.event_id}")
        except Exception as e:
            logger.error(f"Failed to track usage: {e}", exc_info=True)

    async def publish_request(self, request: TemplateRequest) -> str:
        """
        Publish a template operation request (for testing/manual use).

        Args:
            request: Template operation request

        Returns:
            Redis message ID
        """
        try:
            message_id = await self.redis_client.xadd(
                name=self.stream_requests,
                fields={
                    "data": request.model_dump_json()
                }
            )
            logger.info(f"Published request: {request.request_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish request: {e}", exc_info=True)
            raise


# Example usage
async def main():
    """Example usage of TemplateMessageHandler."""

    # Initialize handler
    handler = TemplateMessageHandler(
        redis_url="redis://localhost:6379/0",
        consumer_name="worker-example"
    )

    # Start handler
    await handler.start()

    try:
        # Publish a test request
        test_request = TemplateRequest(
            operation="search",
            tenant_id="tenant-123",
            user_id="user-456",
            parameters={"category": "backend_developer"}
        )

        await handler.publish_request(test_request)
        logger.info("Published test request")

        # Keep running
        await asyncio.sleep(30)

    finally:
        # Stop handler
        await handler.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    asyncio.run(main())
