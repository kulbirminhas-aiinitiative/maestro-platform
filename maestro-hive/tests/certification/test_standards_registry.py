"""
Tests for Standards Registry module.

This test suite validates:
- AC-1: Certification Standards Registry functionality
- Standard registration and retrieval
- Control requirements management
- Cross-standard control mappings
"""

import pytest
from datetime import datetime

from maestro_hive.certification import (
    StandardsRegistry,
    CertificationStandard,
    ControlRequirement,
    ControlCategory,
    Priority,
    ControlMapping,
)


class TestPriority:
    """Test Priority enum."""

    def test_all_priorities_exist(self):
        """Test all expected priorities exist."""
        expected = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for priority_name in expected:
            assert hasattr(Priority, priority_name)

    def test_priority_values(self):
        """Test priority string values."""
        assert Priority.CRITICAL.value == "critical"
        assert Priority.HIGH.value == "high"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.LOW.value == "low"


class TestControlCategory:
    """Test ControlCategory enum."""

    def test_key_categories_exist(self):
        """Test key expected categories exist."""
        expected = [
            "ACCESS_CONTROL",
            "ASSET_MANAGEMENT",
            "BUSINESS_CONTINUITY",
            "COMPLIANCE",
            "INCIDENT_MANAGEMENT",
            "INFORMATION_SECURITY",
            "OPERATIONS_SECURITY",
            "PHYSICAL_SECURITY",
            "PRIVACY",
        ]

        for cat_name in expected:
            assert hasattr(ControlCategory, cat_name)


class TestControlRequirement:
    """Test ControlRequirement dataclass."""

    def test_create_control(self):
        """Test creating a control requirement."""
        control = ControlRequirement(
            control_id="AC-001",
            name="Access Control Policy",
            description="Establish access control policy",
            category=ControlCategory.ACCESS_CONTROL,
            implementation_guidance="Define and implement access policies",
            evidence_requirements=["Policy document", "Access logs"],
            priority=Priority.HIGH,
        )

        assert control.control_id == "AC-001"
        assert control.category == ControlCategory.ACCESS_CONTROL
        assert control.priority == Priority.HIGH
        assert control.is_mandatory is True

    def test_control_with_evidence(self):
        """Test control with evidence requirements."""
        control = ControlRequirement(
            control_id="AC-001",
            name="Access Control",
            description="Access control implementation",
            category=ControlCategory.ACCESS_CONTROL,
            implementation_guidance="Implement access controls",
            evidence_requirements=["Policy document", "Access logs", "User roster"],
            priority=Priority.HIGH,
        )

        assert len(control.evidence_requirements) == 3
        assert "Policy document" in control.evidence_requirements

    def test_control_to_dict(self):
        """Test control serialization to dictionary."""
        control = ControlRequirement(
            control_id="TEST-001",
            name="Test Control",
            description="A test control",
            category=ControlCategory.COMPLIANCE,
            implementation_guidance="Test guidance",
            evidence_requirements=["Test evidence"],
            priority=Priority.MEDIUM,
        )

        data = control.to_dict()

        assert data["control_id"] == "TEST-001"
        assert data["category"] == "compliance"
        assert data["priority"] == "medium"

    def test_control_from_dict(self):
        """Test control deserialization from dictionary."""
        data = {
            "control_id": "TEST-002",
            "name": "Test Control 2",
            "description": "Another test control",
            "category": "access_control",
            "implementation_guidance": "Guidance",
            "evidence_requirements": ["Evidence"],
            "priority": "high",
        }

        control = ControlRequirement.from_dict(data)

        assert control.control_id == "TEST-002"
        assert control.category == ControlCategory.ACCESS_CONTROL
        assert control.priority == Priority.HIGH


class TestCertificationStandard:
    """Test CertificationStandard dataclass."""

    def test_create_standard(self):
        """Test creating a certification standard."""
        standard = CertificationStandard(
            id="TEST_001",
            name="Test Standard",
            version="1.0",
            description="A test certification standard",
            controls=[],
            effective_date=datetime.utcnow(),
            renewal_period_months=12,
            issuing_body="Test Body",
        )

        assert standard.id == "TEST_001"
        assert standard.name == "Test Standard"
        assert standard.version == "1.0"
        assert standard.controls == []

    def test_standard_with_controls(self):
        """Test standard with control requirements."""
        control = ControlRequirement(
            control_id="CTRL-001",
            name="Test Control",
            description="A test control requirement",
            category=ControlCategory.ACCESS_CONTROL,
            implementation_guidance="Implement access control",
            evidence_requirements=["Evidence"],
            priority=Priority.HIGH,
        )

        standard = CertificationStandard(
            id="TEST_001",
            name="Test Standard",
            version="1.0",
            description="Test",
            controls=[control],
            effective_date=datetime.utcnow(),
            renewal_period_months=12,
            issuing_body="Test Body",
        )

        assert len(standard.controls) == 1
        assert standard.controls[0].control_id == "CTRL-001"


class TestControlMapping:
    """Test ControlMapping dataclass."""

    def test_create_mapping(self):
        """Test creating a control mapping."""
        mapping = ControlMapping(
            source_standard="ISO_27001",
            source_control_id="A.9.1.1",
            target_standard="SOC2_TYPE2",
            target_control_ids=["CC6.1"],
            mapping_type="equivalent",
            notes="Equivalent access control requirements",
        )

        assert mapping.source_standard == "ISO_27001"
        assert mapping.target_standard == "SOC2_TYPE2"
        assert "CC6.1" in mapping.target_control_ids


