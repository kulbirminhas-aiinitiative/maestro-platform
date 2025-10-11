#!/usr/bin/env python3
"""
Collaborative Executor - Phase 3: Continuous Collaboration

Enables mid-execution questions and answers between personas.
Personas can pause, ask questions, get answers, and continue.

Based on: AutoGen's human-in-the-loop and agent collaboration patterns
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime

from sdlc_messages import ConversationMessage, SystemMessage
from conversation_manager import ConversationHistory
from personas import SDLCPersonas

logger = logging.getLogger(__name__)


class CollaborativeExecutor:
    """
    Enables continuous collaboration during persona execution
    
    Pattern: Persona → Question → Answer → Continue
    
    Use Cases:
    1. Backend needs security clarification mid-implementation
    2. Frontend needs API contract clarification
    3. QA needs acceptance criteria clarification
    4. DevOps needs deployment requirement clarification
    """
    
    def __init__(
        self,
        conversation: ConversationHistory,
        output_dir: Path
    ):
        """
        Initialize collaborative executor
        
        Args:
            conversation: Shared conversation history
            output_dir: Output directory
        """
        self.conversation = conversation
        self.output_dir = output_dir
        self.all_personas = SDLCPersonas.get_all_personas()
        self.pending_questions = []  # Queue of questions awaiting answers
        
        # Check if Claude is available
        self.claude_available = False
        try:
            from claude_code_sdk import query, ClaudeCodeOptions
            self.claude_available = True
            self.query = query
            self.ClaudeCodeOptions = ClaudeCodeOptions
        except ImportError:
            logger.warning("⚠️  Claude SDK not available, using fallback")
    
    async def check_for_questions(
        self,
        persona_id: str,
        phase: str
    ) -> List[Dict[str, Any]]:
        """
        Check if persona has questions that need answering
        
        Args:
            persona_id: Persona asking questions
            phase: Current SDLC phase
        
        Returns:
            List of questions needing answers
        """
        questions = []
        
        # Check conversation for questions directed to others
        from sdlc_messages import PersonaWorkMessage
        work_messages = self.conversation.get_messages(
            source=persona_id,
            message_type=PersonaWorkMessage,
            phase=phase
        )
        
        for msg in work_messages:
            if isinstance(msg, PersonaWorkMessage):
                for q in msg.questions:
                    if q.get('for') and q.get('question'):
                        questions.append({
                            "question_id": f"{msg.id}_{len(questions)}",
                            "from": persona_id,
                            "to": q['for'],
                            "question": q['question'],
                            "phase": phase,
                            "status": "pending"
                        })
        
        return questions
    
    async def answer_question(
        self,
        question: Dict[str, Any],
        requirement: str
    ) -> Dict[str, Any]:
        """
        Get answer from target persona
        
        Args:
            question: Question dict with 'from', 'to', 'question'
            requirement: Project requirement for context
        
        Returns:
            Answer dict with persona response
        """
        
        target_persona = question['to']
        asking_persona = question['from']
        question_text = question['question']
        
        logger.info(f"❓ Question from {asking_persona} to {target_persona}")
        logger.info(f"   '{question_text[:80]}...'")
        
        if target_persona not in self.all_personas:
            logger.warning(f"Target persona {target_persona} not found")
            return {
                "answer": "Target persona not available",
                "confidence": 0.0
            }
        
        persona_config = self.all_personas[target_persona]
        
        # Get conversation context
        context = self.conversation.get_conversation_text(max_messages=20)
        
        # Build prompt for answering
        prompt = f"""You are the {persona_config['name']}.

PROJECT REQUIREMENT:
{requirement}

CURRENT CONVERSATION CONTEXT:
{context}

QUESTION FROM {asking_persona.replace('_', ' ').title()}:
{question_text}

YOUR EXPERTISE:
{', '.join(persona_config.get('expertise', [])[:5])}

TASK: Provide a clear, concise answer to help {asking_persona} continue their work.

Consider:
1. What specific guidance do they need?
2. What are the best practices in your domain?
3. What potential issues should they be aware of?
4. What would you recommend and why?

Provide 2-3 paragraphs with specific, actionable guidance.

