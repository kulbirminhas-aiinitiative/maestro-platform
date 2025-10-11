#!/usr/bin/env python3
"""
Structured Output Extractor

Uses LLM to extract structured information from persona's work:
- Summary of what was done
- Key decisions with rationale
- Questions for other personas
- Assumptions made
- Dependencies

This replaces simple file lists with rich context.
"""

from typing import Dict, List, Any
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class StructuredOutputExtractor:
    """
    Extracts structured information from persona's work
    
    AutoGen Principle: Capture not just WHAT but WHY and HOW
    """
    
    def __init__(self):
        self.claude_available = False
        try:
            from claude_code_sdk import query, ClaudeCodeOptions
            self.claude_available = True
            self.query = query
            self.ClaudeCodeOptions = ClaudeCodeOptions
        except ImportError:
            logger.warning("Claude SDK not available, using fallback extraction")
    
    async def extract_from_persona_work(
        self,
        persona_id: str,
        files_created: List[str],
        output_dir: Path,
        deliverables: Dict[str, List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured output from persona's work
        
        Args:
            persona_id: Persona identifier
            files_created: List of files created
            output_dir: Output directory
            deliverables: Deliverables map
        
        Returns:
            Dictionary with:
            - summary: Brief summary
            - decisions: List of decisions with rationale
            - questions: Questions for other personas
            - assumptions: Assumptions made
            - dependencies: Dependencies on/from others
            - concerns: Any concerns or risks
        """
        
        # Check for summary/readme files
        existing_summary = await self._find_summary_content(
            files_created,
            output_dir
        )
        
        if self.claude_available:
            return await self._extract_with_claude(
                persona_id,
                files_created,
                existing_summary,
                deliverables
            )
        else:
            return self._extract_fallback(
                persona_id,
                files_created,
                existing_summary,
                deliverables
            )
    
    async def _find_summary_content(
        self,
        files_created: List[str],
        output_dir: Path
    ) -> str:
        """Find and read summary/readme files"""
        summary_keywords = ['readme', 'summary', 'architecture', 'design', 'overview']
        
        for file_path in files_created:
            file_lower = file_path.lower()
            if any(kw in file_lower for kw in summary_keywords):
                try:
                    full_path = output_dir / file_path
                    if full_path.exists() and full_path.is_file():
                        content = full_path.read_text()
                        # Limit size
                        return content[:5000] if len(content) > 5000 else content
                except Exception as e:
                    logger.debug(f"Could not read {file_path}: {e}")
        
        return ""
    
    async def _extract_with_claude(
        self,
        persona_id: str,
        files_created: List[str],
        existing_summary: str,
        deliverables: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Extract using Claude LLM"""
        
        # Build prompt
        prompt = f"""Analyze the work done by {persona_id.replace('_', ' ')} and extract structured information.

Files created ({len(files_created)}):
{', '.join(files_created[:30])}
{'... and more' if len(files_created) > 30 else ''}

{f"Summary document found:{existing_summary[:1000]}" if existing_summary else "No summary document found."}

Extract the following information in JSON format:
{{
    "summary": "1-3 sentence summary of what was accomplished",
    "decisions": [
        {{
            "decision": "What was decided",
            "rationale": "Why this decision was made",
            "alternatives_considered": ["Option A", "Option B"],
            "trade_offs": "What trade-offs were made"
        }}
    ],
    "questions": [
        {{
            "for": "persona_id (e.g., frontend_developer)",
            "question": "Specific question that needs answering"
        }}
    ],
    "assumptions": [
        "Assumption 1 that was made",
        "Assumption 2 that might need validation"
    ],
    "dependencies": {{
        "depends_on": ["persona_id that this work depends on"],
        "provides_for": ["persona_id that will use this work"]
    }},
    "concerns": [
        "Any concern or risk identified"
    ]
}}

Focus on:
1. Technical decisions and why they were made
2. Questions that other team members should answer
3. Assumptions that might need validation
4. Dependencies between team members

Provide comprehensive JSON. If you don't find specific information, use empty arrays.
"""
        
        try:
            options = self.ClaudeCodeOptions(
                model="claude-3-5-sonnet-20241022"
            )
            
            response = ""
            async for message in self.query(prompt=prompt, options=options):
                if hasattr(message, 'text'):
                    response += message.text
            
            # Parse JSON from response
            structured = self._parse_json_from_response(response)
            
            # Validate and fill defaults
            return self._validate_structured_output(structured, persona_id)
            
        except Exception as e:
            logger.warning(f"Claude extraction failed: {e}, using fallback")
            return self._extract_fallback(
                persona_id,
                files_created,
                existing_summary,
                deliverables
            )
    
    def _parse_json_from_response(self, response: str) -> Dict[str, Any]:
        """Extract JSON from Claude response"""
        # Find JSON in response (between { and })
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Try to clean up common issues
                json_str = json_str.replace('\n', ' ').replace('\r', '')
                return json.loads(json_str)
        
        raise ValueError("No JSON found in response")
    
    def _validate_structured_output(
        self,
        structured: Dict[str, Any],
        persona_id: str
    ) -> Dict[str, Any]:
        """Validate and fill missing fields with defaults"""
        return {
            "summary": structured.get("summary", f"{persona_id} completed work"),
            "decisions": structured.get("decisions", []),
            "questions": structured.get("questions", []),
            "assumptions": structured.get("assumptions", []),
            "dependencies": structured.get("dependencies", {
                "depends_on": [],
                "provides_for": []
            }),
            "concerns": structured.get("concerns", [])
        }
    
    def _extract_fallback(
        self,
        persona_id: str,
        files_created: List[str],
        existing_summary: str,
        deliverables: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """Fallback extraction without LLM"""
        
        # Generate simple summary
        file_types = set()
        for f in files_created:
            ext = Path(f).suffix
            if ext:
                file_types.add(ext)
        
        summary = f"{persona_id.replace('_', ' ').title()} created {len(files_created)} files"
        if file_types:
            summary += f" ({', '.join(sorted(file_types))})"
        
        # Try to extract decisions from summary
        decisions = []
        if existing_summary and len(existing_summary) > 100:
            decisions.append({
                "decision": "See detailed documentation in README/summary files",
                "rationale": "Detailed decisions documented in project files",
                "alternatives_considered": [],
                "trade_offs": "N/A"
            })
        
        return {
            "summary": summary,
            "decisions": decisions,
            "questions": [],
            "assumptions": [],
            "dependencies": {
                "depends_on": [],
                "provides_for": []
            },
            "concerns": []
        }
