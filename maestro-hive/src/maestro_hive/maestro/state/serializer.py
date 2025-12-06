"""
State Serializer - Advanced serialization with complex type support

EPIC: MD-2514 - AC-1: State serialization with support for complex objects

Provides:
- JSON serialization with custom encoders
- MessagePack binary serialization (optional)
- Dataclass, enum, datetime support
- Type-preserving round-trip serialization
"""

import dataclasses
import hashlib
import json
import logging
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Literal, Optional, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Optional msgpack support
try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False
    msgpack = None


class StateSerializerError(Exception):
    """Base exception for serialization errors."""
    pass


class SerializationError(StateSerializerError):
    """Raised when serialization fails."""
    pass


class DeserializationError(StateSerializerError):
    """Raised when deserialization fails."""
    pass


class StateEncoder(json.JSONEncoder):
    """
    Custom JSON encoder for complex Python types.

    Supports:
    - dataclasses
    - Enum values
    - datetime/date/time/timedelta
    - sets (converted to lists with type marker)
    - objects with __dict__
    """

    TYPE_MARKER = "__type__"
    VALUE_MARKER = "__value__"

    def default(self, obj: Any) -> Any:
        """Encode non-standard types."""
        # Dataclass
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return {
                self.TYPE_MARKER: "dataclass",
                "__class__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                self.VALUE_MARKER: dataclasses.asdict(obj),
            }

        # Enum
        if isinstance(obj, Enum):
            return {
                self.TYPE_MARKER: "enum",
                "__class__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                self.VALUE_MARKER: obj.value,
            }

        # datetime
        if isinstance(obj, datetime):
            return {
                self.TYPE_MARKER: "datetime",
                self.VALUE_MARKER: obj.isoformat(),
            }

        # date
        if isinstance(obj, date):
            return {
                self.TYPE_MARKER: "date",
                self.VALUE_MARKER: obj.isoformat(),
            }

        # time
        if isinstance(obj, time):
            return {
                self.TYPE_MARKER: "time",
                self.VALUE_MARKER: obj.isoformat(),
            }

        # timedelta
        if isinstance(obj, timedelta):
            return {
                self.TYPE_MARKER: "timedelta",
                self.VALUE_MARKER: obj.total_seconds(),
            }

        # set
        if isinstance(obj, set):
            return {
                self.TYPE_MARKER: "set",
                self.VALUE_MARKER: list(obj),
            }

        # frozenset
        if isinstance(obj, frozenset):
            return {
                self.TYPE_MARKER: "frozenset",
                self.VALUE_MARKER: list(obj),
            }

        # bytes
        if isinstance(obj, bytes):
            return {
                self.TYPE_MARKER: "bytes",
                self.VALUE_MARKER: obj.hex(),
            }

        # Generic object with __dict__
        if hasattr(obj, "__dict__"):
            return {
                self.TYPE_MARKER: "object",
                "__class__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                self.VALUE_MARKER: obj.__dict__,
            }

        return super().default(obj)


def _object_hook(
    data: Dict[str, Any],
    type_registry: Optional[Dict[str, Type]] = None,
) -> Any:
    """
    Decode custom types from JSON.

    Args:
        data: Dictionary that may contain type markers
        type_registry: Optional registry for reconstructing types

    Returns:
        Decoded object
    """
    if StateEncoder.TYPE_MARKER not in data:
        return data

    type_marker = data[StateEncoder.TYPE_MARKER]
    value = data.get(StateEncoder.VALUE_MARKER)

    if type_marker == "datetime":
        return datetime.fromisoformat(value)

    if type_marker == "date":
        return date.fromisoformat(value)

    if type_marker == "time":
        return time.fromisoformat(value)

    if type_marker == "timedelta":
        return timedelta(seconds=value)

    if type_marker == "set":
        return set(value)

    if type_marker == "frozenset":
        return frozenset(value)

    if type_marker == "bytes":
        return bytes.fromhex(value)

    if type_marker in ("dataclass", "enum", "object"):
        class_name = data.get("__class__", "")

        # Try to reconstruct from registry
        if type_registry and class_name in type_registry:
            cls = type_registry[class_name]
            if type_marker == "dataclass":
                return cls(**value)
            elif type_marker == "enum":
                return cls(value)
            elif type_marker == "object":
                obj = cls.__new__(cls)
                obj.__dict__.update(value)
                return obj

        # Return dict with metadata if can't reconstruct
        return {
            "_reconstructed": False,
            "_type": type_marker,
            "_class": class_name,
            **value,
        }

    return data


