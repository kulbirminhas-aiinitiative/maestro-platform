"""
Tests for MD-3118: Reputation System & Identity

Tests all 5 acceptance criteria:
- AC-1: pr_merged event increases score by 20
- AC-2: Score decreases correctly over time if inactive (decay)
- AC-3: Agent auto-promoted to senior_developer after meeting criteria
- AC-4: Agent auto-demoted if score drops below threshold
- AC-5: Scores survive system restart (persistence)

Plus tests for Ed25519 cryptographic identity.
"""

import os
import json
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

# Import modules under test
from maestro_hive.governance.reputation import (
    ReputationEngine,
    ReputationEvent,
    ReputationScore,
    ReputationChange,
)
from maestro_hive.governance.identity import (
    IdentityManager,
    AgentIdentity,
    SignedAction,
    CRYPTO_AVAILABLE,
)
from maestro_hive.governance.persistence import (
    GovernancePersistence,
    FileStorageBackend,
    get_persistence,
)


# =============================================================================
# AC-1: Scoring - pr_merged event increases score by 20
# =============================================================================

class TestAC1_Scoring:
    """Tests for AC-1: pr_merged scoring."""

    def test_pr_merged_adds_20_points(self):
        """AC-1: pr_merged event increases score by 20."""
        engine = ReputationEngine()
        agent_id = "agent-ac1-001"

        # Get initial score
        initial = engine.get_score(agent_id)
        initial_score = initial.score

        # Record pr_merged event
        change = engine.record_event(agent_id, ReputationEvent.PR_MERGED)

        # Verify delta is exactly 20
        assert change.delta == 20
        assert change.event == ReputationEvent.PR_MERGED

        # Verify final score
        final = engine.get_score(agent_id)
        assert final.score == initial_score + 20

    def test_pr_merged_via_convenience_method(self):
        """Test pr_merged via convenience method."""
        engine = ReputationEngine()
        agent_id = "agent-ac1-002"

        initial = engine.get_score(agent_id)
        change = engine.pr_merged(agent_id, metadata={"pr_id": "PR-123"})

        assert change.delta == 20
        assert change.metadata.get("pr_id") == "PR-123"

    def test_multiple_pr_merged_events(self):
        """Test multiple PR merges add up correctly (when not blocked by cooldown)."""
        engine = ReputationEngine()
        agent_id = "agent-ac1-003"

        # Disable cooldown by setting to 0 seconds
        engine._cooldown_seconds = 0

        initial_score = engine.get_score(agent_id).score

        # 3 PR merges (no cooldown)
        engine.pr_merged(agent_id)
        engine.pr_merged(agent_id)
        engine.pr_merged(agent_id)

        final = engine.get_score(agent_id)
        # Should gain 60 points (3 * 20)
        assert final.score == initial_score + 60


# =============================================================================
# AC-2: Decay - Score decreases correctly over time if inactive
# =============================================================================

class TestAC2_Decay:
    """Tests for AC-2: Reputation decay."""

    def test_decay_after_inactivity(self):
        """AC-2: Score decreases with exponential decay after inactivity."""
        engine = ReputationEngine(decay_half_life_days=30, decay_floor=20)
        agent_id = "agent-ac2-001"

        # Set up score with old last_activity
        score = engine.get_score(agent_id)
        score.score = 100

        # Manually set last_activity to 30 days ago
        score.last_activity = datetime.utcnow() - timedelta(days=30)

        # Access score again (triggers decay check)
        engine._apply_decay(score)

        # After 30 days (one half-life), score should be ~50
        # With floor of 20, score should be max(50, 20) = 50
        assert score.score <= 55  # Allow some variance
        assert score.score >= 45

    def test_decay_respects_floor(self):
        """AC-2: Decay doesn't go below floor."""
        engine = ReputationEngine(decay_half_life_days=30, decay_floor=20)
        agent_id = "agent-ac2-002"

        score = engine.get_score(agent_id)
        score.score = 30

        # Set very old activity (multiple half-lives)
        score.last_activity = datetime.utcnow() - timedelta(days=180)

        engine._apply_decay(score)

        # Should be at floor
        assert score.score == 20

    def test_no_decay_for_recent_activity(self):
        """AC-2: No decay if activity is recent."""
        engine = ReputationEngine(decay_half_life_days=30)
        agent_id = "agent-ac2-003"

        score = engine.get_score(agent_id)
        score.score = 100
        score.last_activity = datetime.utcnow() - timedelta(hours=1)

        original_score = score.score
        engine._apply_decay(score)

        # Should be unchanged (activity within day)
        assert score.score == original_score


