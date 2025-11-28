"""
Discussion protocols for managing agent conversations.

Provides different conversation patterns (round-robin, open, structured debate)
that control how agents interact in multi-agent discussions.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Callable
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

logger = logging.getLogger(__name__)


class DiscussionProtocol(ABC):
    """
    Base class for discussion protocols.

    A protocol defines how agents take turns speaking and interact
    in a multi-agent discussion.
    """

    def __init__(self, name: str):
        """
        Initialize protocol.

        Args:
            name: Protocol name
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    def create_speaker_selection_func(
        self,
        agents: List[Agent]
    ) -> Optional[Callable]:
        """
        Create speaker selection function for AutoGen GroupChat.

        Args:
            agents: List of participating agents

        Returns:
            Speaker selection function or None for default behavior
        """
        pass

    @abstractmethod
    def get_max_round(self) -> Optional[int]:
        """
        Get maximum number of rounds for this protocol.

        Returns:
            Max rounds or None for unlimited
        """
        pass

    def get_description(self) -> str:
        """
        Get protocol description.

        Returns:
            Human-readable description
        """
        return f"{self.name} protocol"

    def on_discussion_start(self, agents: List[Agent]) -> None:
        """
        Called when discussion starts.

        Args:
            agents: List of participating agents
        """
        self.logger.info(f"Starting discussion with {len(agents)} agents")

    def on_discussion_end(self, messages: List[Dict[str, Any]]) -> None:
        """
        Called when discussion ends.

        Args:
            messages: List of discussion messages
        """
        self.logger.info(f"Discussion ended with {len(messages)} messages")


class RoundRobinProtocol(DiscussionProtocol):
    """
    Round-robin protocol where each agent speaks in order.

    Agents take turns speaking in a fixed order, ensuring each agent
    gets equal opportunity to contribute.
    """

    def __init__(self, rounds: int = 3):
        """
        Initialize round-robin protocol.

        Args:
            rounds: Number of complete rounds (each agent speaks once per round)
        """
        super().__init__("RoundRobin")
        self.rounds = rounds
        self.current_index = 0
        self.current_round = 0

    def create_speaker_selection_func(
        self,
        agents: List[Agent]
    ) -> Optional[Callable]:
        """
        Create round-robin speaker selection function.

        Args:
            agents: List of participating agents

        Returns:
            Speaker selection function
        """
        agent_count = len(agents)

        def select_speaker(last_speaker: Agent, groupchat: GroupChat) -> Agent:
            """Select next agent in round-robin order."""
            # Find current speaker index
            try:
                current_idx = groupchat.agents.index(last_speaker)
            except ValueError:
                current_idx = -1

            # Move to next agent
            next_idx = (current_idx + 1) % len(groupchat.agents)
            next_agent = groupchat.agents[next_idx]

            self.logger.debug(
                f"Round {self.current_round + 1}/{self.rounds}: "
                f"Selecting {next_agent.name}"
            )

            # Track rounds
            if next_idx == 0:
                self.current_round += 1

            return next_agent

        return select_speaker

    def get_max_round(self) -> Optional[int]:
        """
        Get max rounds (rounds * number of agents).

        Returns:
            Maximum number of messages
        """
        return self.rounds

    def get_description(self) -> str:
        """Get protocol description."""
        return (
            f"Round-robin protocol with {self.rounds} rounds. "
            "Each agent speaks in order."
        )


class OpenDiscussionProtocol(DiscussionProtocol):
    """
    Open discussion protocol where agents can speak freely.

    AutoGen's default speaker selection uses LLM to determine
    which agent should speak next based on the conversation context.
    """

    def __init__(self, max_rounds: Optional[int] = 10):
        """
        Initialize open discussion protocol.

        Args:
            max_rounds: Maximum number of messages (None for unlimited)
        """
        super().__init__("OpenDiscussion")
        self.max_rounds = max_rounds

    def create_speaker_selection_func(
        self,
        agents: List[Agent]
    ) -> Optional[Callable]:
        """
        Use AutoGen's default speaker selection.

        Args:
            agents: List of participating agents

        Returns:
            None to use AutoGen's default LLM-based selection
        """
        # Return None to use AutoGen's default auto speaker selection
        return None

    def get_max_round(self) -> Optional[int]:
        """
        Get max rounds.

        Returns:
            Maximum number of messages or None
        """
        return self.max_rounds

    def get_description(self) -> str:
        """Get protocol description."""
        rounds_desc = f"{self.max_rounds} rounds" if self.max_rounds else "unlimited rounds"
        return (
            f"Open discussion protocol with {rounds_desc}. "
            "Agents speak based on context relevance."
        )


