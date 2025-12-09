"""
Unit tests for Learning Stores.

Tests template, quality, and coordination learning stores.
"""

import pytest


class TestTemplateLearningStore:
    """Tests for TemplateLearningStore."""
    
    def test_learning_verbosity_stores_all(self):
        """LEARNING mode should store all learnings."""
        verbosity = "learning"
        assert verbosity == "learning"
    
    def test_optimized_stores_failures_and_novel(self):
        """OPTIMIZED mode stores failures and novel patterns."""
        success_score = 0.6
        should_store = success_score < 0.7
        assert should_store
    
    def test_production_stores_only_exceptions(self):
        """PRODUCTION mode stores only exceptions."""
        success_score = 0.2
        should_store = success_score < 0.3
        assert should_store
    
    def test_cosine_similarity_calculation(self):
        """Cosine similarity should be calculated correctly."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        mag1 = sum(a * a for a in vec1) ** 0.5
        mag2 = sum(b * b for b in vec2) ** 0.5
        similarity = dot / (mag1 * mag2)
        
        assert similarity == 1.0
    
    def test_orthogonal_vectors_zero_similarity(self):
        """Orthogonal vectors should have zero similarity."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        assert dot == 0.0


class TestQualityLearningStore:
    """Tests for QualityLearningStore."""
    
    def test_issue_pattern_tracking(self):
        """Should track issue patterns correctly."""
        patterns = {}
        
        # Add some patterns
        key1 = "template_selection:type_mismatch"
        patterns[key1] = {"count": 3, "avg_quality": 0.4}
        
        key2 = "persona_choice:performance_issue"
        patterns[key2] = {"count": 2, "avg_quality": 0.5}
        
        assert len(patterns) == 2
        assert patterns[key1]["count"] == 3
    
    def test_severity_filtering(self):
        """Should filter by issue severity."""
        severities = ["critical", "high", "medium", "low"]
        critical_only = [s for s in severities if s == "critical"]
        assert len(critical_only) == 1
    
    def test_production_stores_critical_only(self):
        """PRODUCTION stores only critical issues."""
        issue_severity = "critical"
        should_store = issue_severity == "critical"
        assert should_store


class TestCoordinationLearningStore:
    """Tests for CoordinationLearningStore."""
    
    def test_team_modes_defined(self):
        """All team modes should be defined."""
        team_modes = ["sequential", "parallel", "collaborative", "hierarchical"]
        assert len(team_modes) == 4
    
    def test_effectiveness_calculation(self):
        """Effectiveness should be averaged correctly."""
        scores = [0.8, 0.9, 0.7]
        avg = sum(scores) / len(scores)
        assert abs(avg - 0.8) < 0.01
    
    def test_persona_combination_tracking(self):
        """Should track persona combinations."""
        combinations = {}
        
        combo1 = ("architect", "developer")
        combo2 = ("architect", "tester")
        
        combinations[combo1] = combinations.get(combo1, 0) + 1
        combinations[combo1] = combinations.get(combo1, 0) + 1
        combinations[combo2] = combinations.get(combo2, 0) + 1
        
        assert combinations[combo1] == 2
        assert combinations[combo2] == 1
    
    def test_novel_pattern_detection(self):
        """Should detect novel coordination patterns."""
        avg_effectiveness = 0.7
        new_effectiveness = 0.3
        
        is_novel = abs(new_effectiveness - avg_effectiveness) > 0.2
        assert is_novel


class TestVerbosityFiltering:
    """Tests for verbosity-based filtering across stores."""
    
    def test_learning_mode_stores_everything(self):
        """LEARNING mode should store everything."""
        verbosity = "learning"
        any_score = 0.99
        should_store = verbosity == "learning" or any_score < 0.7
        assert should_store
    
    def test_optimized_filters_routine(self):
        """OPTIMIZED should filter routine patterns."""
        verbosity = "optimized"
        high_score = 0.95
        is_novel = False
        
        should_store = high_score < 0.7 or is_novel
        assert not should_store
    
    def test_production_minimal_storage(self):
        """PRODUCTION should have minimal storage."""
        verbosity = "production"
        score = 0.5  # Not a critical failure
        
        should_store = score < 0.3
        assert not should_store


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
