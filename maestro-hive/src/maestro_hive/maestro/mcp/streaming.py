"""
MCP Streaming Handler

Implements AC-3: Streaming support for long-running tools.

Provides streaming response handling for MCP tools that produce
incremental output over time.

Epic: MD-2565
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, AsyncIterator, Callable, Awaitable
from enum import Enum
import asyncio
import json


class StreamEventType(str, Enum):
    """Types of streaming events"""
    START = "start"
    CHUNK = "chunk"
    PROGRESS = "progress"
    ERROR = "error"
    END = "end"


@dataclass
class StreamChunk:
    """
    A single chunk in a streaming response.

    Represents one piece of output from a streaming tool execution.
    """
    event_type: StreamEventType
    data: Any
    sequence: int
    tool_name: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "event_type": self.event_type.value,
            "data": self.data,
            "sequence": self.sequence,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    def to_sse_format(self) -> str:
        """Convert to Server-Sent Events format"""
        data_str = json.dumps(self.to_dict())
        return f"event: {self.event_type.value}\ndata: {data_str}\n\n"

    def to_ndjson_format(self) -> str:
        """Convert to newline-delimited JSON format"""
        return json.dumps(self.to_dict()) + "\n"

    @classmethod
    def start(cls, tool_name: str, **metadata) -> "StreamChunk":
        """Create a start event"""
        return cls(
            event_type=StreamEventType.START,
            data={"status": "started"},
            sequence=0,
            tool_name=tool_name,
            metadata=metadata
        )

    @classmethod
    def chunk(
        cls,
        tool_name: str,
        data: Any,
        sequence: int,
        **metadata
    ) -> "StreamChunk":
        """Create a data chunk event"""
        return cls(
            event_type=StreamEventType.CHUNK,
            data=data,
            sequence=sequence,
            tool_name=tool_name,
            metadata=metadata
        )

    @classmethod
    def progress(
        cls,
        tool_name: str,
        percent: float,
        sequence: int,
        message: str = "",
        **metadata
    ) -> "StreamChunk":
        """Create a progress event"""
        return cls(
            event_type=StreamEventType.PROGRESS,
            data={"percent": percent, "message": message},
            sequence=sequence,
            tool_name=tool_name,
            metadata=metadata
        )

    @classmethod
    def error(
        cls,
        tool_name: str,
        error: str,
        sequence: int,
        **metadata
    ) -> "StreamChunk":
        """Create an error event"""
        return cls(
            event_type=StreamEventType.ERROR,
            data={"error": error},
            sequence=sequence,
            tool_name=tool_name,
            metadata=metadata
        )

    @classmethod
    def end(
        cls,
        tool_name: str,
        sequence: int,
        final_result: Any = None,
        **metadata
    ) -> "StreamChunk":
        """Create an end event"""
        return cls(
            event_type=StreamEventType.END,
            data={"status": "completed", "result": final_result},
            sequence=sequence,
            tool_name=tool_name,
            metadata=metadata
        )


class MCPStreamHandler:
    """
    Handler for streaming MCP tool executions.

    AC-3 Implementation: Manages streaming responses from long-running tools.

    Features:
    - Chunk buffering
    - Progress tracking
    - Timeout handling
    - Cancellation support
    """

    def __init__(
        self,
        tool_name: str,
        chunk_size: int = 1024,
        timeout_seconds: float = 300.0,
        buffer_size: int = 100
    ):
        """
        Initialize stream handler.

        Args:
            tool_name: Name of the tool being streamed
            chunk_size: Maximum size of each chunk
            timeout_seconds: Maximum streaming duration
            buffer_size: Maximum chunks to buffer
        """
        self.tool_name = tool_name
        self.chunk_size = chunk_size
        self.timeout_seconds = timeout_seconds
        self.buffer_size = buffer_size

        self._sequence = 0
        self._buffer: asyncio.Queue = asyncio.Queue(maxsize=buffer_size)
        self._cancelled = False
        self._completed = False
        self._error: Optional[str] = None
        self._start_time: Optional[datetime] = None
        self._chunks_sent = 0

    async def start(self) -> StreamChunk:
        """Start the streaming session"""
        self._start_time = datetime.utcnow()
        self._sequence = 0
        chunk = StreamChunk.start(self.tool_name)
        await self._buffer.put(chunk)
        return chunk

    async def send_chunk(self, data: Any, **metadata) -> StreamChunk:
        """
        Send a data chunk.

        Args:
            data: Chunk data to send
            **metadata: Additional metadata

        Returns:
            The created StreamChunk
        """
        if self._cancelled:
            raise StreamCancelled("Stream was cancelled")

        if self._completed:
            raise StreamCompleted("Stream already completed")

        self._sequence += 1
        chunk = StreamChunk.chunk(
            self.tool_name,
            data,
            self._sequence,
            **metadata
        )

        try:
            await asyncio.wait_for(
                self._buffer.put(chunk),
                timeout=1.0
            )
            self._chunks_sent += 1
        except asyncio.TimeoutError:
            # Buffer full, skip oldest if needed
            if self._buffer.full():
                try:
                    self._buffer.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                await self._buffer.put(chunk)

        return chunk

    async def send_progress(
        self,
        percent: float,
        message: str = ""
    ) -> StreamChunk:
        """
        Send a progress update.

        Args:
            percent: Completion percentage (0-100)
            message: Optional progress message

        Returns:
            The created StreamChunk
        """
        self._sequence += 1
        chunk = StreamChunk.progress(
            self.tool_name,
            percent,
            self._sequence,
            message
        )
        await self._buffer.put(chunk)
        return chunk

    async def end(self, final_result: Any = None) -> StreamChunk:
        """
        End the streaming session.

        Args:
            final_result: Optional final aggregated result

        Returns:
            The end StreamChunk
        """
        self._sequence += 1
        self._completed = True
        chunk = StreamChunk.end(
            self.tool_name,
            self._sequence,
            final_result
        )
        await self._buffer.put(chunk)
        return chunk

    async def error(self, error_message: str) -> StreamChunk:
        """
        End stream with error.

        Args:
            error_message: Error description

        Returns:
            The error StreamChunk
        """
        self._sequence += 1
        self._error = error_message
        self._completed = True
        chunk = StreamChunk.error(
            self.tool_name,
            error_message,
            self._sequence
        )
        await self._buffer.put(chunk)
        return chunk

    def cancel(self) -> None:
        """Cancel the streaming session"""
        self._cancelled = True

    async def iterate(self) -> AsyncIterator[StreamChunk]:
        """
        Iterate over stream chunks.

        Yields:
            StreamChunk objects as they become available
        """
        start_time = asyncio.get_event_loop().time()

        while not self._completed and not self._cancelled:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.timeout_seconds:
                await self.error(f"Stream timeout after {self.timeout_seconds}s")
                break

            try:
                chunk = await asyncio.wait_for(
                    self._buffer.get(),
                    timeout=1.0
                )
                yield chunk

                if chunk.event_type in (StreamEventType.END, StreamEventType.ERROR):
                    break

            except asyncio.TimeoutError:
                # No chunk available, continue waiting
                continue

    @property
    def is_active(self) -> bool:
        """Check if stream is active"""
        return not self._completed and not self._cancelled

    @property
    def chunks_sent(self) -> int:
        """Get number of chunks sent"""
        return self._chunks_sent

    @property
    def duration_seconds(self) -> float:
        """Get streaming duration"""
        if self._start_time is None:
            return 0.0
        return (datetime.utcnow() - self._start_time).total_seconds()


class StreamCancelled(Exception):
    """Raised when stream is cancelled"""
    pass


class StreamCompleted(Exception):
    """Raised when attempting to send after stream completed"""
    pass


async def stream_text_chunks(
    text: str,
    chunk_size: int = 100
) -> AsyncIterator[str]:
    """
    Utility to stream text in chunks.

    Args:
        text: Text to stream
        chunk_size: Size of each chunk

    Yields:
        Text chunks
    """
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]
        await asyncio.sleep(0)  # Allow other tasks to run


async def collect_stream(
    stream: AsyncIterator[StreamChunk]
) -> tuple[list[Any], Optional[str]]:
    """
    Collect all chunks from a stream.

    Args:
        stream: Stream iterator

    Returns:
        Tuple of (collected data, error if any)
    """
    data = []
    error = None

    async for chunk in stream:
        if chunk.event_type == StreamEventType.CHUNK:
            data.append(chunk.data)
        elif chunk.event_type == StreamEventType.ERROR:
            error = chunk.data.get("error")
            break
        elif chunk.event_type == StreamEventType.END:
            break

    return data, error
