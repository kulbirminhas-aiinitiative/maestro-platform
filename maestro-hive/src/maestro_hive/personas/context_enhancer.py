#!/usr/bin/env python3
"""
Context Enhancer: Response augmentation with RAG-retrieved knowledge.

This module provides intelligent context enhancement for persona responses,
combining retrieved knowledge with persona context to produce more informed
and contextually relevant outputs.

Related EPIC: MD-3026 - RAG Persona Integration
"""

import json
import logging
import hashlib
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import re

from .rag_connector import (
    RAGConnector,
    RetrievalContext,
    RetrievalResult,
    get_rag_connector,
    RAGConfig,
    QueryStrategy
)

logger = logging.getLogger(__name__)


class EnhancementStrategy(Enum):
    """Strategies for enhancing responses with context."""
    PREPEND = "prepend"          # Add context before the prompt
    APPEND = "append"            # Add context after the prompt
    INLINE = "inline"            # Inject context at marked positions
    STRUCTURED = "structured"    # Use structured format with sections
    SUMMARIZE = "summarize"      # Summarize context before injection
    SELECTIVE = "selective"      # Only inject most relevant pieces


class ContextFormat(Enum):
    """Formats for presenting context."""
    PLAIN = "plain"              # Plain text
    MARKDOWN = "markdown"        # Markdown formatted
    JSON = "json"                # JSON structured
    XML = "xml"                  # XML formatted
    BULLETED = "bulleted"        # Bulleted list


class EnhancementPriority(Enum):
    """Priority levels for context enhancement."""
    CRITICAL = "critical"        # Must include, affects correctness
    HIGH = "high"                # Important, should include
    MEDIUM = "medium"            # Helpful, include if space
    LOW = "low"                  # Nice to have
    OPTIONAL = "optional"        # Only if specifically relevant


@dataclass
class EnhancerConfig:
    """Configuration for context enhancement."""
    strategy: EnhancementStrategy = EnhancementStrategy.STRUCTURED
    context_format: ContextFormat = ContextFormat.MARKDOWN
    max_context_tokens: int = 2000
    max_results_to_include: int = 5
    min_relevance_score: float = 0.7
    include_sources: bool = True
    include_confidence: bool = True
    deduplicate: bool = True
    similarity_threshold_for_dedup: float = 0.85
    context_header: str = "## Relevant Context"
    context_footer: str = ""
    preserve_order: bool = True  # Keep by relevance order
    enable_chunking: bool = True
    chunk_overlap_tokens: int = 100
    fallback_on_empty: bool = True
    fallback_message: str = "No relevant context found."


@dataclass
class ContextChunk:
    """A chunk of context to be injected."""
    chunk_id: str
    content: str
    source: Optional[str]
    relevance_score: float
    priority: EnhancementPriority
    token_estimate: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "priority": self.priority.value
        }


@dataclass
class EnhancedPrompt:
    """Result of prompt enhancement."""
    original_prompt: str
    enhanced_prompt: str
    context_chunks: List[ContextChunk]
    total_context_tokens: int
    retrieval_context: Optional[RetrievalContext]
    enhancement_metadata: Dict[str, Any] = field(default_factory=dict)
    strategy_used: EnhancementStrategy = EnhancementStrategy.STRUCTURED
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def context_included(self) -> bool:
        """Check if any context was included."""
        return len(self.context_chunks) > 0

    @property
    def average_relevance(self) -> float:
        """Calculate average relevance of included context."""
        if not self.context_chunks:
            return 0.0
        return sum(c.relevance_score for c in self.context_chunks) / len(self.context_chunks)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_prompt": self.original_prompt,
            "enhanced_prompt": self.enhanced_prompt,
            "context_chunks": [c.to_dict() for c in self.context_chunks],
            "total_context_tokens": self.total_context_tokens,
            "context_included": self.context_included,
            "average_relevance": self.average_relevance,
            "strategy_used": self.strategy_used.value,
            "enhancement_metadata": self.enhancement_metadata,
            "created_at": self.created_at
        }


