#!/usr/bin/env python3
"""
Quality Fabric - Repair Orchestrator
Orchestrates continuous automated error detection and repair
"""

import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid

from .error_monitor import ErrorMonitor, ErrorEvent, ErrorType
# maestro_test_healer not yet implemented
# from maestro_test_healer import AutonomousTestHealer, HealingResult

logger = logging.getLogger(__name__)


class RepairStatus(str, Enum):
    """Repair operation status"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    HEALING = "healing"
    VALIDATING = "validating"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class RepairConfig:
    """Configuration for repair orchestrator"""
    project_path: str
    auto_fix: bool = True
    require_approval: bool = False
    confidence_threshold: float = 0.75
    auto_commit: bool = False
    create_pr: bool = False
    max_concurrent_repairs: int = 3
    monitor_intervals: Dict[str, int] = None


@dataclass
class RepairResult:
    """Result of a repair operation"""
    repair_id: str
    error_event: ErrorEvent
    status: RepairStatus
    healing_result: Optional[Any]  # HealingResult not yet implemented
    validation_passed: bool
    confidence_score: float
    execution_time: float
    fix_applied: bool
    commit_sha: Optional[str]
    pr_url: Optional[str]
    error_message: Optional[str]
    timestamp: str


class RepairOrchestrator:
    """Orchestrates continuous automated error detection and repair"""

    def __init__(self, config: RepairConfig):
        self.config = config
        self.orchestrator_id = str(uuid.uuid4())

        # Components
        self.error_monitor = ErrorMonitor(
            config.project_path,
            config=config.monitor_intervals or {}
        )
        self.test_healer = AutonomousTestHealer()

        # State
        self.is_running = False
        self.repair_queue: asyncio.Queue = asyncio.Queue()
        self.repair_history: List[RepairResult] = []
        self.active_repairs: Dict[str, RepairResult] = {}

        # Statistics
        self.stats = {
            "total_errors_detected": 0,
            "total_repairs_attempted": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "skipped_repairs": 0
        }

        logger.info(f"Repair Orchestrator initialized: {self.orchestrator_id}")

    async def start(self):
        """Start continuous auto-repair service"""
        if self.is_running:
            logger.warning("Repair orchestrator already running")
            return

        self.is_running = True
        logger.info(f"Starting Continuous Auto-Repair Service for: {self.config.project_path}")

        # Initialize healers
        await self.test_healer.initialize_healer()

        # Register error callback
        self.error_monitor.register_error_callback(self._on_error_detected)

        # Start tasks concurrently
        tasks = [
            self.error_monitor.start_monitoring(),
            self._process_repair_queue()
        ]

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Repair orchestrator cancelled")
        except Exception as e:
            logger.error(f"Repair orchestrator error: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """Stop auto-repair service"""
        self.is_running = False
        await self.error_monitor.stop_monitoring()
        logger.info("Stopped Continuous Auto-Repair Service")

    async def _on_error_detected(self, error: ErrorEvent):
        """Callback when error is detected"""
        self.stats["total_errors_detected"] += 1

        logger.info(f"Error detected: {error.error_type} in {error.file_path}")

        # Check if error is healable
        if not error.healable:
            logger.info(f"Error not healable, skipping: {error.error_id}")
            return

        # Check confidence threshold
        if error.confidence < self.config.confidence_threshold:
            logger.info(f"Error confidence {error.confidence} below threshold {self.config.confidence_threshold}, skipping")
            return

        # Add to repair queue
        await self.repair_queue.put(error)
        logger.info(f"Error added to repair queue: {error.error_id}")

    async def _process_repair_queue(self):
        """Process repair queue continuously"""
        logger.info("Repair queue processor started")

        while self.is_running:
            try:
                # Get error from queue (with timeout to check is_running)
                try:
                    error = await asyncio.wait_for(self.repair_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Check max concurrent repairs
                while len(self.active_repairs) >= self.config.max_concurrent_repairs:
                    await asyncio.sleep(1)

                # Process repair
                asyncio.create_task(self._repair_error(error))

            except Exception as e:
                logger.error(f"Error processing repair queue: {e}")

    async def _repair_error(self, error: ErrorEvent):
        """Repair a single error"""
        repair_id = str(uuid.uuid4())
        start_time = datetime.now()

        logger.info(f"Starting repair: {repair_id} for error: {error.error_id}")

        # Create repair result
        repair_result = RepairResult(
            repair_id=repair_id,
            error_event=error,
            status=RepairStatus.ANALYZING,
            healing_result=None,
            validation_passed=False,
            confidence_score=error.confidence,
            execution_time=0.0,
            fix_applied=False,
            commit_sha=None,
            pr_url=None,
            error_message=None,
            timestamp=datetime.now().isoformat()
        )

        self.active_repairs[repair_id] = repair_result
        self.stats["total_repairs_attempted"] += 1

        try:
            # Route to appropriate healer based on error type
            if error.error_type == ErrorType.TEST_FAILURE:
                await self._repair_test_failure(error, repair_result)
            elif error.error_type == ErrorType.TYPE_ERROR:
                await self._repair_type_error(error, repair_result)
            elif error.error_type == ErrorType.BUILD_ERROR:
                await self._repair_build_error(error, repair_result)
            elif error.error_type == ErrorType.LINT_ERROR:
                await self._repair_lint_error(error, repair_result)
            else:
                logger.warning(f"No healer for error type: {error.error_type}")
                repair_result.status = RepairStatus.SKIPPED
                self.stats["skipped_repairs"] += 1

        except Exception as e:
            logger.error(f"Repair failed: {e}")
            repair_result.status = RepairStatus.FAILED
            repair_result.error_message = str(e)
            self.stats["failed_repairs"] += 1

        finally:
            # Calculate execution time
            repair_result.execution_time = (datetime.now() - start_time).total_seconds()

            # Remove from active repairs
            del self.active_repairs[repair_id]

            # Add to history
            self.repair_history.append(repair_result)

            logger.info(f"Repair completed: {repair_id} - Status: {repair_result.status}")

    async def _repair_test_failure(self, error: ErrorEvent, repair_result: RepairResult):
        """Repair test failure using autonomous test healer"""
        repair_result.status = RepairStatus.HEALING

        # Read test file
        test_file = Path(self.config.project_path) / error.file_path
        if not test_file.exists():
            raise FileNotFoundError(f"Test file not found: {test_file}")

        test_code = test_file.read_text()

        # Prepare error details for healer
        error_details = {
            "error_message": error.error_message,
            "stack_trace": error.stack_trace,
            "context": error.context
        }

        # Heal the test
        healing_result = await self.test_healer.heal_failed_test(test_code, error_details)
        repair_result.healing_result = healing_result

        # Check if healing was successful
        if healing_result.success and healing_result.confidence_score >= self.config.confidence_threshold:
            # Apply fix if auto_fix is enabled
            if self.config.auto_fix:
                if await self._apply_fix(test_file, healing_result.healed_code):
                    repair_result.fix_applied = True

                    # Validate fix
                    repair_result.status = RepairStatus.VALIDATING
                    validation_passed = await self._validate_fix(error)
                    repair_result.validation_passed = validation_passed

                    if validation_passed:
                        repair_result.status = RepairStatus.SUCCESS
                        self.stats["successful_repairs"] += 1

                        # Auto-commit if enabled
                        if self.config.auto_commit:
                            commit_sha = await self._commit_fix(error, healing_result)
                            repair_result.commit_sha = commit_sha

                        logger.info(f"✓ Successfully repaired: {error.file_path}")
                    else:
                        # Rollback if validation failed
                        await self._rollback_fix(test_file, test_code)
                        repair_result.status = RepairStatus.FAILED
                        repair_result.error_message = "Validation failed"
                        self.stats["failed_repairs"] += 1
                else:
                    repair_result.status = RepairStatus.FAILED
                    repair_result.error_message = "Failed to apply fix"
                    self.stats["failed_repairs"] += 1
            else:
                # Auto-fix disabled, just report success
                repair_result.status = RepairStatus.SUCCESS
                self.stats["successful_repairs"] += 1
                logger.info(f"Fix generated but not applied (auto_fix=False): {error.file_path}")
        else:
            repair_result.status = RepairStatus.FAILED
            repair_result.error_message = "Healing confidence too low or failed"
            self.stats["failed_repairs"] += 1

    async def _repair_type_error(self, error: ErrorEvent, repair_result: RepairResult):
        """Repair TypeScript type error"""
        # TODO: Implement type error healing
        logger.info(f"Type error healing not yet implemented: {error.file_path}")
        repair_result.status = RepairStatus.SKIPPED
        self.stats["skipped_repairs"] += 1

    async def _repair_build_error(self, error: ErrorEvent, repair_result: RepairResult):
        """Repair build error"""
        # TODO: Implement build error healing
        logger.info(f"Build error healing not yet implemented")
        repair_result.status = RepairStatus.SKIPPED
        self.stats["skipped_repairs"] += 1

    async def _repair_lint_error(self, error: ErrorEvent, repair_result: RepairResult):
        """Repair lint error"""
        # TODO: Implement lint error healing
        logger.info(f"Lint error healing not yet implemented: {error.file_path}")
        repair_result.status = RepairStatus.SKIPPED
        self.stats["skipped_repairs"] += 1

    async def _apply_fix(self, file_path: Path, fixed_code: str) -> bool:
        """Apply fix to file"""
        try:
            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            file_path.rename(backup_path)

            # Write fixed code
            file_path.write_text(fixed_code)

            logger.info(f"Applied fix to: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply fix: {e}")
            # Restore backup if it exists
            if backup_path.exists():
                backup_path.rename(file_path)
            return False

    async def _rollback_fix(self, file_path: Path, original_code: str):
        """Rollback fix"""
        try:
            file_path.write_text(original_code)
            logger.info(f"Rolled back fix for: {file_path}")
        except Exception as e:
            logger.error(f"Failed to rollback: {e}")

    async def _validate_fix(self, error: ErrorEvent) -> bool:
        """Validate that fix resolves the error"""
        # Re-run the check that detected the error
        if error.error_type == ErrorType.TEST_FAILURE:
            return await self._validate_test_fix(error)
        elif error.error_type == ErrorType.TYPE_ERROR:
            return await self._validate_type_fix(error)
        else:
            return True  # Assume valid for now

    async def _validate_test_fix(self, error: ErrorEvent) -> bool:
        """Validate test fix by running the test"""
        try:
            # Run specific test file
            result = await asyncio.create_subprocess_exec(
                'npm', 'test', '--', error.file_path,
                cwd=self.config.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await asyncio.wait_for(result.wait(), timeout=60)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return False

    async def _validate_type_fix(self, error: ErrorEvent) -> bool:
        """Validate type fix by running TypeScript compiler"""
        try:
            result = await asyncio.create_subprocess_exec(
                'npx', 'tsc', '--noEmit',
                cwd=self.config.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await asyncio.wait_for(result.wait(), timeout=60)
            return result.returncode == 0

        except Exception as e:
            logger.error(f"Type validation failed: {e}")
            return False

    async def _commit_fix(self, error: ErrorEvent, healing_result: Any) -> Optional[str]:
        """Commit the fix"""
        try:
            # Git add
            await asyncio.create_subprocess_exec(
                'git', 'add', error.file_path,
                cwd=self.config.project_path
            )

            # Git commit
            commit_message = f"Auto-fix: {error.error_type.value} in {error.file_path}\n\n"
            commit_message += f"Confidence: {healing_result.confidence_score:.2%}\n"
            commit_message += f"Strategy: {healing_result.strategy_used.value}\n\n"
            commit_message += "🤖 Generated by Quality Fabric CARS"

            result = await asyncio.create_subprocess_exec(
                'git', 'commit', '-m', commit_message,
                cwd=self.config.project_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await result.wait()

            if result.returncode == 0:
                logger.info(f"Committed fix for: {error.file_path}")
                return "auto-fix-commit"  # TODO: Get actual commit SHA
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to commit fix: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status"""
        return {
            "orchestrator_id": self.orchestrator_id,
            "is_running": self.is_running,
            "project_path": self.config.project_path,
            "active_repairs": len(self.active_repairs),
            "queue_size": self.repair_queue.qsize(),
            "statistics": self.stats,
            "config": {
                "auto_fix": self.config.auto_fix,
                "require_approval": self.config.require_approval,
                "confidence_threshold": self.config.confidence_threshold,
                "auto_commit": self.config.auto_commit
            }
        }

    def get_repair_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent repair history"""
        return [asdict(r) for r in self.repair_history[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        """Get repair statistics"""
        total = self.stats["total_repairs_attempted"]
        success_rate = (self.stats["successful_repairs"] / total * 100) if total > 0 else 0

        return {
            **self.stats,
            "success_rate": f"{success_rate:.1f}%",
            "error_stats": self.error_monitor.get_error_stats()
        }