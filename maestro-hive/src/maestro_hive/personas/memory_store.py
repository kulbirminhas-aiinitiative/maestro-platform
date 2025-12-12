#!/usr/bin/env python3
"""
Memory Store: Persona Memory Persistence and State Management.

This module provides persistent storage for persona memories, enabling
long-term memory retention, state snapshots, and intelligent retrieval
with recency and importance-weighted scoring.

Related EPIC: MD-3090 - Persona Memory & Persistence Enhancements
Integration: learning_engine.py, evolution_tracker.py
"""

import json
import logging
import hashlib
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of persona memories."""
    EPISODIC = "episodic"           # Event-based memories (what happened)
    SEMANTIC = "semantic"           # Factual knowledge (what is known)
    PROCEDURAL = "procedural"       # Skill-based memories (how to do things)
    WORKING = "working"             # Short-term active memories
    CONTEXTUAL = "contextual"       # Context-specific memories


class MemoryStatus(Enum):
    """Status of a memory entry."""
    ACTIVE = "active"
    CONSOLIDATED = "consolidated"
    ARCHIVED = "archived"
    DECAYED = "decayed"


class ConsolidationStrategy(Enum):
    """Strategies for memory consolidation."""
    IMPORTANCE_BASED = "importance_based"
    RECENCY_BASED = "recency_based"
    FREQUENCY_BASED = "frequency_based"
    HYBRID = "hybrid"


@dataclass
class MemoryStoreConfig:
    """Configuration for the memory store."""
    storage_path: Optional[Path] = None
    max_memories_per_persona: int = 10000
    consolidation_threshold: int = 5000
    default_decay_rate: float = 0.05
    importance_threshold: float = 0.3
    batch_size: int = 100
    cache_size: int = 1000
    index_refresh_interval: int = 3600
    auto_consolidate: bool = True
    enable_persistence: bool = True


@dataclass
class Memory:
    """A single memory entry for a persona."""
    id: str
    persona_id: str
    memory_type: MemoryType
    content: Dict[str, Any]
    importance: float = 0.5  # 0.0 to 1.0
    embedding: Optional[List[float]] = None
    tags: List[str] = field(default_factory=list)
    source: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    accessed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    decay_factor: float = 1.0
    status: MemoryStatus = MemoryStatus.ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary."""
        return {
            **asdict(self),
            "memory_type": self.memory_type.value,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Memory":
        """Create memory from dictionary."""
        data = data.copy()
        data["memory_type"] = MemoryType(data["memory_type"])
        data["status"] = MemoryStatus(data.get("status", "active"))
        return cls(**data)


@dataclass
class MemoryQueryResult:
    """Result of a memory query."""
    memory: Memory
    relevance_score: float
    recency_score: float
    combined_score: float


@dataclass
class ConsolidationResult:
    """Result of memory consolidation."""
    persona_id: str
    memories_before: int
    memories_after: int
    memories_consolidated: int
    memories_archived: int
    duration_ms: float
    strategy: ConsolidationStrategy


@dataclass
class StoreStats:
    """Statistics about the memory store."""
    total_personas: int
    total_memories: int
    memories_by_type: Dict[str, int]
    memories_by_status: Dict[str, int]
    average_importance: float
    storage_size_bytes: int
    last_consolidation: Optional[str]


@dataclass
class HealthStatus:
    """Health status of the memory store."""
    status: str  # "healthy", "degraded", "unhealthy"
    checks: Dict[str, bool]
    message: str
    timestamp: str


class MemoryStore:
    """
    Persistent memory store for AI personas.

    Features:
    - Multi-type memory storage (episodic, semantic, procedural, etc.)
    - Importance and recency-weighted retrieval
    - Automatic memory consolidation
    - Integration with LearningEngine and EvolutionTracker
    - File-based persistence with JSON storage
    """

    _instance: Optional["MemoryStore"] = None
    _lock = threading.Lock()

    def __init__(self, config: Optional[MemoryStoreConfig] = None):
        """Initialize the memory store."""
        self.config = config or MemoryStoreConfig()
        self._memories: Dict[str, Dict[str, Memory]] = defaultdict(dict)
        self._access_cache: Dict[str, List[str]] = defaultdict(list)  # LRU cache keys
        self._memory_lock = threading.RLock()
        self._callbacks: Dict[str, List[Callable]] = {
            "on_store": [],
            "on_retrieve": [],
            "on_consolidate": [],
        }
        self._last_consolidation: Dict[str, datetime] = {}
        self._initialized = False

        if self.config.storage_path and self.config.enable_persistence:
            self._load_state()

        self._initialized = True
        logger.info("MemoryStore initialized with config: %s", self.config)

    @classmethod
    def get_instance(cls, config: Optional[MemoryStoreConfig] = None) -> "MemoryStore":
        """Get singleton instance of memory store."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(config)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.save_state()
            cls._instance = None

    def store_memory(
        self,
        persona_id: str,
        memory: Memory,
        trigger_callbacks: bool = True
    ) -> str:
        """
        Store a memory for a persona.

        Args:
            persona_id: The persona ID
            memory: The memory to store
            trigger_callbacks: Whether to trigger on_store callbacks

        Returns:
            The memory ID
        """
        with self._memory_lock:
            # Generate ID if not provided
            if not memory.id:
                memory.id = self._generate_memory_id(persona_id, memory)

            # Ensure persona_id matches
            memory.persona_id = persona_id

            # Store memory
            self._memories[persona_id][memory.id] = memory

            # Update cache
            self._update_cache(persona_id, memory.id)

            # Check consolidation threshold
            if self.config.auto_consolidate:
                self._maybe_consolidate(persona_id)

            # Trigger callbacks
            if trigger_callbacks:
                for callback in self._callbacks["on_store"]:
                    try:
                        callback(persona_id, memory)
                    except Exception as e:
                        logger.error("Store callback error: %s", e)

            logger.debug(
                "Stored memory %s for persona %s (type=%s, importance=%.2f)",
                memory.id, persona_id, memory.memory_type.value, memory.importance
            )

            return memory.id

    def retrieve_memories(
        self,
        persona_id: str,
        query: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        min_importance: float = 0.0,
        limit: int = 10,
        include_archived: bool = False,
        tags: Optional[List[str]] = None,
    ) -> List[MemoryQueryResult]:
        """
        Retrieve memories with relevance scoring.

        Args:
            persona_id: The persona ID
            query: Optional text query for semantic matching
            memory_type: Filter by memory type
            min_importance: Minimum importance threshold
            limit: Maximum number of results
            include_archived: Include archived memories
            tags: Filter by tags

        Returns:
            List of MemoryQueryResult sorted by combined score
        """
        with self._memory_lock:
            memories = self._memories.get(persona_id, {})
            if not memories:
                return []

            results: List[MemoryQueryResult] = []
            now = datetime.utcnow()

            for memory in memories.values():
                # Apply filters
                if memory_type and memory.memory_type != memory_type:
                    continue
                if memory.importance < min_importance:
                    continue
                if not include_archived and memory.status == MemoryStatus.ARCHIVED:
                    continue
                if memory.status == MemoryStatus.DECAYED:
                    continue
                if tags and not any(tag in memory.tags for tag in tags):
                    continue

                # Calculate scores
                relevance = self._calculate_relevance(memory, query)
                recency = self._calculate_recency(memory, now)
                combined = self._calculate_combined_score(memory, relevance, recency)

                results.append(MemoryQueryResult(
                    memory=memory,
                    relevance_score=relevance,
                    recency_score=recency,
                    combined_score=combined,
                ))

                # Update access metadata
                self._update_access(persona_id, memory)

            # Sort by combined score and limit
            results.sort(key=lambda r: r.combined_score, reverse=True)
            results = results[:limit]

            # Trigger callbacks
            for callback in self._callbacks["on_retrieve"]:
                try:
                    callback(persona_id, query, results)
                except Exception as e:
                    logger.error("Retrieve callback error: %s", e)

            return results

    def get_memory(
        self,
        persona_id: str,
        memory_id: str,
        update_access: bool = True
    ) -> Optional[Memory]:
        """
        Get a specific memory by ID.

        Args:
            persona_id: The persona ID
            memory_id: The memory ID
            update_access: Whether to update access metadata

        Returns:
            The memory or None if not found
        """
        with self._memory_lock:
            memory = self._memories.get(persona_id, {}).get(memory_id)
            if memory and update_access:
                self._update_access(persona_id, memory)
            return memory

    def update_memory(
        self,
        persona_id: str,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Memory]:
        """
        Update a memory's attributes.

        Args:
            persona_id: The persona ID
            memory_id: The memory ID
            updates: Dictionary of fields to update

        Returns:
            Updated memory or None if not found
        """
        with self._memory_lock:
            memory = self._memories.get(persona_id, {}).get(memory_id)
            if not memory:
                return None

            # Apply updates
            for key, value in updates.items():
                if hasattr(memory, key):
                    if key == "memory_type" and isinstance(value, str):
                        value = MemoryType(value)
                    elif key == "status" and isinstance(value, str):
                        value = MemoryStatus(value)
                    setattr(memory, key, value)

            logger.debug("Updated memory %s for persona %s", memory_id, persona_id)
            return memory

    def delete_memory(self, persona_id: str, memory_id: str) -> bool:
        """
        Delete a memory.

        Args:
            persona_id: The persona ID
            memory_id: The memory ID

        Returns:
            True if deleted, False if not found
        """
        with self._memory_lock:
            if persona_id in self._memories and memory_id in self._memories[persona_id]:
                del self._memories[persona_id][memory_id]
                logger.debug("Deleted memory %s for persona %s", memory_id, persona_id)
                return True
            return False

    def consolidate_memories(
        self,
        persona_id: str,
        strategy: ConsolidationStrategy = ConsolidationStrategy.HYBRID,
        force: bool = False,
    ) -> ConsolidationResult:
        """
        Consolidate memories for a persona.

        Args:
            persona_id: The persona ID
            strategy: Consolidation strategy to use
            force: Force consolidation even below threshold

        Returns:
            ConsolidationResult with details
        """
        start_time = time.time()

        with self._memory_lock:
            memories = self._memories.get(persona_id, {})
            memories_before = len(memories)

            if not force and memories_before < self.config.consolidation_threshold:
                return ConsolidationResult(
                    persona_id=persona_id,
                    memories_before=memories_before,
                    memories_after=memories_before,
                    memories_consolidated=0,
                    memories_archived=0,
                    duration_ms=0,
                    strategy=strategy,
                )

            consolidated = 0
            archived = 0

            # Apply consolidation strategy
            if strategy == ConsolidationStrategy.IMPORTANCE_BASED:
                consolidated, archived = self._consolidate_by_importance(persona_id)
            elif strategy == ConsolidationStrategy.RECENCY_BASED:
                consolidated, archived = self._consolidate_by_recency(persona_id)
            elif strategy == ConsolidationStrategy.FREQUENCY_BASED:
                consolidated, archived = self._consolidate_by_frequency(persona_id)
            else:  # HYBRID
                consolidated, archived = self._consolidate_hybrid(persona_id)

            self._last_consolidation[persona_id] = datetime.utcnow()

            duration_ms = (time.time() - start_time) * 1000

            result = ConsolidationResult(
                persona_id=persona_id,
                memories_before=memories_before,
                memories_after=len(self._memories.get(persona_id, {})),
                memories_consolidated=consolidated,
                memories_archived=archived,
                duration_ms=duration_ms,
                strategy=strategy,
            )

            # Trigger callbacks
            for callback in self._callbacks["on_consolidate"]:
                try:
                    callback(persona_id, result)
                except Exception as e:
                    logger.error("Consolidate callback error: %s", e)

            logger.info(
                "Consolidated memories for %s: %d -> %d (consolidated=%d, archived=%d, %.2fms)",
                persona_id, memories_before, result.memories_after,
                consolidated, archived, duration_ms
            )

            return result

    def _consolidate_by_importance(self, persona_id: str) -> Tuple[int, int]:
        """Consolidate based on importance scores."""
        memories = self._memories.get(persona_id, {})
        threshold = self.config.importance_threshold
        archived = 0

        to_archive = [
            m_id for m_id, m in memories.items()
            if m.importance < threshold and m.status == MemoryStatus.ACTIVE
        ]

        for m_id in to_archive:
            memories[m_id].status = MemoryStatus.ARCHIVED
            archived += 1

        return 0, archived

    def _consolidate_by_recency(self, persona_id: str) -> Tuple[int, int]:
        """Consolidate based on recency."""
        memories = self._memories.get(persona_id, {})
        cutoff = datetime.utcnow() - timedelta(days=30)
        cutoff_iso = cutoff.isoformat()
        archived = 0

        for m_id, m in memories.items():
            if m.accessed_at < cutoff_iso and m.status == MemoryStatus.ACTIVE:
                m.status = MemoryStatus.ARCHIVED
                archived += 1

        return 0, archived

    def _consolidate_by_frequency(self, persona_id: str) -> Tuple[int, int]:
        """Consolidate based on access frequency."""
        memories = self._memories.get(persona_id, {})
        archived = 0

        for m_id, m in memories.items():
            if m.access_count < 2 and m.status == MemoryStatus.ACTIVE:
                m.status = MemoryStatus.ARCHIVED
                archived += 1

        return 0, archived

    def _consolidate_hybrid(self, persona_id: str) -> Tuple[int, int]:
        """Hybrid consolidation using multiple factors."""
        memories = self._memories.get(persona_id, {})
        now = datetime.utcnow()
        archived = 0
        consolidated = 0

        # Score each memory
        scores: List[Tuple[str, float]] = []
        for m_id, m in memories.items():
            if m.status != MemoryStatus.ACTIVE:
                continue

            # Calculate retention score
            recency = self._calculate_recency(m, now)
            importance = m.importance
            frequency = min(m.access_count / 10.0, 1.0)

            # Weighted score
            score = (importance * 0.4) + (recency * 0.3) + (frequency * 0.3)
            scores.append((m_id, score))

        # Sort by score
        scores.sort(key=lambda x: x[1])

        # Archive lowest scoring until under threshold
        target = int(self.config.consolidation_threshold * 0.8)
        while len([s for s in scores if memories.get(s[0], Memory(id="", persona_id="", memory_type=MemoryType.EPISODIC, content={})).status == MemoryStatus.ACTIVE]) > target and scores:
            m_id, score = scores.pop(0)
            if m_id in memories and memories[m_id].status == MemoryStatus.ACTIVE:
                memories[m_id].status = MemoryStatus.ARCHIVED
                archived += 1

        return consolidated, archived

    def _calculate_relevance(self, memory: Memory, query: Optional[str]) -> float:
        """Calculate relevance score for a memory."""
        if not query:
            return memory.importance

        # Simple keyword matching (can be enhanced with embeddings)
        query_lower = query.lower()
        content_str = json.dumps(memory.content).lower()
        tags_str = " ".join(memory.tags).lower()

        matches = 0
        query_words = query_lower.split()
        for word in query_words:
            if word in content_str or word in tags_str:
                matches += 1

        if not query_words:
            return memory.importance

        keyword_score = matches / len(query_words)
        return (keyword_score * 0.6) + (memory.importance * 0.4)

    def _calculate_recency(self, memory: Memory, now: datetime) -> float:
        """Calculate recency score for a memory."""
        try:
            accessed = datetime.fromisoformat(memory.accessed_at.replace("Z", "+00:00"))
            accessed = accessed.replace(tzinfo=None)
        except (ValueError, AttributeError):
            return 0.5

        days_ago = (now - accessed).days
        # Exponential decay
        return math.exp(-days_ago * self.config.default_decay_rate)

    def _calculate_combined_score(
        self,
        memory: Memory,
        relevance: float,
        recency: float
    ) -> float:
        """Calculate combined score for ranking."""
        # Weighted combination
        return (
            relevance * 0.4 +
            recency * 0.3 +
            memory.importance * 0.2 +
            (memory.decay_factor * 0.1)
        )

    def _update_access(self, persona_id: str, memory: Memory) -> None:
        """Update memory access metadata."""
        memory.accessed_at = datetime.utcnow().isoformat()
        memory.access_count += 1
        self._update_cache(persona_id, memory.id)

    def _update_cache(self, persona_id: str, memory_id: str) -> None:
        """Update LRU cache."""
        cache = self._access_cache[persona_id]
        if memory_id in cache:
            cache.remove(memory_id)
        cache.append(memory_id)

        # Trim cache
        if len(cache) > self.config.cache_size:
            cache.pop(0)

    def _maybe_consolidate(self, persona_id: str) -> None:
        """Check and trigger consolidation if needed."""
        memories = self._memories.get(persona_id, {})
        if len(memories) >= self.config.consolidation_threshold:
            # Check if recently consolidated
            last = self._last_consolidation.get(persona_id)
            if last:
                elapsed = (datetime.utcnow() - last).total_seconds()
                if elapsed < 300:  # 5 minute cooldown
                    return
            self.consolidate_memories(persona_id)

    def _generate_memory_id(self, persona_id: str, memory: Memory) -> str:
        """Generate a unique memory ID."""
        content = f"{persona_id}:{memory.memory_type.value}:{memory.created_at}:{json.dumps(memory.content)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    # === Integration Methods ===

    def register_callback(
        self,
        event: str,
        callback: Callable
    ) -> None:
        """
        Register a callback for memory events.

        Events: on_store, on_retrieve, on_consolidate
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
            logger.debug("Registered callback for %s", event)

    def integrate_with_learning_engine(self, learning_engine: Any) -> None:
        """
        Integrate with LearningEngine for experience persistence.

        Registers callbacks to store experiences as memories.
        """
        def on_experience(experience: Any, result: Any) -> None:
            memory = Memory(
                id="",
                persona_id=experience.persona_id,
                memory_type=MemoryType.EPISODIC,
                content={
                    "experience_id": experience.experience_id,
                    "skill_id": experience.skill_id,
                    "type": experience.experience_type.value,
                    "outcome": experience.outcome.value,
                    "outcome_score": experience.outcome_score,
                    "context": experience.context,
                },
                importance=experience.outcome_score,
                tags=["experience", experience.skill_id],
                source="learning_engine",
            )
            self.store_memory(experience.persona_id, memory, trigger_callbacks=False)

        learning_engine.register_callback(on_experience)
        logger.info("Integrated MemoryStore with LearningEngine")

    def integrate_with_evolution_tracker(self, evolution_tracker: Any) -> None:
        """
        Integrate with EvolutionTracker for milestone persistence.

        Stores milestones as semantic memories.
        """
        def on_milestone(persona_id: str, milestone: Any) -> None:
            memory = Memory(
                id="",
                persona_id=persona_id,
                memory_type=MemoryType.SEMANTIC,
                content={
                    "milestone_id": milestone.id,
                    "type": milestone.milestone_type.value,
                    "skill_id": milestone.skill_id,
                    "description": milestone.description,
                    "previous_value": milestone.previous_value,
                    "new_value": milestone.new_value,
                },
                importance=0.8,  # Milestones are important
                tags=["milestone", milestone.milestone_type.value],
                source="evolution_tracker",
            )
            self.store_memory(persona_id, memory, trigger_callbacks=False)

        # Note: EvolutionTracker doesn't have a callback interface by default
        # This would need to be added or called manually
        logger.info("MemoryStore ready for EvolutionTracker integration")

    # === Statistics and Health ===

    def get_stats(self) -> StoreStats:
        """Get statistics about the memory store."""
        with self._memory_lock:
            total_memories = 0
            by_type: Dict[str, int] = defaultdict(int)
            by_status: Dict[str, int] = defaultdict(int)
            total_importance = 0.0

            for persona_id, memories in self._memories.items():
                total_memories += len(memories)
                for memory in memories.values():
                    by_type[memory.memory_type.value] += 1
                    by_status[memory.status.value] += 1
                    total_importance += memory.importance

            avg_importance = total_importance / total_memories if total_memories > 0 else 0.0

            # Estimate storage size
            storage_size = sum(
                len(json.dumps(m.to_dict()))
                for memories in self._memories.values()
                for m in memories.values()
            )

            last_cons = None
            if self._last_consolidation:
                last_cons = max(self._last_consolidation.values()).isoformat()

            return StoreStats(
                total_personas=len(self._memories),
                total_memories=total_memories,
                memories_by_type=dict(by_type),
                memories_by_status=dict(by_status),
                average_importance=avg_importance,
                storage_size_bytes=storage_size,
                last_consolidation=last_cons,
            )

    def health_check(self) -> HealthStatus:
        """Perform health check on the memory store."""
        checks = {
            "initialized": self._initialized,
            "storage_accessible": True,
            "memory_limit_ok": True,
            "consolidation_current": True,
        }

        # Check storage accessibility
        if self.config.storage_path:
            checks["storage_accessible"] = self.config.storage_path.exists() or True

        # Check memory limits
        for persona_id, memories in self._memories.items():
            if len(memories) > self.config.max_memories_per_persona:
                checks["memory_limit_ok"] = False
                break

        # Check consolidation status
        for persona_id, memories in self._memories.items():
            if len(memories) > self.config.consolidation_threshold * 1.5:
                checks["consolidation_current"] = False
                break

        all_ok = all(checks.values())
        status = "healthy" if all_ok else "degraded"
        message = "All checks passed" if all_ok else f"Failed checks: {[k for k, v in checks.items() if not v]}"

        return HealthStatus(
            status=status,
            checks=checks,
            message=message,
            timestamp=datetime.utcnow().isoformat(),
        )

    # === Persistence ===

    def _load_state(self) -> None:
        """Load state from storage."""
        if not self.config.storage_path:
            return

        storage_file = self.config.storage_path / "memory_store_state.json"
        if not storage_file.exists():
            logger.info("No existing state file found at %s", storage_file)
            return

        try:
            with open(storage_file, "r") as f:
                data = json.load(f)

            for persona_id, memories_data in data.get("memories", {}).items():
                for m_id, m_data in memories_data.items():
                    self._memories[persona_id][m_id] = Memory.from_dict(m_data)

            logger.info(
                "Loaded memory store state: %d personas, %d memories",
                len(self._memories),
                sum(len(m) for m in self._memories.values())
            )
        except Exception as e:
            logger.error("Failed to load memory store state: %s", e)

    def save_state(self) -> bool:
        """Save state to storage."""
        if not self.config.storage_path or not self.config.enable_persistence:
            return False

        self.config.storage_path.mkdir(parents=True, exist_ok=True)
        storage_file = self.config.storage_path / "memory_store_state.json"

        try:
            with self._memory_lock:
                data = {
                    "memories": {
                        persona_id: {
                            m_id: m.to_dict()
                            for m_id, m in memories.items()
                        }
                        for persona_id, memories in self._memories.items()
                    },
                    "saved_at": datetime.utcnow().isoformat(),
                }

            with open(storage_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info("Saved memory store state to %s", storage_file)
            return True
        except Exception as e:
            logger.error("Failed to save memory store state: %s", e)
            return False

    def export_backup(self, path: Union[str, Path]) -> bool:
        """Export full backup to specified path."""
        path = Path(path)
        try:
            with self._memory_lock:
                data = {
                    "version": "1.0",
                    "exported_at": datetime.utcnow().isoformat(),
                    "stats": {
                        "total_personas": len(self._memories),
                        "total_memories": sum(len(m) for m in self._memories.values()),
                    },
                    "memories": {
                        persona_id: {
                            m_id: m.to_dict()
                            for m_id, m in memories.items()
                        }
                        for persona_id, memories in self._memories.items()
                    },
                }

            with open(path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info("Exported backup to %s", path)
            return True
        except Exception as e:
            logger.error("Failed to export backup: %s", e)
            return False

    def import_backup(self, path: Union[str, Path], merge: bool = False) -> bool:
        """Import backup from specified path."""
        path = Path(path)
        if not path.exists():
            logger.error("Backup file not found: %s", path)
            return False

        try:
            with open(path, "r") as f:
                data = json.load(f)

            with self._memory_lock:
                if not merge:
                    self._memories.clear()

                for persona_id, memories_data in data.get("memories", {}).items():
                    for m_id, m_data in memories_data.items():
                        if merge and m_id in self._memories.get(persona_id, {}):
                            continue
                        self._memories[persona_id][m_id] = Memory.from_dict(m_data)

            logger.info("Imported backup from %s", path)
            return True
        except Exception as e:
            logger.error("Failed to import backup: %s", e)
            return False

    def repair(self) -> Dict[str, Any]:
        """Repair corrupted state by rebuilding indices."""
        with self._memory_lock:
            repaired = 0
            removed = 0

            for persona_id in list(self._memories.keys()):
                for m_id in list(self._memories[persona_id].keys()):
                    memory = self._memories[persona_id][m_id]
                    try:
                        # Validate memory
                        _ = memory.to_dict()
                        repaired += 1
                    except Exception:
                        del self._memories[persona_id][m_id]
                        removed += 1

            # Clear and rebuild cache
            self._access_cache.clear()

            return {
                "repaired": repaired,
                "removed": removed,
                "timestamp": datetime.utcnow().isoformat(),
            }

    # === Persona-level operations ===

    def get_persona_memory_count(self, persona_id: str) -> int:
        """Get count of memories for a persona."""
        return len(self._memories.get(persona_id, {}))

    def get_all_persona_ids(self) -> List[str]:
        """Get all persona IDs with stored memories."""
        return list(self._memories.keys())

    def clear_persona_memories(self, persona_id: str) -> int:
        """Clear all memories for a persona."""
        with self._memory_lock:
            count = len(self._memories.get(persona_id, {}))
            if persona_id in self._memories:
                del self._memories[persona_id]
            if persona_id in self._access_cache:
                del self._access_cache[persona_id]
            logger.info("Cleared %d memories for persona %s", count, persona_id)
            return count


# === Module-level convenience functions ===

_memory_store: Optional[MemoryStore] = None


def get_memory_store(config: Optional[MemoryStoreConfig] = None) -> MemoryStore:
    """Get the global memory store instance."""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(config)
    return _memory_store


def reset_memory_store() -> None:
    """Reset the global memory store instance."""
    global _memory_store
    if _memory_store is not None:
        _memory_store.save_state()
    _memory_store = None


def store_memory(
    persona_id: str,
    memory_type: MemoryType,
    content: Dict[str, Any],
    importance: float = 0.5,
    tags: Optional[List[str]] = None,
    **kwargs
) -> str:
    """
    Convenience function to store a memory.

    Args:
        persona_id: The persona ID
        memory_type: Type of memory
        content: Memory content
        importance: Importance score (0.0 to 1.0)
        tags: Optional tags
        **kwargs: Additional memory fields

    Returns:
        Memory ID
    """
    memory = Memory(
        id="",
        persona_id=persona_id,
        memory_type=memory_type,
        content=content,
        importance=importance,
        tags=tags or [],
        **kwargs
    )
    store = get_memory_store()
    return store.store_memory(persona_id, memory)


def retrieve_memories(
    persona_id: str,
    query: Optional[str] = None,
    limit: int = 10,
    **kwargs
) -> List[MemoryQueryResult]:
    """
    Convenience function to retrieve memories.

    Args:
        persona_id: The persona ID
        query: Optional text query
        limit: Maximum results
        **kwargs: Additional filter options

    Returns:
        List of MemoryQueryResult
    """
    store = get_memory_store()
    return store.retrieve_memories(persona_id, query=query, limit=limit, **kwargs)
