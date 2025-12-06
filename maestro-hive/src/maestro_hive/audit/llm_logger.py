"""
LLM Call Logger with PII Masking.

EU AI Act Article 12 Compliance:
Records all LLM interactions while protecting personal data.
"""

import hashlib
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern, Tuple
from uuid import UUID

from .models import (
    LLMCallRecord,
    PIIMaskingLevel,
    AuditQueryResult
)


logger = logging.getLogger(__name__)


class PIIMasker:
    """
    Detects and masks Personally Identifiable Information (PII).
    """

    # Common PII patterns
    PATTERNS: Dict[str, Pattern] = {
        "email": re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ),
        "phone": re.compile(
            r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'
        ),
        "ssn": re.compile(
            r'\b[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4}\b'
        ),
        "credit_card": re.compile(
            r'\b(?:[0-9]{4}[-\s]?){3}[0-9]{4}\b'
        ),
        "ip_address": re.compile(
            r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ),
        "date_of_birth": re.compile(
            r'\b(?:0?[1-9]|1[0-2])[/\-](?:0?[1-9]|[12][0-9]|3[01])[/\-](?:19|20)[0-9]{2}\b'
        ),
        "passport": re.compile(
            r'\b[A-Z]{1,2}[0-9]{6,9}\b'
        ),
        "api_key": re.compile(
            r'\b(?:sk|pk|api|key|token|secret)[-_]?[A-Za-z0-9]{20,}\b',
            re.IGNORECASE
        ),
        "jwt": re.compile(
            r'\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b'
        )
    }

    # Mask replacements
    MASKS: Dict[str, str] = {
        "email": "[EMAIL_REDACTED]",
        "phone": "[PHONE_REDACTED]",
        "ssn": "[SSN_REDACTED]",
        "credit_card": "[CARD_REDACTED]",
        "ip_address": "[IP_REDACTED]",
        "date_of_birth": "[DOB_REDACTED]",
        "passport": "[PASSPORT_REDACTED]",
        "api_key": "[API_KEY_REDACTED]",
        "jwt": "[JWT_REDACTED]"
    }

    def __init__(self, custom_patterns: Optional[Dict[str, Tuple[Pattern, str]]] = None):
        """
        Initialize the PII masker.

        Args:
            custom_patterns: Additional patterns to detect
        """
        self.patterns = self.PATTERNS.copy()
        self.masks = self.MASKS.copy()

        if custom_patterns:
            for name, (pattern, mask) in custom_patterns.items():
                self.patterns[name] = pattern
                self.masks[name] = mask

    def detect_pii(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text without masking.

        Args:
            text: Text to scan

        Returns:
            List of detected PII types and locations
        """
        detections = []

        for pii_type, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                detections.append({
                    "type": pii_type,
                    "start": match.start(),
                    "end": match.end(),
                    "length": match.end() - match.start()
                })

        return detections

    def mask_pii(
        self,
        text: str,
        level: PIIMaskingLevel = PIIMaskingLevel.FULL
    ) -> Tuple[str, List[str], int]:
        """
        Mask PII in text based on masking level.

        Args:
            text: Text to mask
            level: Masking level

        Returns:
            Tuple of (masked_text, detected_types, mask_count)
        """
        if level == PIIMaskingLevel.NONE:
            return text, [], 0

        detected_types = set()
        mask_count = 0
        masked_text = text

        for pii_type, pattern in self.patterns.items():
            matches = list(pattern.finditer(masked_text))
            if matches:
                detected_types.add(pii_type)
                mask_count += len(matches)

                if level == PIIMaskingLevel.FULL:
                    masked_text = pattern.sub(self.masks[pii_type], masked_text)
                elif level == PIIMaskingLevel.PARTIAL:
                    # Show first/last chars for partial masking
                    for match in reversed(matches):
                        original = match.group()
                        if len(original) > 4:
                            partial = f"{original[:2]}...{original[-2:]}"
                        else:
                            partial = self.masks[pii_type]
                        masked_text = (
                            masked_text[:match.start()] +
                            partial +
                            masked_text[match.end():]
                        )
                elif level == PIIMaskingLevel.REDACTED:
                    # Complete redaction with consistent length
                    masked_text = pattern.sub("[REDACTED]", masked_text)

        return masked_text, list(detected_types), mask_count


class LLMCallLogger:
    """
    Logs LLM API calls with automatic PII masking.

    Ensures compliance with data protection requirements
    while maintaining useful audit trails.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        masking_level: PIIMaskingLevel = PIIMaskingLevel.FULL,
        max_records_in_memory: int = 10000,
        auto_persist: bool = True,
        custom_pii_patterns: Optional[Dict[str, Tuple[Pattern, str]]] = None
    ):
        """
        Initialize the LLM call logger.

        Args:
            storage_path: Path for persistent storage
            masking_level: Default PII masking level
            max_records_in_memory: Maximum records in memory
            auto_persist: Whether to auto-persist
            custom_pii_patterns: Additional PII patterns
        """
        self.storage_path = storage_path or Path("./audit/llm_calls")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.masking_level = masking_level
        self.max_records_in_memory = max_records_in_memory
        self.auto_persist = auto_persist

        self.pii_masker = PIIMasker(custom_pii_patterns)

        self._records: List[LLMCallRecord] = []
        self._records_by_context: Dict[str, List[LLMCallRecord]] = {}

        # Statistics
        self._total_tokens_logged = 0
        self._total_pii_masked = 0

        logger.info(
            f"LLMCallLogger initialized with masking level: {masking_level.value}"
        )

    def log_call(
        self,
        provider: str,
        model: str,
        input_prompt: str,
        output_response: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        context_id: str = "",
        context_type: str = "",
        purpose: str = "",
        success: bool = True,
        error_message: Optional[str] = None,
        estimated_cost_usd: float = 0.0,
        masking_level: Optional[PIIMaskingLevel] = None
    ) -> LLMCallRecord:
        """
        Log an LLM API call with PII masking.

        Args:
            provider: LLM provider (e.g., "openai", "anthropic")
            model: Model name (e.g., "gpt-4", "claude-3")
            input_prompt: The input prompt
            output_response: The model response
            input_tokens: Input token count
            output_tokens: Output token count
            latency_ms: Response latency in milliseconds
            context_id: Context identifier
            context_type: Type of context
            purpose: Purpose of the call
            success: Whether the call succeeded
            error_message: Error message if failed
            estimated_cost_usd: Estimated cost
            masking_level: Override default masking level

        Returns:
            The created LLMCallRecord
        """
        level = masking_level or self.masking_level

        # Mask PII in input
        masked_input, input_pii_types, input_mask_count = self.pii_masker.mask_pii(
            input_prompt, level
        )

        # Mask PII in output
        masked_output, output_pii_types, output_mask_count = self.pii_masker.mask_pii(
            output_response, level
        )

        all_pii_types = list(set(input_pii_types + output_pii_types))
        total_masks = input_mask_count + output_mask_count

        record = LLMCallRecord(
            provider=provider,
            model=model,
            input_prompt=masked_input,
            input_tokens=input_tokens,
            output_response=masked_output,
            output_tokens=output_tokens,
            masking_level=level,
            pii_detected=all_pii_types,
            pii_patterns_masked=total_masks,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            context_id=context_id,
            context_type=context_type,
            purpose=purpose,
            estimated_cost_usd=estimated_cost_usd
        )

        self._records.append(record)

        # Index by context
        if context_id:
            if context_id not in self._records_by_context:
                self._records_by_context[context_id] = []
            self._records_by_context[context_id].append(record)

        # Update statistics
        self._total_tokens_logged += input_tokens + output_tokens
        self._total_pii_masked += total_masks

        logger.debug(
            f"Logged {provider}/{model} call: {input_tokens}+{output_tokens} tokens, "
            f"{total_masks} PII masked"
        )

        # Auto-persist if threshold reached
        if self.auto_persist and len(self._records) >= self.max_records_in_memory:
            self._persist_to_storage()

        return record

    def get_calls_for_context(
        self,
        context_id: str,
        provider: Optional[str] = None
    ) -> List[LLMCallRecord]:
        """
        Get all LLM calls for a specific context.

        Args:
            context_id: The context ID
            provider: Optional provider filter

        Returns:
            List of matching records
        """
        records = self._records_by_context.get(context_id, [])

        if provider:
            records = [r for r in records if r.provider == provider]

        return records

    def query_calls(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        context_type: Optional[str] = None,
        success_only: bool = False,
        has_pii: Optional[bool] = None,
        min_tokens: Optional[int] = None,
        page: int = 1,
        page_size: int = 100
    ) -> AuditQueryResult:
        """
        Query LLM call records with filters.

        Args:
            provider: Filter by provider
            model: Filter by model
            start_time: Start of time range
            end_time: End of time range
            context_type: Filter by context type
            success_only: Only successful calls
            has_pii: Filter by PII detection
            min_tokens: Minimum token threshold
            page: Page number
            page_size: Records per page

        Returns:
            AuditQueryResult with matching records
        """
        import time
        start = time.time()

        filtered = self._records.copy()

        if provider:
            filtered = [r for r in filtered if r.provider == provider]

        if model:
            filtered = [r for r in filtered if r.model == model]

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]

        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        if context_type:
            filtered = [r for r in filtered if r.context_type == context_type]

        if success_only:
            filtered = [r for r in filtered if r.success]

        if has_pii is not None:
            if has_pii:
                filtered = [r for r in filtered if r.pii_patterns_masked > 0]
            else:
                filtered = [r for r in filtered if r.pii_patterns_masked == 0]

        if min_tokens is not None:
            filtered = [
                r for r in filtered
                if (r.input_tokens + r.output_tokens) >= min_tokens
            ]

        # Pagination
        total_count = len(filtered)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_records = filtered[start_idx:end_idx]

        query_time_ms = int((time.time() - start) * 1000)

        return AuditQueryResult(
            records=[r.to_dict() for r in page_records],
            total_count=total_count,
            page=page,
            page_size=page_size,
            query_time_ms=query_time_ms,
            filters_applied={
                "provider": provider,
                "model": model,
                "start_time": start_time.isoformat() if start_time else None,
                "end_time": end_time.isoformat() if end_time else None,
                "context_type": context_type,
                "success_only": success_only,
                "has_pii": has_pii,
                "min_tokens": min_tokens
            }
        )

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about logged LLM calls.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary of statistics
        """
        filtered = self._records.copy()

        if start_time:
            filtered = [r for r in filtered if r.timestamp >= start_time]
        if end_time:
            filtered = [r for r in filtered if r.timestamp <= end_time]

        # Count by provider
        by_provider = {}
        for record in filtered:
            by_provider[record.provider] = by_provider.get(record.provider, 0) + 1

        # Count by model
        by_model = {}
        for record in filtered:
            by_model[record.model] = by_model.get(record.model, 0) + 1

        # Token statistics
        total_input = sum(r.input_tokens for r in filtered)
        total_output = sum(r.output_tokens for r in filtered)

        # Latency statistics
        latencies = [r.latency_ms for r in filtered]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        # Cost statistics
        total_cost = sum(r.estimated_cost_usd for r in filtered)

        # PII statistics
        calls_with_pii = sum(1 for r in filtered if r.pii_patterns_masked > 0)
        total_pii_masked = sum(r.pii_patterns_masked for r in filtered)

        return {
            "total_calls": len(filtered),
            "calls_by_provider": by_provider,
            "calls_by_model": by_model,
            "token_statistics": {
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "total_tokens": total_input + total_output,
                "average_tokens_per_call": (
                    (total_input + total_output) / len(filtered) if filtered else 0
                )
            },
            "latency_statistics": {
                "average_latency_ms": round(avg_latency, 2),
                "min_latency_ms": min(latencies) if latencies else 0,
                "max_latency_ms": max(latencies) if latencies else 0
            },
            "cost_statistics": {
                "total_cost_usd": round(total_cost, 4),
                "average_cost_per_call": (
                    round(total_cost / len(filtered), 6) if filtered else 0
                )
            },
            "pii_statistics": {
                "calls_with_pii_detected": calls_with_pii,
                "total_pii_patterns_masked": total_pii_masked,
                "pii_detection_rate": (
                    round(calls_with_pii / len(filtered), 3) if filtered else 0
                )
            },
            "success_rate": (
                round(sum(1 for r in filtered if r.success) / len(filtered), 3)
                if filtered else 1.0
            )
        }

    def _persist_to_storage(self) -> None:
        """Persist records to storage."""
        if not self._records:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"llm_calls_{timestamp}.json"
        filepath = self.storage_path / filename

        records_data = [r.to_dict() for r in self._records]

        with open(filepath, "w") as f:
            json.dump(records_data, f, indent=2)

        logger.info(f"Persisted {len(self._records)} LLM call records to {filepath}")

        self._records = []
        self._records_by_context = {}

    def export_for_audit(
        self,
        start_time: datetime,
        end_time: datetime,
        output_path: Path,
        include_content: bool = False
    ) -> Dict[str, Any]:
        """
        Export LLM calls for external audit.

        Args:
            start_time: Start of export range
            end_time: End of export range
            output_path: Path for export file
            include_content: Whether to include prompts/responses

        Returns:
            Export metadata
        """
        result = self.query_calls(
            start_time=start_time,
            end_time=end_time,
            page_size=100000
        )

        records = result.records
        if not include_content:
            # Remove content for summary export
            for record in records:
                record["input_prompt"] = f"[{record['input_tokens']} tokens]"
                record["output_response"] = f"[{record['output_tokens']} tokens]"

        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "date_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "total_records": result.total_count,
            "content_included": include_content,
            "masking_level": self.masking_level.value,
            "records": records
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        with open(output_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        return {
            "export_path": str(output_path),
            "record_count": result.total_count,
            "file_hash": file_hash,
            "exported_at": datetime.utcnow().isoformat()
        }

    def clear(self) -> None:
        """Clear all in-memory records."""
        self._records = []
        self._records_by_context = {}
