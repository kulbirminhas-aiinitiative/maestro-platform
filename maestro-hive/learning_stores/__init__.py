#!/usr/bin/env python3
"""
Learning Stores Package for RAG-based Pattern Learning.

Implements three learning stores for AI agent execution patterns:
- Template Learning: Learn which templates work for requirements
- Quality Learning: Learn from quality outcomes of decisions
- Coordination Learning: Learn optimal team composition and execution modes

EPIC: MD-2490
"""

from learning_stores.models import (
    Base,
    TemplateExecution,
    QualityOutcome,
    CoordinationPattern,
    DecisionType,
    Outcome,
    ExecutionMode,
)

from learning_stores.embedding_pipeline import (
    EmbeddingPipeline,
    EmbeddingConfig,
)

from learning_stores.template_learning import TemplateLearningService
from learning_stores.quality_learning import QualityLearningService
from learning_stores.coordination_learning import CoordinationLearningService

__all__ = [
    # Models
    'Base',
    'TemplateExecution',
    'QualityOutcome',
    'CoordinationPattern',
    'DecisionType',
    'Outcome',
    'ExecutionMode',

    # Services
    'EmbeddingPipeline',
    'EmbeddingConfig',
    'TemplateLearningService',
    'QualityLearningService',
    'CoordinationLearningService',
]

__version__ = '1.0.0'