# =============================================================================
# AC-3: Promotion - Auto-promoted to senior_developer after meeting criteria
# =============================================================================

class TestAC3_Promotion:
    """Tests for AC-3: Auto-promotion."""

    def test_promotion_to_senior_developer(self):
        """AC-3: Agent promoted to senior_developer at score >= 200."""
        engine = ReputationEngine()
        agent_id = "agent-ac3-001"

        # Disable anti-gaming measures for testing
        engine._cooldown_seconds = 0
        engine._max_daily_gain = 10000  # Effectively disable

        # Start fresh
        score = engine.get_score(agent_id)
        score.score = 50
        score.role = "developer_agent"

        # Add enough points to reach 200+
        # Need 150 more points (8 PR merges = 160)
        for _ in range(8):
            engine.pr_merged(agent_id)

        final = engine.get_score(agent_id)
        assert final.score >= 200
        assert final.role == "senior_developer_agent"

    def test_promotion_to_architect(self):
        """AC-3: Agent promoted to architect at score >= 500."""
        engine = ReputationEngine()
        agent_id = "agent-ac3-002"

        score = engine.get_score(agent_id)
        score.score = 480
        score.role = "senior_developer_agent"

        # Add 2 more PRs (40 points)
        engine.pr_merged(agent_id)
        engine.pr_merged(agent_id)

        final = engine.get_score(agent_id)
        assert final.score >= 500
        assert final.role == "architect_agent"

    def test_role_change_callback(self):
        """AC-3: Role change triggers callback."""
        engine = ReputationEngine()
        agent_id = "agent-ac3-003"

        callback_called = []

        def on_role_change(agent, old_role, new_role):
            callback_called.append((agent, old_role, new_role))

        engine.on_role_change(on_role_change)

        # Force score to just below threshold
        score = engine.get_score(agent_id)
        score.score = 195
        score.role = "developer_agent"

        # Add event to cross threshold
        engine.pr_merged(agent_id)

        assert len(callback_called) == 1
        assert callback_called[0][2] == "senior_developer_agent"


# =============================================================================
# AC-4: Demotion - Auto-demoted if score drops below threshold
# =============================================================================

class TestAC4_Demotion:
    """Tests for AC-4: Auto-demotion."""

    def test_demotion_from_senior_developer(self):
        """AC-4: Agent demoted from senior_developer when score drops."""
        engine = ReputationEngine()
        agent_id = "agent-ac4-001"

        # Start as senior developer at threshold
        score = engine.get_score(agent_id)
        score.score = 200
        score.role = "senior_developer_agent"

        # Policy violation (-30 points)
        engine.record_event(agent_id, ReputationEvent.POLICY_VIOLATION)

        final = engine.get_score(agent_id)
        assert final.score < 200
        assert final.role == "developer_agent"

    def test_demotion_to_restricted(self):
        """AC-4: Agent demoted to restricted when score drops below 30."""
        engine = ReputationEngine()
        agent_id = "agent-ac4-002"

        score = engine.get_score(agent_id)
        score.score = 35
        score.role = "developer_agent"

        # Two build breaks (-40 points)
        engine.build_broken(agent_id)
        engine.build_broken(agent_id)

        final = engine.get_score(agent_id)
        assert final.score < 30
        assert final.role == "restricted_agent"

    def test_no_demotion_above_threshold(self):
        """AC-4: No demotion if still above threshold."""
        engine = ReputationEngine()
        agent_id = "agent-ac4-003"

        score = engine.get_score(agent_id)
        score.score = 250
        score.role = "senior_developer_agent"

        # One build break (-20 points)
        engine.build_broken(agent_id)

        final = engine.get_score(agent_id)
        assert final.score >= 200
        assert final.role == "senior_developer_agent"


# =============================================================================
# AC-5: Persistence - Scores survive system restart
# =============================================================================

