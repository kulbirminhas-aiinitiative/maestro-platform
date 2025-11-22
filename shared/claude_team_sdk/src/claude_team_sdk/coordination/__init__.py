"""Coordination and communication for multi-agent teams."""

from .team_coordinator import TeamCoordinator
from .communication import MessageType, Message, CommunicationProtocol

__all__ = [
    "TeamCoordinator",
    "MessageType",
    "Message",
    "CommunicationProtocol",
]
