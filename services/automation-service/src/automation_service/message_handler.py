#!/usr/bin/env python3
"""
Maestro Automation Service - Redis Streams Message Handler
Handles async message processing for CARS using Redis Streams
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import redis.asyncio as redis

from automation_service.repair_orchestrator import RepairOrchestrator, RepairConfig
from automation_service.error_monitor import ErrorEvent, ErrorType, ErrorSeverity
from automation_service.config import Settings, get_redis_url, get_stream_names, get_consumer_groups

logger = logging.getLogger(__name__)


class MessageHandler:
    """Handles Redis Streams message processing for CARS"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client: Optional[redis.Redis] = None
        self.is_running = False

        # Stream configuration
        self.streams = get_stream_names()
        self.consumer_groups = get_consumer_groups()

        # Active orchestrators
        self.orchestrators: Dict[str, RepairOrchestrator] = {}

        # Statistics
        self.stats = {
            "total_jobs_processed": 0,
            "total_errors_detected": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "active_orchestrators": 0
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

            # Create consumer groups (ignore if already exist)
            await self._create_consumer_groups()

            # Start consumers
            self.is_running = True

            # Launch consumer tasks
            asyncio.create_task(self.consume_automation_jobs())
            asyncio.create_task(self.consume_healing_requests())
            asyncio.create_task(self.consume_error_events())

            logger.info("Message Handler started successfully")

        except Exception as e:
            logger.error(f"Failed to start Message Handler: {e}")
            raise

    async def stop(self):
        """Stop message handler and close connections"""
        self.is_running = False

        # Stop all orchestrators
        for orchestrator_id, orchestrator in self.orchestrators.items():
            try:
                await orchestrator.stop()
                logger.info(f"Stopped orchestrator: {orchestrator_id}")
            except Exception as e:
                logger.error(f"Error stopping orchestrator {orchestrator_id}: {e}")

        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    async def _create_consumer_groups(self):
        """Create consumer groups for all streams"""
        for stream_name in self.streams.values():
            for group_name in self.consumer_groups.values():
                try:
                    await self.redis_client.xgroup_create(
                        name=stream_name,
                        groupname=group_name,
                        id="0",
                        mkstream=True
                    )
                    logger.info(f"Created consumer group '{group_name}' for stream '{stream_name}'")
                except redis.ResponseError as e:
                    if "BUSYGROUP" in str(e):
                        logger.debug(f"Consumer group '{group_name}' already exists for '{stream_name}'")
                    else:
                        logger.warning(f"Error creating consumer group: {e}")

    async def consume_automation_jobs(self):
        """Consume jobs from automation:jobs stream"""
        stream_name = self.streams["automation_jobs"]
        group_name = self.consumer_groups["automation_workers"]
        consumer_name = self.settings.consumer_name

        logger.info(f"Starting automation jobs consumer: {group_name}/{consumer_name}")

        while self.is_running:
            try:
                # Read messages from stream
                messages = await self.redis_client.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: ">"},
                    count=10,
                    block=5000  # 5 second timeout
                )

                if messages:
                    for stream, message_list in messages:
                        for message_id, data in message_list:
                            try:
                                await self._process_automation_job(message_id, data)

                                # Acknowledge message
                                await self.redis_client.xack(stream_name, group_name, message_id)

                                self.stats["total_jobs_processed"] += 1

                            except Exception as e:
                                logger.error(f"Error processing job {message_id}: {e}")
                                # Don't ack - will be retried

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in automation jobs consumer: {e}")
                await asyncio.sleep(5)

        logger.info("Automation jobs consumer stopped")

    async def consume_healing_requests(self):
        """Consume healing requests from test_healing stream"""
        stream_name = self.streams["test_healing"]
        group_name = self.consumer_groups["healing_workers"]
        consumer_name = self.settings.consumer_name

        logger.info(f"Starting healing requests consumer: {group_name}/{consumer_name}")

        while self.is_running:
            try:
                messages = await self.redis_client.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: ">"},
                    count=10,
                    block=5000
                )

                if messages:
                    for stream, message_list in messages:
                        for message_id, data in message_list:
                            try:
                                await self._process_healing_request(message_id, data)
                                await self.redis_client.xack(stream_name, group_name, message_id)

                            except Exception as e:
                                logger.error(f"Error processing healing request {message_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in healing requests consumer: {e}")
                await asyncio.sleep(5)

        logger.info("Healing requests consumer stopped")

    async def consume_error_events(self):
        """Consume error events from error_monitoring stream"""
        stream_name = self.streams["error_monitoring"]
        group_name = self.consumer_groups["monitoring_workers"]
        consumer_name = self.settings.consumer_name

        logger.info(f"Starting error events consumer: {group_name}/{consumer_name}")

        while self.is_running:
            try:
                messages = await self.redis_client.xreadgroup(
                    groupname=group_name,
                    consumername=consumer_name,
                    streams={stream_name: ">"},
                    count=10,
                    block=5000
                )

                if messages:
                    for stream, message_list in messages:
                        for message_id, data in message_list:
                            try:
                                await self._process_error_event(message_id, data)
                                await self.redis_client.xack(stream_name, group_name, message_id)

                                self.stats["total_errors_detected"] += 1

                            except Exception as e:
                                logger.error(f"Error processing error event {message_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in error events consumer: {e}")
                await asyncio.sleep(5)

        logger.info("Error events consumer stopped")

    async def _process_automation_job(self, message_id: str, data: Dict[str, Any]):
        """Process an automation job message"""
        logger.info(f"Processing automation job: {message_id}")

        try:
            # Parse job data
            job_type = data.get("type", "unknown")
            payload = json.loads(data.get("payload", "{}"))

            if job_type == "start_monitoring":
                await self._handle_start_monitoring(payload)

            elif job_type == "stop_monitoring":
                await self._handle_stop_monitoring(payload)

            elif job_type == "heal_test_failure":
                await self._handle_heal_test_failure(payload)

            else:
                logger.warning(f"Unknown job type: {job_type}")

        except Exception as e:
            logger.error(f"Error processing automation job: {e}")
            raise

    async def _process_healing_request(self, message_id: str, data: Dict[str, Any]):
        """Process a healing request message"""
        logger.info(f"Processing healing request: {message_id}")

        try:
            payload = json.loads(data.get("payload", "{}"))
            await self._handle_heal_test_failure(payload)

        except Exception as e:
            logger.error(f"Error processing healing request: {e}")
            raise

    async def _process_error_event(self, message_id: str, data: Dict[str, Any]):
        """Process an error event message"""
        logger.debug(f"Processing error event: {message_id}")

        try:
            error_type = data.get("error_type")
            error_message = data.get("error_message")
            file_path = data.get("file_path")

            logger.info(f"Error detected: {error_type} in {file_path}: {error_message}")

            # TODO: Route to appropriate healing orchestrator

        except Exception as e:
            logger.error(f"Error processing error event: {e}")

    async def _handle_start_monitoring(self, payload: Dict[str, Any]):
        """Handle start monitoring request"""
        project_path = payload.get("project_path")
        config = payload.get("config", {})

        logger.info(f"Starting monitoring for: {project_path}")

        # Create repair config
        repair_config = RepairConfig(
            project_path=project_path,
            auto_fix=config.get("auto_fix", True),
            require_approval=config.get("require_approval", False),
            confidence_threshold=config.get("confidence_threshold", self.settings.default_confidence_threshold),
            auto_commit=config.get("auto_commit", False),
            create_pr=config.get("create_pr", False),
            max_concurrent_repairs=config.get("max_concurrent_repairs", self.settings.max_concurrent_repairs)
        )

        # Create orchestrator
        orchestrator = RepairOrchestrator(repair_config)
        self.orchestrators[orchestrator.orchestrator_id] = orchestrator

        # Start orchestrator in background
        asyncio.create_task(orchestrator.start())

        self.stats["active_orchestrators"] = len(self.orchestrators)

        # Publish status update
        await self._publish_status_update(orchestrator.orchestrator_id, "started")

    async def _handle_stop_monitoring(self, payload: Dict[str, Any]):
        """Handle stop monitoring request"""
        orchestrator_id = payload.get("orchestrator_id")

        logger.info(f"Stopping monitoring for: {orchestrator_id}")

        if orchestrator_id in self.orchestrators:
            orchestrator = self.orchestrators[orchestrator_id]
            await orchestrator.stop()
            del self.orchestrators[orchestrator_id]

            self.stats["active_orchestrators"] = len(self.orchestrators)

            # Publish status update
            await self._publish_status_update(orchestrator_id, "stopped")

    async def _handle_heal_test_failure(self, payload: Dict[str, Any]):
        """Handle heal test failure request"""
        logger.info("Handling heal test failure request")

        # TODO: Implement direct healing without orchestrator
        # For now, log the request
        logger.info(f"Heal request: {payload}")

    async def _publish_status_update(self, orchestrator_id: str, status: str):
        """Publish status update to results stream"""
        try:
            message = {
                "type": "status_update",
                "orchestrator_id": orchestrator_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }

            await self.redis_client.xadd(
                self.streams["results"],
                message
            )

            logger.debug(f"Published status update: {status} for {orchestrator_id}")

        except Exception as e:
            logger.error(f"Error publishing status update: {e}")

    async def publish_repair_result(self, orchestrator_id: str, result: Dict[str, Any]):
        """Publish repair result to results stream"""
        try:
            message = {
                "type": "repair_result",
                "orchestrator_id": orchestrator_id,
                "result": json.dumps(result),
                "timestamp": datetime.now().isoformat()
            }

            await self.redis_client.xadd(
                self.streams["results"],
                message
            )

            # Update stats
            if result.get("status") == "success":
                self.stats["successful_repairs"] += 1
            else:
                self.stats["failed_repairs"] += 1

            logger.debug(f"Published repair result for {orchestrator_id}")

        except Exception as e:
            logger.error(f"Error publishing repair result: {e}")

    async def get_statistics(self) -> Dict[str, Any]:
        """Get message handler statistics"""
        total_repairs = self.stats["successful_repairs"] + self.stats["failed_repairs"]
        success_rate = (
            self.stats["successful_repairs"] / total_repairs
            if total_repairs > 0
            else 0.0
        )

        return {
            "active_orchestrators": self.stats["active_orchestrators"],
            "total_jobs_processed": self.stats["total_jobs_processed"],
            "total_errors_detected": self.stats["total_errors_detected"],
            "successful_repairs": self.stats["successful_repairs"],
            "failed_repairs": self.stats["failed_repairs"],
            "success_rate": round(success_rate * 100, 2)
        }
