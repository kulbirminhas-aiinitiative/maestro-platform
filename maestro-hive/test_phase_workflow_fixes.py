#!/usr/bin/env python3
"""
Test Phase Workflow Critical Fixes

Tests the following critical fixes:
1. Phase persistence (session save/restore with phase history)
2. Exit criteria validation (fail-safe defaults)
3. Quality regression detection
4. No mock fallback
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
import logging
import json

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from phase_models import (
    SDLCPhase,
    PhaseState,
    PhaseExecution,
    PhaseIssue,
    PhaseGateResult,
    QualityThresholds
)
from session_manager import SessionManager, SDLCSession
from phase_gate_validator import PhaseGateValidator
from progressive_quality_manager import ProgressiveQualityManager

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class TestPhaseWorkflowFixes:
    """Test suite for phase workflow critical fixes"""
    
    def __init__(self):
        self.session_manager = SessionManager(session_dir=Path("./test_sessions"))
        self.phase_gates = PhaseGateValidator()
        self.quality_manager = ProgressiveQualityManager()
        self.test_output_dir = Path("./test_output")
        self.test_output_dir.mkdir(exist_ok=True)
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("\n" + "="*80)
        logger.info("PHASE WORKFLOW CRITICAL FIXES - TEST SUITE")
        logger.info("="*80 + "\n")
        
        results = {}
        
        # Test 1: Phase Persistence
        logger.info("Test 1: Phase Persistence")
        logger.info("-" * 80)
        results['phase_persistence'] = await self.test_phase_persistence()
        
        # Test 2: Exit Criteria Fail-Safe
        logger.info("\nTest 2: Exit Criteria Fail-Safe")
        logger.info("-" * 80)
        results['exit_criteria_fail_safe'] = await self.test_exit_criteria_fail_safe()
        
        # Test 3: Quality Regression Detection
        logger.info("\nTest 3: Quality Regression Detection")
        logger.info("-" * 80)
        results['quality_regression'] = await self.test_quality_regression_detection()
        
        # Test 4: Session Metadata Support
        logger.info("\nTest 4: Session Metadata Support")
        logger.info("-" * 80)
        results['session_metadata'] = await self.test_session_metadata()
        
        # Test 5: Phase History Serialization
        logger.info("\nTest 5: Phase History Serialization")
        logger.info("-" * 80)
        results['phase_serialization'] = await self.test_phase_serialization()
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, passed_status in results.items():
            status = "✅ PASSED" if passed_status else "❌ FAILED"
            logger.info(f"{test_name:30s}: {status}")
        
        logger.info("")
        logger.info(f"Total: {passed}/{total} tests passed")
        logger.info("="*80 + "\n")
        
        return passed == total
    
    async def test_phase_persistence(self) -> bool:
        """Test that phase history can be saved and restored"""
        try:
            # Create a session with phase history
            session = self.session_manager.create_session(
                requirement="Test requirement",
                output_dir=self.test_output_dir,
                session_id="test_persistence"
            )
            
            # Create sample phase execution
            phase_exec = PhaseExecution(
                phase=SDLCPhase.REQUIREMENTS,
                state=PhaseState.COMPLETED,
                iteration=1,
                started_at=datetime.now()
            )
            phase_exec.completed_at = datetime.now()
            phase_exec.personas_executed = ["requirement_analyst"]
            phase_exec.quality_score = 0.85
            phase_exec.completeness = 0.90
            
            # Add to session metadata
            session.metadata["phase_history"] = [phase_exec.to_dict()]
            session.metadata["current_phase"] = SDLCPhase.DESIGN.value
            session.metadata["iteration_count"] = 2
            
            # Save session
            saved = self.session_manager.save_session(session)
            assert saved, "Failed to save session"
            logger.info("✅ Phase history saved to session")
            
            # Load session
            loaded_session = self.session_manager.load_session("test_persistence")
            assert loaded_session is not None, "Failed to load session"
            logger.info("✅ Session loaded successfully")
            
            # Verify phase history
            assert "phase_history" in loaded_session.metadata, "Missing phase_history in metadata"
            assert len(loaded_session.metadata["phase_history"]) == 1, "Wrong phase history count"
            
            # Deserialize phase execution
            phase_data = loaded_session.metadata["phase_history"][0]
            restored_phase = PhaseExecution.from_dict(phase_data)
            
            # Verify phase data
            assert restored_phase.phase == SDLCPhase.REQUIREMENTS, "Wrong phase"
            assert restored_phase.state == PhaseState.COMPLETED, "Wrong state"
            assert restored_phase.quality_score == 0.85, "Wrong quality score"
            assert restored_phase.completeness == 0.90, "Wrong completeness"
            assert "requirement_analyst" in restored_phase.personas_executed, "Wrong personas"
            
            logger.info("✅ Phase history restored correctly")
            logger.info(f"   Phase: {restored_phase.phase.value}")
            logger.info(f"   State: {restored_phase.state.value}")
            logger.info(f"   Quality: {restored_phase.quality_score:.0%}")
            logger.info(f"   Completeness: {restored_phase.completeness:.0%}")
            
            # Cleanup
            self.session_manager.delete_session("test_persistence")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_exit_criteria_fail_safe(self) -> bool:
        """Test that unknown exit criteria fail by default"""
        try:
            # Create dummy phase execution
            phase_exec = PhaseExecution(
                phase=SDLCPhase.IMPLEMENTATION,
                state=PhaseState.IN_PROGRESS,
                iteration=1,
                started_at=datetime.now()
            )
            phase_exec.quality_score = 0.80
            phase_exec.completeness = 0.85
            
            # Test known criterion (should pass)
            known_result = await self.phase_gates._check_exit_criterion(
                "All tests pass",
                phase_exec,
                self.test_output_dir
            )
            assert known_result == True, "Known criterion should pass"
            logger.info("✅ Known criterion passes correctly")
            
            # Test unknown criterion (should FAIL for safety)
            unknown_result = await self.phase_gates._check_exit_criterion(
                "Some completely unknown criterion that we never defined",
                phase_exec,
                self.test_output_dir
            )
            assert unknown_result == False, "Unknown criterion should FAIL for safety"
            logger.info("✅ Unknown criterion fails safely (as expected)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_quality_regression_detection(self) -> bool:
        """Test quality regression detection"""
        try:
            # Create two phase executions with regression
            previous_metrics = {
                'completeness': 0.85,
                'quality_score': 0.80,
                'test_coverage': 0.75
            }
            
            current_metrics = {
                'completeness': 0.70,  # Regression!
                'quality_score': 0.75,  # Regression!
                'test_coverage': 0.80   # Improvement
            }
            
            # Check for regression
            regression_check = self.quality_manager.check_quality_regression(
                SDLCPhase.IMPLEMENTATION,
                current_metrics,
                previous_metrics,
                tolerance=0.05
            )
            
            # Verify regression detected
            assert regression_check['has_regression'], "Should detect regression"
            assert len(regression_check['regressed_metrics']) >= 2, "Should detect 2 regressed metrics"
            assert len(regression_check['improvements']) >= 1, "Should detect 1 improvement"
            
            logger.info("✅ Quality regression detected correctly")
            logger.info(f"   Regressed: {len(regression_check['regressed_metrics'])} metrics")
            for metric in regression_check['regressed_metrics']:
                logger.info(f"      - {metric}")
            logger.info(f"   Improved: {len(regression_check['improvements'])} metrics")
            for metric in regression_check['improvements']:
                logger.info(f"      - {metric}")
            
            # Test no regression case
            no_regression_metrics = {
                'completeness': 0.90,  # Improvement
                'quality_score': 0.85,  # Improvement
                'test_coverage': 0.80   # Stable
            }
            
            no_regression_check = self.quality_manager.check_quality_regression(
                SDLCPhase.IMPLEMENTATION,
                no_regression_metrics,
                previous_metrics,
                tolerance=0.05
            )
            
            assert not no_regression_check['has_regression'], "Should not detect regression"
            logger.info("✅ No false positive regression detected")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_session_metadata(self) -> bool:
        """Test session metadata support"""
        try:
            # Create session
            session = self.session_manager.create_session(
                requirement="Test metadata",
                output_dir=self.test_output_dir,
                session_id="test_metadata"
            )
            
            # Verify metadata exists and has defaults
            assert hasattr(session, 'metadata'), "Session should have metadata attribute"
            assert 'phase_history' in session.metadata, "Should have phase_history"
            assert 'current_phase' in session.metadata, "Should have current_phase"
            assert 'iteration_count' in session.metadata, "Should have iteration_count"
            assert 'workflow_mode' in session.metadata, "Should have workflow_mode"
            
            logger.info("✅ Session has required metadata fields")
            logger.info(f"   Keys: {list(session.metadata.keys())}")
            
            # Add custom metadata
            session.metadata['custom_field'] = 'test_value'
            session.metadata['phase_history'] = [
                {'phase': 'requirements', 'state': 'completed'}
            ]
            
            # Save and reload
            self.session_manager.save_session(session)
            loaded = self.session_manager.load_session("test_metadata")
            
            # Verify metadata persisted
            assert loaded.metadata['custom_field'] == 'test_value', "Custom field not persisted"
            assert len(loaded.metadata['phase_history']) == 1, "Phase history not persisted"
            
            logger.info("✅ Metadata persists correctly across save/load")
            
            # Cleanup
            self.session_manager.delete_session("test_metadata")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_phase_serialization(self) -> bool:
        """Test PhaseExecution serialization/deserialization"""
        try:
            # Create complex phase execution with all fields
            phase_exec = PhaseExecution(
                phase=SDLCPhase.TESTING,
                state=PhaseState.NEEDS_REWORK,
                iteration=3,
                started_at=datetime.now()
            )
            phase_exec.completed_at = datetime.now()
            phase_exec.personas_executed = ["qa_engineer", "integration_tester"]
            phase_exec.personas_reused = ["unit_tester"]
            phase_exec.quality_score = 0.72
            phase_exec.completeness = 0.68
            phase_exec.test_coverage = 0.75
            phase_exec.rework_reason = "Quality below threshold"
            
            # Add gate results
            phase_exec.entry_gate_result = PhaseGateResult(
                passed=True,
                score=0.95,
                criteria_met=["Previous phase complete"],
                criteria_failed=[],
                blocking_issues=[],
                warnings=[],
                recommendations=[]
            )
            
            phase_exec.exit_gate_result = PhaseGateResult(
                passed=False,
                score=0.68,
                criteria_met=["Tests exist"],
                criteria_failed=["Quality too low"],
                blocking_issues=["Quality score 0.72 < 0.75"],
                warnings=["Test coverage could be higher"],
                recommendations=["Improve code quality"]
            )
            
            # Add issues
            phase_exec.issues.append(PhaseIssue(
                severity="high",
                category="quality",
                description="Code quality below threshold",
                affected_persona="qa_engineer",
                affected_deliverable="test_report",
                recommendation="Add more comprehensive tests"
            ))
            
            # Serialize
            phase_dict = phase_exec.to_dict()
            
            # Verify serialization
            assert phase_dict['phase'] == 'testing', "Phase not serialized correctly"
            assert phase_dict['state'] == 'needs_rework', "State not serialized correctly"
            assert phase_dict['iteration'] == 3, "Iteration not serialized correctly"
            assert phase_dict['quality_score'] == 0.72, "Quality score not serialized"
            assert len(phase_dict['personas_executed']) == 2, "Personas executed not serialized"
            assert len(phase_dict['personas_reused']) == 1, "Personas reused not serialized"
            assert phase_dict['entry_gate_result'] is not None, "Entry gate not serialized"
            assert phase_dict['exit_gate_result'] is not None, "Exit gate not serialized"
            assert len(phase_dict['issues']) == 1, "Issues not serialized"
            
            logger.info("✅ PhaseExecution serializes correctly")
            logger.info(f"   Serialized keys: {list(phase_dict.keys())}")
            
            # Deserialize
            restored = PhaseExecution.from_dict(phase_dict)
            
            # Verify deserialization
            assert restored.phase == SDLCPhase.TESTING, "Phase not restored"
            assert restored.state == PhaseState.NEEDS_REWORK, "State not restored"
            assert restored.iteration == 3, "Iteration not restored"
            assert restored.quality_score == 0.72, "Quality score not restored"
            assert len(restored.personas_executed) == 2, "Personas executed not restored"
            assert len(restored.personas_reused) == 1, "Personas reused not restored"
            assert restored.entry_gate_result is not None, "Entry gate not restored"
            assert restored.exit_gate_result is not None, "Exit gate not restored"
            assert len(restored.issues) == 1, "Issues not restored"
            assert restored.rework_reason == "Quality below threshold", "Rework reason not restored"
            
            logger.info("✅ PhaseExecution deserializes correctly")
            logger.info(f"   Phase: {restored.phase.value}")
            logger.info(f"   State: {restored.state.value}")
            logger.info(f"   Issues: {len(restored.issues)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run test suite"""
    tester = TestPhaseWorkflowFixes()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
