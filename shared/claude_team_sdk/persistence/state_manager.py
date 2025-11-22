"""
Unified state manager combining PostgreSQL and Redis
Provides high-level API for all persistence operations
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from .database import DatabaseManager
from .redis_manager import RedisManager, RedisCacheKey, RedisEventChannel
from .models import (
    Message, Task, KnowledgeItem, Artifact, AgentState,
    Decision, WorkflowDefinition, TaskStatus, MessageType
)


class StateManager:
    """
    Unified state manager for Claude Team SDK
    Combines PostgreSQL (source of truth) and Redis (caching + pub/sub)
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        redis_manager: RedisManager,
        cache_ttl: int = 300  # 5 minutes default
    ):
        """
        Initialize state manager

        Args:
            db_manager: Database manager instance
            redis_manager: Redis manager instance
            cache_ttl: Default cache TTL in seconds
        """
        self.db = db_manager
        self.redis = redis_manager
        self.cache_ttl = cache_ttl

    # =========================================================================
    # Message Operations
    # =========================================================================

    async def post_message(
        self,
        team_id: str,
        from_agent: str,
        message: str,
        to_agent: Optional[str] = None,
        message_type: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a message (with caching and pub/sub)"""
        msg_id = str(uuid.uuid4())

        # Create message in database
        msg = Message(
            id=msg_id,
            team_id=team_id,
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=MessageType(message_type),
            content=message,
            metadata=metadata or {},
            thread_id=thread_id
        )

        async with self.db.session() as session:
            session.add(msg)

        # Cache recent messages
        cache_key = RedisCacheKey.message_cache(team_id)
        await self.redis.lpush(cache_key, msg.to_dict().__str__())
        await self.redis.expire(cache_key, self.cache_ttl)

        # Publish event
        await self.redis.publish_event(
            f"team:{team_id}:events:message.posted",
            "message.posted",
            {
                "message_id": msg_id,
                "from": from_agent,
                "to": to_agent,
                "type": message_type
            }
        )

        return msg.to_dict()

    async def get_messages(
        self,
        team_id: str,
        agent_id: Optional[str] = None,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get messages for team/agent"""
        async with self.db.session() as session:
            query = select(Message).where(Message.team_id == team_id)

            if agent_id:
                query = query.where(
                    or_(
                        Message.to_agent == agent_id,
                        Message.to_agent.is_(None),  # Broadcasts
                        Message.from_agent == agent_id
                    )
                )

            if since:
                query = query.where(Message.timestamp >= since)

            query = query.order_by(Message.timestamp.desc()).limit(limit)
            result = await session.execute(query)
            messages = result.scalars().all()

        return [msg.to_dict() for msg in messages]

    # =========================================================================
    # Task Operations with DAG Support
    # =========================================================================

    async def create_task(
        self,
        team_id: str,
        title: str,
        description: str,
        created_by: str,
        required_role: Optional[str] = None,
        priority: int = 0,
        parent_task_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Create a task with optional dependencies"""
        task_id = str(uuid.uuid4())

        task = Task(
            id=task_id,
            team_id=team_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            required_role=required_role,
            created_by=created_by,
            parent_task_id=parent_task_id,
            workflow_id=workflow_id,
            metadata=metadata or {},
            tags=tags or []
        )

        async with self.db.session() as session:
            # Add task
            session.add(task)
            await session.flush()

            # Add dependencies if specified
            if depends_on:
                for dep_id in depends_on:
                    dep_task = await session.get(Task, dep_id)
                    if dep_task:
                        task.dependencies.append(dep_task)

            await session.commit()
            await session.refresh(task)

        # Check if task is ready (all dependencies met)
        if not depends_on or await self._check_dependencies_complete(task_id):
            await self.update_task_status(task_id, TaskStatus.READY)

        # Publish event
        await self.redis.publish_event(
            RedisEventChannel.task_created(team_id),
            "task.created",
            {
                "task_id": task_id,
                "title": title,
                "required_role": required_role,
                "priority": priority
            }
        )

        return task.to_dict()

    async def claim_task(
        self,
        task_id: str,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Claim a task (with distributed lock)"""
        lock_name = f"task_lock:{task_id}"

        # Acquire lock
        acquired = await self.redis.acquire_lock(lock_name, timeout=30)
        if not acquired:
            return None

        try:
            async with self.db.session() as session:
                task = await session.get(Task, task_id)

                if not task or task.assigned_to:
                    return None

                # Verify dependencies are complete
                if not task.can_execute():
                    return None

                # Claim task
                task.assigned_to = agent_id
                task.status = TaskStatus.RUNNING
                task.claimed_at = datetime.utcnow()

                await session.commit()
                await session.refresh(task)

            # Publish event
            await self.redis.publish_event(
                f"team:{task.team_id}:events:task.claimed",
                "task.claimed",
                {
                    "task_id": task_id,
                    "agent_id": agent_id
                }
            )

            return task.to_dict()

        finally:
            await self.redis.release_lock(lock_name)

    async def complete_task(
        self,
        task_id: str,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Complete a task"""
        async with self.db.session() as session:
            task = await session.get(Task, task_id)

            if not task:
                raise ValueError(f"Task {task_id} not found")

            task.status = TaskStatus.SUCCESS
            task.completed_at = datetime.utcnow()
            task.result = result

            # Update agent metrics
            agent_state = await session.execute(
                select(AgentState).where(
                    and_(
                        AgentState.team_id == task.team_id,
                        AgentState.agent_id == task.assigned_to
                    )
                )
            )
            agent = agent_state.scalar_one_or_none()
            if agent:
                agent.tasks_completed += 1

            await session.commit()
            await session.refresh(task)

        # Check if this completion unlocks dependent tasks
        await self._check_and_unlock_dependent_tasks(task_id)

        # Publish event
        await self.redis.publish_event(
            RedisEventChannel.task_completed(task.team_id),
            "task.completed",
            {
                "task_id": task_id,
                "agent_id": task.assigned_to,
                "result": result
            }
        )

        return task.to_dict()

    async def fail_task(
        self,
        task_id: str,
        error: str
    ) -> Dict[str, Any]:
        """Mark task as failed"""
        async with self.db.session() as session:
            task = await session.get(Task, task_id)

            if not task:
                raise ValueError(f"Task {task_id} not found")

            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.utcnow()

            # Update agent metrics
            agent_state = await session.execute(
                select(AgentState).where(
                    and_(
                        AgentState.team_id == task.team_id,
                        AgentState.agent_id == task.assigned_to
                    )
                )
            )
            agent = agent_state.scalar_one_or_none()
            if agent:
                agent.tasks_failed += 1

            await session.commit()
            await session.refresh(task)

        # Publish event
        await self.redis.publish_event(
            RedisEventChannel.task_failed(task.team_id),
            "task.failed",
            {
                "task_id": task_id,
                "agent_id": task.assigned_to,
                "error": error
            }
        )

        return task.to_dict()

    async def get_ready_tasks(
        self,
        team_id: str,
        role: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get tasks that are ready to execute"""
        async with self.db.session() as session:
            query = select(Task).where(
                and_(
                    Task.team_id == team_id,
                    Task.status == TaskStatus.READY,
                    Task.assigned_to.is_(None)
                )
            )

            if role:
                query = query.where(
                    or_(
                        Task.required_role == role,
                        Task.required_role.is_(None)
                    )
                )

            query = query.order_by(Task.priority.desc(), Task.created_at).limit(limit)
            result = await session.execute(query)
            tasks = result.scalars().all()

        return [task.to_dict() for task in tasks]

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus
    ):
        """Update task status"""
        async with self.db.session() as session:
            await session.execute(
                update(Task).where(Task.id == task_id).values(status=status)
            )

    async def _check_dependencies_complete(self, task_id: str) -> bool:
        """Check if all task dependencies are complete"""
        async with self.db.session() as session:
            task = await session.execute(
                select(Task).where(Task.id == task_id).options(
                    selectinload(Task.dependencies)
                )
            )
            task_obj = task.scalar_one()
            return task_obj.can_execute()

    async def _check_and_unlock_dependent_tasks(self, completed_task_id: str):
        """Check and unlock tasks that depended on this task"""
        async with self.db.session() as session:
            # Get all tasks that depend on this one
            result = await session.execute(
                select(Task).where(Task.status == TaskStatus.BLOCKED).options(
                    selectinload(Task.dependencies)
                )
            )
            blocked_tasks = result.scalars().all()

            for task in blocked_tasks:
                if task.can_execute():
                    task.status = TaskStatus.READY

            await session.commit()

    # =========================================================================
    # Knowledge Operations
    # =========================================================================

    async def share_knowledge(
        self,
        team_id: str,
        key: str,
        value: str,
        source_agent: str,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Share knowledge (upsert)"""
        async with self.db.session() as session:
            # Check if key already exists
            result = await session.execute(
                select(KnowledgeItem).where(
                    and_(
                        KnowledgeItem.team_id == team_id,
                        KnowledgeItem.key == key
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                existing.value = value
                existing.source_agent = source_agent
                existing.updated_at = datetime.utcnow()
                existing.version += 1
                existing.metadata = metadata or {}
                existing.tags = tags or []
                if category:
                    existing.category = category
                await session.commit()
                await session.refresh(existing)
                knowledge = existing
            else:
                knowledge = KnowledgeItem(
                    id=str(uuid.uuid4()),
                    team_id=team_id,
                    key=key,
                    value=value,
                    category=category,
                    source_agent=source_agent,
                    metadata=metadata or {},
                    tags=tags or []
                )
                session.add(knowledge)
                await session.commit()
                await session.refresh(knowledge)

        # Publish event
        await self.redis.publish_event(
            RedisEventChannel.knowledge_shared(team_id),
            "knowledge.shared",
            {
                "key": key,
                "category": category,
                "agent": source_agent
            }
        )

        return knowledge.to_dict()

    async def get_knowledge(
        self,
        team_id: str,
        key: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get knowledge items"""
        async with self.db.session() as session:
            query = select(KnowledgeItem).where(KnowledgeItem.team_id == team_id)

            if key:
                query = query.where(KnowledgeItem.key == key)
            if category:
                query = query.where(KnowledgeItem.category == category)

            query = query.order_by(KnowledgeItem.updated_at.desc())
            result = await session.execute(query)
            items = result.scalars().all()

        return [item.to_dict() for item in items]

    # =========================================================================
    # Agent State Operations
    # =========================================================================

    async def update_agent_status(
        self,
        team_id: str,
        agent_id: str,
        role: str,
        status: str,
        message: Optional[str] = None,
        current_task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update agent status"""
        async with self.db.session() as session:
            result = await session.execute(
                select(AgentState).where(
                    and_(
                        AgentState.team_id == team_id,
                        AgentState.agent_id == agent_id
                    )
                )
            )
            agent = result.scalar_one_or_none()

            if agent:
                agent.status = status
                agent.role = role
                agent.message = message
                agent.current_task_id = current_task_id
                agent.metadata = metadata or {}
                agent.updated_at = datetime.utcnow()
            else:
                agent = AgentState(
                    team_id=team_id,
                    agent_id=agent_id,
                    role=role,
                    status=status,
                    message=message,
                    current_task_id=current_task_id,
                    metadata=metadata or {}
                )
                session.add(agent)

            await session.commit()
            await session.refresh(agent)

        # Cache in Redis
        cache_key = RedisCacheKey.agent_state(team_id, agent_id)
        await self.redis.set_json(cache_key, agent.to_dict(), expire=self.cache_ttl)

        # Publish event
        await self.redis.publish_event(
            RedisEventChannel.agent_status(team_id),
            "agent.status",
            {
                "agent_id": agent_id,
                "status": status
            }
        )

        return agent.to_dict()

    async def get_team_status(self, team_id: str) -> List[Dict[str, Any]]:
        """Get status of all agents in team"""
        async with self.db.session() as session:
            result = await session.execute(
                select(AgentState).where(AgentState.team_id == team_id)
            )
            agents = result.scalars().all()

        return [agent.to_dict() for agent in agents]

    # =========================================================================
    # Event Subscriptions
    # =========================================================================

    async def subscribe_to_events(
        self,
        team_id: str,
        event_pattern: str,
        callback: Callable[[str, Dict[str, Any]], None]
    ):
        """
        Subscribe to team events

        Args:
            team_id: Team ID
            event_pattern: Event pattern (e.g., "*" for all, "task.*" for tasks)
            callback: Async callback function
        """
        channel = f"team:{team_id}:events:{event_pattern}"
        await self.redis.subscribe(channel, callback)

    # =========================================================================
    # Health and Metrics
    # =========================================================================

    async def get_workspace_state(self, team_id: str) -> Dict[str, Any]:
        """Get overall workspace state"""
        async with self.db.session() as session:
            # Count messages
            msg_result = await session.execute(
                select(Message).where(Message.team_id == team_id)
            )
            message_count = len(msg_result.scalars().all())

            # Count tasks by status
            task_result = await session.execute(
                select(Task).where(Task.team_id == team_id)
            )
            tasks = task_result.scalars().all()

            task_counts = {}
            for task in tasks:
                status = task.status.value if isinstance(task.status, TaskStatus) else task.status
                task_counts[status] = task_counts.get(status, 0) + 1

            # Count knowledge items
            knowledge_result = await session.execute(
                select(KnowledgeItem).where(KnowledgeItem.team_id == team_id)
            )
            knowledge_count = len(knowledge_result.scalars().all())

            # Count decisions
            decision_result = await session.execute(
                select(Decision).where(Decision.team_id == team_id)
            )
            decision_count = len(decision_result.scalars().all())

        return {
            "messages": message_count,
            "tasks": task_counts,
            "knowledge_items": knowledge_count,
            "decisions": decision_count
        }

    # =========================================================================
    # Team Membership Operations (Dynamic Team Management)
    # =========================================================================

    async def add_team_member(
        self,
        team_id: str,
        agent_id: str,
        persona_id: str,
        role_id: str,
        added_by: str,
        reason: Optional[str] = None,
        initial_state: Optional['MembershipState'] = None
    ) -> Dict[str, Any]:
        """Add a new team member"""
        from .models import TeamMembership, MembershipState

        if initial_state is None:
            initial_state = MembershipState.INITIALIZING

        membership = TeamMembership(
            team_id=team_id,
            agent_id=agent_id,
            persona_id=persona_id,
            role_id=role_id,
            state=initial_state,
            added_by=added_by,
            added_reason=reason
        )

        async with self.db.session() as session:
            session.add(membership)
            await session.commit()
            await session.refresh(membership)

        # Publish event
        await self.redis.publish_event(
            f"team:{team_id}:events:member.added",
            "member.added",
            {
                "agent_id": agent_id,
                "persona_id": persona_id,
                "role_id": role_id,
                "added_by": added_by
            }
        )

        return membership.to_dict()

    async def update_member_state(
        self,
        team_id: str,
        agent_id: str,
        new_state: 'MembershipState',
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update team member state"""
        from .models import TeamMembership

        async with self.db.session() as session:
            result = await session.execute(
                select(TeamMembership).where(
                    and_(
                        TeamMembership.team_id == team_id,
                        TeamMembership.agent_id == agent_id
                    )
                )
            )
            membership = result.scalar_one_or_none()

            if not membership:
                raise ValueError(f"Member {agent_id} not found in team {team_id}")

            membership.update_state(new_state, reason)
            await session.commit()
            await session.refresh(membership)

        # Publish event
        await self.redis.publish_event(
            f"team:{team_id}:events:member.state_changed",
            "member.state_changed",
            {
                "agent_id": agent_id,
                "new_state": new_state.value if hasattr(new_state, 'value') else new_state,
                "reason": reason
            }
        )

        return membership.to_dict()

    async def get_team_members(
        self,
        team_id: str,
        state: Optional['MembershipState'] = None,
        persona_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get team members, optionally filtered by state or persona"""
        from .models import TeamMembership

        async with self.db.session() as session:
            query = select(TeamMembership).where(TeamMembership.team_id == team_id)

            if state:
                query = query.where(TeamMembership.state == state)
            if persona_id:
                query = query.where(TeamMembership.persona_id == persona_id)

            result = await session.execute(query)
            members = result.scalars().all()

        return [member.to_dict() for member in members]

    async def get_member_performance(
        self,
        team_id: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """Get performance metrics for a team member"""
        from .models import TeamMembership

        async with self.db.session() as session:
            # Get membership info
            membership_result = await session.execute(
                select(TeamMembership).where(
                    and_(
                        TeamMembership.team_id == team_id,
                        TeamMembership.agent_id == agent_id
                    )
                )
            )
            membership = membership_result.scalar_one_or_none()

            if not membership:
                return None

            # Get agent state for real-time metrics
            agent_result = await session.execute(
                select(AgentState).where(
                    and_(
                        AgentState.team_id == team_id,
                        AgentState.agent_id == agent_id
                    )
                )
            )
            agent = agent_result.scalar_one_or_none()

            # Get task statistics
            task_result = await session.execute(
                select(Task).where(
                    and_(
                        Task.team_id == team_id,
                        Task.assigned_to == agent_id
                    )
                )
            )
            tasks = task_result.scalars().all()

            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.SUCCESS)
            failed_tasks = sum(1 for t in tasks if t.status == TaskStatus.FAILED)

            # Calculate average task duration
            completed_with_duration = [
                (t.completed_at - t.claimed_at).total_seconds() / 3600
                for t in tasks
                if t.status == TaskStatus.SUCCESS and t.claimed_at and t.completed_at
            ]
            avg_duration = sum(completed_with_duration) / len(completed_with_duration) if completed_with_duration else None

            # Calculate completion rate
            completion_rate = int((completed_tasks / total_tasks * 100)) if total_tasks > 0 else 0

            return {
                "agent_id": agent_id,
                "persona_id": membership.persona_id,
                "state": membership.state.value if hasattr(membership.state, 'value') else membership.state,
                "performance_score": membership.performance_score,
                "task_completion_rate": completion_rate,
                "average_task_duration_hours": avg_duration,
                "collaboration_score": membership.collaboration_score,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "tasks_completed_from_agent_state": agent.tasks_completed if agent else 0,
                "tasks_failed_from_agent_state": agent.tasks_failed if agent else 0
            }

    async def update_member_performance(
        self,
        team_id: str,
        agent_id: str,
        performance_score: Optional[int] = None,
        task_completion_rate: Optional[int] = None,
        average_task_duration_hours: Optional[float] = None,
        collaboration_score: Optional[int] = None
    ) -> Dict[str, Any]:
        """Update performance metrics for a team member"""
        from .models import TeamMembership

        async with self.db.session() as session:
            result = await session.execute(
                select(TeamMembership).where(
                    and_(
                        TeamMembership.team_id == team_id,
                        TeamMembership.agent_id == agent_id
                    )
                )
            )
            membership = result.scalar_one_or_none()

            if not membership:
                raise ValueError(f"Member {agent_id} not found in team {team_id}")

            if performance_score is not None:
                membership.performance_score = performance_score
            if task_completion_rate is not None:
                membership.task_completion_rate = task_completion_rate
            if average_task_duration_hours is not None:
                membership.average_task_duration_hours = int(average_task_duration_hours)
            if collaboration_score is not None:
                membership.collaboration_score = collaboration_score

            await session.commit()
            await session.refresh(membership)

        return membership.to_dict()

    async def retire_team_member(
        self,
        team_id: str,
        agent_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """Retire a team member (graceful removal)"""
        from .models import MembershipState

        return await self.update_member_state(
            team_id=team_id,
            agent_id=agent_id,
            new_state=MembershipState.RETIRED,
            reason=reason
        )