class TestAC5_Persistence:
    """Tests for AC-5: Persistence."""

    def test_file_storage_backend_roundtrip(self):
        """AC-5: File storage can save and load data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            backend = FileStorageBackend(storage_dir=tmpdir)

            # Write data
            backend.set("test:key1", "value1")
            backend.set("test:key2", json.dumps({"score": 100}))

            # Close and reopen
            backend.close()

            # New backend instance
            backend2 = FileStorageBackend(storage_dir=tmpdir)

            # Read data
            assert backend2.get("test:key1") == "value1"
            assert json.loads(backend2.get("test:key2"))["score"] == 100

            backend2.close()

    def test_governance_persistence_reputation_roundtrip(self):
        """AC-5: Reputation scores survive restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First session
            persistence1 = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )

            score_data = {
                "agent_id": "agent-ac5-001",
                "score": 150,
                "role": "senior_developer_agent",
                "last_activity": datetime.utcnow().isoformat(),
            }

            persistence1.save_reputation_score("agent-ac5-001", score_data)
            persistence1.close()

            # Second session (simulates restart)
            persistence2 = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )

            loaded = persistence2.load_reputation_score("agent-ac5-001")

            assert loaded is not None
            assert loaded["score"] == 150
            assert loaded["role"] == "senior_developer_agent"

            persistence2.close()

    def test_persistence_health_check(self):
        """AC-5: Persistence health check works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )

            health = persistence.health_check()
            assert health["status"] == "healthy"
            assert health["write"] is True

            persistence.close()

    def test_persistence_stats(self):
        """AC-5: Persistence stats tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )

            # Save some data
            persistence.save_reputation_score("agent1", {"score": 100})
            persistence.save_reputation_score("agent2", {"score": 200})

            stats = persistence.get_stats()
            assert stats["reputation_scores"] == 2

            persistence.close()


# =============================================================================
# Identity Tests - Ed25519 Cryptographic Signatures
# =============================================================================