class StructuredDebateProtocol(DiscussionProtocol):
    """
    Structured debate protocol with pro/con format and synthesis.

    Agents are divided into pro and con sides, alternating arguments,
    with a synthesizer agent summarizing at the end.
    """

    def __init__(
        self,
        rounds_per_side: int = 2,
        include_synthesis: bool = True
    ):
        """
        Initialize structured debate protocol.

        Args:
            rounds_per_side: Number of rounds each side gets
            include_synthesis: Whether to include final synthesis
        """
        super().__init__("StructuredDebate")
        self.rounds_per_side = rounds_per_side
        self.include_synthesis = include_synthesis
        self.turn_count = 0
        self.pro_agents: List[Agent] = []
        self.con_agents: List[Agent] = []
        self.synthesizer: Optional[Agent] = None

    def create_speaker_selection_func(
        self,
        agents: List[Agent]
    ) -> Optional[Callable]:
        """
        Create debate speaker selection function.

        Assigns agents to pro/con sides and synthesizer role.

        Args:
            agents: List of participating agents

        Returns:
            Speaker selection function
        """
        # Assign roles based on agent count
        agent_count = len(agents)

        if agent_count < 2:
            self.logger.warning("Debate needs at least 2 agents")
            return None

        # Last agent is synthesizer if enabled
        if self.include_synthesis and agent_count >= 3:
            self.synthesizer = agents[-1]
            debate_agents = agents[:-1]
        else:
            self.synthesizer = None
            debate_agents = agents

        # Split remaining agents into pro/con
        mid_point = len(debate_agents) // 2
        self.pro_agents = debate_agents[:mid_point] if mid_point > 0 else [debate_agents[0]]
        self.con_agents = debate_agents[mid_point:] if mid_point < len(debate_agents) else []

        if not self.con_agents and len(debate_agents) > 1:
            # Move last pro agent to con if we have at least 2 agents
            self.con_agents = [self.pro_agents.pop()]

        self.logger.info(
            f"Debate setup: {len(self.pro_agents)} pro, "
            f"{len(self.con_agents)} con, "
            f"synthesizer: {self.synthesizer.name if self.synthesizer else 'None'}"
        )

        def select_speaker(last_speaker: Agent, groupchat: GroupChat) -> Agent:
            """Select next speaker in debate format."""
            total_rounds = self.rounds_per_side * 2  # pro + con rounds
            synthesis_round = total_rounds if self.include_synthesis else -1

            # Determine which side's turn it is
            if self.turn_count >= total_rounds:
                # Synthesis phase
                if self.synthesizer and self.turn_count == synthesis_round:
                    self.logger.info("Final synthesis phase")
                    return self.synthesizer
                else:
                    # Discussion complete, return first agent to end
                    return groupchat.agents[0]

            # Alternate between pro and con
            is_pro_turn = (self.turn_count % 2) == 0
            side_agents = self.pro_agents if is_pro_turn else self.con_agents

            # Select agent from current side (round-robin within side)
            side_turn = self.turn_count // 2
            agent_idx = side_turn % len(side_agents)
            next_agent = side_agents[agent_idx]

            side_name = "Pro" if is_pro_turn else "Con"
            self.logger.debug(
                f"Turn {self.turn_count + 1}: {side_name} side - {next_agent.name}"
            )

            self.turn_count += 1
            return next_agent

        return select_speaker

    def get_max_round(self) -> Optional[int]:
        """
        Get max rounds for debate.

        Returns:
            Total number of rounds including synthesis
        """
        total = self.rounds_per_side * 2  # pro + con
        if self.include_synthesis:
            total += 1
        return total

    def get_description(self) -> str:
        """Get protocol description."""
        synthesis = " with synthesis" if self.include_synthesis else ""
        return (
            f"Structured debate protocol{synthesis}. "
            f"{self.rounds_per_side} rounds per side, alternating pro/con."
        )

    def on_discussion_start(self, agents: List[Agent]) -> None:
        """
        Reset turn counter on discussion start.

        Args:
            agents: List of participating agents
        """
        super().on_discussion_start(agents)
        self.turn_count = 0


class ModeratedProtocol(DiscussionProtocol):
    """
    Moderated protocol where a moderator controls the conversation flow.

    The first agent acts as moderator and decides who speaks next.
    """

    def __init__(self, max_rounds: int = 15):
        """
        Initialize moderated protocol.

        Args:
            max_rounds: Maximum number of rounds
        """
        super().__init__("Moderated")
        self.max_rounds = max_rounds
        self.moderator: Optional[Agent] = None

    def create_speaker_selection_func(
        self,
        agents: List[Agent]
    ) -> Optional[Callable]:
        """
        Create moderated speaker selection.

        First agent is the moderator.

        Args:
            agents: List of participating agents

        Returns:
            Speaker selection function
        """
        if not agents:
            return None

        self.moderator = agents[0]
        self.logger.info(f"Moderator: {self.moderator.name}")

        # Use AutoGen's default speaker selection but with moderator hints
        # The moderator's responses should include hints about who to call on next
        return None  # AutoGen will use LLM-based selection

    def get_max_round(self) -> Optional[int]:
        """Get max rounds."""
        return self.max_rounds

    def get_description(self) -> str:
        """Get protocol description."""
        return (
            f"Moderated protocol with {self.max_rounds} rounds. "
            "First agent acts as moderator."
        )


def create_protocol(
    protocol_type: str,
    **kwargs
) -> DiscussionProtocol:
    """
    Factory function to create discussion protocols.

    Args:
        protocol_type: Type of protocol (round_robin, open, structured_debate, moderated)
        **kwargs: Protocol-specific parameters

    Returns:
        DiscussionProtocol instance

    Raises:
        ValueError: If protocol_type is unknown
    """
    protocol_map = {
        "round_robin": RoundRobinProtocol,
        "open": OpenDiscussionProtocol,
        "structured_debate": StructuredDebateProtocol,
        "moderated": ModeratedProtocol,
    }

    protocol_class = protocol_map.get(protocol_type.lower())

    if not protocol_class:
        raise ValueError(
            f"Unknown protocol type: {protocol_type}. "
            f"Available: {', '.join(protocol_map.keys())}"
        )

    return protocol_class(**kwargs)
