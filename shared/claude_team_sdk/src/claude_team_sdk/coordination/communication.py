"""
Communication Protocols for Multi-Agent Teams
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Any
from datetime import datetime


class MessageType(str, Enum):
    """Message types for inter-agent communication"""
    INFO = "info"
    REQUEST = "request"
    RESPONSE = "response"
    ALERT = "alert"
    QUESTION = "question"
    DECISION = "decision"
    BROADCAST = "broadcast"


@dataclass
class Message:
    """Agent communication message"""
    id: str
    from_agent: str
    to_agent: str  # or "all" for broadcast
    content: str
    message_type: MessageType
    timestamp: str
    thread_id: Optional[str] = None  # For threaded conversations
    metadata: Optional[dict] = None

    def is_broadcast(self) -> bool:
        """Check if message is broadcast to all"""
        return self.to_agent == "all"

    def is_for_agent(self, agent_id: str) -> bool:
        """Check if message is for specific agent"""
        return self.to_agent == agent_id or self.is_broadcast()


class TeamChannel:
    """
    Team communication channel for structured messaging.

    Provides:
    - Threaded conversations
    - Message filtering
    - Broadcast capabilities
    - Message history
    """

    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        self.messages: List[Message] = []
        self.threads: dict[str, List[Message]] = {}

    def add_message(self, message: Message):
        """Add message to channel"""
        self.messages.append(message)

        # Add to thread if applicable
        if message.thread_id:
            if message.thread_id not in self.threads:
                self.threads[message.thread_id] = []
            self.threads[message.thread_id].append(message)

    def get_messages_for_agent(
        self,
        agent_id: str,
        limit: int = 10,
        message_type: Optional[MessageType] = None
    ) -> List[Message]:
        """Get messages for specific agent"""
        messages = [
            m for m in self.messages
            if m.is_for_agent(agent_id)
        ]

        # Filter by type if specified
        if message_type:
            messages = [m for m in messages if m.message_type == message_type]

        # Return most recent
        return messages[-limit:]

    def get_thread(self, thread_id: str) -> List[Message]:
        """Get messages in a thread"""
        return self.threads.get(thread_id, [])

    def get_unread_messages(
        self,
        agent_id: str,
        last_read_timestamp: str
    ) -> List[Message]:
        """Get unread messages for agent"""
        return [
            m for m in self.messages
            if m.is_for_agent(agent_id) and m.timestamp > last_read_timestamp
        ]


@dataclass
class AgentRequest:
    """Request from one agent to another"""
    request_id: str
    from_agent: str
    to_agent: str
    request_type: str  # "help", "review", "information", "approval"
    content: str
    priority: int = 5
    deadline: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed, cancelled

    def to_message(self) -> Message:
        """Convert request to message"""
        return Message(
            id=self.request_id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            content=self.content,
            message_type=MessageType.REQUEST,
            timestamp=datetime.now().isoformat(),
            metadata={
                "request_type": self.request_type,
                "priority": self.priority,
                "deadline": self.deadline
            }
        )


@dataclass
class AgentResponse:
    """Response to an agent request"""
    response_id: str
    request_id: str
    from_agent: str
    to_agent: str
    content: str
    success: bool = True

    def to_message(self) -> Message:
        """Convert response to message"""
        return Message(
            id=self.response_id,
            from_agent=self.from_agent,
            to_agent=self.to_agent,
            content=self.content,
            message_type=MessageType.RESPONSE,
            timestamp=datetime.now().isoformat(),
            thread_id=self.request_id,  # Link to original request
            metadata={"success": self.success}
        )


class CommunicationProtocol:
    """
    Communication protocol for standardized agent interactions.

    Patterns:
    - Request/Response
    - Broadcast/Subscribe
    - Question/Answer
    - Decision/Vote
    """

    @staticmethod
    def create_request(
        from_agent: str,
        to_agent: str,
        request_type: str,
        content: str,
        priority: int = 5
    ) -> AgentRequest:
        """Create a request from one agent to another"""
        import uuid
        return AgentRequest(
            request_id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            request_type=request_type,
            content=content,
            priority=priority
        )

    @staticmethod
    def create_broadcast(
        from_agent: str,
        content: str,
        message_type: MessageType = MessageType.BROADCAST
    ) -> Message:
        """Create broadcast message to all agents"""
        import uuid
        return Message(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent="all",
            content=content,
            message_type=message_type,
            timestamp=datetime.now().isoformat()
        )

    @staticmethod
    def create_direct_message(
        from_agent: str,
        to_agent: str,
        content: str,
        message_type: MessageType = MessageType.INFO
    ) -> Message:
        """Create direct message to specific agent"""
        import uuid
        return Message(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            timestamp=datetime.now().isoformat()
        )
