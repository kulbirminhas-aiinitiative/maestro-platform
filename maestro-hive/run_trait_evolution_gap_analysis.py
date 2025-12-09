import os
import sys
import logging
from pathlib import Path
from src.maestro_hive.core.self_reflection.gap_to_jira import GapToJira, JiraConfig
from src.maestro_hive.core.self_reflection.gap_detector import GapDetector

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_gap_analysis():
    try:
        logger.info("Starting Gap Analysis for 'Trait Evolution'...")
        
        # Configuration
        workspace_root = "/home/ec2-user/projects/maestro-platform/maestro-hive"
        registry_path = "src/maestro_hive/core/self_reflection/registry.json"
        scope = "persona_trait_management"
        parent_epic = "MD-2883"

        # Load JIRA Config
        try:
            config = JiraConfig.from_env()
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)

        # Run Gap Detection
        logger.info(f"Scanning workspace: {workspace_root}")
        detector = GapDetector(workspace_root, registry_path)
        gaps = detector.scan(scope=scope)

        if not gaps:
            logger.info("No gaps detected. System is healthy!")
            return

        logger.info(f"Found {len(gaps)} gaps")

        # Sync to JIRA
        gap_to_jira = GapToJira(config, parent_epic=parent_epic)
        results = gap_to_jira.sync_gaps(gaps)
        
        logger.info("Gap Analysis complete.")
        
    except Exception as e:
        logger.error(f"Gap Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_gap_analysis()
