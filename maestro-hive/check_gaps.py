import logging
import sys
from maestro_hive.core.self_reflection.gap_detector import GapDetector
import os

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

registry_path = "src/maestro_hive/core/self_reflection/registry.json"
detector = GapDetector("/home/ec2-user/projects/maestro-platform/maestro-hive", registry_path)
gaps = detector.scan(scope="core")

print(f"Found {len(gaps)} gaps:")
for gap in gaps:
    print(f"- {gap.description} (Block: {gap.block_id})")
