"""
Discussion manager for orchestrating multi-agent conversations.

Manages discussion sessions, coordinates agents using AutoGen's GroupChat,
and handles persistence through SharedContext.
"""
from __future__ import annotations
from typing import Dict, List, Optional, AsyncIterator, Callable, Any
from datetime import datetime
from uuid import uuid4
import asyncio
import logging

try:
    from autogen import Agent, GroupChat, GroupChatManager
except ImportError:
    # Define stub classes if autogen not installed
    class Agent:
        pass

    class GroupChat:
        def __init__(self, *args, **kwargs):
            raise ImportError("pyautogen is not installed")

    class GroupChatManager:
        def __init__(self, *args, **kwargs):
            raise ImportError("pyautogen is not installed")

from .agent_factory import AgentFactory
from .context import SharedContext
from .models import (
    DiscussionSession,
    DiscussionRequest,
    Message,
    Participant,
    ParticipantType,
    MessageType,
    DiscussionStatus,
)
from .discussion_protocols import create_protocol, DiscussionProtocol

logger = logging.getLogger(__name__)


class DiscussionManager:
    """
    Manager for multi-agent discussion sessions.

    Coordinates agents using AutoGen's GroupChat, integrates with
    execution-platform for LLM calls, and persists state to Redis
    via SharedContext.
    """

    def __init__(
        self,
        agent_factory: AgentFactory,
        shared_context: SharedContext
    ):
        """
        Initialize DiscussionManager.

        Args:
            agent_factory: Factory for creating AutoGen agents
            shared_context: Shared context for persistence
        """
        self.agent_factory = agent_factory
        self.shared_context = shared_context
        self._active_sessions: Dict[str, GroupChatManager] = {}
        self._message_callbacks: Dict[str, List[Callable]] = {}
        logger.info("DiscussionManager initialized")

    async def create_discussion(
        self,
        request: DiscussionRequest
    ) -> DiscussionSession:
        """
        Create a new discussion session.

        Args:
            request: Discussion request configuration

        Returns:
            Created DiscussionSession

        Raises:
            ValueError: If request is invalid
        """
        try:
            # Validate request
            if not request.agents:
                raise ValueError("At least one agent is required")

            # Create session ID
            session_id = f"disc_{uuid4().hex}"

            # Create agents using factory
            agents = []
            participants = []

            for agent_config in request.agents:
                # Create AutoGen agent
                agent = self.agent_factory.create_agent(
                    agent_config=agent_config,
                    system_message=agent_config.system_prompt,
                )
                agents.append(agent)

                # Create participant record
                participant = Participant(
                    participant_id=agent_config.agent_id,
                    name=agent_config.agent_id,
                    participant_type=ParticipantType.AGENT,
                    config=agent_config.model_dump(),
                )
                participants.append(participant)

            # Add human participants
            for human_config in request.humans:
                participant = Participant(
                    participant_id=human_config.user_id,
                    name=human_config.name,
                    participant_type=ParticipantType.HUMAN,
                    config=human_config.model_dump(),
                )
                participants.append(participant)

            # Create discussion session
            session = DiscussionSession(
                id=session_id,
                topic=request.topic,
                protocol=request.protocol,
                participants=participants,
                status=DiscussionStatus.PENDING,
                max_rounds=request.max_rounds,
                context=request.context or {},
            )

            # Persist to SharedContext
            created = await self.shared_context.create_session(session)
            if not created:
                raise RuntimeError(f"Failed to create session {session_id}")

            logger.info(
                f"Created discussion {session_id} with {len(agents)} agents, "
                f"protocol: {request.protocol}"
            )

            return session

        except Exception as e:
            logger.error(f"Failed to create discussion: {e}", exc_info=True)
            raise

    async def start_discussion(
        self,
        session_id: str,
        initial_message: str,
        message_callback: Optional[Callable[[Message], None]] = None
    ) -> AsyncIterator[Message]:
        """
        Start a discussion session.

        Args:
            session_id: Discussion session ID
            initial_message: Initial message to start the discussion
            message_callback: Optional callback for each message

        Yields:
            Messages as they are generated

        Raises:
            ValueError: If session not found or invalid state
        """
        try:
            # Get session from context
            session = await self.shared_context.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            if session.status not in [DiscussionStatus.PENDING, DiscussionStatus.PAUSED]:
                raise ValueError(f"Session {session_id} is not in a startable state")

            # Update status to active
            session.status = DiscussionStatus.ACTIVE
            session.started_at = datetime.utcnow()
            await self.shared_context.update_session(session)

            # Register message callback
            if message_callback:
                if session_id not in self._message_callbacks:
                    self._message_callbacks[session_id] = []
                self._message_callbacks[session_id].append(message_callback)

            # Get agents
            agents = self._get_session_agents(session)

            # Create protocol
            protocol = create_protocol(
                session.protocol.value,
                max_rounds=session.max_rounds
            )

            # Add initial message
            initial_msg = Message(
                participant_id="system",
                participant_name="System",
                participant_type=ParticipantType.HUMAN,
                content=initial_message,
                message_type=MessageType.TEXT,
            )
            await self.shared_context.add_message(session_id, initial_msg)
            yield initial_msg

            # Notify callbacks
            await self._notify_callbacks(session_id, initial_msg)

            # Create GroupChat
            groupchat = GroupChat(
                agents=agents,
                messages=[],
                max_round=protocol.get_max_round() or 10,
                speaker_selection_method=(
                    protocol.create_speaker_selection_func(agents)
                    if protocol.create_speaker_selection_func(agents)
                    else "auto"
                ),
            )

            # Create GroupChatManager
            manager = GroupChatManager(
                groupchat=groupchat,
                llm_config=agents[0].llm_config if agents else {},
            )

            self._active_sessions[session_id] = manager

            # Notify protocol
            protocol.on_discussion_start(agents)

            # Start discussion with async iteration
            logger.info(f"Starting discussion {session_id}")

            # Initiate the chat asynchronously
            # Note: AutoGen's initiate_chat may need to be wrapped
            async for msg in self._run_discussion(
                session_id,
                manager,
                agents[0] if agents else None,
                initial_message,
            ):
                yield msg

            # Mark as completed
            session.status = DiscussionStatus.COMPLETED
            session.completed_at = datetime.utcnow()
            await self.shared_context.update_session(session)

            protocol.on_discussion_end(groupchat.messages)

            logger.info(f"Discussion {session_id} completed")

        except Exception as e:
            logger.error(f"Error in start_discussion: {e}", exc_info=True)
            # Mark session as failed
            try:
                session = await self.shared_context.get_session(session_id)
                if session:
                    session.status = DiscussionStatus.FAILED
                    await self.shared_context.update_session(session)
            except:
                pass
            raise

    async def add_human_message(
        self,
        session_id: str,
        user_id: str,
        message: str
    ) -> Message:
        """
        Add a human message to the discussion.

        Args:
            session_id: Discussion session ID
            user_id: User identifier
            message: Message content

        Returns:
            Created Message object

        Raises:
            ValueError: If session not found or user not a participant
        """
        try:
            # Get session
            session = await self.shared_context.get_session(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            # Find participant
            participant = next(
                (p for p in session.participants if p.participant_id == user_id),
                None
            )
            if not participant:
                raise ValueError(f"User {user_id} is not a participant")

            # Create message
            msg = Message(
                participant_id=user_id,
                participant_name=participant.name,
                participant_type=ParticipantType.HUMAN,
                content=message,
                message_type=MessageType.TEXT,
            )

            # Persist message
            await self.shared_context.add_message(session_id, msg)

            # Notify callbacks
            await self._notify_callbacks(session_id, msg)

            logger.info(f"Added human message from {user_id} to {session_id}")

            return msg

        except Exception as e:
            logger.error(f"Failed to add human message: {e}", exc_info=True)
            raise

    async def get_session(self, session_id: str) -> Optional[DiscussionSession]:
        """
        Get discussion session.

        Args:
            session_id: Session ID

        Returns:
            DiscussionSession or None if not found
        """
        return await self.shared_context.get_session(session_id)

    async def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """
        Get discussion message history.

        Args:
            session_id: Session ID
            limit: Max messages to retrieve
            offset: Offset from start

        Returns:
            List of messages
        """
        return await self.shared_context.get_history(session_id, limit, offset)

    async def pause_discussion(self, session_id: str) -> bool:
        """
        Pause a discussion.

        Args:
            session_id: Session ID

        Returns:
            True if paused successfully
        """
        try:
            session = await self.shared_context.get_session(session_id)
            if not session:
                return False

            session.status = DiscussionStatus.PAUSED
            await self.shared_context.update_session(session)

            # Remove from active sessions
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]

            logger.info(f"Paused discussion {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to pause discussion: {e}")
            return False

    async def stop_discussion(self, session_id: str) -> bool:
        """
        Stop a discussion permanently.

        Args:
            session_id: Session ID

        Returns:
            True if stopped successfully
        """
        try:
            await self.shared_context.update_status(
                session_id,
                DiscussionStatus.COMPLETED
            )

            # Remove from active sessions
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]

            logger.info(f"Stopped discussion {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stop discussion: {e}")
            return False

    def _get_session_agents(self, session: DiscussionSession) -> List[Agent]:
        """
        Get AutoGen agents for a session.

        Args:
            session: Discussion session

        Returns:
            List of agents
        """
        agents = []
        for participant in session.participants:
            if participant.participant_type == ParticipantType.AGENT:
                agent = self.agent_factory.get_agent(participant.participant_id)
                if agent:
                    agents.append(agent)
        return agents

    async def _run_discussion(
        self,
        session_id: str,
        manager: GroupChatManager,
        initiator: Optional[Agent],
        initial_message: str,
    ) -> AsyncIterator[Message]:
        """
        Run the discussion and yield messages.

        Args:
            session_id: Session ID
            manager: GroupChatManager
            initiator: Agent to initiate the chat
            initial_message: Initial message

        Yields:
            Messages as they are generated
        """
        try:
            # This is a simplified implementation
            # In a real implementation, we'd need to:
            # 1. Properly integrate with AutoGen's async chat
            # 2. Intercept and yield messages as they're generated
            # 3. Stream responses in real-time

            # For now, we'll use a callback-based approach
            messages_queue = asyncio.Queue()

            def message_handler(sender, message, recipient):
                """Handle messages from AutoGen."""
                msg = Message(
                    participant_id=sender.name,
                    participant_name=sender.name,
                    participant_type=ParticipantType.AGENT,
                    content=message if isinstance(message, str) else message.get("content", ""),
                    message_type=MessageType.TEXT,
                )
                # Put in queue for async iteration
                asyncio.create_task(messages_queue.put(msg))

            # Note: This is a simplified implementation
            # Real AutoGen integration would require proper async handling
            # and message interception

            # Run chat in thread pool to not block
            loop = asyncio.get_event_loop()

            def run_chat():
                try:
                    if initiator:
                        initiator.initiate_chat(
                            manager,
                            message=initial_message,
                        )
                except Exception as e:
                    logger.error(f"Error in chat execution: {e}")
                finally:
                    # Signal completion
                    asyncio.run_coroutine_threadsafe(
                        messages_queue.put(None),
                        loop
                    )

            # Start chat in executor
            await loop.run_in_executor(None, run_chat)

            # Yield messages as they come
            while True:
                msg = await messages_queue.get()
                if msg is None:  # Completion signal
                    break

                # Persist message
                await self.shared_context.add_message(session_id, msg)

                # Notify callbacks
                await self._notify_callbacks(session_id, msg)

                yield msg

        except Exception as e:
            logger.error(f"Error running discussion: {e}", exc_info=True)
            raise

    async def _notify_callbacks(self, session_id: str, message: Message) -> None:
        """
        Notify registered callbacks of a new message.

        Args:
            session_id: Session ID
            message: New message
        """
        callbacks = self._message_callbacks.get(session_id, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")