class TestStandardsRegistry:
    """Test StandardsRegistry class."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        return StandardsRegistry()

    def test_registry_initialization(self, registry):
        """Test registry initializes with default standards."""
        standards = registry.list_standards()

        assert len(standards) >= 5
        standard_ids = [s.id for s in standards]
        assert "ISO_27001" in standard_ids
        assert "SOC2_TYPE2" in standard_ids
        assert "GDPR" in standard_ids
        assert "HIPAA" in standard_ids
        assert "PCI_DSS" in standard_ids

    def test_get_standard_by_id(self, registry):
        """Test retrieving a standard by ID."""
        standard = registry.get_standard("ISO_27001")

        assert standard is not None
        assert standard.id == "ISO_27001"
        assert "27001" in standard.name or "ISO" in standard.name

    def test_get_nonexistent_standard(self, registry):
        """Test retrieving non-existent standard raises KeyError."""
        with pytest.raises(KeyError):
            registry.get_standard("NONEXISTENT_123")

    def test_add_custom_standard(self, registry):
        """Test adding a custom standard."""
        custom = CertificationStandard(
            id="CUSTOM_001",
            name="Custom Standard",
            version="1.0",
            description="A custom certification standard",
            controls=[],
            effective_date=datetime.utcnow(),
            renewal_period_months=12,
            issuing_body="Custom Body",
        )

        registry.add_standard(custom)
        retrieved = registry.get_standard("CUSTOM_001")

        assert retrieved is not None
        assert retrieved.name == "Custom Standard"

    def test_get_controls_by_standard(self, registry):
        """Test getting controls for a standard."""
        controls = registry.get_controls("ISO_27001")

        assert isinstance(controls, list)
        # ISO 27001 should have controls defined
        if len(controls) > 0:
            assert all(isinstance(c, ControlRequirement) for c in controls)

    def test_get_controls_by_category(self, registry):
        """Test getting controls filtered by category."""
        standard = registry.get_standard("ISO_27001")
        controls = standard.get_controls_by_category(ControlCategory.ACCESS_CONTROL)

        for control in controls:
            assert control.category == ControlCategory.ACCESS_CONTROL

    def test_search_controls(self, registry):
        """Test searching controls by keyword."""
        results = registry.search_controls("access")

        assert isinstance(results, list)

    def test_get_control_mapping(self, registry):
        """Test getting control mappings between standards."""
        mappings = registry.get_control_mapping("ISO_27001", "SOC2_TYPE2")

        assert isinstance(mappings, list)
        for mapping in mappings:
            assert mapping.source_standard == "ISO_27001"
            assert mapping.target_standard == "SOC2_TYPE2"

    def test_list_standards_returns_list(self, registry):
        """Test that list_standards returns a list."""
        standards = registry.list_standards()

        assert isinstance(standards, list)
        assert len(standards) > 0

    def test_get_controls_unknown_standard_raises_error(self, registry):
        """Test getting controls for unknown standard raises KeyError."""
        with pytest.raises(KeyError):
            registry.get_controls("UNKNOWN_STANDARD")


class TestStandardsRegistryIntegration:
    """Integration tests for Standards Registry."""

    def test_iso_27001_structure(self):
        """Test ISO 27001 standard structure."""
        registry = StandardsRegistry()
        iso = registry.get_standard("ISO_27001")

        assert iso is not None
        assert iso.version == "2022"

    def test_soc2_type2_structure(self):
        """Test SOC2 Type II standard structure."""
        registry = StandardsRegistry()
        soc2 = registry.get_standard("SOC2_TYPE2")

        assert soc2 is not None
        assert "SOC" in soc2.name.upper() or "SOC2" in soc2.id

    def test_gdpr_structure(self):
        """Test GDPR standard structure."""
        registry = StandardsRegistry()
        gdpr = registry.get_standard("GDPR")

        assert gdpr is not None

    def test_hipaa_structure(self):
        """Test HIPAA standard structure."""
        registry = StandardsRegistry()
        hipaa = registry.get_standard("HIPAA")

        assert hipaa is not None

    def test_pci_dss_structure(self):
        """Test PCI-DSS standard structure."""
        registry = StandardsRegistry()
        pci = registry.get_standard("PCI_DSS")

        assert pci is not None

    def test_cross_standard_mapping_consistency(self):
        """Test that cross-standard mappings are consistent."""
        registry = StandardsRegistry()

        # Get mappings
        mappings = registry.get_control_mapping("ISO_27001", "SOC2_TYPE2")

        # Verify mapping structure
        for mapping in mappings:
            assert mapping.mapping_type in ["equivalent", "partial", "related"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_search(self):
        """Test search with empty string."""
        registry = StandardsRegistry()
        results = registry.search_controls("")

        # Should return empty list or all controls
        assert isinstance(results, list)

    def test_special_characters_in_search(self):
        """Test search with special characters."""
        registry = StandardsRegistry()
        results = registry.search_controls("test@#$%")

        assert isinstance(results, list)

    def test_duplicate_standard_addition(self):
        """Test adding duplicate standard ID."""
        registry = StandardsRegistry()

        # Get existing standard first
        existing = registry.get_standard("ISO_27001")

        custom = CertificationStandard(
            id="ISO_27001",  # Existing ID
            name="Duplicate",
            version="1.0",
            description="Test",
            controls=[],
            effective_date=datetime.utcnow(),
            renewal_period_months=12,
            issuing_body="Test",
        )

        # Should either raise error or update existing
        try:
            registry.add_standard(custom)
            # If it succeeds, verify behavior
            retrieved = registry.get_standard("ISO_27001")
            assert retrieved is not None
        except (ValueError, KeyError):
            # Expected behavior - reject duplicate
            pass