@dataclass
class EnhancedResponse:
    """An enhanced response with grounding information."""
    original_response: str
    grounded_response: str
    sources_used: List[str]
    confidence_score: float
    grounding_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class TokenEstimator:
    """Estimates token counts for text."""

    def __init__(self, chars_per_token: float = 4.0):
        self.chars_per_token = chars_per_token

    def estimate(self, text: str) -> int:
        """Estimate token count for text."""
        return int(len(text) / self.chars_per_token)

    def estimate_batch(self, texts: List[str]) -> List[int]:
        """Estimate token counts for multiple texts."""
        return [self.estimate(text) for text in texts]


class ContentDeduplicator:
    """Deduplicates similar content chunks."""

    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold

    def deduplicate(self, chunks: List[ContextChunk]) -> List[ContextChunk]:
        """Remove duplicate or highly similar chunks."""
        if not chunks:
            return []

        unique_chunks: List[ContextChunk] = []

        for chunk in chunks:
            is_duplicate = False

            for unique in unique_chunks:
                similarity = self._calculate_similarity(chunk.content, unique.content)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    # Keep the one with higher relevance
                    if chunk.relevance_score > unique.relevance_score:
                        unique_chunks.remove(unique)
                        unique_chunks.append(chunk)
                    break

            if not is_duplicate:
                unique_chunks.append(chunk)

        return unique_chunks

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        if union == 0:
            return 0.0

        return intersection / union


class ContextFormatter:
    """Formats context chunks for injection."""

    def __init__(self, format_type: ContextFormat = ContextFormat.MARKDOWN):
        self.format_type = format_type

    def format_chunks(
        self,
        chunks: List[ContextChunk],
        header: str = "",
        footer: str = "",
        include_sources: bool = True,
        include_confidence: bool = True
    ) -> str:
        """Format context chunks into a single string."""
        if not chunks:
            return ""

        if self.format_type == ContextFormat.MARKDOWN:
            return self._format_markdown(chunks, header, footer, include_sources, include_confidence)
        elif self.format_type == ContextFormat.PLAIN:
            return self._format_plain(chunks, header, footer, include_sources)
        elif self.format_type == ContextFormat.JSON:
            return self._format_json(chunks)
        elif self.format_type == ContextFormat.BULLETED:
            return self._format_bulleted(chunks, header, footer)
        else:
            return self._format_plain(chunks, header, footer, include_sources)

    def _format_markdown(
        self,
        chunks: List[ContextChunk],
        header: str,
        footer: str,
        include_sources: bool,
        include_confidence: bool
    ) -> str:
        """Format as markdown."""
        lines = []

        if header:
            lines.append(header)
            lines.append("")

        for i, chunk in enumerate(chunks, 1):
            lines.append(f"### Context {i}")
            lines.append(chunk.content)

            annotations = []
            if include_sources and chunk.source:
                annotations.append(f"Source: {chunk.source}")
            if include_confidence:
                annotations.append(f"Relevance: {chunk.relevance_score:.2f}")

            if annotations:
                lines.append(f"*{' | '.join(annotations)}*")

            lines.append("")

        if footer:
            lines.append(footer)

        return "\n".join(lines)

    def _format_plain(
        self,
        chunks: List[ContextChunk],
        header: str,
        footer: str,
        include_sources: bool
    ) -> str:
        """Format as plain text."""
        lines = []

        if header:
            lines.append(header)
            lines.append("-" * 40)

        for chunk in chunks:
            lines.append(chunk.content)
            if include_sources and chunk.source:
                lines.append(f"(Source: {chunk.source})")
            lines.append("")

        if footer:
            lines.append("-" * 40)
            lines.append(footer)

        return "\n".join(lines)

    def _format_json(self, chunks: List[ContextChunk]) -> str:
        """Format as JSON."""
        data = {
            "context_chunks": [
                {
                    "content": c.content,
                    "source": c.source,
                    "relevance": c.relevance_score
                }
                for c in chunks
            ]
        }
        return json.dumps(data, indent=2)

    def _format_bulleted(
        self,
        chunks: List[ContextChunk],
        header: str,
        footer: str
    ) -> str:
        """Format as bulleted list."""
        lines = []

        if header:
            lines.append(header)

        for chunk in chunks:
            # Truncate long content for bullets
            content = chunk.content
            if len(content) > 200:
                content = content[:197] + "..."
            lines.append(f"- {content}")

        if footer:
            lines.append(footer)

        return "\n".join(lines)


