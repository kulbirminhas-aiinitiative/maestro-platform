#!/usr/bin/env python3
"""
Tests for TraitManager module.

Related EPIC: MD-3018 - Persona Trait Evolution & Guidance
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime

from maestro_hive.personas.trait_manager import (
    TraitManager,
    Trait,
    TraitCategory,
    TraitStatus,
    TraitMetrics,
    TraitEvent,
    TraitValidationError,
    TraitNotFoundError,
    get_trait_manager
)


class TestTraitMetrics:
    """Tests for TraitMetrics dataclass."""

    def test_record_practice_success(self):
        """Test recording successful practice."""
        metrics = TraitMetrics()
        metrics.record_practice(success=True, duration_hours=2.0, new_level=0.6)

        assert metrics.practice_count == 1
        assert metrics.success_count == 1
        assert metrics.failure_count == 0
        assert metrics.total_practice_time_hours == 2.0
        assert metrics.last_practice is not None
        assert len(metrics.level_history) == 1

    def test_record_practice_failure(self):
        """Test recording failed practice."""
        metrics = TraitMetrics()
        metrics.record_practice(success=False, duration_hours=1.5, new_level=0.5)

        assert metrics.practice_count == 1
        assert metrics.success_count == 0
        assert metrics.failure_count == 1

    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = TraitMetrics()
        metrics.record_practice(success=True, duration_hours=1.0, new_level=0.6)
        metrics.record_practice(success=True, duration_hours=1.0, new_level=0.65)
        metrics.record_practice(success=False, duration_hours=1.0, new_level=0.63)
        metrics.record_practice(success=True, duration_hours=1.0, new_level=0.68)

        assert metrics.success_rate == 0.75

    def test_success_rate_no_practice(self):
        """Test success rate with no practice."""
        metrics = TraitMetrics()
        assert metrics.success_rate == 0.0

    def test_level_history_limit(self):
        """Test that level history is limited to 100 entries."""
        metrics = TraitMetrics()
        for i in range(150):
            metrics.record_practice(success=True, duration_hours=0.5, new_level=0.5 + i * 0.001)

        assert len(metrics.level_history) == 100


class TestTrait:
    """Tests for Trait dataclass."""

    def test_trait_creation(self):
        """Test basic trait creation."""
        trait = Trait(
            id="trait_001",
            name="Python",
            description="Python programming skills",
            category=TraitCategory.TECHNICAL
        )

        assert trait.id == "trait_001"
        assert trait.name == "Python"
        assert trait.level == 0.5  # Default
        assert trait.status == TraitStatus.ACTIVE
        assert trait.created_at is not None

    def test_trait_validation_empty_id(self):
        """Test validation rejects empty ID."""
        with pytest.raises(TraitValidationError, match="ID cannot be empty"):
            Trait(id="", name="Test", description="Test", category=TraitCategory.TECHNICAL)

    def test_trait_validation_empty_name(self):
        """Test validation rejects empty name."""
        with pytest.raises(TraitValidationError, match="name cannot be empty"):
            Trait(id="t1", name="", description="Test", category=TraitCategory.TECHNICAL)

    def test_trait_validation_invalid_level(self):
        """Test validation rejects invalid level."""
        with pytest.raises(TraitValidationError, match="level must be between"):
            Trait(id="t1", name="Test", description="Test", category=TraitCategory.TECHNICAL, level=1.5)

    def test_trait_validation_min_max_level(self):
        """Test validation rejects min > max level."""
        with pytest.raises(TraitValidationError, match="min_level cannot be greater"):
            Trait(id="t1", name="Test", description="Test", category=TraitCategory.TECHNICAL,
                  min_level=0.8, max_level=0.3)

    def test_update_level(self):
        """Test updating trait level."""
        trait = Trait(
            id="trait_001",
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            level=0.5
        )

        trait.update_level(0.7, reason="practice")

        assert trait.level == 0.7
        assert trait.status == TraitStatus.EVOLVING

    def test_update_level_mastered(self):
        """Test mastery status at high level."""
        trait = Trait(
            id="trait_001",
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            level=0.9
        )

        trait.update_level(0.98, reason="practice")

        assert trait.level == 0.98
        assert trait.status == TraitStatus.MASTERED

    def test_update_level_decaying(self):
        """Test decaying status when level decreases."""
        trait = Trait(
            id="trait_001",
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            level=0.7
        )

        trait.update_level(0.5, reason="decay")

        assert trait.level == 0.5
        assert trait.status == TraitStatus.DECAYING

    def test_update_level_clamping(self):
        """Test level clamping to min/max."""
        trait = Trait(
            id="trait_001",
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            level=0.5,
            min_level=0.2,
            max_level=0.9
        )

        trait.update_level(1.0, reason="practice")
        assert trait.level == 0.9

        trait.update_level(0.0, reason="decay")
        assert trait.level == 0.2

    def test_to_dict(self):
        """Test serialization to dictionary."""
        trait = Trait(
            id="trait_001",
            name="Python",
            description="Python programming",
            category=TraitCategory.TECHNICAL,
            level=0.6,
            tags=["backend", "scripting"]
        )

        data = trait.to_dict()

        assert data["id"] == "trait_001"
        assert data["name"] == "Python"
        assert data["category"] == "technical"
        assert data["level"] == 0.6
        assert data["tags"] == ["backend", "scripting"]

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "id": "trait_001",
            "name": "Python",
            "description": "Python programming",
            "category": "technical",
            "level": 0.6,
            "min_level": 0.0,
            "max_level": 1.0,
            "status": "active",
            "persona_id": "persona_1",
            "parent_trait_id": None,
            "tags": ["backend"],
            "metadata": {},
            "metrics": {
                "practice_count": 5,
                "success_count": 4,
                "failure_count": 1,
                "total_practice_time_hours": 10.0,
                "last_practice": None,
                "level_history": []
            },
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }

        trait = Trait.from_dict(data)

        assert trait.id == "trait_001"
        assert trait.category == TraitCategory.TECHNICAL
        assert trait.status == TraitStatus.ACTIVE
        assert trait.metrics.practice_count == 5


class TestTraitManager:
    """Tests for TraitManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh TraitManager for each test."""
        return TraitManager(max_traits_per_persona=10)

    @pytest.fixture
    def manager_with_persistence(self, tmp_path):
        """Create TraitManager with persistence."""
        persistence_file = tmp_path / "traits.json"
        return TraitManager(persistence_path=persistence_file)

    def test_create_trait(self, manager):
        """Test creating a trait."""
        trait = manager.create_trait(
            name="Python",
            description="Python programming",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.6,
            tags=["backend"]
        )

        assert trait.id.startswith("trait_")
        assert trait.name == "Python"
        assert trait.level == 0.6
        assert trait.persona_id == "persona_1"

    def test_create_trait_limit(self, manager):
        """Test trait limit per persona."""
        for i in range(10):
            manager.create_trait(
                name=f"Skill_{i}",
                description=f"Skill {i}",
                category=TraitCategory.TECHNICAL,
                persona_id="persona_1"
            )

        with pytest.raises(TraitValidationError, match="max traits limit"):
            manager.create_trait(
                name="Extra",
                description="Extra skill",
                category=TraitCategory.TECHNICAL,
                persona_id="persona_1"
            )

    def test_get_trait(self, manager):
        """Test getting a trait by ID."""
        created = manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL
        )

        retrieved = manager.get_trait(created.id)
        assert retrieved.id == created.id
        assert retrieved.name == "Python"

    def test_get_trait_not_found(self, manager):
        """Test getting non-existent trait."""
        with pytest.raises(TraitNotFoundError):
            manager.get_trait("nonexistent")

    def test_get_traits_by_persona(self, manager):
        """Test getting traits by persona."""
        manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1"
        )
        manager.create_trait(
            name="Leadership",
            description="Leadership",
            category=TraitCategory.LEADERSHIP,
            persona_id="persona_1"
        )
        manager.create_trait(
            name="Java",
            description="Java",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_2"
        )

        traits = manager.get_traits_by_persona("persona_1")

        assert len(traits) == 2
        assert all(t.persona_id == "persona_1" for t in traits)

    def test_get_traits_by_category(self, manager):
        """Test getting traits by category."""
        manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL
        )
        manager.create_trait(
            name="Leadership",
            description="Leadership",
            category=TraitCategory.LEADERSHIP
        )
        manager.create_trait(
            name="Java",
            description="Java",
            category=TraitCategory.TECHNICAL
        )

        traits = manager.get_traits_by_category(TraitCategory.TECHNICAL)

        assert len(traits) == 2
        assert all(t.category == TraitCategory.TECHNICAL for t in traits)

    def test_update_trait(self, manager):
        """Test updating a trait."""
        created = manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            initial_level=0.5
        )

        updated = manager.update_trait(
            trait_id=created.id,
            name="Python Expert",
            level=0.8,
            tags=["expert"]
        )

        assert updated.name == "Python Expert"
        assert updated.level == 0.8
        assert updated.tags == ["expert"]

    def test_update_trait_not_found(self, manager):
        """Test updating non-existent trait."""
        with pytest.raises(TraitNotFoundError):
            manager.update_trait(trait_id="nonexistent", name="New Name")

    def test_delete_trait(self, manager):
        """Test deleting a trait."""
        created = manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1"
        )

        manager.delete_trait(created.id)

        with pytest.raises(TraitNotFoundError):
            manager.get_trait(created.id)

        # Check persona mapping is also updated
        traits = manager.get_traits_by_persona("persona_1")
        assert len(traits) == 0

    def test_delete_trait_not_found(self, manager):
        """Test deleting non-existent trait."""
        with pytest.raises(TraitNotFoundError):
            manager.delete_trait("nonexistent")

    def test_record_practice(self, manager):
        """Test recording practice for a trait."""
        created = manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            initial_level=0.5
        )

        updated = manager.record_practice(
            trait_id=created.id,
            success=True,
            duration_hours=2.0,
            level_change=0.05
        )

        assert updated.level == 0.55
        assert updated.metrics.practice_count == 1
        assert updated.metrics.success_count == 1

    def test_event_handler(self, manager):
        """Test event handler registration and emission."""
        events = []

        def handler(event):
            events.append(event)

        manager.register_event_handler(handler)

        trait = manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL
        )

        assert len(events) == 1
        assert events[0].event_type == "created"
        assert events[0].trait_id == trait.id

    def test_get_trait_statistics(self, manager):
        """Test getting aggregate statistics."""
        manager.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            persona_id="p1",
            initial_level=0.8
        )
        manager.create_trait(
            name="Leadership",
            description="Leadership",
            category=TraitCategory.LEADERSHIP,
            persona_id="p1",
            initial_level=0.6
        )

        stats = manager.get_trait_statistics()

        assert stats["total_traits"] == 2
        assert stats["by_category"]["technical"] == 1
        assert stats["by_category"]["leadership"] == 1
        assert stats["personas_with_traits"] == 1
        assert 0.6 < stats["average_level"] < 0.8

    def test_persistence(self, manager_with_persistence, tmp_path):
        """Test trait persistence."""
        manager_with_persistence.create_trait(
            name="Python",
            description="Python",
            category=TraitCategory.TECHNICAL,
            persona_id="p1"
        )

        # Create new manager with same persistence path
        new_manager = TraitManager(persistence_path=tmp_path / "traits.json")

        assert len(new_manager._traits) == 1
        traits = new_manager.get_traits_by_persona("p1")
        assert len(traits) == 1
        assert traits[0].name == "Python"


class TestGetTraitManager:
    """Tests for singleton factory function."""

    def test_singleton_behavior(self):
        """Test singleton returns same instance."""
        manager1 = get_trait_manager(force_new=True)
        manager2 = get_trait_manager()

        assert manager1 is manager2

    def test_force_new(self):
        """Test force_new creates new instance."""
        manager1 = get_trait_manager(force_new=True)
        manager2 = get_trait_manager(force_new=True)

        assert manager1 is not manager2
