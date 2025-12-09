#!/usr/bin/env python3
"""
Close original EPICs/Tasks after successful remediation.
"""
import asyncio
import logging
from jira_task_adapter import JiraTaskAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def close_original_tickets():
    adapter = JiraTaskAdapter()
    
    # List of original tickets that have been remediated/deployed
    tickets_to_close = [
        # Global Compliance Remediation
        {"key": "MD-2156", "msg": "Deployed Personal Data & Privacy (GDPR) to src/maestro_hive/gdpr/."},
        {"key": "MD-2159", "msg": "Deployed Technical Documentation to src/maestro_hive/technical_docs/."},
        {"key": "MD-2332", "msg": "Deployed EU AI Act & GDPR Initiative to src/maestro_hive/eu_ai_act/."},
        {"key": "MD-2334", "msg": "Deployed AI Security and Robustness to src/maestro_hive/security/."},
        {"key": "MD-2371", "msg": "Deployed Team-Based Artifact Generation to src/maestro_hive/frontend_assets/team_artifacts/."},
        {"key": "MD-2484", "msg": "Deployed Enterprise Features to src/maestro_hive/enterprise/."},
        {"key": "MD-2502", "msg": "Deployed CLI Slash Command Interface to src/maestro_hive/cli/."},
        {"key": "MD-2510", "msg": "Corrected deployment of Block Promotion Pipeline to src/maestro_hive/orchestration/block_promotion.py."},
        {"key": "MD-2554", "msg": "Deployed Persona Schema Definition to src/maestro_hive/persona_engine/."}
    ]

    for ticket in tickets_to_close:
        key = ticket["key"]
        msg = ticket["msg"]
        
        comment = f"""✅ **Remediation Complete**

The compliance gaps identified for this item have been resolved.
**Action Taken**: {msg}

The code is now deployed in the production codebase and no longer exists solely as a mockup/proof-of-concept.
"""
        logger.info(f"Closing original ticket {key}...")
        
        # Add comment
        success = await adapter.add_comment(key, comment)
        if success:
            logger.info(f"  - Comment added")
        else:
            logger.error(f"  - Failed to add comment to {key}")
            
        # Update status to Done
        success = await adapter.update_task_status(key, "Done")
        if success:
            logger.info(f"  - Status updated to Done")
        else:
            logger.error(f"  - Failed to update status for {key}")

if __name__ == "__main__":
    asyncio.run(close_original_tickets())
