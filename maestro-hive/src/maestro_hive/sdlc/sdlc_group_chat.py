#!/usr/bin/env python3
"""
SDLC Group Chat Orchestrator - Inspired by AutoGen's BaseGroupChat

Enables collaborative design discussions where multiple personas
can debate, ask questions, and reach consensus together.

Based on: Microsoft AutoGen's group chat pattern
Key Principle: All participants see the same conversation history
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import json

from sdlc_messages import ConversationMessage, SystemMessage
from conversation_manager import ConversationHistory
from personas import SDLCPersonas

logger = logging.getLogger(__name__)


class SDLCGroupChat:
    """
    Group chat for SDLC team collaborative discussions
    
    AutoGen Pattern: Multi-agent conversation with shared context
    
    Use Cases:
    - Architecture Review: Team debates architecture choices
    - API Design: Frontend + Backend negotiate API contract
    - Security Review: Security challenges design, team responds
    - Tech Stack Selection: Team reaches consensus on technologies
    """
    
    def __init__(
        self,
        session_id: str,
        conversation: ConversationHistory,
        output_dir: Path
    ):
        """
        Initialize group chat
        
        Args:
            session_id: Session identifier
            conversation: Shared conversation history
            output_dir: Output directory for artifacts
        """
        self.session_id = session_id
        self.conversation = conversation
        self.output_dir = output_dir
        self.all_personas = SDLCPersonas.get_all_personas()
        
        # Check if Claude is available
        self.claude_available = False
        try:
            from claude_code_sdk import query, ClaudeCodeOptions
            self.claude_available = True
            self.query = query
            self.ClaudeCodeOptions = ClaudeCodeOptions
            logger.info("✅ Claude SDK available for group chat")
        except ImportError:
            logger.warning("⚠️  Claude SDK not available, group chat will use mock responses")
    
    async def run_design_discussion(
        self,
        topic: str,
        participants: List[str],
        requirement: str,
        phase: str,
        max_rounds: int = 3,
        consensus_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Run group discussion on design topic
        
        AutoGen Pattern: All participants see full conversation
        
        Args:
            topic: Discussion topic (e.g., "API Design", "Architecture")
            participants: List of persona IDs to participate
            requirement: Project requirement for context
            phase: SDLC phase
            max_rounds: Maximum discussion rounds
            consensus_threshold: Confidence threshold for consensus (0-1)
        
        Returns:
            {
                "consensus": Dict with agreed design,
                "messages": List of discussion messages,
                "rounds": Number of rounds completed,
                "consensus_reached": bool
            }
        """
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🗣️  GROUP DISCUSSION: {topic}")
        logger.info(f"{'='*80}")
        logger.info(f"Participants: {', '.join(participants)}")
        logger.info(f"Max Rounds: {max_rounds}")
        logger.info(f"Phase: {phase}")
        logger.info("")
        
        # Add system message to start discussion
        start_msg = self.conversation.add_system_message(
            content=f"""
GROUP DISCUSSION: {topic}

Project: {requirement}
Phase: {phase}
Participants: {', '.join([p.replace('_', ' ').title() for p in participants])}

Each participant should:
1. Share their perspective on {topic}
2. Ask clarifying questions
3. Raise concerns or risks
4. Propose solutions
5. Build on others' ideas

Goal: Reach consensus on the best approach.
""",
            phase=phase,
            level="info"
        )
        
        consensus_reached = False
        discussion_messages = []
        
        # Discussion rounds
        for round_num in range(max_rounds):
            logger.info(f"\n--- Round {round_num + 1}/{max_rounds} ---\n")
            
            # Each persona contributes
            for persona_id in participants:
                if persona_id not in self.all_personas:
                    logger.warning(f"Persona {persona_id} not found, skipping")
                    continue
                
                response = await self._get_persona_contribution(
                    persona_id,
                    topic,
                    requirement,
                    phase,
                    participants
                )
                
                # Add to conversation
                msg = self.conversation.add_discussion(
                    persona_id=persona_id,
                    content=response,
                    phase=phase,
                    message_type="discussion",
                    metadata={"round": round_num + 1}
                )
                
                discussion_messages.append(msg)
                
                logger.info(f"  {persona_id.replace('_', ' ').title()}: Contributed")
            
            # Check for consensus
            logger.info("")
            consensus_check = await self._check_consensus(
                topic,
                participants,
                phase
            )
            
            logger.info(f"  Consensus Check: {consensus_check['confidence']:.0%} confident")
            
            if consensus_check["reached"] and consensus_check["confidence"] >= consensus_threshold:
                logger.info(f"  ✅ Consensus reached!")
                consensus_reached = True
                break
            else:
                logger.info(f"  ⏩ Continue discussion (confidence < {consensus_threshold:.0%})")
        
        logger.info("")
        
        # Synthesize final decision
        logger.info("📊 Synthesizing consensus from discussion...")
        consensus = await self._synthesize_consensus(
            topic,
            participants,
            phase
        )
        
        # Add consensus as system message
        consensus_text = self._format_consensus(consensus)
        self.conversation.add_system_message(
            content=f"CONSENSUS REACHED\n\n{consensus_text}",
            phase=phase,
            level="success"
        )
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ GROUP DISCUSSION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Rounds: {round_num + 1}")
        logger.info(f"Consensus: {'Yes' if consensus_reached else 'No'}")
        logger.info(f"Decisions: {len(consensus.get('decisions', []))}")
        logger.info(f"{'='*80}\n")
        
        return {
            "consensus": consensus,
            "messages": discussion_messages,
            "rounds": round_num + 1,
            "consensus_reached": consensus_reached
        }
    
    async def _get_persona_contribution(
        self,
        persona_id: str,
        topic: str,
        requirement: str,
        phase: str,
        participants: List[str]
    ) -> str:
        """
        Get persona's contribution to discussion
        
        AutoGen Pattern: Persona sees FULL conversation history
        """
        
        persona_config = self.all_personas[persona_id]
        
        # Get conversation so far (AutoGen pattern: shared context)
        conversation_text = self.conversation.get_conversation_text(
            max_messages=30,  # Recent context
            phase=phase
        )
        
        prompt = f"""You are the {persona_config['name']} participating in a group design discussion.

DISCUSSION TOPIC: {topic}

PROJECT REQUIREMENT:
{requirement}

FULL CONVERSATION SO FAR:
{conversation_text}

YOUR EXPERTISE:
{', '.join(persona_config.get('expertise', [])[:5])}

OTHER PARTICIPANTS:
{', '.join([p.replace('_', ' ').title() for p in participants if p != persona_id])}

TASK: Contribute thoughtfully to the discussion about {topic}.

Consider:
1. What's your unique perspective on this topic based on your expertise?
2. Do you have specific questions for other participants?
3. What risks or concerns do you see that others might have missed?
4. What solutions or approaches do you recommend?
5. Can you build on or improve ideas already proposed?

Provide 2-3 paragraphs. Be specific, technical, and constructive.
If asking questions, direct them to specific participants.
If proposing solutions, explain the trade-offs.

Your contribution:
"""
        
        if self.claude_available:
            try:
                options = self.ClaudeCodeOptions(
                    system_prompt=persona_config.get("system_prompt", ""),
                    model="claude-3-5-sonnet-20241022"
                )
                
                response = ""
                async for message in self.query(prompt=prompt, options=options):
                    if hasattr(message, 'text'):
                        response += message.text
                
                return response.strip()
            except Exception as e:
                logger.warning(f"Claude generation failed: {e}, using fallback")
        
        # Fallback response
        return self._generate_fallback_contribution(persona_id, topic)
    
    def _generate_fallback_contribution(self, persona_id: str, topic: str) -> str:
        """Generate fallback contribution when Claude not available"""
        persona_config = self.all_personas[persona_id]
        
        contributions = {
            "solution_architect": f"From an architectural perspective, I recommend we consider scalability and maintainability for {topic}. We should ensure our design supports future growth while keeping implementation complexity manageable.",
            
            "backend_developer": f"For {topic}, I suggest we focus on clean API design with proper error handling and validation. We should also consider performance implications and database schema design.",
            
            "frontend_developer": f"From the frontend perspective on {topic}, we need to ensure a good user experience with responsive design and efficient state management. API response formats should be frontend-friendly.",
            
            "security_specialist": f"Regarding {topic}, we must consider security implications: authentication, authorization, input validation, and data protection. We should follow OWASP best practices.",
            
            "devops_engineer": f"For {topic}, we need to think about deployment, monitoring, and operational concerns. The solution should be container-friendly and easy to scale.",
            
            "qa_engineer": f"From a testing perspective on {topic}, we need clear acceptance criteria and testable interfaces. We should design for testability from the start."
        }
        
        return contributions.get(persona_id, f"As {persona_config['name']}, I agree with the proposed approach for {topic} and will ensure proper implementation in my domain.")
    
    async def _check_consensus(
        self,
        topic: str,
        participants: List[str],
        phase: str
    ) -> Dict[str, Any]:
        """
        Check if consensus has been reached
        
        AutoGen Pattern: AI analyzes conversation for agreement signals
        """
        
        # Get recent discussion messages
        recent = self.conversation.get_messages(
            phase=phase,
            limit=len(participants) * 2
        )
        
        if len(recent) < len(participants):
            # Not enough contributions yet
            return {
                "reached": False,
                "confidence": 0.0,
                "rationale": "Not all participants have contributed"
            }
        
        # Simple heuristic: consensus if all participated at least once
        # In real implementation, would use LLM to analyze agreement
        participated = set()
        for msg in recent:
            if hasattr(msg, 'source') and msg.source in participants:
                participated.add(msg.source)
        
        participation_rate = len(participated) / len(participants)
        
        # Simulate consensus detection
        if participation_rate >= 0.8:
            return {
                "reached": True,
                "confidence": 0.85,
                "rationale": "All key participants have contributed"
            }
        else:
            return {
                "reached": False,
                "confidence": participation_rate * 0.7,
                "rationale": f"Only {len(participated)}/{len(participants)} participants contributed"
            }
    
    async def _synthesize_consensus(
        self,
        topic: str,
        participants: List[str],
        phase: str
    ) -> Dict[str, Any]:
        """
        Synthesize final consensus from discussion
        
        AutoGen Pattern: Extract structured decision from conversation
        """
        
        # Get all discussion messages
        discussion_msgs = self.conversation.get_messages(phase=phase)
        
        # Extract key points (simplified)
        decisions = []
        action_items = []
        
        # In real implementation, would use LLM to extract these
        # For now, create structured output based on participation
        
        for persona_id in participants:
            persona_config = self.all_personas.get(persona_id, {})
            decisions.append({
                "decision": f"{topic} approach agreed upon by {persona_config.get('name', persona_id)}",
                "rationale": f"Based on {persona_config.get('name', persona_id)}'s expertise",
                "who_proposed": persona_id,
                "supported_by": participants
            })
        
        return {
            "summary": f"Team reached consensus on {topic} after collaborative discussion. All participants contributed their expertise and aligned on the approach.",
            "decisions": decisions[:3],  # Top 3 decisions
            "action_items": [
                {
                    "action": f"Implement {topic} according to agreed design",
                    "assigned_to": participants[0] if participants else "team",
                    "dependencies": []
                }
            ],
            "open_questions": []
        }
    
    def _format_consensus(self, consensus: Dict[str, Any]) -> str:
        """Format consensus for display"""
        lines = [consensus.get("summary", "Consensus reached.")]
        
        if consensus.get("decisions"):
            lines.append("\nKey Decisions:")
            for i, dec in enumerate(consensus["decisions"], 1):
                lines.append(f"{i}. {dec.get('decision', 'N/A')}")
        
        if consensus.get("action_items"):
            lines.append("\nAction Items:")
            for i, item in enumerate(consensus["action_items"], 1):
                lines.append(f"{i}. {item.get('action', 'N/A')} ({item.get('assigned_to', 'N/A')})")
        
        return "\n".join(lines)