class ContextEnhancer:
    """
    Enhances prompts and responses with RAG-retrieved context.

    Provides intelligent context injection, deduplication, and formatting
    to improve persona response quality.
    """

    def __init__(
        self,
        config: Optional[EnhancerConfig] = None,
        rag_connector: Optional[RAGConnector] = None
    ):
        self.config = config or EnhancerConfig()
        self._rag_connector = rag_connector
        self._token_estimator = TokenEstimator()
        self._deduplicator = ContentDeduplicator(
            similarity_threshold=self.config.similarity_threshold_for_dedup
        )
        self._formatter = ContextFormatter(format_type=self.config.context_format)

        self._enhancement_count = 0
        self._total_context_tokens = 0
        self._lock = threading.Lock()

        logger.info(
            f"ContextEnhancer initialized with strategy={self.config.strategy.value}, "
            f"format={self.config.context_format.value}"
        )

    @property
    def rag_connector(self) -> RAGConnector:
        """Get or create RAG connector."""
        if self._rag_connector is None:
            self._rag_connector = get_rag_connector()
        return self._rag_connector

    async def enhance_prompt(
        self,
        prompt: str,
        persona_id: Optional[str] = None,
        query_override: Optional[str] = None,
        additional_context: Optional[List[str]] = None,
        priority_filter: Optional[EnhancementPriority] = None
    ) -> EnhancedPrompt:
        """
        Enhance a prompt with relevant context.

        Args:
            prompt: The original prompt to enhance.
            persona_id: Optional persona ID for filtering.
            query_override: Custom query instead of using prompt.
            additional_context: Extra context to include.
            priority_filter: Minimum priority for context inclusion.

        Returns:
            EnhancedPrompt with context injected.
        """
        # Determine query for retrieval
        query = query_override or self._extract_query(prompt)

        # Retrieve context from RAG
        retrieval_context = await self.rag_connector.retrieve(
            query=query,
            persona_id=persona_id,
            top_k=self.config.max_results_to_include * 2,  # Fetch extra for filtering
            min_score=self.config.min_relevance_score
        )

        # Convert results to chunks
        chunks = self._results_to_chunks(retrieval_context.results)

        # Add additional context if provided
        if additional_context:
            for i, ctx in enumerate(additional_context):
                chunk = ContextChunk(
                    chunk_id=f"additional_{i}",
                    content=ctx,
                    source="user_provided",
                    relevance_score=1.0,  # User-provided is highly relevant
                    priority=EnhancementPriority.HIGH,
                    token_estimate=self._token_estimator.estimate(ctx)
                )
                chunks.append(chunk)

        # Filter by priority if specified
        if priority_filter:
            priority_order = list(EnhancementPriority)
            min_idx = priority_order.index(priority_filter)
            chunks = [c for c in chunks if priority_order.index(c.priority) <= min_idx]

        # Deduplicate if enabled
        if self.config.deduplicate:
            chunks = self._deduplicator.deduplicate(chunks)

        # Sort by relevance (or preserve order based on config)
        if not self.config.preserve_order:
            chunks.sort(key=lambda c: c.relevance_score, reverse=True)

        # Limit to max results
        chunks = chunks[:self.config.max_results_to_include]

        # Trim to fit token budget
        chunks, total_tokens = self._fit_token_budget(chunks)

        # Generate enhanced prompt based on strategy
        enhanced_prompt = self._apply_enhancement_strategy(prompt, chunks)

        # Update stats
        with self._lock:
            self._enhancement_count += 1
            self._total_context_tokens += total_tokens

        return EnhancedPrompt(
            original_prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            context_chunks=chunks,
            total_context_tokens=total_tokens,
            retrieval_context=retrieval_context,
            strategy_used=self.config.strategy,
            enhancement_metadata={
                "query_used": query,
                "persona_id": persona_id,
                "results_retrieved": len(retrieval_context.results),
                "chunks_included": len(chunks)
            }
        )

    def enhance_prompt_sync(
        self,
        prompt: str,
        context_texts: List[str],
        sources: Optional[List[str]] = None
    ) -> EnhancedPrompt:
        """
        Synchronously enhance a prompt with provided context.

        Args:
            prompt: The original prompt.
            context_texts: List of context texts to include.
            sources: Optional source labels for each context.

        Returns:
            EnhancedPrompt with context injected.
        """
        sources = sources or [None] * len(context_texts)

        chunks = []
        for i, (text, source) in enumerate(zip(context_texts, sources)):
            chunk = ContextChunk(
                chunk_id=f"sync_{i}",
                content=text,
                source=source,
                relevance_score=1.0 - (i * 0.1),  # Decreasing relevance
                priority=EnhancementPriority.HIGH if i < 3 else EnhancementPriority.MEDIUM,
                token_estimate=self._token_estimator.estimate(text)
            )
            chunks.append(chunk)

        # Deduplicate and trim
        if self.config.deduplicate:
            chunks = self._deduplicator.deduplicate(chunks)

        chunks = chunks[:self.config.max_results_to_include]
        chunks, total_tokens = self._fit_token_budget(chunks)

        enhanced_prompt = self._apply_enhancement_strategy(prompt, chunks)

        return EnhancedPrompt(
            original_prompt=prompt,
            enhanced_prompt=enhanced_prompt,
            context_chunks=chunks,
            total_context_tokens=total_tokens,
            retrieval_context=None,
            strategy_used=self.config.strategy
        )

    def ground_response(
        self,
        response: str,
        context_chunks: List[ContextChunk],
        verify_claims: bool = True
    ) -> EnhancedResponse:
        """
        Ground a response by verifying against context.

        Args:
            response: The response to ground.
            context_chunks: Context chunks used for generation.
            verify_claims: Whether to verify claims against context.

        Returns:
            EnhancedResponse with grounding information.
        """
        sources_used = []
        grounding_metadata: Dict[str, Any] = {}

        if not context_chunks:
            return EnhancedResponse(
                original_response=response,
                grounded_response=response,
                sources_used=[],
                confidence_score=0.5,  # No grounding available
                grounding_metadata={"warning": "No context available for grounding"}
            )

        # Extract potential facts/claims from response
        claims = self._extract_claims(response)

        # Verify each claim against context
        verified_claims = 0
        unverified_claims = []

        for claim in claims:
            is_supported, supporting_chunk = self._verify_claim(claim, context_chunks)
            if is_supported and supporting_chunk:
                verified_claims += 1
                if supporting_chunk.source and supporting_chunk.source not in sources_used:
                    sources_used.append(supporting_chunk.source)
            else:
                unverified_claims.append(claim)

        # Calculate confidence based on verification
        if claims:
            confidence = verified_claims / len(claims)
        else:
            confidence = 0.8  # Default for responses without clear claims

        grounding_metadata = {
            "total_claims": len(claims),
            "verified_claims": verified_claims,
            "unverified_claims": unverified_claims,
            "context_chunks_used": len(context_chunks)
        }

        # Add source citations if configured
        grounded_response = response
        if self.config.include_sources and sources_used:
            source_list = ", ".join(sources_used[:3])  # Limit to top 3
            grounded_response = f"{response}\n\n*Sources: {source_list}*"

        return EnhancedResponse(
            original_response=response,
            grounded_response=grounded_response,
            sources_used=sources_used,
            confidence_score=confidence,
            grounding_metadata=grounding_metadata
        )

    def _extract_query(self, prompt: str) -> str:
        """Extract the most relevant query from a prompt."""
        # Simple extraction: use the last sentence or question
        sentences = re.split(r'[.!?]', prompt)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return prompt

        # Prefer questions
        questions = [s for s in sentences if "?" in s or any(
            s.lower().startswith(q) for q in ["what", "how", "why", "when", "where", "who", "which"]
        )]

        if questions:
            return questions[-1]

        # Use last substantial sentence
        return sentences[-1] if len(sentences[-1]) > 20 else prompt[:200]

    def _results_to_chunks(self, results: List[RetrievalResult]) -> List[ContextChunk]:
        """Convert retrieval results to context chunks."""
        chunks = []

        for result in results:
            # Determine priority based on relevance
            if result.similarity_score >= 0.9:
                priority = EnhancementPriority.CRITICAL
            elif result.similarity_score >= 0.8:
                priority = EnhancementPriority.HIGH
            elif result.similarity_score >= 0.7:
                priority = EnhancementPriority.MEDIUM
            else:
                priority = EnhancementPriority.LOW

            chunk = ContextChunk(
                chunk_id=result.result_id,
                content=result.content,
                source=result.source_document,
                relevance_score=result.similarity_score,
                priority=priority,
                token_estimate=self._token_estimator.estimate(result.content),
                metadata=result.metadata
            )
            chunks.append(chunk)

        return chunks

    def _fit_token_budget(
        self,
        chunks: List[ContextChunk]
    ) -> Tuple[List[ContextChunk], int]:
        """Fit chunks within token budget."""
        included = []
        total_tokens = 0

        for chunk in chunks:
            if total_tokens + chunk.token_estimate <= self.config.max_context_tokens:
                included.append(chunk)
                total_tokens += chunk.token_estimate
            elif self.config.enable_chunking:
                # Try to fit a truncated version
                remaining_budget = self.config.max_context_tokens - total_tokens
                if remaining_budget > 50:  # Minimum meaningful chunk
                    truncated_content = self._truncate_to_tokens(
                        chunk.content, remaining_budget
                    )
                    truncated_chunk = ContextChunk(
                        chunk_id=f"{chunk.chunk_id}_truncated",
                        content=truncated_content,
                        source=chunk.source,
                        relevance_score=chunk.relevance_score,
                        priority=chunk.priority,
                        token_estimate=remaining_budget,
                        metadata={**chunk.metadata, "truncated": True}
                    )
                    included.append(truncated_chunk)
                    total_tokens += remaining_budget
                break

        return included, total_tokens

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit token limit."""
        estimated_chars = int(max_tokens * self._token_estimator.chars_per_token)

        if len(text) <= estimated_chars:
            return text

        # Truncate at word boundary
        truncated = text[:estimated_chars]
        last_space = truncated.rfind(" ")

        if last_space > estimated_chars * 0.8:
            truncated = truncated[:last_space]

        return truncated + "..."

    def _apply_enhancement_strategy(
        self,
        prompt: str,
        chunks: List[ContextChunk]
    ) -> str:
        """Apply the configured enhancement strategy."""
        if not chunks:
            if self.config.fallback_on_empty:
                return f"{self.config.fallback_message}\n\n{prompt}"
            return prompt

        formatted_context = self._formatter.format_chunks(
            chunks,
            header=self.config.context_header,
            footer=self.config.context_footer,
            include_sources=self.config.include_sources,
            include_confidence=self.config.include_confidence
        )

        if self.config.strategy == EnhancementStrategy.PREPEND:
            return f"{formatted_context}\n\n---\n\n{prompt}"

        elif self.config.strategy == EnhancementStrategy.APPEND:
            return f"{prompt}\n\n---\n\n{formatted_context}"

        elif self.config.strategy == EnhancementStrategy.STRUCTURED:
            return f"""## Task
{prompt}

