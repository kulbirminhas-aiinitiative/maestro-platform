"""
Universal Knowledge Store - Store, Index, and Retrieve Domain Knowledge
Core component of the AI Persona Foundry platform.
"""
from .models import (
    KnowledgeArtifact,
    KnowledgeType,
    KnowledgeVersion,
    KnowledgeMetadata,
    KnowledgeContribution,
    RelevanceScore,
)
from .store import KnowledgeStore
from .indexer import KnowledgeIndexer
from .retriever import KnowledgeRetriever
from .contributor import KnowledgeContributor

__version__ = "1.0.0"
__all__ = [
    "KnowledgeArtifact",
    "KnowledgeType",
    "KnowledgeVersion",
    "KnowledgeMetadata",
    "KnowledgeContribution",
    "RelevanceScore",
    "KnowledgeStore",
    "KnowledgeIndexer",
    "KnowledgeRetriever",
    "KnowledgeContributor",
]
