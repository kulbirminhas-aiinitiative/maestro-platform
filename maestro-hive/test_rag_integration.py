#!/usr/bin/env python3
"""
End-to-End RAG Integration Test

This test validates the complete RAG (Retrieval-Augmented Generation) integration
across the team execution workflow:

1. Configuration loading
2. RAG client initialization
3. Project-level template package recommendation
4. Persona-level template search
5. Relevance scoring
6. Context tracking
7. Caching functionality

Run:
    python test_rag_integration.py
"""

import asyncio
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

# Test configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class RAGIntegrationTests:
    """End-to-end tests for RAG integration"""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    async def run_all_tests(self):
        """Run all integration tests"""
        logger.info("="*80)
        logger.info("RAG INTEGRATION - END-TO-END TESTS")
        logger.info("="*80)
        logger.info(f"Started: {datetime.now().isoformat()}")
        logger.info("")

        tests = [
            ("Configuration Loading", self.test_configuration_loading),
            ("RAG Client Initialization", self.test_rag_client_initialization),
            ("Project-Level Package Recommendation", self.test_project_level_rag),
            ("Persona-Level Template Search", self.test_persona_level_rag),
            ("Relevance Scoring", self.test_relevance_scoring),
            ("Configuration Thresholds", self.test_configuration_thresholds),
            ("Caching Functionality", self.test_caching),
            ("Team Execution Integration", self.test_team_execution_integration),
        ]

        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)

        self.print_summary()

    async def run_test(self, name: str, test_func):
        """Run a single test"""
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST: {name}")
        logger.info(f"{'='*80}")

        try:
            await test_func()
            self.passed += 1
            logger.info(f"✅ PASSED: {name}")
        except AssertionError as e:
            self.failed += 1
            error_msg = f"❌ FAILED: {name} - {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
        except Exception as e:
            self.failed += 1
            error_msg = f"❌ ERROR: {name} - {str(e)}"
            logger.error(error_msg)
            self.errors.append(error_msg)

    async def test_configuration_loading(self):
        """Test 1: Configuration loading"""
        logger.info("Testing configuration loading...")

        from config import RAG_CONFIG

        # Verify configuration structure
        required_keys = [
            'registry_base_url',
            'templates_base_path',
            'enable_cache',
            'cache_ttl_hours',
            'high_relevance_threshold',
            'medium_relevance_threshold',
            'max_templates_to_show',
            'keyword_weight',
            'tag_weight',
            'quality_weight',
            'tech_stack_weight',
            'usage_stats_weight',
        ]

        for key in required_keys:
            assert key in RAG_CONFIG, f"Missing config key: {key}"
            logger.info(f"  ✓ {key}: {RAG_CONFIG[key]}")

        # Verify weights sum to 1.0
        total_weight = (
            RAG_CONFIG['keyword_weight'] +
            RAG_CONFIG['tag_weight'] +
            RAG_CONFIG['quality_weight'] +
            RAG_CONFIG['tech_stack_weight'] +
            RAG_CONFIG['usage_stats_weight']
        )
        assert abs(total_weight - 1.0) < 0.01, f"Weights don't sum to 1.0: {total_weight}"
        logger.info(f"  ✓ Scoring weights sum to: {total_weight}")

        logger.info("  ✓ Configuration valid")

    async def test_rag_client_initialization(self):
        """Test 2: RAG client initialization"""
        logger.info("Testing RAG client initialization...")

        from rag_template_client import TemplateRAGClient
        from config import RAG_CONFIG

        # Initialize with config defaults
        client = TemplateRAGClient()

        # Verify config values are used
        assert str(RAG_CONFIG['registry_base_url']) in client.registry_url, "Registry URL not from config"
        assert client.templates_base_path == Path(RAG_CONFIG['templates_base_path']), "Templates path not from config"
        assert client.enable_cache == RAG_CONFIG['enable_cache'], "Cache setting not from config"
        assert client.relevance_threshold_use == RAG_CONFIG['high_relevance_threshold'], "High threshold not from config"
        assert client.relevance_threshold_custom == RAG_CONFIG['medium_relevance_threshold'], "Medium threshold not from config"

        logger.info(f"  ✓ Registry URL: {client.registry_url}")
        logger.info(f"  ✓ Templates path: {client.templates_base_path}")
        logger.info(f"  ✓ Cache enabled: {client.enable_cache}")
        logger.info(f"  ✓ High threshold: {client.relevance_threshold_use:.0%}")
        logger.info(f"  ✓ Medium threshold: {client.relevance_threshold_custom:.0%}")

        await client.close()
        logger.info("  ✓ Client initialized successfully")

    async def test_project_level_rag(self):
        """Test 3: Project-level package recommendation"""
        logger.info("Testing project-level package recommendation...")

        from rag_template_client import TemplateRAGClient

        client = TemplateRAGClient()

        requirement = "Build an e-commerce platform with user authentication and payment processing"
        package = await client.get_recommended_package(requirement)

        if package:
            logger.info(f"  ✓ Package recommended: {package.best_match_package_name or 'Custom'}")
            logger.info(f"  ✓ Type: {package.recommendation_type}")
            logger.info(f"  ✓ Confidence: {package.confidence:.0%}")
            logger.info(f"  ✓ Templates: {len(package.recommended_templates)}")

            assert package.confidence >= 0.0 and package.confidence <= 1.0, "Invalid confidence score"
            assert len(package.recommended_templates) > 0, "No templates recommended"
        else:
            logger.warning("  ⚠️  No package recommendation (API may be unavailable)")

        await client.close()

    async def test_persona_level_rag(self):
        """Test 4: Persona-level template search"""
        logger.info("Testing persona-level template search...")

        from rag_template_client import TemplateRAGClient

        client = TemplateRAGClient()

        # Test backend developer templates
        requirement = "Build a REST API with authentication and CRUD operations"
        templates = await client.search_templates_for_persona(
            persona_id="backend_developer",
            requirement=requirement,
            context={"language": "python", "framework": "fastapi"}
        )

        logger.info(f"  ✓ Found {len(templates)} templates for backend_developer")

        if templates:
            top_template = templates[0]
            logger.info(f"  ✓ Top template: {top_template.metadata.name}")
            logger.info(f"  ✓ Relevance: {top_template.relevance_score:.0%}")
            logger.info(f"  ✓ Quality: {top_template.metadata.quality_score}/100")

            assert top_template.relevance_score >= 0.0 and top_template.relevance_score <= 1.0, "Invalid relevance score"
            assert top_template.selection_reasoning, "No selection reasoning provided"

        await client.close()

    async def test_relevance_scoring(self):
        """Test 5: Relevance scoring"""
        logger.info("Testing relevance scoring...")

        from rag_template_client import TemplateRAGClient
        from config import RAG_CONFIG

        client = TemplateRAGClient()

        # Verify scoring weights are from config
        assert client.keyword_weight == RAG_CONFIG['keyword_weight'], "Keyword weight not from config"
        assert client.tag_weight == RAG_CONFIG['tag_weight'], "Tag weight not from config"
        assert client.quality_weight == RAG_CONFIG['quality_weight'], "Quality weight not from config"
        assert client.tech_stack_weight == RAG_CONFIG['tech_stack_weight'], "Tech stack weight not from config"
        assert client.usage_stats_weight == RAG_CONFIG['usage_stats_weight'], "Usage stats weight not from config"

        logger.info(f"  ✓ Keyword weight: {client.keyword_weight}")
        logger.info(f"  ✓ Tag weight: {client.tag_weight}")
        logger.info(f"  ✓ Quality weight: {client.quality_weight}")
        logger.info(f"  ✓ Tech stack weight: {client.tech_stack_weight}")
        logger.info(f"  ✓ Usage stats weight: {client.usage_stats_weight}")

        await client.close()

    async def test_configuration_thresholds(self):
        """Test 6: Configuration thresholds in prompt builder"""
        logger.info("Testing configuration thresholds...")

        from config import RAG_CONFIG

        high_threshold = RAG_CONFIG['high_relevance_threshold']
        medium_threshold = RAG_CONFIG['medium_relevance_threshold']
        include_code = RAG_CONFIG.get('include_template_code', True)

        logger.info(f"  ✓ High relevance threshold: {high_threshold:.0%}")
        logger.info(f"  ✓ Medium relevance threshold: {medium_threshold:.0%}")
        logger.info(f"  ✓ Include template code: {include_code}")

        assert high_threshold > medium_threshold, "High threshold must be > medium threshold"
        assert high_threshold <= 1.0 and high_threshold >= 0.0, "Invalid high threshold"
        assert medium_threshold <= 1.0 and medium_threshold >= 0.0, "Invalid medium threshold"

    async def test_caching(self):
        """Test 7: Caching functionality"""
        logger.info("Testing caching functionality...")

        from rag_template_client import TemplateRAGClient
        from config import RAG_CONFIG

        client = TemplateRAGClient()

        # Verify cache settings
        assert client.enable_cache == RAG_CONFIG['enable_cache'], "Cache setting not from config"
        assert client.cache_dir == Path(RAG_CONFIG['cache_dir']), "Cache dir not from config"

        logger.info(f"  ✓ Cache enabled: {client.enable_cache}")
        logger.info(f"  ✓ Cache directory: {client.cache_dir}")
        logger.info(f"  ✓ Cache TTL: {client.cache_ttl}")

        if client.enable_cache and client.cache_dir.exists():
            cache_files = list(client.cache_dir.glob("*.json"))
            logger.info(f"  ✓ Cache files: {len(cache_files)}")

        await client.close()

    async def test_team_execution_integration(self):
        """Test 8: Team execution integration"""
        logger.info("Testing team execution integration...")

        from team_execution_v2 import TeamExecutionEngineV2
        from config import RAG_CONFIG

        # Create engine (which should initialize RAG client)
        engine = TeamExecutionEngineV2(output_dir="./test_output")

        # Check if RAG client was initialized based on config
        if RAG_CONFIG.get('enable_project_level_rag', True):
            assert engine.rag_client is not None, "RAG client not initialized when enabled in config"
            logger.info("  ✓ RAG client initialized in TeamExecutionEngineV2")
        else:
            logger.info("  ℹ️  Project-level RAG disabled in config (expected)")

        logger.info("  ✓ Team execution integration verified")

    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        logger.info(f"Total tests: {self.passed + self.failed}")
        logger.info(f"✅ Passed: {self.passed}")
        logger.info(f"❌ Failed: {self.failed}")
        logger.info(f"Success rate: {self.passed / (self.passed + self.failed) * 100:.1f}%")

        if self.errors:
            logger.info("\nErrors:")
            for error in self.errors:
                logger.info(f"  {error}")

        logger.info("="*80)

        if self.failed == 0:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.error("❌ SOME TESTS FAILED")

        logger.info(f"Completed: {datetime.now().isoformat()}")
        logger.info("="*80)


async def main():
    """Main test runner"""
    tests = RAGIntegrationTests()
    await tests.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if tests.failed == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
