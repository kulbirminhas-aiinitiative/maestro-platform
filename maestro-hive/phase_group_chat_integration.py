#!/usr/bin/env python3
"""
Phase Workflow Integration for Group Chat

Auto-triggers group discussions at appropriate phase boundaries.
Seamlessly integrates group chat into phase workflow.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from sdlc_group_chat import SDLCGroupChat
from conversation_manager import ConversationHistory
from phase_models import SDLCPhase

logger = logging.getLogger(__name__)


class PhaseGroupChatIntegration:
    """
    Integrates group chat into phase workflow
    
    Automatically triggers discussions at key phase boundaries:
    - Requirements → Design: Requirements review
    - Design → Implementation: Architecture review, API design
    - Implementation → Testing: Test strategy
    - Testing → Deployment: Deployment readiness
    """
    
    # Define which phases should trigger group discussions
    DISCUSSION_CONFIG = {
        SDLCPhase.REQUIREMENTS: {
            "enabled": True,
            "discussions": [
                {
                    "topic": "Requirements Validation",
                    "participants": ["requirement_analyst", "solution_architect", "qa_engineer"],
                    "max_rounds": 2,
                    "description": "Validate requirements are clear, complete, and testable"
                }
            ]
        },
        SDLCPhase.DESIGN: {
            "enabled": True,
            "discussions": [
                {
                    "topic": "System Architecture",
                    "participants": ["solution_architect", "security_specialist", 
                                   "backend_developer", "frontend_developer"],
                    "max_rounds": 3,
                    "description": "Debate and finalize system architecture"
                },
                {
                    "topic": "API Contract Design",
                    "participants": ["backend_developer", "frontend_developer", "solution_architect"],
                    "max_rounds": 2,
                    "description": "Agree on API contracts between frontend and backend"
                },
                {
                    "topic": "Security Architecture",
                    "participants": ["security_specialist", "solution_architect", "devops_engineer"],
                    "max_rounds": 2,
                    "description": "Review security design and identify risks"
                }
            ]
        },
        SDLCPhase.IMPLEMENTATION: {
            "enabled": False,  # Usually don't need discussion during implementation
            "discussions": []
        },
        SDLCPhase.TESTING: {
            "enabled": True,
            "discussions": [
                {
                    "topic": "Test Strategy Review",
                    "participants": ["qa_engineer", "test_engineer", "backend_developer"],
                    "max_rounds": 2,
                    "description": "Review test coverage and strategy"
                }
            ]
        },
        SDLCPhase.DEPLOYMENT: {
            "enabled": True,
            "discussions": [
                {
                    "topic": "Deployment Readiness",
                    "participants": ["devops_engineer", "deployment_specialist", 
                                   "qa_engineer", "security_specialist"],
                    "max_rounds": 2,
                    "description": "Validate deployment readiness and plan"
                }
            ]
        }
    }
    
    def __init__(
        self,
        conversation: ConversationHistory,
        output_dir: Path,
        enable_auto_discussions: bool = True
    ):
        """
        Initialize integration
        
        Args:
            conversation: Conversation history
            output_dir: Output directory
            enable_auto_discussions: Auto-trigger discussions
        """
        self.conversation = conversation
        self.output_dir = output_dir
        self.enable_auto_discussions = enable_auto_discussions
        self.group_chat = SDLCGroupChat(
            session_id=conversation.session_id,
            conversation=conversation,
            output_dir=output_dir
        )
    
    async def run_phase_discussions(
        self,
        phase: SDLCPhase,
        requirement: str,
        available_personas: List[str]
    ) -> Dict[str, Any]:
        """
        Run all configured discussions for a phase
        
        Args:
            phase: Current SDLC phase
            requirement: Project requirement
            available_personas: Personas available in this workflow
        
        Returns:
            {
                "discussions_run": int,
                "results": List of discussion results,
                "total_decisions": int
            }
        """
        
        if not self.enable_auto_discussions:
            logger.info(f"  Auto-discussions disabled, skipping")
            return {"discussions_run": 0, "results": [], "total_decisions": 0}
        
        config = self.DISCUSSION_CONFIG.get(phase)
        
        if not config or not config.get("enabled"):
            logger.info(f"  No group discussions configured for {phase.value}")
            return {"discussions_run": 0, "results": [], "total_decisions": 0}
        
        discussions = config.get("discussions", [])
        
        if not discussions:
            return {"discussions_run": 0, "results": [], "total_decisions": 0}
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🗣️  PHASE GROUP DISCUSSIONS: {phase.value.upper()}")
        logger.info(f"{'='*80}")
        logger.info(f"Configured discussions: {len(discussions)}")
        logger.info("")
        
        results = []
        total_decisions = 0
        
        for i, discussion_config in enumerate(discussions, 1):
            topic = discussion_config["topic"]
            participants = discussion_config["participants"]
            max_rounds = discussion_config.get("max_rounds", 2)
            description = discussion_config.get("description", "")
            
            # Filter to only available personas
            available_participants = [
                p for p in participants
                if p in available_personas
            ]
            
            if len(available_participants) < 2:
                logger.warning(f"  ⚠️  Discussion {i}: Not enough participants available")
                logger.warning(f"     Needed: {participants}")
                logger.warning(f"     Available: {available_participants}")
                continue
            
            logger.info(f"\n--- Discussion {i}/{len(discussions)}: {topic} ---")
            logger.info(f"Description: {description}")
            logger.info(f"Participants: {', '.join(available_participants)}")
            logger.info("")
            
            try:
                result = await self.group_chat.run_design_discussion(
                    topic=topic,
                    participants=available_participants,
                    requirement=requirement,
                    phase=phase.value,
                    max_rounds=max_rounds
                )
                
                results.append({
                    "topic": topic,
                    "result": result,
                    "participants": available_participants
                })
                
                total_decisions += len(result['consensus'].get('decisions', []))
                
                logger.info(f"  ✅ Discussion complete: {topic}")
                logger.info(f"     Consensus: {result['consensus_reached']}")
                logger.info(f"     Decisions: {len(result['consensus'].get('decisions', []))}")
                
            except Exception as e:
                logger.error(f"  ❌ Discussion failed: {topic}")
                logger.error(f"     Error: {e}")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ PHASE DISCUSSIONS COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Discussions run: {len(results)}/{len(discussions)}")
        logger.info(f"Total decisions: {total_decisions}")
        logger.info(f"{'='*80}\n")
        
        return {
            "discussions_run": len(results),
            "results": results,
            "total_decisions": total_decisions
        }
    
    def get_discussion_summary(
        self,
        phase: SDLCPhase,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Get summary of discussions for phase
        
        Args:
            phase: Phase
            results: Discussion results
        
        Returns:
            Formatted summary
        """
        
        if not results:
            return f"No group discussions for {phase.value}"
        
        lines = [f"# Group Discussions - {phase.value.upper()}\n"]
        
        for result in results:
            topic = result['topic']
            discussion_result = result['result']
            consensus = discussion_result['consensus']
            
            lines.append(f"## {topic}\n")
            lines.append(f"**Participants:** {', '.join(result['participants'])}\n")
            lines.append(f"**Consensus Reached:** {'Yes' if discussion_result['consensus_reached'] else 'No'}\n")
            lines.append(f"**Rounds:** {discussion_result['rounds']}\n")
            lines.append(f"\n**Summary:**\n{consensus.get('summary', 'N/A')}\n")
            
            if consensus.get('decisions'):
                lines.append(f"\n**Key Decisions:**")
                for i, dec in enumerate(consensus['decisions'], 1):
                    lines.append(f"{i}. {dec.get('decision', 'N/A')}")
            
            lines.append("\n---\n")
        
        return "\n".join(lines)
    
    async def should_trigger_discussion(
        self,
        phase: SDLCPhase,
        iteration: int,
        quality_met: bool
    ) -> bool:
        """
        Determine if group discussion should be triggered
        
        Args:
            phase: Current phase
            iteration: Current iteration
            quality_met: Whether quality gates met
        
        Returns:
            True if discussion should run
        """
        
        # Only trigger on first iteration or if quality not met
        if iteration > 1 and quality_met:
            return False
        
        config = self.DISCUSSION_CONFIG.get(phase, {})
        return config.get("enabled", False) and len(config.get("discussions", [])) > 0
