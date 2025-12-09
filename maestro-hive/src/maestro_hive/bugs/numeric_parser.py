"""
Numeric Parser - Fix for MD-1993.

Provides centralized parsing of numeric values including Prisma Decimal types.
Addresses the issue where Team Performance Overview shows zeros because
parseNumericValue fails on Prisma Decimal objects.

Usage:
    from maestro_hive.bugs import parse_numeric_value

    # Handle any numeric type safely
    value = parse_numeric_value(prisma_decimal_field)

EPIC: MD-2798 - [Bugs] Known Issues & Fixes
Task: MD-1993 - Team Performance Overview showing all zeros
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class NumericParseError(Exception):
    """Exception raised when numeric parsing fails."""

    def __init__(self, value: Any, reason: str):
        self.value = value
        self.reason = reason
        super().__init__(f"Failed to parse numeric value '{value}': {reason}")


def parse_numeric_value(
    value: Any,
    default: float = 0.0,
    precision: int = 6,
    raise_on_error: bool = False,
) -> float:
    """
    Safely convert any numeric type to float.

    Handles:
    - None/undefined values (returns default)
    - String values (parseFloat equivalent)
    - Integer values (direct conversion)
    - Float values (pass through)
    - Decimal objects from Prisma (calls appropriate conversion)
    - Objects with toNumber() method (Prisma Decimal pattern)

    Args:
        value: The value to parse. Can be any type.
        default: Value to return if parsing fails. Default 0.0.
        precision: Number of decimal places for rounding. Default 6.
        raise_on_error: If True, raise NumericParseError instead of returning default.

    Returns:
        float: The parsed numeric value, or default if parsing fails.

    Raises:
        NumericParseError: If raise_on_error is True and parsing fails.

    Examples:
        >>> parse_numeric_value(None)
        0.0
        >>> parse_numeric_value("3.14")
        3.14
        >>> parse_numeric_value(42)
        42.0
        >>> parse_numeric_value(Decimal("123.456789"))
        123.456789
    """
    try:
        # Handle None/undefined
        if value is None:
            return default

        # Handle string values
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default
            try:
                return round(float(value), precision)
            except ValueError:
                if raise_on_error:
                    raise NumericParseError(value, "Invalid string format")
                logger.warning(f"Failed to parse string as float: {value}")
                return default

        # Handle integer values
        if isinstance(value, int) and not isinstance(value, bool):
            return float(value)

        # Handle float values
        if isinstance(value, float):
            return round(value, precision)

        # Handle Decimal objects (Python decimal.Decimal)
        if isinstance(value, Decimal):
            try:
                quantized = value.quantize(
                    Decimal(10) ** -precision,
                    rounding=ROUND_HALF_UP
                )
                return float(quantized)
            except InvalidOperation:
                if raise_on_error:
                    raise NumericParseError(value, "Invalid Decimal value")
                logger.warning(f"Failed to convert Decimal: {value}")
                return default

        # Handle objects with toNumber() method (Prisma Decimal pattern in JS/TS)
        if hasattr(value, 'toNumber') and callable(getattr(value, 'toNumber')):
            try:
                return round(value.toNumber(), precision)
            except Exception as e:
                if raise_on_error:
                    raise NumericParseError(value, f"toNumber() failed: {e}")
                logger.warning(f"toNumber() method failed: {e}")
                return default

        # Handle objects with __float__ method (but not booleans)
        if hasattr(value, '__float__') and not isinstance(value, bool):
            try:
                return round(float(value), precision)
            except Exception as e:
                if raise_on_error:
                    raise NumericParseError(value, f"__float__ failed: {e}")
                logger.warning(f"__float__ conversion failed: {e}")
                return default

        # Handle dict with 'value' key (some ORM patterns)
        if isinstance(value, dict) and 'value' in value:
            return parse_numeric_value(value['value'], default, precision, raise_on_error)

        # Unknown type
        if raise_on_error:
            raise NumericParseError(value, f"Unsupported type: {type(value).__name__}")
        logger.warning(f"Unknown type for numeric conversion: {type(value).__name__}")
        return default

    except NumericParseError:
        raise
    except Exception as e:
        if raise_on_error:
            raise NumericParseError(value, str(e))
        logger.error(f"Unexpected error parsing numeric value: {e}")
        return default


def parse_decimal(
    value: Any,
    precision: int = 6,
    default: Optional[Decimal] = None,
) -> Optional[Decimal]:
    """
    Parse a value to Python Decimal with specified precision.

    Useful for financial calculations where float precision is insufficient.

    Args:
        value: Value to parse.
        precision: Number of decimal places.
        default: Value to return on failure. Default None.

    Returns:
        Decimal or default value.

    Examples:
        >>> parse_decimal("123.456789", precision=4)
        Decimal('123.4568')
    """
    if value is None:
        return default

    try:
        if isinstance(value, Decimal):
            return value.quantize(Decimal(10) ** -precision, rounding=ROUND_HALF_UP)

        if isinstance(value, (int, float)):
            return Decimal(str(value)).quantize(
                Decimal(10) ** -precision,
                rounding=ROUND_HALF_UP
            )

        if isinstance(value, str):
            return Decimal(value.strip()).quantize(
                Decimal(10) ** -precision,
                rounding=ROUND_HALF_UP
            )

        # Try float conversion first
        float_val = parse_numeric_value(value, raise_on_error=True)
        return Decimal(str(float_val)).quantize(
            Decimal(10) ** -precision,
            rounding=ROUND_HALF_UP
        )

    except Exception as e:
        logger.warning(f"Failed to parse as Decimal: {value} - {e}")
        return default


def safe_divide(
    numerator: Any,
    denominator: Any,
    default: float = 0.0,
    precision: int = 6,
) -> float:
    """
    Safely divide two numeric values.

    Handles division by zero, None values, and Prisma Decimal types.

    Args:
        numerator: The numerator value.
        denominator: The denominator value.
        default: Value to return on division by zero or error.
        precision: Decimal places for result.

    Returns:
        float: Result of division or default value.

    Examples:
        >>> safe_divide(10, 2)
        5.0
        >>> safe_divide(10, 0)
        0.0
        >>> safe_divide(None, 5)
        0.0
    """
    num = parse_numeric_value(numerator, default=0.0, precision=precision)
    denom = parse_numeric_value(denominator, default=0.0, precision=precision)

    if denom == 0.0:
        return default

    return round(num / denom, precision)


def aggregate_numeric_values(
    values: List[Any],
    operation: str = "sum",
    precision: int = 6,
    skip_none: bool = True,
) -> float:
    """
    Aggregate a list of numeric values.

    Safely handles mixed types including Prisma Decimals.

    Args:
        values: List of values to aggregate.
        operation: One of "sum", "avg", "min", "max".
        precision: Decimal places for result.
        skip_none: If True, skip None values. If False, treat as 0.

    Returns:
        float: Aggregated result.

    Examples:
        >>> aggregate_numeric_values([1, 2, Decimal("3.5"), "4.5"], "sum")
        11.0
        >>> aggregate_numeric_values([10, 20, 30], "avg")
        20.0
    """
    parsed_values = []
    for v in values:
        if v is None and skip_none:
            continue
        parsed = parse_numeric_value(v, default=0.0, precision=precision)
        parsed_values.append(parsed)

    if not parsed_values:
        return 0.0

    if operation == "sum":
        return round(sum(parsed_values), precision)
    elif operation == "avg":
        return round(sum(parsed_values) / len(parsed_values), precision)
    elif operation == "min":
        return round(min(parsed_values), precision)
    elif operation == "max":
        return round(max(parsed_values), precision)
    else:
        raise ValueError(f"Unknown operation: {operation}")


# Type alias for TypeScript-like interface
NumericValue = Union[int, float, Decimal, str, None]
