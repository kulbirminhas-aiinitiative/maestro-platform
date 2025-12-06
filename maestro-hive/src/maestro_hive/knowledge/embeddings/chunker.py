"""
Document Chunking Strategies for Embedding Pipeline.

EPIC: MD-2557
AC-2: Chunking strategy for large documents
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from maestro_hive.knowledge.embeddings.exceptions import ChunkingError
from maestro_hive.knowledge.embeddings.models import Chunk

logger = logging.getLogger(__name__)


class DocumentChunker(ABC):
    """
    Abstract base class for document chunking strategies.

    AC-2: Defines interface for chunking large documents.
    """

    @abstractmethod
    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """
        Split content into chunks suitable for embedding.

        Args:
            content: Full document content
            metadata: Optional metadata to attach to chunks

        Returns:
            List of Chunk objects

        Raises:
            ChunkingError: If chunking fails
        """
        pass

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Return the chunking strategy name."""
        pass


class FixedSizeChunker(DocumentChunker):
    """
    Fixed-size chunking with overlap.

    AC-2: Simple strategy for consistent chunk sizes.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        overlap: int = 50,
        unit: str = "characters",  # "characters" or "tokens"
    ):
        """
        Initialize fixed-size chunker.

        Args:
            chunk_size: Size of each chunk
            overlap: Overlap between chunks
            unit: Unit of measurement ("characters" or "tokens")
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.unit = unit

    @property
    def strategy_name(self) -> str:
        return "fixed_size"

    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split content into fixed-size chunks."""
        if not content:
            return []

        try:
            if self.unit == "tokens":
                # Approximate tokens as words
                words = content.split()
                chunks = []
                step = max(1, self.chunk_size - self.overlap)

                for i in range(0, len(words), step):
                    chunk_words = words[i : i + self.chunk_size]
                    chunk_text = " ".join(chunk_words)

                    # Calculate approximate positions
                    start = len(" ".join(words[:i])) + (1 if i > 0 else 0)
                    end = start + len(chunk_text)

                    chunks.append(
                        Chunk(
                            content=chunk_text,
                            start_position=start,
                            end_position=end,
                        )
                    )
            else:
                # Character-based chunking
                chunks = []
                step = max(1, self.chunk_size - self.overlap)

                for i in range(0, len(content), step):
                    chunk_text = content[i : i + self.chunk_size]
                    chunks.append(
                        Chunk(
                            content=chunk_text,
                            start_position=i,
                            end_position=i + len(chunk_text),
                        )
                    )

            logger.debug(f"Created {len(chunks)} fixed-size chunks")
            return chunks

        except Exception as e:
            raise ChunkingError(f"Fixed-size chunking failed: {e}")


class SemanticChunker(DocumentChunker):
    """
    Semantic chunking that respects document structure.

    AC-2: Splits on natural boundaries (paragraphs, sections).
    """

    def __init__(
        self,
        max_chunk_size: int = 512,
        overlap: int = 50,
        preserve_paragraphs: bool = True,
    ):
        """
        Initialize semantic chunker.

        Args:
            max_chunk_size: Maximum tokens per chunk
            overlap: Overlap between chunks in tokens
            preserve_paragraphs: Keep paragraphs intact if possible
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.preserve_paragraphs = preserve_paragraphs

    @property
    def strategy_name(self) -> str:
        return "semantic"

    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split content on semantic boundaries."""
        if not content:
            return []

        try:
            # Split into paragraphs first
            paragraphs = self._split_paragraphs(content)

            chunks = []
            current_chunk = ""
            current_start = 0

            for para in paragraphs:
                para_words = len(para.split())

                # If paragraph fits in remaining space
                if len(current_chunk.split()) + para_words <= self.max_chunk_size:
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    # Save current chunk if not empty
                    if current_chunk:
                        end_pos = current_start + len(current_chunk)
                        chunks.append(
                            Chunk(
                                content=current_chunk,
                                start_position=current_start,
                                end_position=end_pos,
                            )
                        )
                        current_start = end_pos

                    # Handle paragraph larger than max size
                    if para_words > self.max_chunk_size:
                        # Split large paragraph
                        sub_chunks = self._split_large_paragraph(para)
                        for sub in sub_chunks:
                            end_pos = current_start + len(sub)
                            chunks.append(
                                Chunk(
                                    content=sub,
                                    start_position=current_start,
                                    end_position=end_pos,
                                )
                            )
                            current_start = end_pos
                        current_chunk = ""
                    else:
                        current_chunk = para

            # Add remaining chunk
            if current_chunk:
                chunks.append(
                    Chunk(
                        content=current_chunk,
                        start_position=current_start,
                        end_position=current_start + len(current_chunk),
                    )
                )

            logger.debug(f"Created {len(chunks)} semantic chunks")
            return chunks

        except Exception as e:
            raise ChunkingError(f"Semantic chunking failed: {e}")

    def _split_paragraphs(self, content: str) -> List[str]:
        """Split content into paragraphs."""
        # Split on double newlines or markdown headers
        paragraphs = re.split(r'\n\n+|(?=^#+ )', content, flags=re.MULTILINE)
        return [p.strip() for p in paragraphs if p.strip()]

    def _split_large_paragraph(self, paragraph: str) -> List[str]:
        """Split a large paragraph into smaller chunks."""
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        chunks = []
        current = ""

        for sentence in sentences:
            if len((current + " " + sentence).split()) <= self.max_chunk_size:
                current = (current + " " + sentence).strip()
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks


class CodeChunker(DocumentChunker):
    """
    Specialized chunker for source code.

    AC-2: Respects code structure (functions, classes).
    """

    def __init__(
        self,
        language: str = "python",
        chunk_by: str = "function",  # "function", "class", "module"
        include_context: bool = True,
        max_chunk_size: int = 1000,
    ):
        """
        Initialize code chunker.

        Args:
            language: Programming language
            chunk_by: Chunking granularity
            include_context: Include surrounding context (imports, etc.)
            max_chunk_size: Maximum chunk size in characters
        """
        self.language = language
        self.chunk_by = chunk_by
        self.include_context = include_context
        self.max_chunk_size = max_chunk_size

    @property
    def strategy_name(self) -> str:
        return f"code_{self.chunk_by}"

    def chunk(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Split code into semantic chunks."""
        if not content:
            return []

        try:
            if self.language == "python":
                return self._chunk_python(content)
            else:
                # Fall back to line-based chunking for other languages
                return self._chunk_by_lines(content)

        except Exception as e:
            raise ChunkingError(f"Code chunking failed: {e}")

    def _chunk_python(self, content: str) -> List[Chunk]:
        """Chunk Python code by functions/classes."""
        chunks = []
        lines = content.split("\n")

        # Collect header context (imports, module docstring)
        context_lines = []
        code_start = 0

        for i, line in enumerate(lines):
            if line.startswith(("import ", "from ", "#")) or not line.strip():
                context_lines.append(line)
                code_start = i + 1
            elif line.startswith('"""') or line.startswith("'''"):
                context_lines.append(line)
                code_start = i + 1
            else:
                break

        context = "\n".join(context_lines)

        # Find function/class definitions
        current_block = []
        current_start = code_start
        in_block = False
        block_indent = 0

        for i in range(code_start, len(lines)):
            line = lines[i]
            stripped = line.lstrip()

            # Check for function or class definition
            if stripped.startswith("def ") or stripped.startswith("class "):
                # Save previous block
                if current_block and in_block:
                    block_content = "\n".join(current_block)
                    if self.include_context and context:
                        block_content = context + "\n\n" + block_content

                    start_pos = sum(len(l) + 1 for l in lines[:current_start])
                    end_pos = start_pos + len(block_content)

                    chunks.append(
                        Chunk(
                            content=block_content,
                            start_position=start_pos,
                            end_position=end_pos,
                        )
                    )

                current_block = [line]
                current_start = i
                in_block = True
                block_indent = len(line) - len(stripped)

            elif in_block:
                # Check if still in block (indented or empty)
                if not stripped or line.startswith(" " * (block_indent + 1)):
                    current_block.append(line)
                else:
                    # End of block
                    in_block = False
                    block_content = "\n".join(current_block)
                    if self.include_context and context:
                        block_content = context + "\n\n" + block_content

                    start_pos = sum(len(l) + 1 for l in lines[:current_start])
                    end_pos = start_pos + len(block_content)

                    chunks.append(
                        Chunk(
                            content=block_content,
                            start_position=start_pos,
                            end_position=end_pos,
                        )
                    )
                    current_block = []

        # Handle last block
        if current_block:
            block_content = "\n".join(current_block)
            if self.include_context and context:
                block_content = context + "\n\n" + block_content

            start_pos = sum(len(l) + 1 for l in lines[:current_start])
            end_pos = start_pos + len(block_content)

            chunks.append(
                Chunk(
                    content=block_content,
                    start_position=start_pos,
                    end_position=end_pos,
                )
            )

        # If no chunks created, return whole file as one chunk
        if not chunks:
            chunks.append(
                Chunk(
                    content=content,
                    start_position=0,
                    end_position=len(content),
                )
            )

        return chunks

    def _chunk_by_lines(self, content: str) -> List[Chunk]:
        """Fall back to line-based chunking."""
        lines = content.split("\n")
        chunks = []
        current_lines = []
        current_start = 0

        for i, line in enumerate(lines):
            current_lines.append(line)
            current_text = "\n".join(current_lines)

            if len(current_text) >= self.max_chunk_size:
                start_pos = sum(len(l) + 1 for l in lines[:current_start])
                chunks.append(
                    Chunk(
                        content=current_text,
                        start_position=start_pos,
                        end_position=start_pos + len(current_text),
                    )
                )
                current_lines = []
                current_start = i + 1

        if current_lines:
            current_text = "\n".join(current_lines)
            start_pos = sum(len(l) + 1 for l in lines[:current_start])
            chunks.append(
                Chunk(
                    content=current_text,
                    start_position=start_pos,
                    end_position=start_pos + len(current_text),
                )
            )

        return chunks


def create_chunker(
    strategy: str,
    **kwargs: Any,
) -> DocumentChunker:
    """
    Factory function to create document chunkers.

    Args:
        strategy: Chunking strategy ('fixed', 'semantic', 'code')
        **kwargs: Strategy-specific configuration

    Returns:
        Configured DocumentChunker instance
    """
    chunkers = {
        "fixed": FixedSizeChunker,
        "semantic": SemanticChunker,
        "code": CodeChunker,
    }

    if strategy not in chunkers:
        raise ValueError(
            f"Unknown chunking strategy: {strategy}. "
            f"Available: {list(chunkers.keys())}"
        )

    return chunkers[strategy](**kwargs)