Your answer:
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
                
                answer_text = response.strip()
                
            except Exception as e:
                logger.warning(f"Claude answer generation failed: {e}")
                answer_text = self._generate_fallback_answer(
                    target_persona,
                    asking_persona,
                    question_text
                )
        else:
            answer_text = self._generate_fallback_answer(
                target_persona,
                asking_persona,
                question_text
            )
        
        # Add answer to conversation
        answer_msg = self.conversation.add_discussion(
            persona_id=target_persona,
            content=f"**Answering {asking_persona}'s question:**\n\n{answer_text}",
            phase=question['phase'],
            message_type="answer",
            reply_to=question['question_id'],
            metadata={"question_from": asking_persona}
        )
        
        logger.info(f"✅ Answer provided by {target_persona}")
        
        return {
            "answer": answer_text,
            "answerer": target_persona,
            "confidence": 0.9 if self.claude_available else 0.6,
            "message_id": answer_msg.id
        }
    
    def _generate_fallback_answer(
        self,
        target_persona: str,
        asking_persona: str,
        question: str
    ) -> str:
        """Generate fallback answer when Claude not available"""
        
        persona_config = self.all_personas.get(target_persona, {})
        
        fallback_answers = {
            "security_specialist": f"From a security perspective: Implement proper authentication and authorization. Use industry-standard libraries (JWT, OAuth2). Validate all inputs. Follow OWASP guidelines. Encrypt sensitive data at rest and in transit.",
            
            "solution_architect": f"Architecturally: Keep it modular and maintainable. Follow SOLID principles. Consider scalability and performance. Document key decisions. Use established patterns where applicable.",
            
            "backend_developer": f"For implementation: Use proper error handling. Add logging for debugging. Write unit tests. Keep business logic separate from routes. Follow REST conventions.",
            
            "frontend_developer": f"On the frontend: Focus on user experience. Handle loading and error states. Make it responsive. Optimize performance. Keep components reusable.",
            
            "qa_engineer": f"From QA perspective: Ensure it's testable. Add clear acceptance criteria. Consider edge cases. Test both happy and error paths. Automate where possible.",
            
            "devops_engineer": f"For deployment: Make it container-friendly. Use environment variables for config. Add health check endpoints. Plan for monitoring and logging. Consider zero-downtime deployment."
        }
        
        base_answer = fallback_answers.get(
            target_persona,
            f"As {persona_config.get('name', target_persona)}, I recommend following best practices in your domain and consulting relevant documentation."
        )
        
        return f"{base_answer}\n\nRegarding your specific question about '{question[:50]}...': I suggest reviewing the project requirements and aligning with the team's established patterns."
    
    async def resolve_pending_questions(
        self,
        requirement: str,
        phase: str,
        max_questions: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Resolve all pending questions from recent work
        
        Args:
            requirement: Project requirement
            phase: Current phase
            max_questions: Maximum questions to resolve
        
        Returns:
            List of resolved questions with answers
        """
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🤔 RESOLVING PENDING QUESTIONS")
        logger.info(f"{'='*80}\n")
        
        # Collect all questions from recent work
        all_questions = []
        from sdlc_messages import PersonaWorkMessage
        work_messages = self.conversation.get_messages(
            message_type=PersonaWorkMessage,
            phase=phase
        )
        
        for msg in work_messages:
            if isinstance(msg, PersonaWorkMessage) and msg.questions:
                for q in msg.questions:
                    if q.get('for') and q.get('question'):
                        all_questions.append({
                            "question_id": f"{msg.id}_{msg.source}",
                            "from": msg.source,
                            "to": q['for'],
                            "question": q['question'],
                            "phase": phase,
                            "status": "pending"
                        })
        
        if not all_questions:
            logger.info("  No pending questions found")
            return []
        
        logger.info(f"  Found {len(all_questions)} question(s)")
        
        # Limit questions
        questions_to_answer = all_questions[:max_questions]
        
        resolved = []
        for i, question in enumerate(questions_to_answer, 1):
            logger.info(f"\n  Question {i}/{len(questions_to_answer)}:")
            
            answer = await self.answer_question(question, requirement)
            
            resolved.append({
                **question,
                "answer": answer['answer'],
                "answerer": answer['answerer'],
                "status": "resolved"
            })
        
        logger.info(f"\n✅ Resolved {len(resolved)} question(s)\n")
        logger.info(f"{'='*80}\n")
        
        return resolved
    
    async def enable_mid_execution_qa(
        self,
        persona_id: str,
        requirement: str,
        phase: str,
        check_interval: int = 30
    ) -> None:
        """
        Enable continuous Q&A checking during execution
        
        This would be called in a separate thread/task during persona execution
        to periodically check for questions and get answers.
        
        Args:
            persona_id: Persona being executed
            requirement: Project requirement
            phase: Current phase
            check_interval: Seconds between checks
        """
        
        logger.info(f"🔄 Enabled mid-execution Q&A for {persona_id}")
        
        # In a real implementation, this would run in parallel with persona execution
        # and check for questions periodically, pausing execution if needed
        
        # For now, this is a placeholder for future implementation
        # showing the pattern of how it would work
        
        pass
