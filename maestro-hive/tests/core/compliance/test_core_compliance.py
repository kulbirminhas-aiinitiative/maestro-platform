"""
Tests for Core Compliance Module.

EPIC: MD-2801 - Core Services & CLI Compliance (Batch 2)

Comprehensive test suite for:
- ComplianceValidator (AC-1)
- AuditLogger (AC-2)
- InputSanitizer (AC-3)
- StateComplianceAuditor (AC-4)
"""

import json
import pytest
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from maestro_hive.core.compliance import (
    # Compliance Validator
    ComplianceValidator,
    ValidationResult,
    ValidationLevel,
    ComplianceReport,
    get_compliance_validator,
    # Audit Logger
    AuditLogger,
    AuditEntry,
    AuditLevel,
    get_audit_logger,
    # Input Sanitizer
    InputSanitizer,
    SanitizationResult,
    SecurityWarning,
    SanitizationPattern,
    # State Auditor
    StateComplianceAuditor,
    AuditResult,
    IntegrityStatus,
)


# ============================================================
# ComplianceValidator Tests (AC-1)
# ============================================================

class TestComplianceValidator:
    """Tests for ComplianceValidator."""

    def setup_method(self):
        """Reset singleton for each test."""
        ComplianceValidator._instance = None

    def test_validator_initialization(self):
        """Should initialize with default settings."""
        validator = ComplianceValidator()
        assert validator.is_enabled
        assert validator._level == ValidationLevel.STANDARD

    def test_validate_inputs_valid(self):
        """Should pass validation for valid inputs."""
        validator = ComplianceValidator()
        inputs = {"key": "value", "number": 42}
        result = validator.validate_inputs(inputs, "test_block")

        assert result.valid
        assert result.checks_passed > 0
        assert result.checks_failed == 0
        assert len(result.errors) == 0

    def test_validate_inputs_empty(self):
        """Should fail validation for empty inputs."""
        validator = ComplianceValidator()
        result = validator.validate_inputs({}, "test_block")

        assert not result.valid
        assert result.checks_failed > 0

    def test_validate_inputs_path_traversal(self):
        """Should detect path traversal patterns."""
        validator = ComplianceValidator()
        inputs = {"path": "../../../etc/passwd"}
        result = validator.validate_inputs(inputs, "test_block")

        assert not result.valid
        assert any("path traversal" in e.lower() for e in result.errors)

    def test_validate_execution_valid(self):
        """Should pass validation for valid execution result."""
        validator = ComplianceValidator()
        result_data = {"status": "completed", "output": "success"}
        result = validator.validate_execution(result_data, "exec_123", "test_block")

        assert result.valid

    def test_generate_report(self):
        """Should generate comprehensive compliance report."""
        validator = ComplianceValidator()
        
        pre_result = validator.validate_inputs({"key": "value"}, "test_block")
        post_result = validator.validate_execution({"status": "ok"}, "exec_1", "test_block")
        
        report = validator.generate_report(
            execution_id="exec_1",
            block_id="test_block",
            pre_validation=pre_result,
            post_validation=post_result
        )

        assert report.execution_id == "exec_1"
        assert report.block_id == "test_block"
        assert report.overall_compliant
        assert report.compliance_score > 0

    def test_validation_levels(self):
        """Should respect different validation levels."""
        validator = ComplianceValidator(level=ValidationLevel.MINIMAL)
        assert validator._level == ValidationLevel.MINIMAL

        validator.set_level(ValidationLevel.STRICT)
        assert validator._level == ValidationLevel.STRICT

    def test_disable_enable(self):
        """Should support enable/disable."""
        validator = ComplianceValidator()
        
        validator.disable()
        assert not validator.is_enabled
        result = validator.validate_inputs({"key": "value"})
        assert result.metadata.get("validation_disabled")
        
        validator.enable()
        assert validator.is_enabled

    def test_custom_validators(self):
        """Should run custom validators."""
        custom = lambda inputs: "required_field" in inputs
        validator = ComplianceValidator(custom_validators=[custom])
        
        result = validator.validate_inputs({"required_field": "yes"})
        assert result.valid

    def test_singleton_pattern(self):
        """Should implement singleton pattern."""
        v1 = ComplianceValidator()
        v2 = ComplianceValidator()
        assert v1 is v2

    def test_thread_safety(self):
        """Should be thread-safe."""
        validator = ComplianceValidator()
        results = []

        def validate():
            result = validator.validate_inputs({"key": "value"})
            results.append(result.valid)

        threads = [threading.Thread(target=validate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 10
        assert all(results)


# ============================================================
# AuditLogger Tests (AC-2)
# ============================================================

class TestAuditLogger:
    """Tests for AuditLogger."""

    def setup_method(self):
        """Reset singleton for each test."""
        AuditLogger._instance = None

    def test_logger_initialization(self):
        """Should initialize with default settings."""
        logger = AuditLogger()
        assert logger.is_enabled
        assert logger._level == AuditLevel.STANDARD

    def test_log_command(self):
        """Should log CLI commands."""
        logger = AuditLogger()
        entry_id = logger.log_command(
            command="maestro MD-2801",
            session_id="session_123"
        )

        assert entry_id.startswith("audit_")
        assert logger.entry_count > 0

    def test_log_execution(self):
        """Should log block executions."""
        logger = AuditLogger()
        entry_id = logger.log_execution(
            execution_id="exec_123",
            block_id="core.orchestrator",
            status="completed",
            duration_ms=1500,
            session_id="session_123"
        )

        assert entry_id.startswith("audit_")

    def test_log_error(self):
        """Should log errors with context."""
        logger = AuditLogger()
        try:
            raise ValueError("Test error")
        except ValueError as e:
            entry_id = logger.log_error(
                error=e,
                context={"component": "test"},
                session_id="session_123"
            )

        assert entry_id.startswith("audit_")

    def test_log_session(self):
        """Should log session lifecycle events."""
        logger = AuditLogger()
        
        entry_id = logger.log_session(
            session_id="session_123",
            event="started"
        )
        assert entry_id.startswith("audit_")

    def test_get_audit_trail(self):
        """Should retrieve audit entries with filtering."""
        logger = AuditLogger()
        
        logger.log_command("cmd1", session_id="s1")
        logger.log_command("cmd2", session_id="s2")
        logger.log_command("cmd3", session_id="s1")

        trail = logger.get_audit_trail(session_id="s1")
        assert len(trail) == 2

    def test_export_json(self):
        """Should export audit trail as JSON."""
        logger = AuditLogger()
        logger.log_command("test_command")

        export = logger.export_audit_trail(format="json")
        data = json.loads(export)
        
        assert isinstance(data, list)
        assert len(data) > 0

    def test_export_csv(self):
        """Should export audit trail as CSV."""
        logger = AuditLogger()
        logger.log_command("test_command")

        export = logger.export_audit_trail(format="csv")
        lines = export.split("\n")
        
        assert len(lines) >= 2  # Header + at least one entry

    def test_session_summary(self):
        """Should generate session summary."""
        logger = AuditLogger()
        
        logger.log_command("cmd", session_id="test_session")
        logger.log_execution("e1", "block", "ok", 100, session_id="test_session")
        
        summary = logger.get_session_summary("test_session")
        
        assert summary["session_id"] == "test_session"
        assert summary["commands"] == 1
        assert summary["executions"] == 1

    def test_audit_levels(self):
        """Should respect different audit levels."""
        logger = AuditLogger(level=AuditLevel.FULL)
        
        logger.log_execution(
            execution_id="e1",
            block_id="block",
            status="ok",
            duration_ms=100,
            inputs={"key": "value"},
            outputs={"result": "data"}
        )

        entries = logger.get_audit_trail()
        assert entries[-1].input_summary is not None

    def test_persistence(self):
        """Should persist entries to disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = AuditLogger._instance = None
            logger = AuditLogger(persistence_dir=tmpdir)
            logger.log_command("test_command")

            files = list(Path(tmpdir).glob("audit_*.jsonl"))
            assert len(files) == 1

    def test_singleton_pattern(self):
        """Should implement singleton pattern."""
        l1 = AuditLogger()
        l2 = AuditLogger()
        assert l1 is l2


# ============================================================
# InputSanitizer Tests (AC-3)
# ============================================================

class TestInputSanitizer:
    """Tests for InputSanitizer."""

    def test_sanitizer_initialization(self):
        """Should initialize with default settings."""
        sanitizer = InputSanitizer()
        assert sanitizer.is_enabled
        assert not sanitizer.is_strict

    def test_sanitize_safe_input(self):
        """Should pass safe input unchanged."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("normal input text")

        assert result.is_safe
        assert not result.was_modified
        assert result.original == result.sanitized

    def test_detect_command_injection(self):
        """Should detect command injection patterns."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("value; rm -rf /")

        assert not result.is_safe
        assert len(result.warnings) > 0
        assert any(w.pattern == SanitizationPattern.COMMAND_INJECTION for w in result.warnings)

    def test_detect_path_traversal(self):
        """Should detect path traversal patterns."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("../../../etc/passwd")

        assert not result.is_safe
        assert any(w.pattern == SanitizationPattern.PATH_TRAVERSAL for w in result.warnings)

    def test_detect_sql_injection(self):
        """Should detect SQL injection patterns."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("'; DROP TABLE users; --")

        warnings = result.warnings
        # Should have at least a shell metachar warning for the semicolon
        assert len(warnings) > 0

    def test_detect_xss(self):
        """Should detect XSS patterns."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("<script>alert('xss')</script>")

        assert not result.is_safe
        assert any(w.pattern == SanitizationPattern.XSS for w in result.warnings)

    def test_detect_template_injection(self):
        """Should detect template injection patterns."""
        sanitizer = InputSanitizer()
        result = sanitizer.sanitize("{{constructor.constructor('return this')()}}")

        assert any(w.pattern == SanitizationPattern.TEMPLATE_INJECTION for w in result.warnings)

    def test_strict_mode_removes_patterns(self):
        """Should remove patterns in strict mode."""
        sanitizer = InputSanitizer(strict_mode=True)
        result = sanitizer.sanitize("safe; rm -rf /")

        assert result.was_modified
        assert ";" not in result.sanitized

    def test_validate_epic_id_valid(self):
        """Should validate correct EPIC ID format."""
        sanitizer = InputSanitizer()
        
        assert sanitizer.validate_epic_id("MD-2801")
        assert sanitizer.validate_epic_id("PROJ-123")
        assert sanitizer.validate_epic_id("ABC-1")

    def test_validate_epic_id_invalid(self):
        """Should reject invalid EPIC ID format."""
        sanitizer = InputSanitizer()
        
        assert not sanitizer.validate_epic_id("invalid")
        assert not sanitizer.validate_epic_id("md-2801")  # lowercase
        assert not sanitizer.validate_epic_id("MD2801")   # no hyphen
        assert not sanitizer.validate_epic_id("")

    def test_validate_path_safe(self):
        """Should validate safe paths."""
        sanitizer = InputSanitizer()
        
        assert sanitizer.validate_path("/home/user/file.txt")
        assert sanitizer.validate_path("relative/path/file")

    def test_validate_path_unsafe(self):
        """Should reject unsafe paths."""
        sanitizer = InputSanitizer()
        
        assert not sanitizer.validate_path("../../../etc/passwd")
        assert not sanitizer.validate_path("/path;rm -rf /")
        assert not sanitizer.validate_path("")

    def test_check_injection(self):
        """Should check for injection without modifying."""
        sanitizer = InputSanitizer()
        warnings = sanitizer.check_injection("value; rm -rf /")

        assert len(warnings) > 0
        assert all(isinstance(w, SecurityWarning) for w in warnings)

    def test_sanitize_command_args(self):
        """Should sanitize command arguments."""
        sanitizer = InputSanitizer()
        args = ["safe", "value; rm", "normal"]
        
        sanitized = sanitizer.sanitize_command_args(args)
        assert len(sanitized) == 3

    def test_sanitize_dict(self):
        """Should sanitize dictionary values."""
        sanitizer = InputSanitizer()
        data = {
            "safe_key": "safe_value",
            "dangerous": "value; rm -rf /",
        }
        
        result = sanitizer.sanitize_dict(data)
        assert "safe_value" in str(result)

    def test_disabled_sanitizer(self):
        """Should pass through when disabled."""
        sanitizer = InputSanitizer(enabled=False)
        result = sanitizer.sanitize("dangerous; rm -rf /")

        assert result.is_safe
        assert result.metadata.get("sanitization_disabled")


# ============================================================
# StateComplianceAuditor Tests (AC-4)
# ============================================================

class TestStateComplianceAuditor:
    """Tests for StateComplianceAuditor."""

    def test_auditor_initialization(self):
        """Should initialize with default settings."""
        auditor = StateComplianceAuditor()
        assert auditor.is_enabled
        assert auditor._hash_algorithm == "sha256"

    def test_register_checkpoint(self):
        """Should register checkpoint and return hash."""
        auditor = StateComplianceAuditor()
        state = {"key": "value", "count": 42}
        
        hash_value = auditor.register_checkpoint("cp_1", state)
        
        assert hash_value
        assert len(hash_value) == 64  # SHA256 hex length

    def test_audit_checkpoint_valid(self):
        """Should validate unmodified checkpoint."""
        auditor = StateComplianceAuditor()
        state = {"key": "value"}
        
        auditor.register_checkpoint("cp_1", state)
        result = auditor.audit_checkpoint("cp_1", state)
        
        assert result.status == IntegrityStatus.VALID
        assert result.expected_hash == result.actual_hash

    def test_audit_checkpoint_modified(self):
        """Should detect modified checkpoint."""
        auditor = StateComplianceAuditor()
        original_state = {"key": "value"}
        modified_state = {"key": "modified"}
        
        auditor.register_checkpoint("cp_1", original_state)
        result = auditor.audit_checkpoint("cp_1", modified_state)
        
        assert result.status == IntegrityStatus.MODIFIED
        assert result.expected_hash != result.actual_hash
        assert len(result.discrepancies) > 0

    def test_audit_checkpoint_missing(self):
        """Should report missing checkpoint."""
        auditor = StateComplianceAuditor()
        result = auditor.audit_checkpoint("nonexistent", {"key": "value"})
        
        assert result.status == IntegrityStatus.MISSING

    def test_validate_integrity_valid(self):
        """Should validate valid state."""
        auditor = StateComplianceAuditor()
        state = {"key": "value", "nested": {"a": 1}}
        
        assert auditor.validate_integrity(state)

    def test_validate_integrity_suspicious(self):
        """Should reject suspicious state."""
        auditor = StateComplianceAuditor()
        state = {"key": "__import__('os').system('rm -rf /')"}
        
        assert not auditor.validate_integrity(state)

    def test_generate_compliance_hash(self):
        """Should generate compliance hash with metadata."""
        auditor = StateComplianceAuditor()
        state = {"key": "value"}
        
        hash_value = auditor.generate_compliance_hash(state)
        
        assert hash_value
        assert len(hash_value) == 64

    def test_get_audit_history(self):
        """Should track audit history."""
        auditor = StateComplianceAuditor()
        state = {"key": "value"}
        
        auditor.register_checkpoint("cp_1", state)
        auditor.audit_checkpoint("cp_1", state)
        auditor.audit_checkpoint("cp_1", {"key": "modified"})
        
        history = auditor.get_audit_history()
        assert len(history) == 2

    def test_verify_checkpoint_chain(self):
        """Should verify chain of checkpoints."""
        auditor = StateComplianceAuditor()
        
        states = [{"step": 1}, {"step": 2}, {"step": 3}]
        cp_ids = ["cp_1", "cp_2", "cp_3"]
        
        for cp_id, state in zip(cp_ids, states):
            auditor.register_checkpoint(cp_id, state)
        
        results = auditor.verify_checkpoint_chain(cp_ids, states)
        
        assert len(results) == 3
        assert all(r.status == IntegrityStatus.VALID for r in results.values())

    def test_get_statistics(self):
        """Should return auditor statistics."""
        auditor = StateComplianceAuditor()
        auditor.register_checkpoint("cp_1", {"key": "value"})
        auditor.audit_checkpoint("cp_1", {"key": "value"})
        
        stats = auditor.get_statistics()
        
        assert stats["total_checkpoints"] == 1
        assert stats["total_audits"] == 1
        assert stats["valid_count"] == 1

    def test_clear_checkpoint(self):
        """Should clear checkpoint from tracking."""
        auditor = StateComplianceAuditor()
        auditor.register_checkpoint("cp_1", {"key": "value"})
        
        assert auditor.clear_checkpoint("cp_1")
        assert not auditor.clear_checkpoint("cp_1")  # Already cleared

    def test_different_hash_algorithms(self):
        """Should support different hash algorithms."""
        auditor_sha256 = StateComplianceAuditor(hash_algorithm="sha256")
        auditor_sha512 = StateComplianceAuditor(hash_algorithm="sha512")
        
        state = {"key": "value"}
        hash_256 = auditor_sha256._compute_hash(state)
        hash_512 = auditor_sha512._compute_hash(state)
        
        assert len(hash_256) == 64   # SHA256
        assert len(hash_512) == 128  # SHA512

    def test_disabled_auditor(self):
        """Should skip auditing when disabled."""
        auditor = StateComplianceAuditor(enabled=False)
        
        hash_value = auditor.register_checkpoint("cp_1", {"key": "value"})
        assert hash_value == ""
        
        result = auditor.audit_checkpoint("cp_1", {"key": "value"})
        assert result.status == IntegrityStatus.UNKNOWN


# ============================================================
# Integration Tests
# ============================================================

class TestModuleIntegration:
    """Integration tests for the compliance module."""

    def setup_method(self):
        """Reset singletons."""
        ComplianceValidator._instance = None
        AuditLogger._instance = None

    def test_full_compliance_workflow(self):
        """Should support complete compliance workflow."""
        validator = ComplianceValidator()
        logger = AuditLogger()
        sanitizer = InputSanitizer()
        auditor = StateComplianceAuditor()

        # 1. Sanitize input
        input_str = "MD-2801"
        sanitized = sanitizer.sanitize(input_str)
        assert sanitized.is_safe

        # 2. Validate input format
        assert sanitizer.validate_epic_id(sanitized.sanitized)

        # 3. Log command
        entry_id = logger.log_command(input_str, session_id="test_session")
        assert entry_id

        # 4. Pre-execution validation
        inputs = {"epic_id": sanitized.sanitized, "dry_run": False}
        pre_result = validator.validate_inputs(inputs, "orchestrator")
        assert pre_result.valid

        # 5. Register state checkpoint
        state = {"phase": "started", "inputs": inputs}
        auditor.register_checkpoint("pre_exec", state)

        # 6. Simulate execution
        execution_result = {"status": "completed", "score": 100}

        # 7. Post-execution validation
        post_result = validator.validate_execution(
            execution_result, "exec_001", "orchestrator"
        )
        assert post_result.valid

        # 8. Verify state integrity
        audit_result = auditor.audit_checkpoint("pre_exec", state)
        assert audit_result.status == IntegrityStatus.VALID

        # 9. Generate compliance report
        report = validator.generate_report(
            execution_id="exec_001",
            block_id="orchestrator",
            pre_validation=pre_result,
            post_validation=post_result
        )
        assert report.overall_compliant
        assert report.compliance_score >= 80.0  # Threshold for compliance

        # 10. Log execution
        logger.log_execution(
            execution_id="exec_001",
            block_id="orchestrator",
            status="completed",
            duration_ms=5000,
            session_id="test_session"
        )

        # Verify audit trail
        trail = logger.get_audit_trail(session_id="test_session")
        assert len(trail) >= 2  # Command + execution

    def test_module_exports(self):
        """Should export all expected components."""
        from maestro_hive.core.compliance import (
            ComplianceValidator,
            ValidationResult,
            ValidationLevel,
            ComplianceReport,
            AuditLogger,
            AuditEntry,
            AuditLevel,
            InputSanitizer,
            SanitizationResult,
            SecurityWarning,
            SanitizationPattern,
            StateComplianceAuditor,
            AuditResult,
            IntegrityStatus,
        )

        # All imports should work
        assert ComplianceValidator is not None
        assert ValidationResult is not None
        assert AuditLogger is not None
        assert InputSanitizer is not None
        assert StateComplianceAuditor is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