class TestIdentity:
    """Tests for cryptographic identity."""

    def test_create_identity(self):
        """Test identity creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = IdentityManager(
                storage_path=os.path.join(tmpdir, "identities.json")
            )

            identity = manager.create_identity("agent-id-001")

            assert identity.agent_id == "agent-id-001"
            assert identity.public_key is not None
            assert len(identity.public_key) > 0
            assert identity.fingerprint is not None

    def test_identity_persistence(self):
        """Test identity survives restart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, "identities.json")

            # Create identity
            manager1 = IdentityManager(storage_path=storage_path)
            identity1 = manager1.create_identity("agent-id-002")
            fingerprint = identity1.fingerprint

            # New manager instance
            manager2 = IdentityManager(storage_path=storage_path)
            identity2 = manager2.get_identity("agent-id-002")

            assert identity2 is not None
            assert identity2.fingerprint == fingerprint

    def test_sign_action(self):
        """Test action signing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = IdentityManager(
                storage_path=os.path.join(tmpdir, "identities.json")
            )

            manager.create_identity("agent-id-003")

            action = manager.sign_action(
                agent_id="agent-id-003",
                action_type="tool_call",
                payload={"tool": "read_file", "path": "/test.py"},
            )

            assert action.agent_id == "agent-id-003"
            assert action.action_type == "tool_call"
            assert action.signature is not None
            assert len(action.signature) > 0

    def test_verify_action(self):
        """Test action verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = IdentityManager(
                storage_path=os.path.join(tmpdir, "identities.json")
            )

            manager.create_identity("agent-id-004")

            action = manager.sign_action(
                agent_id="agent-id-004",
                action_type="write_file",
                payload={"path": "/output.txt", "content": "hello"},
            )

            # Verify signature
            is_valid = manager.verify_action(action)
            assert is_valid is True

    def test_verify_tampered_action_fails(self):
        """Test that tampered actions fail verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = IdentityManager(
                storage_path=os.path.join(tmpdir, "identities.json")
            )

            manager.create_identity("agent-id-005")

            action = manager.sign_action(
                agent_id="agent-id-005",
                action_type="delete_file",
                payload={"path": "/important.py"},
            )

            # Tamper with payload
            action.payload["path"] = "/evil.py"

            # Verification should fail
            is_valid = manager.verify_action(action)
            assert is_valid is False

    def test_key_rotation(self):
        """Test key rotation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = IdentityManager(
                storage_path=os.path.join(tmpdir, "identities.json")
            )

            # Create initial identity
            identity1 = manager.create_identity("agent-id-006")
            old_fingerprint = identity1.fingerprint

            # Rotate key
            identity2 = manager.rotate_key("agent-id-006")

            assert identity2.fingerprint != old_fingerprint
            assert identity2.metadata.get("rotated_from") == old_fingerprint


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple components."""

    def test_reputation_with_persistence(self):
        """Test reputation engine with persistent storage."""
        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )

            # Create engine with no cooldown for testing
            engine1 = ReputationEngine()
            engine1._cooldown_seconds = 0
            agent_id = "agent-int-001"

            engine1.pr_merged(agent_id)
            engine1.pr_merged(agent_id)

            # Save scores manually
            score = engine1.get_score(agent_id)
            persistence.save_reputation_score(agent_id, {
                "agent_id": score.agent_id,
                "score": score.score,
                "role": score.role,
                "total_events": score.total_events,
            })

            persistence.close()

            # Simulate restart and load
            persistence2 = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )

            loaded = persistence2.load_reputation_score(agent_id)
            assert loaded["score"] == 50 + 40  # Initial + 2 PRs
            assert loaded["total_events"] == 2

            persistence2.close()

    def test_signed_reputation_event(self):
        """Test signing reputation events."""
        with tempfile.TemporaryDirectory() as tmpdir:
            identity_mgr = IdentityManager(
                storage_path=os.path.join(tmpdir, "identities.json")
            )
            engine = ReputationEngine()

            agent_id = "agent-int-002"
            identity_mgr.create_identity(agent_id)

            # Record event and sign it
            change = engine.pr_merged(agent_id)

            signed = identity_mgr.sign_action(
                agent_id=agent_id,
                action_type="reputation_change",
                payload={
                    "event": change.event.value,
                    "delta": change.delta,
                    "new_score": change.new_score,
                },
            )

            # Verify the signed change
            assert identity_mgr.verify_action(signed) is True


# =============================================================================
# JIRA Acceptance Scenario Tests
# =============================================================================

class TestJiraAcceptanceScenarios:
    """Direct tests of JIRA acceptance criteria scenarios."""

    def test_jira_ac1_pr_merged_plus_20(self):
        """
        JIRA AC-1: pr_merged event increases score by 20.

        Scenario: An agent merges a PR.
        Expected: Score increases by exactly 20 points.
        """
        engine = ReputationEngine()
        agent_id = "jira-ac1-agent"

        initial = engine.get_score(agent_id).score
        change = engine.pr_merged(agent_id)

        assert change.delta == 20, "pr_merged must add exactly 20 points"
        assert engine.get_score(agent_id).score == initial + 20

    def test_jira_ac2_decay_over_time(self):
        """
        JIRA AC-2: Score decreases correctly over time if inactive.

        Scenario: An agent is inactive for 30 days.
        Expected: Score roughly halves (30-day half-life).
        """
        engine = ReputationEngine(decay_half_life_days=30, decay_floor=10)
        agent_id = "jira-ac2-agent"

        score = engine.get_score(agent_id)
        score.score = 100
        score.last_activity = datetime.utcnow() - timedelta(days=30)

        engine._apply_decay(score)

        # After one half-life, should be approximately half
        assert 45 <= score.score <= 55, f"After 30 days, score should be ~50, got {score.score}"

    def test_jira_ac3_auto_promotion(self):
        """
        JIRA AC-3: Agent auto-promoted to senior_developer after meeting criteria.

        Scenario: Agent reaches score >= 200.
        Expected: Role changes to senior_developer_agent.
        """
        engine = ReputationEngine()
        agent_id = "jira-ac3-agent"

        # Start with developer role
        score = engine.get_score(agent_id)
        score.score = 199
        score.role = "developer_agent"

        # One more PR pushes over threshold
        engine.pr_merged(agent_id)

        final = engine.get_score(agent_id)
        assert final.role == "senior_developer_agent", "Should be promoted to senior_developer_agent"

    def test_jira_ac4_auto_demotion(self):
        """
        JIRA AC-4: Agent auto-demoted if score drops below threshold.

        Scenario: Senior developer's score drops below 200.
        Expected: Role changes to developer_agent.
        """
        engine = ReputationEngine()
        agent_id = "jira-ac4-agent"

        # Start as senior developer at threshold
        score = engine.get_score(agent_id)
        score.score = 200
        score.role = "senior_developer_agent"

        # Policy violation drops score
        engine.record_event(agent_id, ReputationEvent.POLICY_VIOLATION)

        final = engine.get_score(agent_id)
        assert final.role == "developer_agent", "Should be demoted to developer_agent"

    def test_jira_ac5_scores_survive_restart(self):
        """
        JIRA AC-5: Scores survive system restart.

        Scenario: Save score, simulate restart, load score.
        Expected: Score is recovered exactly.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            agent_id = "jira-ac5-agent"
            test_score = 175

            # Session 1: Save score
            persistence1 = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )
            persistence1.save_reputation_score(agent_id, {
                "agent_id": agent_id,
                "score": test_score,
                "role": "developer_agent",
            })
            persistence1.close()

            # Session 2: Load score (simulates restart)
            persistence2 = GovernancePersistence(
                backend=FileStorageBackend(storage_dir=tmpdir)
            )
            loaded = persistence2.load_reputation_score(agent_id)
            persistence2.close()

            assert loaded is not None, "Score must be recoverable after restart"
            assert loaded["score"] == test_score, f"Score must match: expected {test_score}, got {loaded['score']}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
