"""
Unit tests for dde/capability_matcher.py
"""

import unittest
from datetime import datetime
from dde.capability_matcher import CapabilityMatcher, AgentProfile, CapabilityTaxonomy
import yaml
from pathlib import Path

class TestCapabilityMatcher(unittest.TestCase):

    def setUp(self):
        """Set up a test taxonomy and matcher."""
        self.taxonomy_path = Path("test_taxonomy.yaml")
        taxonomy_data = {
            'taxonomy': {
                'Backend': ['Python', 'Node'],
                'Backend:Python': ['FastAPI', 'Django']
            },
            'aliases': {'api': 'Backend:Python:FastAPI'},
            'groups': {'backend_dev': ['Backend:Python', 'Backend:Node']}
        }
        with open(self.taxonomy_path, "w") as f:
            yaml.dump(taxonomy_data, f)

        self.taxonomy = CapabilityTaxonomy(taxonomy_file=str(self.taxonomy_path))
        self.matcher = CapabilityMatcher(taxonomy=self.taxonomy)

        self.agent1 = AgentProfile(
            agent_id="agent1", name="Python Pro", availability_status="available",
            wip_limit=3, current_wip=1, recent_quality_score=0.9,
            last_active=datetime.now(),
            capabilities={"Backend:Python:FastAPI": 5, "Data:SQL": 4}
        )
        self.agent2 = AgentProfile(
            agent_id="agent2", name="JS Dev", availability_status="busy",
            wip_limit=2, current_wip=2, recent_quality_score=0.8,
            last_active=datetime.now(),
            capabilities={"Backend:Node": 4, "Web:React": 5}
        )
        self.agent3 = AgentProfile(
            agent_id="agent3", name="Generalist", availability_status="available",
            wip_limit=5, current_wip=0, recent_quality_score=0.85,
            last_active=datetime.now(),
            capabilities={"Backend:Python": 3, "Web:React": 3}
        )
        self.matcher.register_agent(self.agent1)
        self.matcher.register_agent(self.agent2)
        self.matcher.register_agent(self.agent3)

    def tearDown(self):
        """Clean up the test taxonomy file."""
        if self.taxonomy_path.exists():
            self.taxonomy_path.unlink()

    def test_match_success(self):
        """Test successful matching of an agent."""
        matches = self.matcher.match(required_skills=["Backend:Python:FastAPI"])
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0][0], "agent1")

    def test_match_with_alias(self):
        """Test matching using a capability alias."""
        matches = self.matcher.match(required_skills=["api"])
        self.assertEqual(matches[0][0], "agent1")

    def test_match_with_parent_capability(self):
        """Test matching based on a less specific parent capability."""
        matches = self.matcher.match(required_skills=["Backend:Python"])
        # agent1 has a more specific skill, agent3 has the exact skill
        self.assertIn(matches[0][0], ["agent1", "agent3"])
        self.assertIn(matches[1][0], ["agent1", "agent3"])

    def test_match_no_suitable_agent(self):
        """Test matching when no agent has the required skill."""
        matches = self.matcher.match(required_skills=["Backend:Ruby"])
        self.assertEqual(len(matches), 0)

    def test_match_respects_min_proficiency(self):
        """Test that matching filters by minimum proficiency."""
        matches = self.matcher.match(required_skills=["Backend:Python"], min_proficiency=4)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0][0], "agent1")

    def test_scoring_logic(self):
        """Test the scoring logic by comparing two potential candidates."""
        # agent1 is highly proficient but has some load.
        # agent3 is less proficient but has no load.
        # agent1 should still score higher due to proficiency weight.
        matches = self.matcher.match(required_skills=["Backend:Python"])
        
        agent1_score = [s for a, s in matches if a == 'agent1'][0]
        agent3_score = [s for a, s in matches if a == 'agent3'][0]

        self.assertGreater(agent1_score, agent3_score)

    def test_availability_impacts_score(self):
        """Test that availability status affects the match score."""
        # Make agent1 busy
        self.matcher.update_agent_status("agent1", availability_status="busy")
        
        matches = self.matcher.match(required_skills=["Backend:Python:FastAPI"])
        
        # agent3 should now be the top match as agent1 is busy
        self.assertEqual(matches[0][0], "agent3")

if __name__ == '__main__':
    unittest.main()
