#!/usr/bin/env python3
"""
Maestro K8s Execution Service - Redis Streams Message Handler
Handles async message processing for K8s execution requests
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import redis.asyncio as redis

from k8s_execution.engine import KubernetesExecutionEngine, EnvironmentSpec
from k8s_execution.config import Settings, get_redis_url, get_stream_names

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles Redis Streams message processing for K8s execution"""

    def __init__(self, settings: Settings, k8s_engine: KubernetesExecutionEngine):
        self.settings = settings
        self.k8s_engine = k8s_engine
        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False

        # Stream configuration
        self.streams = get_stream_names()
        self.consumer_group = settings.consumer_group_k8s
        self.consumer_name = settings.consumer_name

        # Statistics
        self.stats = {
            "total_jobs_processed": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "active_environments": 0
        }

        logger.info("Message Handler initialized")

    async def start(self):
        """Start message handler and consumers"""
        try:
            # Connect to Redis
            self.redis_client = await redis.from_url(
                get_redis_url(),
                encoding="utf-8",
                decode_responses=True
            )

            logger.info(f"Connected to Redis: {self.settings.redis_host}:{self.settings.redis_port}")

            # Create consumer groups
            await self._create_consumer_groups()

            # Start consumers
            self.is_running = True

            # Launch consumer tasks
            asyncio.create_task(self.consume_execution_jobs())
            asyncio.create_task(self.cleanup_expired_environments())

            logger.info("Message Handler started successfully")

        except Exception as e:
            logger.error(f"Failed to start Message Handler: {e}")
            raise

    async def stop(self):
        """Stop message handler and close connections"""
        self.is_running = False

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    async def _create_consumer_groups(self):
        """Create consumer groups for all streams"""
        for stream_name in self.streams.values():
            try:
                await self.redis_client.xgroup_create(
                    name=stream_name,
                    groupname=self.consumer_group,
                    id="0",
                    mkstream=True
                )
                logger.info(f"Created consumer group '{self.consumer_group}' for stream '{stream_name}'")
            except redis.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(f"Consumer group '{self.consumer_group}' already exists for '{stream_name}'")
                else:
                    logger.warning(f"Error creating consumer group: {e}")

    async def consume_execution_jobs(self):
        """Consume execution jobs from k8s:jobs stream"""
        stream_name = self.streams["k8s_jobs"]
        group_name = self.consumer_group
        consumer_name = self.consumer_name

        logger.info(f"Starting K8s execution jobs consumer: {group_name}/{consumer_name}")

        while self.is_running:
            try:
                # Read messages from stream
                messages = await self.redis_client.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: ">"},
                    count=5,
                    block=5000
                )

                if messages:
                    for stream, message_list in messages:
                        for message_id, data in message_list:
                            try:
                                await self._process_execution_job(message_id, data)

                                # Acknowledge message
                                await self.redis_client.xack(stream_name, group_name, message_id)

                                self.stats["total_jobs_processed"] += 1

                            except Exception as e:
                                logger.error(f"Error processing job {message_id}: {e}")
                                # Don't ack - will be retried

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in execution jobs consumer: {e}")
                await asyncio.sleep(5)

        logger.info("K8s execution jobs consumer stopped")

    async def cleanup_expired_environments(self):
        """Periodically cleanup expired environments"""
        logger.info("Starting environment cleanup task")

        while self.is_running:
            try:
                await asyncio.sleep(self.settings.k8s_cleanup_interval_minutes * 60)

                if self.k8s_engine and self.k8s_engine.k8s_available:
                    logger.info("Running cleanup of expired environments...")
                    await self.k8s_engine.cleanup_orphaned_environments()
                    logger.info("Cleanup complete")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

        logger.info("Environment cleanup task stopped")

    async def _process_execution_job(self, message_id: str, data: Dict[str, Any]):
        """Process a K8s execution job message"""
        logger.info(f"Processing K8s execution job: {message_id}")

        try:
            # Parse job data
            job_type = data.get("type", "execute_ephemeral_test")
            payload = json.loads(data.get("payload", "{}"))

            if job_type == "execute_ephemeral_test":
                await self._handle_execute_test(payload)

            elif job_type == "cleanup_environment":
                await self._handle_cleanup(payload)

            elif job_type == "get_logs":
                await self._handle_get_logs(payload)

            else:
                logger.warning(f"Unknown job type: {job_type}")

        except Exception as e:
            logger.error(f"Error processing execution job: {e}")
            raise

    async def _handle_execute_test(self, payload: Dict[str, Any]):
        """Handle execute test request"""
        logger.info("Handling execute test request")

        try:
            # Extract configuration
            environment_spec_data = payload.get("environment_spec", {})
            test_config = payload.get("test_config", {})

            # Create environment spec
            environment_spec = EnvironmentSpec(
                app_image=environment_spec_data.get("app_image"),
                app_port=environment_spec_data.get("app_port"),
                database_type=environment_spec_data.get("database_type"),
                redis_enabled=environment_spec_data.get("redis_enabled", False),
                replicas=environment_spec_data.get("replicas", 1),
                resources=environment_spec_data.get("resources"),
                env_vars=environment_spec_data.get("env_vars")
            )

            # Create ephemeral environment
            context = await self.k8s_engine.create_ephemeral_environment(
                environment_spec,
                test_config
            )

            # Execute tests
            result = await self.k8s_engine.execute_tests(context)

            # Publish result
            await self._publish_execution_result(context.execution_id, result)

            self.stats["successful_executions"] += 1

        except Exception as e:
            logger.error(f"Error executing test: {e}")
            self.stats["failed_executions"] += 1
            raise

    async def _handle_cleanup(self, payload: Dict[str, Any]):
        """Handle cleanup request"""
        execution_id = payload.get("execution_id")
        logger.info(f"Handling cleanup request for: {execution_id}")

        try:
            await self.k8s_engine.cleanup_environment(execution_id)
            logger.info(f"Cleanup complete for: {execution_id}")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def _handle_get_logs(self, payload: Dict[str, Any]):
        """Handle get logs request"""
        execution_id = payload.get("execution_id")
        logger.info(f"Handling get logs request for: {execution_id}")

        try:
            logs = await self.k8s_engine.get_test_logs(execution_id)

            # Publish logs
            await self._publish_logs(execution_id, logs)

        except Exception as e:
            logger.error(f"Error getting logs: {e}")

    async def _publish_execution_result(self, execution_id: str, result: Dict[str, Any]):
        """Publish execution result to results stream"""
        try:
            message = {
                "type": "execution_result",
                "execution_id": execution_id,
                "result": json.dumps(result),
                "timestamp": datetime.now().isoformat()
            }

            await self.redis_client.xadd(
                self.streams["k8s_results"],
                message
            )

            logger.debug(f"Published execution result for {execution_id}")

        except Exception as e:
            logger.error(f"Error publishing execution result: {e}")

    async def _publish_logs(self, execution_id: str, logs: str):
        """Publish logs to results stream"""
        try:
            message = {
                "type": "execution_logs",
                "execution_id": execution_id,
                "logs": logs,
                "timestamp": datetime.now().isoformat()
            }

            await self.redis_client.xadd(
                self.streams["k8s_results"],
                message
            )

            logger.debug(f"Published logs for {execution_id}")

        except Exception as e:
            logger.error(f"Error publishing logs: {e}")

    async def publish_status_update(self, execution_id: str, status: str, details: Dict[str, Any] = None):
        """Publish status update to status stream"""
        try:
            message = {
                "type": "status_update",
                "execution_id": execution_id,
                "status": status,
                "details": json.dumps(details or {}),
                "timestamp": datetime.now().isoformat()
            }

            await self.redis_client.xadd(
                self.streams["k8s_status"],
                message
            )

            logger.debug(f"Published status update: {status} for {execution_id}")

        except Exception as e:
            logger.error(f"Error publishing status update: {e}")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get message handler statistics"""
        self.stats["active_environments"] = len(self.k8s_engine.execution_contexts) if self.k8s_engine else 0

        return {
            "total_jobs_processed": self.stats["total_jobs_processed"],
            "successful_executions": self.stats["successful_executions"],
            "failed_executions": self.stats["failed_executions"],
            "active_environments": self.stats["active_environments"]
        }
