"""
Team Coordinator - Main orchestration for multi-agent teams
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

from claude_code_sdk import (
    tool,
    create_sdk_mcp_server,
    ClaudeSDKClient,
    ClaudeCodeOptions,
    McpSdkServerConfig
)


@dataclass
class TeamConfig:
    """Team configuration"""
    team_id: str = field(default_factory=lambda: f"team_{uuid.uuid4().hex[:8]}")
    workspace_path: Path = field(default_factory=lambda: Path("./team_workspace"))
    max_agents: int = 10
    enable_logging: bool = True
    coordination_interval: float = 0.5  # seconds

    def __post_init__(self):
        self.workspace_path = Path(self.workspace_path)
        self.workspace_path.mkdir(parents=True, exist_ok=True)


class TeamCoordinator:
    """
    Main coordinator for multi-agent team collaboration.

    Features:
    - True multi-agent with separate processes
    - Shared MCP server for inter-agent communication
    - Real-time bidirectional messaging
    - Task queue and workload distribution
    - Shared knowledge base
    - Agent status tracking

    Example:
        ```python
        coordinator = TeamCoordinator(TeamConfig())

        # Create shared coordination server
        coord_server = await coordinator.create_coordination_server()

        # Spawn agents
        architect = await coordinator.spawn_agent("architect", coord_server)
        developer = await coordinator.spawn_agent("developer", coord_server)

        # Execute team task
        result = await coordinator.execute_team_task("Build a REST API")
        ```
    """

    def __init__(self, config: TeamConfig):
        self.config = config
        self.team_id = config.team_id
        self.workspace = config.workspace_path

        # Shared state (in-memory)
        self.shared_workspace = {
            "messages": [],
            "tasks": {},
            "knowledge": {},
            "agent_status": {},
            "artifacts": {},
            "decisions": []
        }

        # Agent tracking
        self.agents: Dict[str, Any] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}

        # Coordination
        self._coordination_lock = asyncio.Lock()
        self._event_queue = asyncio.Queue()
        self._running = False

    def create_coordination_server(self) -> McpSdkServerConfig:
        """
        Create shared MCP coordination server for team communication.

        Returns:
            McpSdkServerConfig ready to be shared across all agents
        """

        # Agent Communication Tools
        @tool("post_message", "Post message to team channel", {
            "from_agent": str,
            "to_agent": str,
            "message": str,
            "message_type": str
        })
        async def post_message(args):
            async with self._coordination_lock:
                msg = {
                    "id": str(uuid.uuid4()),
                    "from": args["from_agent"],
                    "to": args.get("to_agent", "all"),
                    "message": args["message"],
                    "type": args.get("message_type", "info"),
                    "timestamp": datetime.now().isoformat()
                }
                self.shared_workspace["messages"].append(msg)

                # Broadcast to event queue
                await self._event_queue.put({
                    "type": "message",
                    "data": msg
                })

            return {
                "content": [{
                    "type": "text",
                    "text": f"Message posted from {args['from_agent']}"
                }]
            }

        @tool("get_messages", "Get messages from team channel", {
            "agent_id": str,
            "limit": int
        })
        async def get_messages(args):
            agent_id = args["agent_id"]
            limit = args.get("limit", 10)

            # Filter messages for this agent
            messages = [
                m for m in self.shared_workspace["messages"]
                if m["to"] == "all" or m["to"] == agent_id
            ][-limit:]

            msg_text = "\n".join([
                f"[{m['from']}]: {m['message']}" for m in messages
            ])

            return {
                "content": [{
                    "type": "text",
                    "text": msg_text or "No messages"
                }]
            }

        @tool("claim_task", "Claim a task from the queue", {
            "agent_id": str,
            "agent_role": str
        })
        async def claim_task(args):
            agent_id = args["agent_id"]
            agent_role = args["agent_role"]

            async with self._coordination_lock:
                # Find unclaimed task matching agent role
                for task_id, task in self.shared_workspace["tasks"].items():
                    if (task.get("status") == "pending" and
                        task.get("required_role") in [agent_role, "any"]):

                        task["status"] = "in_progress"
                        task["assigned_to"] = agent_id
                        task["claimed_at"] = datetime.now().isoformat()

                        return {
                            "content": [{
                                "type": "text",
                                "text": f"Task claimed: {task_id}\n{task['description']}"
                            }]
                        }

            return {
                "content": [{
                    "type": "text",
                    "text": "No tasks available"
                }]
            }

        @tool("complete_task", "Mark task as complete", {
            "agent_id": str,
            "task_id": str,
            "result": str
        })
        async def complete_task(args):
            task_id = args["task_id"]

            async with self._coordination_lock:
                if task_id in self.shared_workspace["tasks"]:
                    self.shared_workspace["tasks"][task_id]["status"] = "completed"
                    self.shared_workspace["tasks"][task_id]["result"] = args.get("result", "")
                    self.shared_workspace["tasks"][task_id]["completed_at"] = datetime.now().isoformat()

                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Task {task_id} marked complete"
                        }]
                    }

            return {
                "content": [{
                    "type": "text",
                    "text": f"Task {task_id} not found"
                }]
            }

        @tool("share_knowledge", "Share knowledge with team", {
            "agent_id": str,
            "key": str,
            "value": str,
            "category": str
        })
        async def share_knowledge(args):
            async with self._coordination_lock:
                key = args["key"]
                self.shared_workspace["knowledge"][key] = {
                    "value": args["value"],
                    "category": args.get("category", "general"),
                    "from": args["agent_id"],
                    "timestamp": datetime.now().isoformat()
                }

            return {
                "content": [{
                    "type": "text",
                    "text": f"Knowledge '{key}' shared with team"
                }]
            }

        @tool("get_knowledge", "Get knowledge from team", {
            "key": str
        })
        async def get_knowledge(args):
            key = args["key"]

            if key in self.shared_workspace["knowledge"]:
                k = self.shared_workspace["knowledge"][key]
                return {
                    "content": [{
                        "type": "text",
                        "text": f"{key}: {k['value']}\n(from {k['from']}, {k['category']})"
                    }]
                }

            return {
                "content": [{
                    "type": "text",
                    "text": f"Knowledge '{key}' not found"
                }]
            }

        @tool("update_status", "Update agent status", {
            "agent_id": str,
            "status": str,
            "current_task": str
        })
        async def update_status(args):
            async with self._coordination_lock:
                self.shared_workspace["agent_status"][args["agent_id"]] = {
                    "status": args["status"],
                    "current_task": args.get("current_task"),
                    "updated_at": datetime.now().isoformat()
                }

            return {
                "content": [{
                    "type": "text",
                    "text": "Status updated"
                }]
            }

        @tool("get_team_status", "Get status of all team members", {})
        async def get_team_status(args):
            status_text = "\n".join([
                f"{agent_id}: {info['status']} - {info.get('current_task', 'idle')}"
                for agent_id, info in self.shared_workspace["agent_status"].items()
            ])

            return {
                "content": [{
                    "type": "text",
                    "text": status_text or "No agents registered"
                }]
            }

        @tool("store_artifact", "Store work artifact", {
            "agent_id": str,
            "artifact_name": str,
            "artifact_data": str,
            "artifact_type": str
        })
        async def store_artifact(args):
            async with self._coordination_lock:
                artifact_id = str(uuid.uuid4())
                self.shared_workspace["artifacts"][artifact_id] = {
                    "name": args["artifact_name"],
                    "data": args["artifact_data"],
                    "type": args.get("artifact_type", "general"),
                    "created_by": args["agent_id"],
                    "created_at": datetime.now().isoformat()
                }

            return {
                "content": [{
                    "type": "text",
                    "text": f"Artifact stored: {artifact_id}"
                }]
            }

        @tool("get_artifacts", "Get team artifacts", {
            "artifact_type": str
        })
        async def get_artifacts(args):
            artifact_type = args.get("artifact_type", "all")

            artifacts = [
                f"{aid}: {a['name']} ({a['type']})"
                for aid, a in self.shared_workspace["artifacts"].items()
                if artifact_type == "all" or a["type"] == artifact_type
            ]

            return {
                "content": [{
                    "type": "text",
                    "text": "\n".join(artifacts) or "No artifacts"
                }]
            }

        @tool("propose_decision", "Propose a team decision", {
            "agent_id": str,
            "decision": str,
            "rationale": str
        })
        async def propose_decision(args):
            async with self._coordination_lock:
                decision_id = str(uuid.uuid4())
                self.shared_workspace["decisions"].append({
                    "id": decision_id,
                    "decision": args["decision"],
                    "rationale": args.get("rationale", ""),
                    "proposed_by": args["agent_id"],
                    "votes": {},
                    "status": "pending",
                    "timestamp": datetime.now().isoformat()
                })

            return {
                "content": [{
                    "type": "text",
                    "text": f"Decision proposed: {decision_id}"
                }]
            }

        @tool("vote_decision", "Vote on a team decision", {
            "agent_id": str,
            "decision_id": str,
            "vote": str
        })
        async def vote_decision(args):
            decision_id = args["decision_id"]
            vote = args["vote"]  # "approve", "reject", "abstain"

            async with self._coordination_lock:
                for decision in self.shared_workspace["decisions"]:
                    if decision["id"] == decision_id:
                        decision["votes"][args["agent_id"]] = vote

                        return {
                            "content": [{
                                "type": "text",
                                "text": f"Vote recorded: {vote}"
                            }]
                        }

            return {
                "content": [{
                    "type": "text",
                    "text": "Decision not found"
                }]
            }

        # Create coordination server with all tools
        return create_sdk_mcp_server(
            name=f"team_coordination_{self.team_id}",
            version="1.0.0",
            tools=[
                post_message,
                get_messages,
                claim_task,
                complete_task,
                share_knowledge,
                get_knowledge,
                update_status,
                get_team_status,
                store_artifact,
                get_artifacts,
                propose_decision,
                vote_decision
            ]
        )

    async def add_task(self, description: str, required_role: str = "any", priority: int = 5):
        """Add task to team queue"""
        async with self._coordination_lock:
            task_id = f"task_{len(self.shared_workspace['tasks'])}"
            self.shared_workspace["tasks"][task_id] = {
                "id": task_id,
                "description": description,
                "required_role": required_role,
                "priority": priority,
                "status": "pending",
                "created_at": datetime.now().isoformat()
            }
        return task_id

    async def get_workspace_state(self) -> Dict[str, Any]:
        """Get current workspace state"""
        async with self._coordination_lock:
            return {
                "team_id": self.team_id,
                "active_agents": len(self.shared_workspace["agent_status"]),
                "messages": len(self.shared_workspace["messages"]),
                "tasks": {
                    "total": len(self.shared_workspace["tasks"]),
                    "pending": sum(1 for t in self.shared_workspace["tasks"].values() if t["status"] == "pending"),
                    "in_progress": sum(1 for t in self.shared_workspace["tasks"].values() if t["status"] == "in_progress"),
                    "completed": sum(1 for t in self.shared_workspace["tasks"].values() if t["status"] == "completed"),
                },
                "knowledge_items": len(self.shared_workspace["knowledge"]),
                "artifacts": len(self.shared_workspace["artifacts"]),
                "decisions": len(self.shared_workspace["decisions"])
            }

    async def shutdown(self):
        """Shutdown team coordination"""
        self._running = False

        # Cancel all agent tasks
        for task in self.agent_tasks.values():
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.agent_tasks.values(), return_exceptions=True)

        self.agents.clear()
        self.agent_tasks.clear()
