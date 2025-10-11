"""
Artifact Storage Module
Version: 1.0.0

Content-addressable artifact storage with deduplication.
"""

from contracts.artifacts.models import Artifact, ArtifactManifest, compute_sha256
from contracts.artifacts.store import ArtifactStore

__all__ = ["Artifact", "ArtifactManifest", "compute_sha256", "ArtifactStore"]