{formatted_context}

## Instructions
Use the provided context to inform your response. Cite sources where applicable."""

        elif self.config.strategy == EnhancementStrategy.INLINE:
            # Look for {{context}} marker
            if "{{context}}" in prompt:
                return prompt.replace("{{context}}", formatted_context)
            else:
                # Default to prepend if no marker
                return f"{formatted_context}\n\n{prompt}"

        else:
            return f"{formatted_context}\n\n{prompt}"

    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text."""
        # Simple claim extraction based on sentences with factual indicators
        sentences = re.split(r'[.!]', text)
        claims = []

        factual_indicators = [
            "is", "are", "was", "were", "has", "have", "had",
            "will", "can", "should", "must", "according to",
            "research shows", "studies indicate", "data suggests"
        ]

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Skip very short sentences
                # Check for factual indicators
                sentence_lower = sentence.lower()
                if any(ind in sentence_lower for ind in factual_indicators):
                    claims.append(sentence)

        return claims

    def _verify_claim(
        self,
        claim: str,
        chunks: List[ContextChunk]
    ) -> Tuple[bool, Optional[ContextChunk]]:
        """Verify a claim against context chunks."""
        claim_words = set(claim.lower().split())

        # Remove common words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "must", "shall",
                      "can", "of", "in", "to", "for", "with", "on", "at", "by"}
        claim_words = claim_words - stop_words

        best_match: Optional[ContextChunk] = None
        best_overlap = 0.0

        for chunk in chunks:
            chunk_words = set(chunk.content.lower().split()) - stop_words

            if claim_words and chunk_words:
                overlap = len(claim_words & chunk_words) / len(claim_words)

                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match = chunk

        # Claim is supported if significant word overlap
        is_supported = best_overlap >= 0.3

        return is_supported, best_match if is_supported else None

    def get_metrics(self) -> Dict[str, Any]:
        """Get enhancer metrics."""
        with self._lock:
            avg_tokens = (
                self._total_context_tokens / self._enhancement_count
                if self._enhancement_count > 0 else 0.0
            )

            return {
                "enhancement_count": self._enhancement_count,
                "total_context_tokens": self._total_context_tokens,
                "average_context_tokens": avg_tokens,
                "strategy": self.config.strategy.value,
                "format": self.config.context_format.value,
                "max_context_tokens": self.config.max_context_tokens
            }


# Module-level singleton
_default_enhancer: Optional[ContextEnhancer] = None
_enhancer_lock = threading.Lock()


def get_context_enhancer(config: Optional[EnhancerConfig] = None) -> ContextEnhancer:
    """
    Get or create the default context enhancer instance.

    Args:
        config: Optional configuration for new enhancer.

    Returns:
        ContextEnhancer instance.
    """
    global _default_enhancer

    with _enhancer_lock:
        if _default_enhancer is None:
            _default_enhancer = ContextEnhancer(config=config)
        return _default_enhancer


def reset_context_enhancer() -> None:
    """Reset the default context enhancer instance."""
    global _default_enhancer

    with _enhancer_lock:
        _default_enhancer = None


async def enhance_prompt(
    prompt: str,
    persona_id: Optional[str] = None
) -> EnhancedPrompt:
    """
    Convenience function for quick prompt enhancement.

    Args:
        prompt: The prompt to enhance.
        persona_id: Optional persona ID filter.

    Returns:
        EnhancedPrompt with context.
    """
    enhancer = get_context_enhancer()
    return await enhancer.enhance_prompt(prompt, persona_id=persona_id)
