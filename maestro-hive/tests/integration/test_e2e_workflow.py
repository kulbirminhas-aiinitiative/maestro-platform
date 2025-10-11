#!/usr/bin/env python3
"""
End-to-End Workflow Integration Test

Simulates a complete project lifecycle from COMPREHENSIVE_TEAM_MANAGEMENT.md:
E-Commerce Payment Gateway Feature (from MVP to Production)

This test verifies all three paradigms working together:
1. Parallel Execution Engine - MVD, speculative execution, convergence
2. Smart Team Management - Performance scoring, auto-scaling
3. Elastic Team Model - Phase transitions, onboarding, handoffs

Timeline: Requirements → Design → Implementation → Testing → Deployment
"""

import pytest
from parallel_workflow_engine import ParallelWorkflowEngine
from dynamic_team_manager import DynamicTeamManager
from performance_metrics import PerformanceMetricsAnalyzer
from contract_manager import ContractManager
from assumption_tracker import AssumptionTracker
from team_composition_policies import ProjectType
from persistence.models import MembershipState, ConflictSeverity
import team_organization

SDLCPhase = team_organization.SDLCPhase


@pytest.mark.asyncio
class TestECommercePaymentGatewayE2E:
    """
    End-to-end test simulating the e-commerce payment gateway example
    from the documentation
    """

    async def test_complete_sdlc_workflow(self, state_manager, team_id):
        """
        Complete SDLC workflow with all three paradigms

        Phases:
        1. Requirements (BA + UX Designer)
        2. Design (Architect creates contracts in parallel with BA)
        3. Implementation (Backend + Frontend work in parallel on API contract)
        4. Testing (QA tests while devs continue)
        5. Deployment (DevOps deploys, team scales down)
        """
        # Initialize all managers
        parallel_engine = ParallelWorkflowEngine(team_id, state_manager)
        contract_mgr = ContractManager(state_manager)
        assumption_tracker = AssumptionTracker(state_manager)
        team_manager = DynamicTeamManager(
            team_id=team_id,
            state_manager=state_manager,
            project_type=ProjectType.MEDIUM_FEATURE,
            project_name="E-Commerce Payment Gateway"
        )
        performance_analyzer = PerformanceMetricsAnalyzer(state_manager)

        # =====================================================================
        # PHASE 1: REQUIREMENTS (Day 0)
        # =====================================================================
        print("\n=== PHASE 1: REQUIREMENTS ===")

        # Initialize roles
        await team_manager.initialize_role_based_assignments()

        # Start with minimal team
        ba_result = await team_manager.add_member_with_briefing(
            persona_id="requirement_analyst",
            current_phase=SDLCPhase.REQUIREMENTS,
            role_id=None
        )

        ux_result = await team_manager.add_member_with_briefing(
            persona_id="ui_ux_designer",
            current_phase=SDLCPhase.REQUIREMENTS,
            role_id=None
        )

        ba_agent = ba_result["membership"]["agent_id"]
        ux_agent = ux_result["membership"]["agent_id"]

        # BA and UX work on requirements
        req_task = await state_manager.create_task(
            team_id=team_id,
            title="Define payment gateway requirements",
            description="Gather requirements for Stripe/PayPal integration",
            status="completed"
        )

        print(f"✓ Requirements team: {ba_agent}, {ux_agent}")
        print(f"✓ Requirements task completed: {req_task}")

        # =====================================================================
        # PHASE 2: DESIGN + PARALLEL CONTRACT CREATION (Day 1-2)
        # =====================================================================
        print("\n=== PHASE 2: DESIGN (Parallel Execution Starts) ===")

        # Scale for design phase
        await team_manager.scale_for_phase_transition(
            from_phase=SDLCPhase.REQUIREMENTS,
            to_phase=SDLCPhase.DESIGN
        )

        # Add architect
        arch_result = await team_manager.add_member_with_briefing(
            persona_id="solution_architect",
            current_phase=SDLCPhase.DESIGN,
            role_id=None
        )
        arch_agent = arch_result["membership"]["agent_id"]

        # Define MVD (Minimum Viable Definition)
        mvd = {
            "id": "payment_gateway_mvd",
            "title": "Payment Gateway Integration",
            "description": "Integrate Stripe and PayPal with order processing",
            "key_requirements": [
                "Support credit card payments",
                "Support PayPal",
                "Handle payment webhooks",
                "Store payment methods securely"
            ]
        }

        # Architect creates API contract (T+15 minutes in parallel)
        payment_contract = await contract_mgr.create_contract(
            team_id=team_id,
            contract_name="PaymentGatewayAPI",
            version="v0.1",
            contract_type="REST_API",
            specification={
                "endpoints": [
                    {"path": "/payments", "method": "POST", "params": ["amount", "currency", "payment_method"]},
                    {"path": "/payments/{id}", "method": "GET"},
                    {"path": "/webhooks/stripe", "method": "POST"},
                    {"path": "/webhooks/paypal", "method": "POST"}
                ],
                "models": {
                    "Payment": ["id", "amount", "currency", "status", "created_at"]
                }
            },
            owner_role="Tech Lead",
            owner_agent=arch_agent,
            consumers=["backend_lead", "frontend_lead"]
        )

        # Activate contract
        await contract_mgr.activate_contract(payment_contract["id"], arch_agent)

        print(f"✓ Design team includes: {arch_agent}")
        print(f"✓ Payment API Contract v0.1 created and activated")

        # =====================================================================
        # PHASE 3: IMPLEMENTATION (Day 2-4, Parallel Work)
        # =====================================================================
        print("\n=== PHASE 3: IMPLEMENTATION (Full Parallel Execution) ===")

        # Transition to implementation
        await team_manager.scale_for_phase_transition(
            from_phase=SDLCPhase.DESIGN,
            to_phase=SDLCPhase.IMPLEMENTATION
        )

        # Add developers
        be_result = await team_manager.add_member_with_briefing(
            persona_id="backend_developer",
            current_phase=SDLCPhase.IMPLEMENTATION,
            role_id=None
        )

        fe_result = await team_manager.add_member_with_briefing(
            persona_id="frontend_developer",
            current_phase=SDLCPhase.IMPLEMENTATION,
            role_id=None
        )

        be_agent = be_result["membership"]["agent_id"]
        fe_agent = fe_result["membership"]["agent_id"]

        # Start parallel work streams
        work_streams = [
            {
                "role": "Backend Lead",
                "agent_id": be_agent,
                "stream_type": "api_implementation",
                "initial_task": "Implement payment API endpoints"
            },
            {
                "role": "Frontend Lead",
                "agent_id": fe_agent,
                "stream_type": "ui_implementation",
                "initial_task": "Build payment UI components"
            }
        ]

        parallel_session = await parallel_engine.start_parallel_work_streams(mvd, work_streams)

        print(f"✓ Parallel execution started with {len(parallel_session['streams'])} streams")
        print(f"  - Backend: {be_agent}")
        print(f"  - Frontend: {fe_agent}")

        # Backend makes assumption (Day 2, T+30)
        backend_assumption = await assumption_tracker.track_assumption(
            team_id=team_id,
            made_by_agent=be_agent,
            made_by_role="Backend Lead",
            assumption_text="Payment webhooks will only send id, status, amount fields",
            assumption_category="api_contract",
            related_artifact_type="contract",
            related_artifact_id=payment_contract["id"],
            dependent_artifacts=[
                {"type": "task", "id": "implement_webhook_handler"}
            ]
        )

        print(f"✓ Backend assumption tracked: '{backend_assumption['assumption_text'][:50]}...'")

        # Frontend makes assumption (Day 2, T+45)
        frontend_assumption = await assumption_tracker.track_assumption(
            team_id=team_id,
            made_by_agent=fe_agent,
            made_by_role="Frontend Lead",
            assumption_text="Payment response will include redirect_url for 3D Secure",
            assumption_category="data_structure",
            related_artifact_type="contract",
            related_artifact_id=payment_contract["id"],
            dependent_artifacts=[
                {"type": "task", "id": "implement_payment_redirect"}
            ]
        )

        print(f"✓ Frontend assumption tracked: '{frontend_assumption['assumption_text'][:50]}...'")

        # Day 3: Contract evolution with breaking change
        print("\n--- Day 3: Contract Evolution ---")

        evolved_contract = await contract_mgr.evolve_contract(
            team_id=team_id,
            contract_name="PaymentGatewayAPI",
            new_version="v0.2",
            new_specification={
                "endpoints": [
                    # ... same endpoints ...
                ],
                "models": {
                    "Payment": ["id", "amount", "currency", "status", "created_at", "metadata", "customer_id"],  # Added fields!
                    "WebhookPayload": ["id", "status", "amount", "metadata", "timestamp"]  # New webhook structure!
                }
            },
            changes_from_previous={
                "added_fields": ["metadata", "customer_id"],
                "new_webhook_format": True
            },
            breaking_changes=True,
            owner_agent=arch_agent
        )

        print(f"✓ Contract evolved: v0.1 → v0.2 (BREAKING CHANGES)")

        # Detect contract breach
        conflict = await parallel_engine.detect_contract_breach(
            old_contract=payment_contract,
            new_contract=evolved_contract
        )

        assert conflict is not None
        assert conflict["severity"] == ConflictSeverity.HIGH
        print(f"✓ Conflict detected: {conflict['conflict_type']}")
        print(f"  Affected agents: {', '.join(conflict['affected_agents'])}")

        # Invalidate backend assumption
        await assumption_tracker.invalidate_assumption(
            assumption_id=backend_assumption["id"],
            invalidated_by=arch_agent,
            validation_notes="Webhook now includes metadata and timestamp"
        )

        print(f"✓ Backend assumption invalidated")

        # =====================================================================
        # PHASE 4: CONVERGENCE (Day 3, T+180 - 3 hours)
        # =====================================================================
        print("\n=== PHASE 4: CONVERGENCE ===")

        # Trigger convergence to resolve conflicts
        convergence = await parallel_engine.trigger_convergence(
            trigger_type="contract_breaking_change",
            trigger_description="Payment API v0.2 requires team alignment",
            conflict_ids=[conflict["id"]],
            participants=[be_agent, fe_agent, arch_agent]
        )

        print(f"✓ Convergence triggered: {convergence['id']}")
        print(f"  Participants: {len(convergence['participants'])} agents")

        # Complete convergence with decisions
        completed_convergence = await parallel_engine.complete_convergence(
            convergence_id=convergence["id"],
            decisions_made=[
                {
                    "decision": "Update backend webhook handler to process new fields",
                    "agreed_by": [be_agent, arch_agent]
                },
                {
                    "decision": "Frontend will ignore metadata for now",
                    "agreed_by": [fe_agent, arch_agent]
                }
            ],
            artifacts_updated=[
                {"type": "contract", "id": evolved_contract["id"]},
                {"type": "task", "id": "update_webhook_handler"}
            ],
            rework_performed=[
                {"agent": be_agent, "task": "refactor_webhook", "hours": 2},
                {"agent": fe_agent, "task": "verify_compatibility", "hours": 1}
            ]
        )

        print(f"✓ Convergence completed in {completed_convergence['duration_minutes']} minutes")
        print(f"  Actual rework: {completed_convergence['actual_rework_hours']} hours")

        # =====================================================================
        # PHASE 5: TESTING (Day 4-5)
        # =====================================================================
        print("\n=== PHASE 5: TESTING ===")

        await team_manager.scale_for_phase_transition(
            from_phase=SDLCPhase.IMPLEMENTATION,
            to_phase=SDLCPhase.TESTING
        )

        qa_result = await team_manager.add_member_with_briefing(
            persona_id="qa_engineer",
            current_phase=SDLCPhase.TESTING,
            role_id=None
        )
        qa_agent = qa_result["membership"]["agent_id"]

        print(f"✓ QA team member added: {qa_agent}")

        # Simulate QA finding issues (performance impact)
        await state_manager.update_member_performance(
            team_id=team_id,
            agent_id=be_agent,
            performance_score=70,  # Lower due to rework
            task_completion_rate=75,
            average_task_duration_hours=6.0,
            collaboration_score=80
        )

        # =====================================================================
        # PHASE 6: DEPLOYMENT (Day 5)
        # =====================================================================
        print("\n=== PHASE 6: DEPLOYMENT ===")

        await team_manager.scale_for_phase_transition(
            from_phase=SDLCPhase.TESTING,
            to_phase=SDLCPhase.DEPLOYMENT
        )

        devops_result = await team_manager.add_member_with_briefing(
            persona_id="devops_engineer",
            current_phase=SDLCPhase.DEPLOYMENT,
            role_id=None
        )
        devops_agent = devops_result["membership"]["agent_id"]

        print(f"✓ DevOps engineer added: {devops_agent}")

        # =====================================================================
        # PHASE 7: POST-DEPLOYMENT (Team Scale-Down)
        # =====================================================================
        print("\n=== PHASE 7: POST-DEPLOYMENT (Scale Down) ===")

        # Retire members with handoffs
        # BA can retire (requirements complete)
        ba_handoff = await team_manager.retire_member_with_handoff(
            agent_id=ba_agent,
            successor_agent_id=None  # No successor needed, requirements done
        )

        print(f"✓ BA retired with handoff: {ba_handoff['handoff'].departing_agent_id}")

        # Frontend developer to standby
        fe_membership = await state_manager.get_team_member(team_id, fe_agent)
        await state_manager.update_team_member(
            membership_id=fe_membership["id"],
            state=MembershipState.ON_STANDBY
        )

        print(f"✓ Frontend developer moved to standby")

        # =====================================================================
        # FINAL: VERIFY SYSTEM STATE
        # =====================================================================
        print("\n=== FINAL VERIFICATION ===")

        # Team health
        health = await performance_analyzer.analyze_team_health(team_id)
        print(f"✓ Team health score: {health.overall_health_score}/100")
        print(f"  Active members: {health.active_members}")
        print(f"  Standby members: {health.standby_members}")
        print(f"  Retired members: {health.retired_members}")

        # Parallel execution metrics
        parallel_metrics = await parallel_engine.get_parallel_execution_metrics()
        print(f"✓ Parallel execution metrics:")
        print(f"  Total conflicts: {parallel_metrics['total_conflicts']}")
        print(f"  Resolved conflicts: {parallel_metrics['resolved_conflicts']}")
        print(f"  Total convergences: {parallel_metrics['total_convergences']}")
        print(f"  Rework efficiency: {parallel_metrics['rework_efficiency']:.1f}%")

        # Assumption summary
        assumption_summary = await assumption_tracker.get_assumption_summary(team_id)
        print(f"✓ Assumptions:")
        print(f"  Total tracked: {assumption_summary['total_assumptions']}")
        print(f"  Validated: {assumption_summary['validated_count']}")
        print(f"  Invalidated: {assumption_summary['invalidated_count']}")

        # Contract summary
        contract_summary = await contract_mgr.get_contract_summary(team_id)
        print(f"✓ Contracts:")
        print(f"  Total: {contract_summary['total_contracts']}")
        print(f"  Active: {len(contract_summary['active_contracts'])}")

        # =====================================================================
        # ASSERTIONS
        # =====================================================================

        # Team management assertions
        assert health.retired_members >= 1, "Should have retired members"
        assert health.standby_members >= 1, "Should have standby members"
        assert health.active_members >= 2, "Should have active members for production support"

        # Parallel execution assertions
        assert parallel_metrics["total_conflicts"] >= 1, "Should have detected conflicts"
        assert parallel_metrics["resolved_conflicts"] >= 1, "Should have resolved conflicts"
        assert parallel_metrics["total_convergences"] >= 1, "Should have triggered convergence"
        assert parallel_metrics["rework_efficiency"] <= 100, "Rework efficiency should be <= 100%"

        # Assumption tracking assertions
        assert assumption_summary["total_assumptions"] >= 2, "Should have tracked assumptions"
        assert assumption_summary["invalidated_count"] >= 1, "Should have invalidated assumptions"

        # Contract versioning assertions
        assert contract_summary["total_contracts"] >= 2, "Should have contract versions"
        assert len(contract_summary["active_contracts"]) >= 1, "Should have active contract"

        print("\n=== ✅ END-TO-END TEST PASSED ===")
        print("All three paradigms successfully integrated:")
        print("  1. ✓ Parallel Execution Engine (MVD → Convergence)")
        print("  2. ✓ Smart Team Management (Performance → Scaling)")
        print("  3. ✓ Elastic Team Model (Phase transitions → Handoffs)")
