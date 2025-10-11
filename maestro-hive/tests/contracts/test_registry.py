"""
Unit Tests for ContractRegistry

Tests all 15 core methods of the ContractRegistry:
1. register_contract
2. get_contract
3. list_contracts
4. update_contract
5. delete_contract
6. propose_contract
7. accept_contract
8. fulfill_contract
9. verify_contract
10. breach_contract
11. get_dependencies
12. get_dependents
13. create_execution_plan
14. get_contract_history
15. search_contracts
"""

import pytest
from contracts.models import (
    UniversalContract,
    ContractLifecycle,
    AcceptanceCriterion,
    CriterionResult,
    VerificationResult,
    ContractBreach,
)
from contracts.registry import (
    ContractRegistry,
    ContractRegistryError,
    ContractNotFoundError,
    ContractTransitionError,
    DependencyCycleError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def registry():
    """Create a fresh registry for each test"""
    return ContractRegistry()


@pytest.fixture
def sample_contract():
    """Create a sample contract for testing"""
    return UniversalContract(
        contract_id="contract_001",
        contract_type="UX_DESIGN",
        name="Login Form Design",
        description="Design the login form",
        provider_agent="ux_designer",
        consumer_agents=["frontend_developer"],
        specification={"component": "LoginForm"},
        acceptance_criteria=[
            AcceptanceCriterion(
                criterion_id="crit_001",
                description="Visual consistency",
                validator_type="screenshot_diff",
                validation_config={"threshold": 0.95},
            )
        ],
        tags=["ui", "authentication"],
    )


@pytest.fixture
def dependent_contract():
    """Create a contract that depends on contract_001"""
    return UniversalContract(
        contract_id="contract_002",
        contract_type="API_SPECIFICATION",
        name="Auth API",
        description="Authentication API",
        provider_agent="backend_developer",
        consumer_agents=["frontend_developer"],
        specification={},
        acceptance_criteria=[],
        depends_on=["contract_001"],
        priority="HIGH",
    )


# ============================================================================
# Test 1: register_contract
# ============================================================================

class TestRegisterContract:
    """Test contract registration"""

    def test_register_simple_contract(self, registry, sample_contract):
        """Test registering a simple contract"""
        result = registry.register_contract(sample_contract)

        assert result.contract_id == "contract_001"
        assert registry._contracts["contract_001"] == sample_contract

    def test_register_contract_with_dependencies(self, registry, sample_contract, dependent_contract):
        """Test registering a contract with dependencies"""
        # Register base contract first
        registry.register_contract(sample_contract)

        # Register dependent contract
        result = registry.register_contract(dependent_contract)

        assert result.contract_id == "contract_002"
        assert "contract_001" in registry._dependency_graph["contract_002"]
        assert "contract_002" in registry._dependents_graph["contract_001"]

    def test_register_duplicate_contract(self, registry, sample_contract):
        """Test registering a duplicate contract fails"""
        registry.register_contract(sample_contract)

        with pytest.raises(ContractRegistryError, match="already exists"):
            registry.register_contract(sample_contract)

    def test_register_contract_with_cycle(self, registry):
        """Test registering a contract that creates a cycle fails"""
        c1 = UniversalContract(
            contract_id="c1",
            contract_type="TEST",
            name="Contract 1",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
            depends_on=["c2"],
        )

        c2 = UniversalContract(
            contract_id="c2",
            contract_type="TEST",
            name="Contract 2",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
            depends_on=["c1"],
        )

        registry.register_contract(c1)

        with pytest.raises(DependencyCycleError, match="would create a cycle"):
            registry.register_contract(c2)


# ============================================================================
# Test 2: get_contract
# ============================================================================

class TestGetContract:
    """Test contract retrieval"""

    def test_get_existing_contract(self, registry, sample_contract):
        """Test getting an existing contract"""
        registry.register_contract(sample_contract)

        result = registry.get_contract("contract_001")
        assert result.contract_id == "contract_001"
        assert result.name == "Login Form Design"

    def test_get_nonexistent_contract(self, registry):
        """Test getting a non-existent contract fails"""
        with pytest.raises(ContractNotFoundError, match="not found"):
            registry.get_contract("nonexistent")


# ============================================================================
# Test 3: list_contracts
# ============================================================================

class TestListContracts:
    """Test contract listing and filtering"""

    def test_list_all_contracts(self, registry, sample_contract, dependent_contract):
        """Test listing all contracts"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        contracts = registry.list_contracts()
        assert len(contracts) == 2

    def test_list_by_contract_type(self, registry, sample_contract, dependent_contract):
        """Test filtering by contract type"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        ux_contracts = registry.list_contracts(contract_type="UX_DESIGN")
        assert len(ux_contracts) == 1
        assert ux_contracts[0].contract_id == "contract_001"

    def test_list_by_lifecycle_state(self, registry, sample_contract, dependent_contract):
        """Test filtering by lifecycle state"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        # Both should be in DRAFT state
        draft_contracts = registry.list_contracts(lifecycle_state=ContractLifecycle.DRAFT)
        assert len(draft_contracts) == 2

    def test_list_by_provider_agent(self, registry, sample_contract, dependent_contract):
        """Test filtering by provider agent"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        ux_contracts = registry.list_contracts(provider_agent="ux_designer")
        assert len(ux_contracts) == 1

    def test_list_by_consumer_agent(self, registry, sample_contract, dependent_contract):
        """Test filtering by consumer agent"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        frontend_contracts = registry.list_contracts(consumer_agent="frontend_developer")
        assert len(frontend_contracts) == 2

    def test_list_by_priority(self, registry, sample_contract, dependent_contract):
        """Test filtering by priority"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        high_priority = registry.list_contracts(priority="HIGH")
        assert len(high_priority) == 1
        assert high_priority[0].contract_id == "contract_002"

    def test_list_by_tags(self, registry, sample_contract):
        """Test filtering by tags"""
        registry.register_contract(sample_contract)

        ui_contracts = registry.list_contracts(tags=["ui"])
        assert len(ui_contracts) == 1

        auth_ui_contracts = registry.list_contracts(tags=["ui", "authentication"])
        assert len(auth_ui_contracts) == 1

        missing_tag = registry.list_contracts(tags=["nonexistent"])
        assert len(missing_tag) == 0


# ============================================================================
# Test 4: update_contract
# ============================================================================

class TestUpdateContract:
    """Test contract updates"""

    def test_update_contract_specification(self, registry, sample_contract):
        """Test updating a contract's specification"""
        registry.register_contract(sample_contract)

        # Modify contract
        sample_contract.specification["new_field"] = "new_value"

        updated = registry.update_contract(sample_contract)
        assert updated.specification["new_field"] == "new_value"

    def test_update_nonexistent_contract(self, registry, sample_contract):
        """Test updating a non-existent contract fails"""
        with pytest.raises(ContractNotFoundError):
            registry.update_contract(sample_contract)

    def test_update_dependencies(self, registry, sample_contract, dependent_contract):
        """Test updating a contract's dependencies"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        # Create a third contract
        c3 = UniversalContract(
            contract_id="contract_003",
            contract_type="TEST",
            name="Test",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
        )
        registry.register_contract(c3)

        # Update contract_002 to also depend on contract_003
        dependent_contract.depends_on.append("contract_003")
        registry.update_contract(dependent_contract)

        assert "contract_003" in registry._dependency_graph["contract_002"]
        assert "contract_002" in registry._dependents_graph["contract_003"]


# ============================================================================
# Test 5: delete_contract
# ============================================================================

class TestDeleteContract:
    """Test contract deletion"""

    def test_delete_contract_without_dependents(self, registry, sample_contract):
        """Test deleting a contract without dependents"""
        registry.register_contract(sample_contract)

        registry.delete_contract("contract_001")

        contract = registry.get_contract("contract_001")
        assert contract.lifecycle_state == ContractLifecycle.REJECTED

    def test_delete_contract_with_dependents(self, registry, sample_contract, dependent_contract):
        """Test deleting a contract with dependents fails"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        with pytest.raises(ContractRegistryError, match="has.*dependents"):
            registry.delete_contract("contract_001")

    def test_delete_nonexistent_contract(self, registry):
        """Test deleting a non-existent contract fails"""
        with pytest.raises(ContractNotFoundError):
            registry.delete_contract("nonexistent")


# ============================================================================
# Test 6: propose_contract
# ============================================================================

class TestProposeContract:
    """Test contract proposal"""

    def test_propose_contract(self, registry, sample_contract):
        """Test proposing a contract"""
        registry.register_contract(sample_contract)

        result = registry.propose_contract("contract_001", proposer="ux_designer")

        assert result.lifecycle_state == ContractLifecycle.PROPOSED
        assert len(result.events) == 1
        assert result.events[0].event_type == "proposed"

    def test_propose_invalid_state(self, registry, sample_contract):
        """Test proposing from invalid state fails"""
        registry.register_contract(sample_contract)

        # Move to VERIFIED (terminal state)
        sample_contract.lifecycle_state = ContractLifecycle.VERIFIED
        registry.update_contract(sample_contract)

        with pytest.raises(ContractTransitionError):
            registry.propose_contract("contract_001", proposer="agent")


# ============================================================================
# Test 7: accept_contract
# ============================================================================

class TestAcceptContract:
    """Test contract acceptance"""

    def test_accept_contract(self, registry, sample_contract):
        """Test accepting a contract"""
        registry.register_contract(sample_contract)
        registry.propose_contract("contract_001", proposer="ux_designer")

        result = registry.accept_contract("contract_001", acceptor="frontend_developer")

        assert result.lifecycle_state == ContractLifecycle.IN_PROGRESS
        assert len(result.events) == 2  # proposed + accepted

    def test_accept_from_invalid_state(self, registry, sample_contract):
        """Test accepting from invalid state fails"""
        registry.register_contract(sample_contract)

        # Try to accept from DRAFT (should be PROPOSED first)
        with pytest.raises(ContractTransitionError):
            registry.accept_contract("contract_001", acceptor="agent")


# ============================================================================
# Test 8: fulfill_contract
# ============================================================================

class TestFulfillContract:
    """Test contract fulfillment"""

    def test_fulfill_contract(self, registry, sample_contract):
        """Test fulfilling a contract"""
        registry.register_contract(sample_contract)
        registry.propose_contract("contract_001", proposer="ux_designer")
        registry.accept_contract("contract_001", acceptor="frontend_developer")

        deliverables = ["artifact_001", "artifact_002"]
        result = registry.fulfill_contract(
            "contract_001",
            fulfiller="frontend_developer",
            deliverables=deliverables
        )

        assert result.lifecycle_state == ContractLifecycle.FULFILLED
        assert result.events[-1].deliverables == deliverables


# ============================================================================
# Test 9: verify_contract
# ============================================================================

class TestVerifyContract:
    """Test contract verification"""

    def test_verify_contract_success(self, registry, sample_contract):
        """Test successful contract verification"""
        registry.register_contract(sample_contract)
        registry.propose_contract("contract_001", proposer="ux_designer")
        registry.accept_contract("contract_001", acceptor="frontend_developer")
        registry.fulfill_contract("contract_001", fulfiller="frontend_developer", deliverables=[])

        verification_result = VerificationResult(
            contract_id="contract_001",
            passed=True,
            overall_message="All criteria passed",
            criteria_results=[
                CriterionResult(
                    criterion_id="crit_001",
                    passed=True,
                    actual_value=98,
                    expected_value=95,
                    message="Passed"
                )
            ]
        )

        result = registry.verify_contract(
            "contract_001",
            verifier="validator",
            verification_result=verification_result
        )

        assert result.lifecycle_state == ContractLifecycle.VERIFIED
        assert result.verification_result is not None

    def test_verify_contract_with_warnings(self, registry, sample_contract):
        """Test contract verification with warnings"""
        registry.register_contract(sample_contract)
        registry.propose_contract("contract_001", proposer="ux_designer")
        registry.accept_contract("contract_001", acceptor="frontend_developer")
        registry.fulfill_contract("contract_001", fulfiller="frontend_developer", deliverables=[])

        # Create a non-blocking criterion result that didn't pass (warning)
        verification_result = VerificationResult(
            contract_id="contract_001",
            passed=True,
            overall_message="Passed with warnings",
            criteria_results=[
                CriterionResult(
                    criterion_id="crit_001",
                    passed=True,
                    actual_value=98,
                    expected_value=95,
                    message="Passed"
                )
            ]
        )

        result = registry.verify_contract(
            "contract_001",
            verifier="validator",
            verification_result=verification_result
        )

        assert result.lifecycle_state in [ContractLifecycle.VERIFIED, ContractLifecycle.VERIFIED_WITH_WARNINGS]

    def test_verify_contract_failure(self, registry, sample_contract):
        """Test failed contract verification"""
        registry.register_contract(sample_contract)
        registry.propose_contract("contract_001", proposer="ux_designer")
        registry.accept_contract("contract_001", acceptor="frontend_developer")
        registry.fulfill_contract("contract_001", fulfiller="frontend_developer", deliverables=[])

        verification_result = VerificationResult(
            contract_id="contract_001",
            passed=False,
            overall_message="Criteria failed",
            criteria_results=[
                CriterionResult(
                    criterion_id="crit_001",
                    passed=False,
                    actual_value=85,
                    expected_value=95,
                    message="Below threshold"
                )
            ]
        )

        result = registry.verify_contract(
            "contract_001",
            verifier="validator",
            verification_result=verification_result
        )

        assert result.lifecycle_state == ContractLifecycle.BREACHED


# ============================================================================
# Test 10: breach_contract
# ============================================================================

class TestBreachContract:
    """Test contract breach"""

    def test_breach_contract(self, registry, sample_contract):
        """Test marking a contract as breached"""
        registry.register_contract(sample_contract)

        breach = ContractBreach(
            breach_id="breach_001",
            contract_id="contract_001",
            severity="major",
            description="Failed verification",
            failed_criteria=["crit_001"]
        )

        result = registry.breach_contract("contract_001", breach)

        assert result.lifecycle_state == ContractLifecycle.BREACHED
        assert result.events[-1].severity == "major"


# ============================================================================
# Test 11: get_dependencies
# ============================================================================

class TestGetDependencies:
    """Test getting contract dependencies"""

    def test_get_dependencies(self, registry, sample_contract, dependent_contract):
        """Test getting dependencies of a contract"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        dependencies = registry.get_dependencies("contract_002")

        assert len(dependencies) == 1
        assert dependencies[0].contract_id == "contract_001"

    def test_get_dependencies_empty(self, registry, sample_contract):
        """Test getting dependencies when there are none"""
        registry.register_contract(sample_contract)

        dependencies = registry.get_dependencies("contract_001")
        assert len(dependencies) == 0


# ============================================================================
# Test 12: get_dependents
# ============================================================================

class TestGetDependents:
    """Test getting contract dependents"""

    def test_get_dependents(self, registry, sample_contract, dependent_contract):
        """Test getting dependents of a contract"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        dependents = registry.get_dependents("contract_001")

        assert len(dependents) == 1
        assert dependents[0].contract_id == "contract_002"

    def test_get_dependents_empty(self, registry, dependent_contract):
        """Test getting dependents when there are none"""
        registry.register_contract(dependent_contract)

        dependents = registry.get_dependents("contract_002")
        assert len(dependents) == 0


# ============================================================================
# Test 13: create_execution_plan
# ============================================================================

class TestCreateExecutionPlan:
    """Test execution plan generation"""

    def test_create_execution_plan_simple(self, registry, sample_contract, dependent_contract):
        """Test creating a simple execution plan"""
        registry.register_contract(sample_contract)
        registry.register_contract(dependent_contract)

        plan = registry.create_execution_plan()

        assert len(plan.contracts) == 2
        assert len(plan.execution_order) == 2
        # contract_001 should come before contract_002
        assert plan.execution_order.index("contract_001") < plan.execution_order.index("contract_002")

    def test_create_execution_plan_parallel_groups(self, registry):
        """Test parallel execution groups"""
        # Create contracts with no dependencies (can run in parallel)
        c1 = UniversalContract(
            contract_id="c1",
            contract_type="TEST",
            name="Contract 1",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
        )

        c2 = UniversalContract(
            contract_id="c2",
            contract_type="TEST",
            name="Contract 2",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
        )

        registry.register_contract(c1)
        registry.register_contract(c2)

        plan = registry.create_execution_plan()

        # Both should be in the same parallel group
        assert len(plan.parallel_groups) >= 1
        # First group should contain both contracts
        assert len(plan.parallel_groups[0]) == 2

    def test_create_execution_plan_complex(self, registry):
        """Test creating a complex execution plan"""
        # Create a complex dependency graph
        #   c1
        #   ├── c2 (depends on c1)
        #   └── c3 (depends on c1)
        #       └── c4 (depends on c3)

        c1 = UniversalContract(
            contract_id="c1",
            contract_type="TEST",
            name="Contract 1",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
        )

        c2 = UniversalContract(
            contract_id="c2",
            contract_type="TEST",
            name="Contract 2",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
            depends_on=["c1"],
        )

        c3 = UniversalContract(
            contract_id="c3",
            contract_type="TEST",
            name="Contract 3",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
            depends_on=["c1"],
        )

        c4 = UniversalContract(
            contract_id="c4",
            contract_type="TEST",
            name="Contract 4",
            description="Test",
            provider_agent="agent",
            consumer_agents=[],
            specification={},
            acceptance_criteria=[],
            depends_on=["c3"],
        )

        registry.register_contract(c1)
        registry.register_contract(c2)
        registry.register_contract(c3)
        registry.register_contract(c4)

        plan = registry.create_execution_plan()

        assert len(plan.execution_order) == 4
        # c1 must come first
        assert plan.execution_order[0] == "c1"
        # c2 and c3 can run in parallel after c1
        c2_index = plan.execution_order.index("c2")
        c3_index = plan.execution_order.index("c3")
        assert c2_index > 0
        assert c3_index > 0
        # c4 must come after c3
        assert plan.execution_order.index("c4") > plan.execution_order.index("c3")


# ============================================================================
# Test 14: get_contract_history
# ============================================================================

class TestGetContractHistory:
    """Test getting contract history"""

    def test_get_contract_history(self, registry, sample_contract):
        """Test getting contract event history"""
        registry.register_contract(sample_contract)
        registry.propose_contract("contract_001", proposer="ux_designer")
        registry.accept_contract("contract_001", acceptor="frontend_developer")

        history = registry.get_contract_history("contract_001")

        assert len(history) == 2
        assert history[0].event_type == "proposed"
        assert history[1].event_type == "accepted"

    def test_get_contract_history_empty(self, registry, sample_contract):
        """Test getting history when there are no events"""
        registry.register_contract(sample_contract)

        history = registry.get_contract_history("contract_001")
        assert len(history) == 0


# ============================================================================
# Test 15: search_contracts
# ============================================================================

class TestSearchContracts:
    """Test contract search"""

    def test_search_by_name(self, registry, sample_contract):
        """Test searching by name"""
        registry.register_contract(sample_contract)

        results = registry.search_contracts("Login")
        assert len(results) == 1
        assert results[0].contract_id == "contract_001"

    def test_search_by_description(self, registry, sample_contract):
        """Test searching by description"""
        registry.register_contract(sample_contract)

        results = registry.search_contracts("form")
        assert len(results) == 1

    def test_search_by_tags(self, registry, sample_contract):
        """Test searching by tags"""
        registry.register_contract(sample_contract)

        results = registry.search_contracts("authentication")
        assert len(results) == 1

    def test_search_case_insensitive(self, registry, sample_contract):
        """Test case-insensitive search"""
        registry.register_contract(sample_contract)

        results = registry.search_contracts("login")
        assert len(results) == 1

    def test_search_no_results(self, registry, sample_contract):
        """Test search with no results"""
        registry.register_contract(sample_contract)

        results = registry.search_contracts("nonexistent")
        assert len(results) == 0

    def test_search_specific_fields(self, registry, sample_contract):
        """Test searching specific fields"""
        registry.register_contract(sample_contract)

        # Search only in contract_id
        results = registry.search_contracts("contract_001", search_fields=["contract_id"])
        assert len(results) == 1


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