class StateSerializer:
    """
    Serializer for workflow state with complex type support.

    Supports JSON and MessagePack formats with:
    - Dataclass serialization
    - Enum preservation
    - datetime/date/time handling
    - Set/frozenset support
    - Optional type reconstruction
    """

    def __init__(
        self,
        type_registry: Optional[Dict[str, Type]] = None,
        default_format: Literal["json", "msgpack"] = "json",
    ):
        """
        Initialize serializer.

        Args:
            type_registry: Optional registry for type reconstruction
            default_format: Default serialization format
        """
        self._type_registry = type_registry or {}
        self._default_format = default_format

        if default_format == "msgpack" and not MSGPACK_AVAILABLE:
            logger.warning("MessagePack not available, falling back to JSON")
            self._default_format = "json"

    def register_type(self, cls: Type) -> None:
        """
        Register a type for reconstruction during deserialization.

        Args:
            cls: Class to register
        """
        key = f"{cls.__module__}.{cls.__name__}"
        self._type_registry[key] = cls

    def serialize(
        self,
        obj: Any,
        format: Optional[Literal["json", "msgpack"]] = None,
        compact: bool = False,
    ) -> bytes:
        """
        Serialize object to bytes.

        Args:
            obj: Object to serialize
            format: Output format (json or msgpack)
            compact: Use compact JSON (no indentation)

        Returns:
            Serialized bytes

        Raises:
            SerializationError: If serialization fails
        """
        fmt = format or self._default_format

        try:
            if fmt == "msgpack":
                if not MSGPACK_AVAILABLE:
                    raise SerializationError("MessagePack not available")
                # Convert to JSON-compatible dict first
                json_str = json.dumps(obj, cls=StateEncoder)
                data = json.loads(json_str)
                return msgpack.packb(data, use_bin_type=True)
            else:
                indent = None if compact else 2
                return json.dumps(
                    obj,
                    cls=StateEncoder,
                    indent=indent,
                    sort_keys=True,
                ).encode("utf-8")

        except Exception as e:
            raise SerializationError(f"Failed to serialize: {e}") from e

    def deserialize(
        self,
        data: bytes,
        format: Optional[Literal["json", "msgpack"]] = None,
        target_type: Optional[Type[T]] = None,
    ) -> Union[T, Any]:
        """
        Deserialize bytes to object.

        Args:
            data: Serialized bytes
            format: Input format (json or msgpack)
            target_type: Optional type hint for result

        Returns:
            Deserialized object

        Raises:
            DeserializationError: If deserialization fails
        """
        fmt = format or self._default_format

        try:
            if fmt == "msgpack":
                if not MSGPACK_AVAILABLE:
                    raise DeserializationError("MessagePack not available")
                raw = msgpack.unpackb(data, raw=False)
                # Apply object hook recursively
                return self._apply_object_hook(raw)
            else:
                return json.loads(
                    data.decode("utf-8"),
                    object_hook=lambda d: _object_hook(d, self._type_registry),
                )

        except Exception as e:
            raise DeserializationError(f"Failed to deserialize: {e}") from e

    def _apply_object_hook(self, obj: Any) -> Any:
        """Apply object hook recursively for msgpack data."""
        if isinstance(obj, dict):
            obj = {k: self._apply_object_hook(v) for k, v in obj.items()}
            return _object_hook(obj, self._type_registry)
        elif isinstance(obj, list):
            return [self._apply_object_hook(item) for item in obj]
        return obj

    def compute_checksum(
        self,
        data: bytes,
        algorithm: str = "sha256",
    ) -> str:
        """
        Compute checksum of serialized data.

        Args:
            data: Serialized bytes
            algorithm: Hash algorithm (sha256, md5, etc.)

        Returns:
            Hex digest of checksum
        """
        hasher = hashlib.new(algorithm)
        hasher.update(data)
        return hasher.hexdigest()

    def serialize_with_checksum(
        self,
        obj: Any,
        format: Optional[Literal["json", "msgpack"]] = None,
    ) -> tuple:
        """
        Serialize object and return with checksum.

        Args:
            obj: Object to serialize
            format: Output format

        Returns:
            Tuple of (serialized_bytes, checksum)
        """
        data = self.serialize(obj, format)
        checksum = self.compute_checksum(data)
        return data, checksum

    def verify_checksum(
        self,
        data: bytes,
        expected_checksum: str,
        algorithm: str = "sha256",
    ) -> bool:
        """
        Verify data checksum.

        Args:
            data: Serialized bytes
            expected_checksum: Expected checksum
            algorithm: Hash algorithm

        Returns:
            True if checksum matches
        """
        actual = self.compute_checksum(data, algorithm)
        return actual == expected_checksum
