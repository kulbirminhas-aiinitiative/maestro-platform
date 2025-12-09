"""
Knowledge Indexer - Index artifacts for efficient search

Implements:
- AC-2543-1: Index knowledge artifacts with semantic search capabilities
"""
import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

from .models import (
    KnowledgeArtifact,
    KnowledgeType,
    RelevanceScore,
)


logger = logging.getLogger(__name__)


@dataclass
class IndexEntry:
    """Entry in the inverted index."""
    artifact_id: UUID
    term_frequency: int = 1
    positions: List[int] = field(default_factory=list)
    field: str = "content"  # title, content, keywords, tags


@dataclass
class SearchResult:
    """Result from a search query."""
    artifact_id: UUID
    score: RelevanceScore
    highlights: List[str] = field(default_factory=list)
    matched_terms: List[str] = field(default_factory=list)


class KnowledgeIndexer:
    """
    Indexes knowledge artifacts for efficient search and retrieval.
    
    Features:
    - Inverted index for keyword search
    - TF-IDF scoring
    - Semantic similarity (simulated with keyword overlap)
    - Domain-aware indexing
    """
    
    def __init__(self):
        """Initialize the indexer."""
        # Inverted index: term -> list of IndexEntry
        self._inverted_index: Dict[str, List[IndexEntry]] = defaultdict(list)
        
        # Document frequency: term -> number of documents containing it
        self._doc_frequency: Dict[str, int] = defaultdict(int)
        
        # Document lengths for normalization
        self._doc_lengths: Dict[UUID, int] = {}
        
        # Total document count
        self._total_docs = 0
        
        # Domain-specific vocabularies
        self._domain_terms: Dict[str, Set[str]] = defaultdict(set)
        
        # Stopwords
        self._stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "to", "of", "in", "for", "on", "with", "at", "by",
            "from", "as", "into", "through", "during", "before", "after",
            "above", "below", "between", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "each", "few", "more", "most", "other", "some",
            "such", "no", "nor", "not", "only", "own", "same", "so",
            "than", "too", "very", "just", "and", "but", "if", "or",
            "because", "until", "while", "this", "that", "these", "those",
        }
        
        logger.info("KnowledgeIndexer initialized")
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        # Lowercase and extract words
        text_lower = text.lower()
        words = re.findall(r'\b[a-z][a-z0-9_]*\b', text_lower)
        
        # Filter stopwords and short words
        tokens = [w for w in words if len(w) > 2 and w not in self._stopwords]
        
        return tokens
    
    def _get_term_positions(self, text: str, term: str) -> List[int]:
        """Get positions of a term in text."""
        text_lower = text.lower()
        positions = []
        start = 0
        while True:
            pos = text_lower.find(term, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        return positions
    
    def index_artifact(self, artifact: KnowledgeArtifact) -> None:
        """
        Index a knowledge artifact.
        
        Args:
            artifact: Artifact to index
        """
        # Remove any existing index entries for this artifact
        self.remove_artifact(artifact.id)
        
        # Combine searchable text
        all_text = f"{artifact.title} {artifact.content}"
        
        # Tokenize
        tokens = self._tokenize(all_text)
        
        # Count term frequencies
        term_freq: Dict[str, int] = defaultdict(int)
        for token in tokens:
            term_freq[token] += 1
        
        # Update inverted index
        for term, freq in term_freq.items():
            entry = IndexEntry(
                artifact_id=artifact.id,
                term_frequency=freq,
                positions=self._get_term_positions(all_text.lower(), term),
                field="content",
            )
            self._inverted_index[term].append(entry)
            self._doc_frequency[term] += 1
        
        # Index keywords separately
        for keyword in artifact.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower not in term_freq:
                entry = IndexEntry(
                    artifact_id=artifact.id,
                    term_frequency=3,  # Boost keyword matches
                    positions=[],
                    field="keywords",
                )
                self._inverted_index[keyword_lower].append(entry)
                self._doc_frequency[keyword_lower] += 1
        
        # Index tags
        for tag in artifact.metadata.tags:
            tag_lower = tag.lower()
            entry = IndexEntry(
                artifact_id=artifact.id,
                term_frequency=5,  # Boost tag matches
                positions=[],
                field="tags",
            )
            self._inverted_index[tag_lower].append(entry)
            self._doc_frequency[tag_lower] += 1
        
        # Track document length and count
        self._doc_lengths[artifact.id] = len(tokens)
        self._total_docs += 1
        
        # Track domain vocabulary
        if artifact.metadata.domain:
            self._domain_terms[artifact.metadata.domain].update(tokens)
        
        logger.debug("Indexed artifact %s with %d terms", artifact.id, len(term_freq))
    
    def remove_artifact(self, artifact_id: UUID) -> None:
        """Remove an artifact from the index."""
        # Remove from inverted index
        terms_to_remove = []
        for term, entries in self._inverted_index.items():
            original_len = len(entries)
            self._inverted_index[term] = [e for e in entries if e.artifact_id != artifact_id]
            if len(self._inverted_index[term]) < original_len:
                self._doc_frequency[term] -= 1
            if not self._inverted_index[term]:
                terms_to_remove.append(term)
        
        for term in terms_to_remove:
            del self._inverted_index[term]
            del self._doc_frequency[term]
        
        # Remove document length
        if artifact_id in self._doc_lengths:
            del self._doc_lengths[artifact_id]
            self._total_docs = max(0, self._total_docs - 1)
    
    def search(
        self,
        query: str,
        domain: Optional[str] = None,
        knowledge_types: Optional[List[KnowledgeType]] = None,
        limit: int = 20,
    ) -> List[Tuple[UUID, RelevanceScore]]:
        """
        Search for artifacts matching the query.
        
        Args:
            query: Search query string
            domain: Optional domain filter
            knowledge_types: Optional type filter
            limit: Maximum results
        
        Returns:
            List of (artifact_id, relevance_score) tuples
        """
        # Tokenize query
        query_terms = self._tokenize(query)
        
        if not query_terms:
            return []
        
        # Calculate scores for each matching document
        scores: Dict[UUID, RelevanceScore] = {}
        matched_terms: Dict[UUID, Set[str]] = defaultdict(set)
        
        for term in query_terms:
            if term not in self._inverted_index:
                continue
            
            # Calculate IDF for this term
            idf = math.log(self._total_docs / (self._doc_frequency[term] + 1)) + 1
            
            for entry in self._inverted_index[term]:
                aid = entry.artifact_id
                
                if aid not in scores:
                    scores[aid] = RelevanceScore()
                
                # TF-IDF contribution
                tf = entry.term_frequency
                doc_len = self._doc_lengths.get(aid, 1)
                normalized_tf = tf / (doc_len + 1)
                tfidf = normalized_tf * idf
                
                # Add to keyword match score
                scores[aid].keyword_match += tfidf
                matched_terms[aid].add(term)
                
                # Boost for field-specific matches
                if entry.field == "tags":
                    scores[aid].keyword_match += 0.2
                elif entry.field == "keywords":
                    scores[aid].keyword_match += 0.1
        
        # Calculate domain relevance
        if domain and domain in self._domain_terms:
            domain_vocab = self._domain_terms[domain]
            for aid in scores:
                overlap = len(matched_terms[aid] & domain_vocab)
                scores[aid].domain_relevance = min(1.0, overlap / (len(query_terms) + 1))
        
        # Normalize keyword scores
        if scores:
            max_keyword = max(s.keyword_match for s in scores.values())
            if max_keyword > 0:
                for s in scores.values():
                    s.keyword_match = min(1.0, s.keyword_match / max_keyword)
        
        # Simulate semantic similarity (based on term overlap)
        query_set = set(query_terms)
        for aid in scores:
            term_overlap = len(matched_terms[aid]) / len(query_set)
            scores[aid].semantic_similarity = min(1.0, term_overlap)
        
        # Sort by overall score
        sorted_results = sorted(
            scores.items(),
            key=lambda x: x[1].overall_score(),
            reverse=True,
        )
        
        return sorted_results[:limit]
    
    def suggest_terms(self, prefix: str, limit: int = 10) -> List[str]:
        """
        Suggest terms for autocomplete.
        
        Args:
            prefix: Prefix to match
            limit: Maximum suggestions
        
        Returns:
            List of matching terms
        """
        prefix_lower = prefix.lower()
        matches = []
        
        for term in self._inverted_index.keys():
            if term.startswith(prefix_lower):
                matches.append((term, self._doc_frequency[term]))
        
        # Sort by frequency
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return [m[0] for m in matches[:limit]]
    
    def get_related_terms(self, term: str, limit: int = 10) -> List[str]:
        """
        Get terms that frequently co-occur with the given term.
        
        Args:
            term: Term to find related terms for
            limit: Maximum results
        
        Returns:
            List of related terms
        """
        term_lower = term.lower()
        
        if term_lower not in self._inverted_index:
            return []
        
        # Get documents containing this term
        doc_ids = {e.artifact_id for e in self._inverted_index[term_lower]}
        
        # Count co-occurring terms
        cooccurrence: Dict[str, int] = defaultdict(int)
        for other_term, entries in self._inverted_index.items():
            if other_term == term_lower:
                continue
            for entry in entries:
                if entry.artifact_id in doc_ids:
                    cooccurrence[other_term] += 1
        
        # Sort by frequency
        sorted_terms = sorted(cooccurrence.items(), key=lambda x: x[1], reverse=True)
        
        return [t[0] for t in sorted_terms[:limit]]
    
    def get_domain_vocabulary(self, domain: str) -> Set[str]:
        """Get vocabulary specific to a domain."""
        return self._domain_terms.get(domain, set())
    
    def get_stats(self) -> Dict[str, Any]:
        """Get indexer statistics."""
        return {
            "total_documents": self._total_docs,
            "unique_terms": len(self._inverted_index),
            "domains_indexed": len(self._domain_terms),
            "avg_doc_length": (
                sum(self._doc_lengths.values()) / len(self._doc_lengths)
                if self._doc_lengths else 0
            ),
        }
