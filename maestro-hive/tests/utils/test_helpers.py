#!/usr/bin/env python3
"""
Test helper utilities for integration tests
"""

from typing import Dict, Any, List
import uuid


async def create_test_task(state_manager, team_id: str, **kwargs) -> str:
    """Create a test task with sensible defaults"""
    defaults = {
        "title": f"Test Task {uuid.uuid4().hex[:6]}",
        "description": "Integration test task",
        "status": "ready"
    }
    defaults.update(kwargs)

    task_id = await state_manager.create_task(
        team_id=team_id,
        **defaults
    )
    return task_id


async def create_test_contract(
    contract_manager,
    team_id: str,
    contract_name: str = "TestAPI",
    version: str = "v1.0"
) -> Dict[str, Any]:
    """Create a test contract"""
    return await contract_manager.create_contract(
        team_id=team_id,
        contract_name=contract_name,
        version=version,
        contract_type="REST_API",
        specification={
            "endpoints": [
                {"path": "/test", "method": "GET"}
            ],
            "schemas": {}
        },
        owner_role="Tech Lead",
        owner_agent="architect_001",
        consumers=["backend_001", "frontend_001"]
    )


async def create_test_assumption(
    assumption_tracker,
    team_id: str,
    made_by_agent: str = "backend_001",
    **kwargs
) -> Dict[str, Any]:
    """Create a test assumption"""
    defaults = {
        "made_by_role": "Backend Lead",
        "assumption_text": "Test data structure assumption",
        "assumption_category": "data_structure",
        "related_artifact_type": "contract",
        "related_artifact_id": "test_contract_001"
    }
    defaults.update(kwargs)

    return await assumption_tracker.track_assumption(
        team_id=team_id,
        made_by_agent=made_by_agent,
        **defaults
    )


async def add_test_member(
    state_manager,
    team_id: str,
    agent_id: str,
    persona_id: str
) -> Dict[str, Any]:
    """Add a test team member"""
    return await state_manager.add_team_member(
        team_id=team_id,
        agent_id=agent_id,
        persona_id=persona_id
    )


def assert_metric_in_range(value: float, min_val: float, max_val: float, metric_name: str = "metric"):
    """Assert a metric is within expected range"""
    assert min_val <= value <= max_val, \
        f"{metric_name} {value} not in expected range [{min_val}, {max_val}]"


def assert_contains_keys(data: Dict, required_keys: List[str]):
    """Assert dictionary contains all required keys"""
    missing = [key for key in required_keys if key not in data]
    assert not missing, f"Missing required keys: {missing}"
