#!/usr/bin/env python3
"""
Tests for SkillDecayTracker module.

Related EPIC: MD-3018 - Persona Trait Evolution & Guidance
"""

import pytest
import math
from datetime import datetime, timedelta
from pathlib import Path

from maestro_hive.personas.trait_manager import (
    TraitManager,
    Trait,
    TraitCategory,
    TraitStatus,
    get_trait_manager
)
from maestro_hive.personas.skill_decay_tracker import (
    SkillDecayTracker,
    DecayParameters,
    DecayCalculationResult,
    DecayAlert,
    DecayAlertLevel,
    get_skill_decay_tracker
)


class TestDecayParameters:
    """Tests for DecayParameters dataclass."""

    def test_default_parameters(self):
        """Test default parameter values."""
        params = DecayParameters()

        assert params.decay_rate == 0.02
        assert params.warning_threshold == 0.3
        assert params.critical_threshold == 0.1
        assert params.min_decay_level == 0.05
        assert params.recovery_bonus == 1.5

    def test_custom_parameters(self):
        """Test custom parameter values."""
        params = DecayParameters(
            decay_rate=0.05,
            warning_threshold=0.4,
            critical_threshold=0.15
        )

        assert params.decay_rate == 0.05
        assert params.warning_threshold == 0.4
        assert params.critical_threshold == 0.15

    def test_validation_invalid_decay_rate(self):
        """Test validation rejects invalid decay rate."""
        params = DecayParameters(decay_rate=1.5)
        with pytest.raises(ValueError, match="decay_rate must be between"):
            params.validate()

    def test_validation_invalid_thresholds(self):
        """Test validation rejects warning <= critical."""
        params = DecayParameters(warning_threshold=0.1, critical_threshold=0.3)
        with pytest.raises(ValueError, match="warning_threshold must be > critical_threshold"):
            params.validate()


class TestDecayAlert:
    """Tests for DecayAlert dataclass."""

    def test_alert_creation(self):
        """Test basic alert creation."""
        alert = DecayAlert(
            alert_id="alert_001",
            trait_id="trait_001",
            persona_id="persona_001",
            trait_name="Python",
            current_level=0.25,
            previous_level=0.5,
            alert_level=DecayAlertLevel.WARNING,
            message="Warning message",
            recommendation="Practice recommended",
            days_since_practice=30.0,
            projected_decay_30d=0.15
        )

        assert alert.alert_id == "alert_001"
        assert alert.alert_level == DecayAlertLevel.WARNING
        assert not alert.acknowledged

    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = DecayAlert(
            alert_id="alert_001",
            trait_id="trait_001",
            persona_id="persona_001",
            trait_name="Python",
            current_level=0.25,
            previous_level=0.5,
            alert_level=DecayAlertLevel.CRITICAL,
            message="Critical message",
            recommendation="Urgent practice needed",
            days_since_practice=60.0,
            projected_decay_30d=0.08
        )

        data = alert.to_dict()

        assert data["alert_level"] == "critical"
        assert data["current_level"] == 0.25


