#!/usr/bin/env python3
"""
Skill Injector: Dynamic skill injection engine for AI personas.

This module provides the capability to dynamically inject skills into personas,
enhancing their functionality at runtime without requiring permanent changes.

Related EPIC: MD-3016 - AI Skill Injection Marketplace
"""

import json
import time
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import hashlib

from .skill_registry import (
    SkillRegistry,
    SkillDefinition,
    SkillStatus,
    SkillCompatibility,
    get_skill_registry
)
from .persona_registry import (
    PersonaRegistry,
    PersonaDefinition,
    get_persona_registry
)

logger = logging.getLogger(__name__)


class InjectionMode(Enum):
    """Mode of skill injection."""
    TEMPORARY = "temporary"  # Skill active only for current session
    PERSISTENT = "persistent"  # Skill remains until explicitly removed
    ONE_TIME = "one_time"  # Skill executes once and is removed


class InjectionPriority(Enum):
    """Priority level for injected skills."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class InjectionStatus(Enum):
    """Status of a skill injection."""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class InjectionConfig:
    """Configuration for skill injection."""
    mode: InjectionMode = InjectionMode.TEMPORARY
    priority: InjectionPriority = InjectionPriority.NORMAL
    timeout_seconds: Optional[int] = None  # Auto-expire after timeout
    max_executions: Optional[int] = None  # Limit number of executions
    parameters: Dict[str, Any] = field(default_factory=dict)
    context_override: Optional[str] = None  # Override skill context


@dataclass
class InjectionRecord:
    """Record of a skill injection."""
    id: str
    skill_id: str
    persona_id: str
    config: InjectionConfig
    status: InjectionStatus = InjectionStatus.PENDING
    execution_count: int = 0
    last_executed: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    expires_at: Optional[str] = None
    error_message: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if injection has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow().isoformat() > self.expires_at

    def can_execute(self) -> bool:
        """Check if injection can be executed."""
        if self.status not in (InjectionStatus.ACTIVE, InjectionStatus.PENDING):
            return False
        if self.is_expired():
            return False
        if self.config.max_executions and self.execution_count >= self.config.max_executions:
            return False
        return True


@dataclass
class InjectionResult:
    """Result of a skill injection or execution."""
    success: bool
    injection_id: str
    skill_id: str
    persona_id: str
    output: Optional[Any] = None
    execution_time_ms: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SkillInjector:
    """
    Dynamic skill injection engine.

    Provides the capability to inject skills into personas at runtime,
    manage active injections, and execute injected skills with proper
    context and parameter handling.
    """

    _instance: Optional['SkillInjector'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global injector access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        persona_registry: Optional[PersonaRegistry] = None
    ):
        """
        Initialize the skill injector.

        Args:
            skill_registry: SkillRegistry instance (optional, uses singleton)
            persona_registry: PersonaRegistry instance (optional, uses singleton)
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._skill_registry = skill_registry or get_skill_registry()
        self._persona_registry = persona_registry or get_persona_registry()
        self._injections: Dict[str, InjectionRecord] = {}
        self._persona_injections: Dict[str, Set[str]] = {}  # persona_id -> injection_ids
        self._injector_lock = threading.RLock()
        self._injection_counter = 0
        self._execution_hooks: Dict[str, List[Callable]] = {
            'pre_inject': [],
            'post_inject': [],
            'pre_execute': [],
            'post_execute': [],
            'on_error': []
        }
        self._initialized = True

        logger.info("SkillInjector initialized")

    def inject(
        self,
        skill_id: str,
        persona_id: str,
        config: Optional[InjectionConfig] = None
    ) -> InjectionResult:
        """
        Inject a skill into a persona.

        Args:
            skill_id: ID of skill to inject
            persona_id: ID of target persona
            config: Injection configuration

        Returns:
            InjectionResult indicating success or failure
        """
        start_time = time.time()
        config = config or InjectionConfig()

        with self._injector_lock:
            # Validate skill exists and is available
            skill = self._skill_registry.get(skill_id)
            if not skill:
                return InjectionResult(
                    success=False,
                    injection_id="",
                    skill_id=skill_id,
                    persona_id=persona_id,
                    error=f"Skill not found: {skill_id}"
                )

            if skill.status != SkillStatus.AVAILABLE:
                return InjectionResult(
                    success=False,
                    injection_id="",
                    skill_id=skill_id,
                    persona_id=persona_id,
                    error=f"Skill not available: {skill.status.value}"
                )

            # Validate persona exists
            persona = self._persona_registry.get(persona_id)
            if not persona:
                return InjectionResult(
                    success=False,
                    injection_id="",
                    skill_id=skill_id,
                    persona_id=persona_id,
                    error=f"Persona not found: {persona_id}"
                )

            # Check compatibility
            if not skill.is_compatible_with(persona.capabilities):
                return InjectionResult(
                    success=False,
                    injection_id="",
                    skill_id=skill_id,
                    persona_id=persona_id,
                    error="Skill not compatible with persona capabilities"
                )

            # Run pre-injection hooks
            self._run_hooks('pre_inject', skill, persona, config)

            # Create injection record
            self._injection_counter += 1
            injection_id = self._generate_injection_id(skill_id, persona_id)

            # Calculate expiration
            expires_at = None
            if config.timeout_seconds:
                from datetime import timedelta
                expires_at = (
                    datetime.utcnow() + timedelta(seconds=config.timeout_seconds)
                ).isoformat()

            record = InjectionRecord(
                id=injection_id,
                skill_id=skill_id,
                persona_id=persona_id,
                config=config,
                status=InjectionStatus.ACTIVE,
                expires_at=expires_at
            )

            # Store injection
            self._injections[injection_id] = record
            if persona_id not in self._persona_injections:
                self._persona_injections[persona_id] = set()
            self._persona_injections[persona_id].add(injection_id)

            # Run post-injection hooks
            self._run_hooks('post_inject', skill, persona, config)

            execution_time = (time.time() - start_time) * 1000

            logger.info(
                f"Skill injected: {skill_id} -> {persona_id} "
                f"(injection_id: {injection_id}, mode: {config.mode.value})"
            )

            return InjectionResult(
                success=True,
                injection_id=injection_id,
                skill_id=skill_id,
                persona_id=persona_id,
                execution_time_ms=execution_time,
                metadata={
                    'mode': config.mode.value,
                    'priority': config.priority.value,
                    'expires_at': expires_at
                }
            )

    def remove(self, injection_id: str) -> bool:
        """
        Remove an active injection.

        Args:
            injection_id: ID of injection to remove

        Returns:
            True if injection was found and removed
        """
        with self._injector_lock:
            if injection_id not in self._injections:
                return False

            record = self._injections.pop(injection_id)
            if record.persona_id in self._persona_injections:
                self._persona_injections[record.persona_id].discard(injection_id)

            logger.info(f"Injection removed: {injection_id}")
            return True

    def execute(
        self,
        injection_id: str,
        inputs: Dict[str, Any],
        executor: Optional[Callable] = None
    ) -> InjectionResult:
        """
        Execute an injected skill.

        Args:
            injection_id: ID of injection to execute
            inputs: Input parameters for the skill
            executor: Optional custom executor function

        Returns:
            InjectionResult with execution output
        """
        start_time = time.time()

        with self._injector_lock:
            # Get injection record
            record = self._injections.get(injection_id)
            if not record:
                return InjectionResult(
                    success=False,
                    injection_id=injection_id,
                    skill_id="",
                    persona_id="",
                    error=f"Injection not found: {injection_id}"
                )

            if not record.can_execute():
                reason = "expired" if record.is_expired() else f"status: {record.status.value}"
                return InjectionResult(
                    success=False,
                    injection_id=injection_id,
                    skill_id=record.skill_id,
                    persona_id=record.persona_id,
                    error=f"Cannot execute injection: {reason}"
                )

            # Get skill definition
            skill = self._skill_registry.get(record.skill_id)
            if not skill:
                return InjectionResult(
                    success=False,
                    injection_id=injection_id,
                    skill_id=record.skill_id,
                    persona_id=record.persona_id,
                    error=f"Skill no longer available: {record.skill_id}"
                )

            # Merge parameters
            merged_params = {**record.config.parameters, **inputs}

            # Run pre-execution hooks
            self._run_hooks('pre_execute', skill, merged_params)

            try:
                # Build prompt from template
                prompt = self._build_prompt(skill, merged_params)

                # Execute skill
                if executor:
                    output = executor(prompt, skill, merged_params)
                else:
                    # Default execution - return prepared prompt
                    output = {
                        'prompt': prompt,
                        'skill': skill.name,
                        'inputs': merged_params
                    }

                # Update record
                record.execution_count += 1
                record.last_executed = datetime.utcnow().isoformat()

                # Handle one-time mode
                if record.config.mode == InjectionMode.ONE_TIME:
                    record.status = InjectionStatus.COMPLETED

                # Check max executions
                if (record.config.max_executions and
                        record.execution_count >= record.config.max_executions):
                    record.status = InjectionStatus.COMPLETED

                execution_time = (time.time() - start_time) * 1000

                # Record metrics
                self._skill_registry.record_injection(
                    record.skill_id, True, execution_time
                )

                # Run post-execution hooks
                self._run_hooks('post_execute', skill, output)

                return InjectionResult(
                    success=True,
                    injection_id=injection_id,
                    skill_id=record.skill_id,
                    persona_id=record.persona_id,
                    output=output,
                    execution_time_ms=execution_time,
                    metadata={
                        'execution_count': record.execution_count,
                        'status': record.status.value
                    }
                )

            except Exception as e:
                execution_time = (time.time() - start_time) * 1000
                error_msg = str(e)

                # Record failure
                record.error_message = error_msg
                self._skill_registry.record_injection(
                    record.skill_id, False, execution_time
                )

                # Run error hooks
                self._run_hooks('on_error', skill, e)

                logger.error(f"Skill execution failed: {error_msg}")

                return InjectionResult(
                    success=False,
                    injection_id=injection_id,
                    skill_id=record.skill_id,
                    persona_id=record.persona_id,
                    error=error_msg,
                    execution_time_ms=execution_time
                )

    def get_persona_skills(self, persona_id: str) -> List[Dict[str, Any]]:
        """
        Get all skills currently injected into a persona.

        Args:
            persona_id: ID of persona

        Returns:
            List of active skill injection info
        """
        with self._injector_lock:
            injection_ids = self._persona_injections.get(persona_id, set())
            skills = []

            for inj_id in injection_ids:
                record = self._injections.get(inj_id)
                if record and record.status == InjectionStatus.ACTIVE:
                    skill = self._skill_registry.get(record.skill_id)
                    if skill:
                        skills.append({
                            'injection_id': inj_id,
                            'skill_id': skill.id,
                            'skill_name': skill.name,
                            'category': skill.category.value,
                            'mode': record.config.mode.value,
                            'priority': record.config.priority.value,
                            'execution_count': record.execution_count,
                            'expires_at': record.expires_at
                        })

            # Sort by priority (highest first)
            skills.sort(key=lambda s: s['priority'], reverse=True)
            return skills

    def get_injection(self, injection_id: str) -> Optional[InjectionRecord]:
        """
        Get an injection record by ID.

        Args:
            injection_id: ID of injection

        Returns:
            InjectionRecord or None
        """
        with self._injector_lock:
            return self._injections.get(injection_id)

    def pause_injection(self, injection_id: str) -> bool:
        """
        Pause an active injection.

        Args:
            injection_id: ID of injection to pause

        Returns:
            True if successfully paused
        """
        with self._injector_lock:
            record = self._injections.get(injection_id)
            if not record or record.status != InjectionStatus.ACTIVE:
                return False

            record.status = InjectionStatus.PAUSED
            logger.info(f"Injection paused: {injection_id}")
            return True

    def resume_injection(self, injection_id: str) -> bool:
        """
        Resume a paused injection.

        Args:
            injection_id: ID of injection to resume

        Returns:
            True if successfully resumed
        """
        with self._injector_lock:
            record = self._injections.get(injection_id)
            if not record or record.status != InjectionStatus.PAUSED:
                return False

            record.status = InjectionStatus.ACTIVE
            logger.info(f"Injection resumed: {injection_id}")
            return True

    def cleanup_expired(self) -> int:
        """
        Clean up expired injections.

        Returns:
            Number of injections cleaned up
        """
        with self._injector_lock:
            expired = [
                inj_id for inj_id, record in self._injections.items()
                if record.is_expired()
            ]

            for inj_id in expired:
                record = self._injections.pop(inj_id)
                record.status = InjectionStatus.EXPIRED
                if record.persona_id in self._persona_injections:
                    self._persona_injections[record.persona_id].discard(inj_id)

            if expired:
                logger.info(f"Cleaned up {len(expired)} expired injections")

            return len(expired)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get injector statistics.

        Returns:
            Dictionary with injector stats
        """
        with self._injector_lock:
            status_counts = {}
            for record in self._injections.values():
                status = record.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            return {
                'total_injections': len(self._injections),
                'personas_with_skills': len(self._persona_injections),
                'status_breakdown': status_counts,
                'total_executions': sum(
                    r.execution_count for r in self._injections.values()
                )
            }

    def register_hook(
        self,
        event: str,
        handler: Callable
    ) -> None:
        """
        Register an execution hook.

        Args:
            event: Event name (pre_inject, post_inject, etc.)
            handler: Handler function
        """
        if event in self._execution_hooks:
            self._execution_hooks[event].append(handler)

    def _generate_injection_id(self, skill_id: str, persona_id: str) -> str:
        """Generate a unique injection ID."""
        timestamp = datetime.utcnow().isoformat()
        content = f"{skill_id}:{persona_id}:{timestamp}:{self._injection_counter}"
        hash_part = hashlib.sha256(content.encode()).hexdigest()[:8]
        return f"inj_{hash_part}_{self._injection_counter}"

    def _build_prompt(
        self,
        skill: SkillDefinition,
        params: Dict[str, Any]
    ) -> str:
        """Build execution prompt from skill template."""
        prompt = skill.prompt_template

        # Simple template substitution
        for key, value in params.items():
            placeholder = f"{{{key}}}"
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, str(value))

        return prompt

    def _run_hooks(self, event: str, *args) -> None:
        """Run all handlers for an event."""
        for handler in self._execution_hooks.get(event, []):
            try:
                handler(*args)
            except Exception as e:
                logger.error(f"Hook error for {event}: {e}")


# Convenience function to get singleton instance
def get_skill_injector(**kwargs) -> SkillInjector:
    """Get the singleton SkillInjector instance."""
    return SkillInjector(**kwargs)


# Helper function for quick skill injection
def inject_skill(
    skill_id: str,
    persona_id: str,
    mode: InjectionMode = InjectionMode.TEMPORARY,
    **kwargs
) -> InjectionResult:
    """
    Convenience function to inject a skill into a persona.

    Args:
        skill_id: ID of skill to inject
        persona_id: ID of target persona
        mode: Injection mode
        **kwargs: Additional injection config parameters

    Returns:
        InjectionResult
    """
    injector = get_skill_injector()
    config = InjectionConfig(mode=mode, **kwargs)
    return injector.inject(skill_id, persona_id, config)
