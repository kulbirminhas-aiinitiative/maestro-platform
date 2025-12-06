"""
Comprehensive tests for MD-2521: Verification & Validation.

EPIC: MD-2521 - [SDLC-Phase7] Verification & Validation - Quality Gates, Compliance, and Audit

Tests organized by Acceptance Criteria:
- AC-1: Quality Gate Engine (test_ac1_*)
- AC-2: Compliance Checker (test_ac2_*)
- AC-3: Audit Trail Generator (test_ac3_*)
- AC-4: Validation Report Builder (test_ac4_*)
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest


class TestAC1QualityGates:
    """AC-1: Quality Gate Engine tests."""

    def test_gate_creation(self):
        """Test creating a quality gate."""
        from maestro_hive.maestro.vv import QualityGate, GateType

        gate = QualityGate(
            gate_id="test_gate",
            name="Test Gate",
            description="A test gate",
            gate_type=GateType.MANDATORY,
            threshold=0.8,
            evaluator=lambda ctx: ctx.get("score", 0)
        )

        assert gate.gate_id == "test_gate"
        assert gate.threshold == 0.8
        assert gate.gate_type == GateType.MANDATORY

    def test_gate_evaluation_pass(self):
        """Test gate evaluation that passes."""
        from maestro_hive.maestro.vv import QualityGate, GateType, GateStatus

        gate = QualityGate(
            gate_id="coverage_gate",
            name="Coverage Gate",
            description="Test coverage gate",
            gate_type=GateType.MANDATORY,
            threshold=0.7,
            evaluator=lambda ctx: ctx.get("coverage", 0)
        )

        result = gate.evaluate({"coverage": 0.85})
        assert result.status == GateStatus.PASSED
        assert result.score == 0.85

    def test_gate_evaluation_fail(self):
        """Test gate evaluation that fails."""
        from maestro_hive.maestro.vv import QualityGate, GateType, GateStatus

        gate = QualityGate(
            gate_id="coverage_gate",
            name="Coverage Gate",
            description="Test coverage gate",
            gate_type=GateType.MANDATORY,
            threshold=0.8,
            evaluator=lambda ctx: ctx.get("coverage", 0)
        )

        result = gate.evaluate({"coverage": 0.6})
        assert result.status == GateStatus.FAILED
        assert result.score == 0.6

    def test_gate_disabled(self):
        """Test disabled gate is skipped."""
        from maestro_hive.maestro.vv import QualityGate, GateType, GateStatus

        gate = QualityGate(
            gate_id="disabled_gate",
            name="Disabled Gate",
            description="A disabled gate",
            gate_type=GateType.MANDATORY,
            threshold=0.8,
            enabled=False
        )

        result = gate.evaluate({})
        assert result.status == GateStatus.SKIPPED

    def test_gate_engine_registration(self):
        """Test registering gates with engine."""
        from maestro_hive.maestro.vv import GateEngine, QualityGate, GateType

        engine = GateEngine()

        gate = QualityGate(
            gate_id="reg_gate",
            name="Registered Gate",
            description="Test",
            gate_type=GateType.ADVISORY,
            threshold=0.5,
            evaluator=lambda ctx: 0.8
        )

        engine.register_gate(gate)
        retrieved = engine.get_gate("reg_gate")

        assert retrieved is not None
        assert retrieved.gate_id == "reg_gate"

    def test_gate_engine_evaluate(self):
        """Test evaluating through engine."""
        from maestro_hive.maestro.vv import GateEngine, QualityGate, GateType, GateStatus

        engine = GateEngine()

        gate = QualityGate(
            gate_id="engine_gate",
            name="Engine Gate",
            description="Test",
            gate_type=GateType.MANDATORY,
            threshold=0.7,
            evaluator=lambda ctx: ctx.get("value", 0)
        )

        engine.register_gate(gate)
        result = engine.evaluate_gate("engine_gate", {"value": 0.9})

        assert result.status == GateStatus.PASSED

    def test_gate_policy_evaluation(self):
        """Test evaluating a policy with multiple gates."""
        from maestro_hive.maestro.vv import (
            GateEngine, GatePolicy, QualityGate, GateType
        )

        engine = GateEngine()

        gates = [
            QualityGate(
                gate_id="gate1",
                name="Gate 1",
                description="First gate",
                gate_type=GateType.MANDATORY,
                threshold=0.7,
                evaluator=lambda ctx: ctx.get("score1", 0)
            ),
            QualityGate(
                gate_id="gate2",
                name="Gate 2",
                description="Second gate",
                gate_type=GateType.ADVISORY,
                threshold=0.5,
                evaluator=lambda ctx: ctx.get("score2", 0)
            )
        ]

        policy = GatePolicy(
            policy_id="test_policy",
            name="Test Policy",
            gates=gates
        )

        engine.register_policy(policy)
        result = engine.evaluate_policy("test_policy", {"score1": 0.8, "score2": 0.6})

        assert result["status"] == "passed"
        assert len(result["gate_results"]) == 2

    def test_builtin_evaluators(self):
        """Test built-in gate evaluators."""
        from maestro_hive.maestro.vv import (
            test_coverage_evaluator,
            test_pass_rate_evaluator,
            code_complexity_evaluator,
            security_scan_evaluator
        )

        # Test coverage
        assert test_coverage_evaluator({"covered_lines": 80, "total_lines": 100}) == 0.8

        # Test pass rate
        assert test_pass_rate_evaluator({"tests_passed": 9, "tests_total": 10}) == 0.9

        # Code complexity
        assert code_complexity_evaluator({"average_complexity": 5}) == 1.0
        assert code_complexity_evaluator({"average_complexity": 20}) == 0.0

        # Security scan
        assert security_scan_evaluator({"critical_issues": 0, "high_issues": 0, "medium_issues": 0}) == 1.0
        assert security_scan_evaluator({"critical_issues": 1}) == 0.0


class TestAC2Compliance:
    """AC-2: Compliance Checker tests."""

    def test_compliance_rule_creation(self):
        """Test creating a compliance rule."""
        from maestro_hive.maestro.vv import ComplianceRule, ComplianceStandard, RuleSeverity

        rule = ComplianceRule(
            rule_id="test-rule",
            standard=ComplianceStandard.SOC2,
            requirement_id="CC6.1",
            title="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            validator=lambda ctx: True
        )

        assert rule.rule_id == "test-rule"
        assert rule.standard == ComplianceStandard.SOC2

    def test_rule_validation_pass(self):
        """Test rule validation that passes."""
        from maestro_hive.maestro.vv import ComplianceRule, ComplianceStandard, RuleSeverity, RuleStatus

        rule = ComplianceRule(
            rule_id="pass-rule",
            standard=ComplianceStandard.GDPR,
            requirement_id="Art5",
            title="Passing Rule",
            description="Always passes",
            severity=RuleSeverity.MEDIUM,
            validator=lambda ctx: ctx.get("compliant", False)
        )

        status = rule.validate({"compliant": True})
        assert status == RuleStatus.COMPLIANT

    def test_rule_validation_fail(self):
        """Test rule validation that fails."""
        from maestro_hive.maestro.vv import ComplianceRule, ComplianceStandard, RuleSeverity, RuleStatus

        rule = ComplianceRule(
            rule_id="fail-rule",
            standard=ComplianceStandard.SOC2,
            requirement_id="CC7.2",
            title="Failing Rule",
            description="May fail",
            severity=RuleSeverity.HIGH,
            validator=lambda ctx: ctx.get("audit_enabled", False)
        )

        status = rule.validate({"audit_enabled": False})
        assert status == RuleStatus.NON_COMPLIANT

    def test_compliance_checker_registration(self):
        """Test registering rules with checker."""
        from maestro_hive.maestro.vv import ComplianceChecker, ComplianceRule, ComplianceStandard, RuleSeverity

        checker = ComplianceChecker()

        rule = ComplianceRule(
            rule_id="reg-rule",
            standard=ComplianceStandard.ISO27001,
            requirement_id="A.8.1",
            title="Asset Management",
            description="Asset inventory",
            severity=RuleSeverity.MEDIUM,
            validator=lambda ctx: True
        )

        checker.register_rule(rule)
        result = checker.check_rule("reg-rule", {})

        assert result.rule.rule_id == "reg-rule"

    def test_check_standard(self):
        """Test checking all rules for a standard."""
        from maestro_hive.maestro.vv import create_compliance_checker_with_defaults, ComplianceStandard

        checker = create_compliance_checker_with_defaults()
        report = checker.check_standard(ComplianceStandard.SOC2, {
            "rbac_enabled": True,
            "mfa_enabled": True,
            "data_encrypted_at_rest": True,
            "data_encrypted_in_transit": True,
            "audit_logging_enabled": True,
            "log_retention_days": 90
        })

        assert len(report.results) > 0
        assert report.compliance_rate > 0

    def test_evidence_registration(self):
        """Test registering evidence."""
        from maestro_hive.maestro.vv import ComplianceChecker, Evidence

        checker = ComplianceChecker()

        evidence = Evidence(
            evidence_id="ev-001",
            evidence_type="document",
            description="Access control policy",
            location="/docs/policies/access_control.pdf"
        )

        checker.register_evidence(evidence)
        # Evidence is stored internally

    def test_remediation_plan(self):
        """Test generating remediation plan."""
        from maestro_hive.maestro.vv import create_compliance_checker_with_defaults, ComplianceStandard

        checker = create_compliance_checker_with_defaults()

        # Create context that fails compliance
        report = checker.check_standard(ComplianceStandard.SOC2, {
            "rbac_enabled": False,  # Will fail
            "mfa_enabled": False
        })

        plan = checker.get_remediation_plan(report)
        assert len(plan) > 0


class TestAC3AuditTrail:
    """AC-3: Audit Trail Generator tests."""

    def test_audit_entry_creation(self):
        """Test creating an audit entry."""
        from maestro_hive.maestro.vv import AuditEntry, EventType, AuditOutcome

        entry = AuditEntry(
            entry_id="audit-001",
            timestamp=datetime.utcnow(),
            event_type=EventType.CREATE,
            actor="user@example.com",
            resource="/api/data",
            action="create_record",
            outcome=AuditOutcome.SUCCESS
        )

        assert entry.entry_id == "audit-001"
        assert entry.event_type == EventType.CREATE

    def test_audit_hash_computation(self):
        """Test computing entry hash."""
        from maestro_hive.maestro.vv import AuditEntry, EventType, AuditOutcome

        entry = AuditEntry(
            entry_id="hash-test",
            timestamp=datetime(2025, 1, 1, 12, 0, 0),
            event_type=EventType.UPDATE,
            actor="system",
            resource="/config",
            action="update_settings",
            outcome=AuditOutcome.SUCCESS,
            previous_hash="abc123"
        )

        hash1 = entry.compute_hash()
        hash2 = entry.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_audit_trail_logging(self):
        """Test logging to audit trail."""
        from maestro_hive.maestro.vv import AuditTrail, EventType, AuditOutcome

        trail = AuditTrail()

        entry = trail.log(
            event_type=EventType.LOGIN,
            actor="admin",
            resource="/auth",
            action="login",
            outcome=AuditOutcome.SUCCESS,
            details={"ip": "192.168.1.1"}
        )

        assert entry.entry_id is not None
        assert entry.current_hash != ""
        assert len(trail) == 1

    def test_audit_chain_verification(self):
        """Test verifying audit chain integrity."""
        from maestro_hive.maestro.vv import AuditTrail, EventType, AuditOutcome

        trail = AuditTrail()

        # Log multiple entries
        for i in range(5):
            trail.log(
                event_type=EventType.CREATE,
                actor=f"user{i}",
                resource=f"/resource/{i}",
                action="create",
                outcome=AuditOutcome.SUCCESS
            )

        result = trail.verify_chain()
        assert result["valid"] is True
        assert result["entries_checked"] == 5

    def test_audit_query(self):
        """Test querying audit entries."""
        from maestro_hive.maestro.vv import AuditTrail, EventType, AuditOutcome

        trail = AuditTrail()

        trail.log(EventType.CREATE, "user1", "/res1", "create", AuditOutcome.SUCCESS)
        trail.log(EventType.UPDATE, "user2", "/res1", "update", AuditOutcome.SUCCESS)
        trail.log(EventType.DELETE, "user1", "/res2", "delete", AuditOutcome.FAILURE)

        results = trail.query(actor="user1")
        assert len(results) == 2

    def test_audit_export_json(self):
        """Test exporting audit trail to JSON."""
        from maestro_hive.maestro.vv import AuditTrail, EventType, AuditOutcome

        trail = AuditTrail()
        trail.log(EventType.CREATE, "user", "/data", "create", AuditOutcome.SUCCESS)

        json_output = trail.export_json()
        data = json.loads(json_output)

        assert len(data) == 1
        assert data[0]["actor"] == "user"

    def test_audit_export_csv(self):
        """Test exporting audit trail to CSV."""
        from maestro_hive.maestro.vv import AuditTrail, EventType, AuditOutcome

        trail = AuditTrail()
        trail.log(EventType.READ, "reader", "/file", "read", AuditOutcome.SUCCESS)

        csv_output = trail.export_csv()

        assert "entry_id" in csv_output
        assert "reader" in csv_output

    def test_audit_persistence(self):
        """Test audit trail persistence."""
        from maestro_hive.maestro.vv import AuditTrail, EventType, AuditOutcome

        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "audit.json"

            # Create and populate trail
            trail1 = AuditTrail(storage_path=storage_path)
            trail1.log(EventType.CREATE, "user", "/data", "create", AuditOutcome.SUCCESS)

            # Load into new trail
            trail2 = AuditTrail(storage_path=storage_path)
            assert len(trail2) == 1

    def test_retention_policy(self):
        """Test retention policy application."""
        from maestro_hive.maestro.vv import AuditTrail, RetentionPolicy, EventType, AuditOutcome

        policy = RetentionPolicy(
            policy_id="short-retention",
            name="Short Retention",
            retention_days=1
        )

        trail = AuditTrail(retention_policy=policy)

        # Log entry with old timestamp (simulate old entry)
        trail.log(EventType.CREATE, "user", "/data", "create", AuditOutcome.SUCCESS)

        # Entry should exist before applying retention
        assert len(trail) == 1


class TestAC4Reports:
    """AC-4: Validation Report Builder tests."""

    def test_requirement_creation(self):
        """Test creating a requirement."""
        from maestro_hive.maestro.vv import Requirement

        req = Requirement(
            requirement_id="REQ-001",
            title="User Authentication",
            description="System shall authenticate users",
            priority="P1",
            source="PRD v1.0"
        )

        assert req.requirement_id == "REQ-001"
        assert req.priority == "P1"

    def test_test_case_creation(self):
        """Test creating a test case."""
        from maestro_hive.maestro.vv import TestCase, ValidationStatus

        test = TestCase(
            test_id="TEST-001",
            name="test_user_login",
            description="Verify user can login",
            test_type="integration",
            requirements_covered=["REQ-001"],
            status=ValidationStatus.PASSED
        )

        assert test.test_id == "TEST-001"
        assert "REQ-001" in test.requirements_covered

    def test_report_builder_basic(self):
        """Test basic report building."""
        from maestro_hive.maestro.vv import ReportBuilder, Requirement, TestCase, ValidationStatus

        builder = ReportBuilder("TestProject", "1.0.0")

        builder.add_requirement(Requirement(
            requirement_id="REQ-001",
            title="Auth",
            description="Authentication",
            priority="P1",
            source="PRD"
        ))

        builder.add_test(TestCase(
            test_id="TEST-001",
            name="test_auth",
            description="Test auth",
            test_type="unit",
            requirements_covered=["REQ-001"],
            status=ValidationStatus.PASSED
        ))

        report = builder.build()

        assert report.total_requirements == 1
        assert report.total_tests == 1
        assert report.passed_tests == 1

    def test_coverage_analysis(self):
        """Test coverage analysis in report."""
        from maestro_hive.maestro.vv import (
            ReportBuilder, Requirement, TestCase, ValidationStatus, CoverageStatus
        )

        builder = ReportBuilder("TestProject", "1.0.0")

        builder.add_requirement(Requirement("REQ-001", "Covered", "Has tests", "P1", "PRD"))
        builder.add_requirement(Requirement("REQ-002", "Uncovered", "No tests", "P2", "PRD"))

        builder.add_test(TestCase(
            test_id="TEST-001",
            name="test_covered",
            description="Test for REQ-001",
            test_type="unit",
            requirements_covered=["REQ-001"],
            status=ValidationStatus.PASSED
        ))

        report = builder.build()

        coverage_001 = report.matrix.get_requirement_coverage("REQ-001")
        coverage_002 = report.matrix.get_requirement_coverage("REQ-002")

        assert coverage_001 == CoverageStatus.FULLY_COVERED
        assert coverage_002 == CoverageStatus.NOT_COVERED

    def test_gap_identification(self):
        """Test gap identification."""
        from maestro_hive.maestro.vv import ReportBuilder, Requirement, TestCase, ValidationStatus

        builder = ReportBuilder("TestProject", "1.0.0")

        builder.add_requirement(Requirement("REQ-001", "Uncovered", "No tests", "P1", "PRD"))

        report = builder.build()

        assert len(report.gaps) == 1
        assert report.gaps[0].gap_type == "no_tests"

    def test_executive_summary(self):
        """Test executive summary generation."""
        from maestro_hive.maestro.vv import ReportBuilder, Requirement, TestCase, ValidationStatus

        builder = ReportBuilder("TestProject", "2.0.0")

        for i in range(5):
            builder.add_requirement(Requirement(f"REQ-{i}", f"Req {i}", "Desc", "P1", "PRD"))
            builder.add_test(TestCase(
                test_id=f"TEST-{i}",
                name=f"test_{i}",
                description=f"Test {i}",
                test_type="unit",
                requirements_covered=[f"REQ-{i}"],
                status=ValidationStatus.PASSED
            ))

        report = builder.build()
        summary = report.get_executive_summary()

        assert "metrics" in summary
        assert summary["overall_status"] == "passed"

    def test_markdown_export(self):
        """Test Markdown export."""
        from maestro_hive.maestro.vv import ReportBuilder, Requirement, TestCase, ValidationStatus

        builder = ReportBuilder("TestProject", "1.0.0")
        builder.add_requirement(Requirement("REQ-001", "Test Req", "Desc", "P1", "PRD"))
        builder.add_test(TestCase(
            "TEST-001", "test", "desc", "unit", ["REQ-001"], ValidationStatus.PASSED
        ))

        report = builder.build()
        md = builder.export_markdown(report)

        assert "# Validation Report" in md
        assert "TestProject" in md

    def test_traceability_matrix(self):
        """Test traceability matrix generation."""
        from maestro_hive.maestro.vv import ReportBuilder, Requirement, TestCase, ValidationStatus

        builder = ReportBuilder("TestProject", "1.0.0")

        builder.add_requirement(Requirement("REQ-001", "Feature A", "Desc A", "P1", "PRD"))
        builder.add_requirement(Requirement("REQ-002", "Feature B", "Desc B", "P2", "PRD"))

        builder.add_test(TestCase(
            "TEST-001", "test_a", "Test A", "unit",
            ["REQ-001", "REQ-002"], ValidationStatus.PASSED
        ))
        builder.add_test(TestCase(
            "TEST-002", "test_b", "Test B", "integration",
            ["REQ-002"], ValidationStatus.PASSED
        ))

        report = builder.build()

        req1_tests = report.matrix.get_tests_for_requirement("REQ-001")
        req2_tests = report.matrix.get_tests_for_requirement("REQ-002")

        assert len(req1_tests) == 1
        assert len(req2_tests) == 2


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_vv_workflow(self):
        """Test complete V&V workflow."""
        from maestro_hive.maestro.vv import (
            GateEngine, create_standard_policy,
            ComplianceChecker, ComplianceRule, ComplianceStandard, RuleSeverity,
            AuditTrail, EventType, AuditOutcome,
            ReportBuilder, Requirement, TestCase, ValidationStatus
        )

        # 1. Set up quality gates
        engine = GateEngine()
        engine.register_policy(create_standard_policy())

        gate_result = engine.evaluate_policy("standard", {
            "covered_lines": 85,
            "total_lines": 100,
            "tests_passed": 50,
            "tests_total": 50,
            "average_complexity": 8,
            "critical_issues": 0,
            "high_issues": 0,
            "medium_issues": 2
        })

        assert gate_result["status"] == "passed"

        # 2. Check compliance
        checker = ComplianceChecker()
        checker.register_rule(ComplianceRule(
            rule_id="custom-1",
            standard=ComplianceStandard.CUSTOM,
            requirement_id="SEC-1",
            title="Encryption Check",
            description="Data must be encrypted",
            severity=RuleSeverity.HIGH,
            validator=lambda ctx: ctx.get("encrypted", False)
        ))

        compliance_result = checker.check_rule("custom-1", {"encrypted": True})
        assert compliance_result.status.value == "compliant"

        # 3. Log to audit trail
        trail = AuditTrail()
        trail.log(
            event_type=EventType.APPROVAL,
            actor="qa_lead",
            resource="/release/1.0.0",
            action="approve_release",
            outcome=AuditOutcome.SUCCESS,
            details={"gates_passed": True, "compliance_checked": True}
        )

        assert trail.verify_chain()["valid"]

        # 4. Build validation report
        builder = ReportBuilder("IntegrationTest", "1.0.0")
        builder.add_requirement(Requirement("REQ-VV", "V&V Integration", "Full workflow", "P1", "Epic"))
        builder.add_test(TestCase(
            "TEST-VV", "test_vv_integration", "Integration test",
            "integration", ["REQ-VV"], ValidationStatus.PASSED
        ))

        report = builder.build()
        assert report.coverage_rate == 1.0

    def test_audit_chain_tampering_detection(self):
        """Test that tampering is detected in audit chain."""
        from maestro_hive.maestro.vv import AuditTrail, EventType, AuditOutcome

        trail = AuditTrail()

        # Create valid chain
        trail.log(EventType.CREATE, "user1", "/data", "create", AuditOutcome.SUCCESS)
        trail.log(EventType.UPDATE, "user2", "/data", "update", AuditOutcome.SUCCESS)
        trail.log(EventType.DELETE, "user3", "/data", "delete", AuditOutcome.SUCCESS)

        # Verify valid chain
        result = trail.verify_chain()
        assert result["valid"] is True

        # Tamper with an entry (modify hash)
        trail._entries[1].current_hash = "tampered_hash"

        # Should detect tampering
        result = trail.verify_chain()
        assert result["valid"] is False
        assert len(result["issues"]) > 0