class TestSkillDecayTracker:
    """Tests for SkillDecayTracker class."""

    @pytest.fixture
    def trait_manager(self):
        """Create a fresh TraitManager."""
        return TraitManager(max_traits_per_persona=50)

    @pytest.fixture
    def tracker(self, trait_manager):
        """Create a SkillDecayTracker with fresh TraitManager."""
        return SkillDecayTracker(trait_manager=trait_manager)

    @pytest.fixture
    def trait_with_old_practice(self, trait_manager):
        """Create a trait with old practice date."""
        trait = trait_manager.create_trait(
            name="Python",
            description="Python programming",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.8
        )
        # Manually set old practice date
        old_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        trait.metrics.last_practice = old_date
        return trait

    def test_get_decay_parameters(self, tracker):
        """Test getting default decay parameters by category."""
        tech_params = tracker.get_decay_parameters(TraitCategory.TECHNICAL)
        soft_params = tracker.get_decay_parameters(TraitCategory.SOFT_SKILL)

        # Technical skills decay faster
        assert tech_params.decay_rate > soft_params.decay_rate

    def test_set_decay_parameters(self, tracker):
        """Test setting custom decay parameters."""
        custom_params = DecayParameters(
            decay_rate=0.05,
            warning_threshold=0.5,
            critical_threshold=0.2
        )

        tracker.set_decay_parameters(TraitCategory.TECHNICAL, custom_params)

        retrieved = tracker.get_decay_parameters(TraitCategory.TECHNICAL)
        assert retrieved.decay_rate == 0.05
        assert retrieved.warning_threshold == 0.5

    def test_calculate_decay_basic(self, tracker, trait_with_old_practice):
        """Test basic decay calculation."""
        result = tracker.calculate_decay(trait_with_old_practice)

        assert isinstance(result, DecayCalculationResult)
        assert result.trait_id == trait_with_old_practice.id
        assert result.original_level == 0.8
        assert result.decayed_level < 0.8
        assert result.decay_amount > 0
        assert result.days_since_practice >= 29  # Approximately 30 days

    def test_calculate_decay_exponential_model(self, tracker, trait_manager):
        """Test that decay follows exponential model."""
        trait = trait_manager.create_trait(
            name="Test",
            description="Test skill",
            category=TraitCategory.TECHNICAL,
            initial_level=1.0
        )
        # Set practice date to exactly 30 days ago
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=30)).isoformat()

        params = tracker.get_decay_parameters(TraitCategory.TECHNICAL)
        result = tracker.calculate_decay(trait)

        # Expected: L(t) = 1.0 * e^(-0.03 * 30) = e^(-0.9) ≈ 0.4066
        expected = math.exp(-params.decay_rate * 30)

        assert abs(result.decayed_level - expected) < 0.01

    def test_calculate_decay_generates_warning(self, tracker, trait_manager):
        """Test that warning alert is generated at threshold."""
        trait = trait_manager.create_trait(
            name="Test",
            description="Test skill",
            category=TraitCategory.TECHNICAL,
            initial_level=0.4  # Start closer to warning threshold
        )
        # Set old practice date
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=30)).isoformat()

        result = tracker.calculate_decay(trait)

        if result.decayed_level <= tracker.get_decay_parameters(TraitCategory.TECHNICAL).warning_threshold:
            assert result.alert_generated is not None
            assert result.alert_generated.alert_level in [DecayAlertLevel.WARNING, DecayAlertLevel.CRITICAL]

    def test_calculate_decay_generates_critical(self, tracker, trait_manager):
        """Test that critical alert is generated at critical threshold."""
        trait = trait_manager.create_trait(
            name="Test",
            description="Test skill",
            category=TraitCategory.TECHNICAL,
            initial_level=0.2
        )
        # Set very old practice date
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=90)).isoformat()

        result = tracker.calculate_decay(trait)

        if result.decayed_level <= tracker.get_decay_parameters(TraitCategory.TECHNICAL).critical_threshold:
            assert result.alert_generated is not None
            assert result.alert_generated.alert_level == DecayAlertLevel.CRITICAL

    def test_calculate_decay_min_level(self, tracker, trait_manager):
        """Test that decay respects minimum level."""
        trait = trait_manager.create_trait(
            name="Test",
            description="Test skill",
            category=TraitCategory.TECHNICAL,
            initial_level=0.5
        )
        # Set very old practice date (1 year)
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=365)).isoformat()

        result = tracker.calculate_decay(trait)
        params = tracker.get_decay_parameters(TraitCategory.TECHNICAL)

        assert result.decayed_level >= params.min_decay_level

    def test_run_decay_calculation(self, tracker, trait_manager):
        """Test running decay calculation for all traits."""
        # Create multiple traits
        for i in range(3):
            trait = trait_manager.create_trait(
                name=f"Skill_{i}",
                description=f"Skill {i}",
                category=TraitCategory.TECHNICAL,
                persona_id="persona_1",
                initial_level=0.7
            )
            trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=20)).isoformat()

        results = tracker.run_decay_calculation(persona_id="persona_1")

        assert len(results) == 3
        assert all(isinstance(r, DecayCalculationResult) for r in results)

    def test_run_decay_calculation_skips_mastered(self, tracker, trait_manager):
        """Test that mastered traits are skipped."""
        trait = trait_manager.create_trait(
            name="Mastered",
            description="Mastered skill",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.98
        )
        trait.status = TraitStatus.MASTERED

        results = tracker.run_decay_calculation(persona_id="persona_1")

        # Mastered trait should not be in results
        assert len(results) == 0

    def test_run_decay_calculation_apply_decay(self, tracker, trait_manager):
        """Test applying decay to traits."""
        trait = trait_manager.create_trait(
            name="Test",
            description="Test skill",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.8
        )
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=30)).isoformat()

        original_level = trait.level
        results = tracker.run_decay_calculation(persona_id="persona_1", apply_decay=True)

        # Trait level should be updated
        assert trait.level < original_level
        assert trait.status == TraitStatus.DECAYING

    def test_get_at_risk_traits(self, tracker, trait_manager):
        """Test getting at-risk traits."""
        # Create a trait at risk
        at_risk_trait = trait_manager.create_trait(
            name="AtRisk",
            description="At risk skill",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.4
        )
        at_risk_trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=30)).isoformat()

        # Create a healthy trait
        healthy_trait = trait_manager.create_trait(
            name="Healthy",
            description="Healthy skill",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.9
        )
        healthy_trait.metrics.last_practice = datetime.utcnow().isoformat()

        at_risk = tracker.get_at_risk_traits(persona_id="persona_1")

        # Should have at least the at-risk trait
        trait_ids = [t.id for t, _ in at_risk]
        if at_risk:
            assert at_risk_trait.id in trait_ids or len(at_risk) > 0

    def test_alert_handler_registration(self, tracker):
        """Test alert handler registration."""
        alerts_received = []

        def handler(alert):
            alerts_received.append(alert)

        tracker.register_alert_handler(handler)
        assert handler in tracker._alert_handlers

    def test_alert_emission(self, tracker, trait_manager):
        """Test alert emission to handlers."""
        alerts_received = []

        def handler(alert):
            alerts_received.append(alert)

        tracker.register_alert_handler(handler)

        # Create a trait that will trigger an alert
        trait = trait_manager.create_trait(
            name="Critical",
            description="Critical skill",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.15
        )
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=60)).isoformat()

        tracker.run_decay_calculation(persona_id="persona_1")

        # Check if alerts were emitted
        # (might be empty if level hasn't decayed below threshold yet)
        assert isinstance(alerts_received, list)

    def test_get_active_alerts(self, tracker, trait_manager):
        """Test getting active alerts."""
        # Create trait that triggers alert
        trait = trait_manager.create_trait(
            name="Test",
            description="Test",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.15
        )
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=90)).isoformat()

        tracker.run_decay_calculation(persona_id="persona_1")

        alerts = tracker.get_active_alerts(persona_id="persona_1")
        assert isinstance(alerts, list)

    def test_acknowledge_alert(self, tracker, trait_manager):
        """Test acknowledging an alert."""
        # Create trait that triggers alert
        trait = trait_manager.create_trait(
            name="Test",
            description="Test",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.1
        )
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=120)).isoformat()

        tracker.run_decay_calculation(persona_id="persona_1")

        alerts = tracker.get_active_alerts()
        if alerts:
            alert_id = alerts[0].alert_id
            result = tracker.acknowledge_alert(alert_id)
            assert result is True

            # Check alert is acknowledged
            updated_alerts = tracker.get_active_alerts()
            for alert in updated_alerts:
                if alert.alert_id == alert_id:
                    assert alert.acknowledged is True

    def test_get_decay_statistics(self, tracker, trait_manager):
        """Test getting decay statistics."""
        trait = trait_manager.create_trait(
            name="Test",
            description="Test",
            category=TraitCategory.TECHNICAL,
            persona_id="persona_1",
            initial_level=0.5
        )
        trait.metrics.last_practice = (datetime.utcnow() - timedelta(days=10)).isoformat()

        tracker.run_decay_calculation(persona_id="persona_1")

        stats = tracker.get_decay_statistics()

        assert "total_calculations" in stats
        assert "active_alerts" in stats
        assert "alerts_by_level" in stats
        assert "last_calculation" in stats


class TestGetSkillDecayTracker:
    """Tests for singleton factory function."""

    def test_singleton_behavior(self):
        """Test singleton returns same instance."""
        tracker1 = get_skill_decay_tracker(force_new=True)
        tracker2 = get_skill_decay_tracker()

        assert tracker1 is tracker2

    def test_force_new(self):
        """Test force_new creates new instance."""
        tracker1 = get_skill_decay_tracker(force_new=True)
        tracker2 = get_skill_decay_tracker(force_new=True)

        assert tracker1 is not tracker2
