#!/usr/bin/env python3
"""
Autonomous SDLC with Intelligent Retry Logic

Features:
- Run all development personas in sequence
- Automatically retry failed quality gates (up to 3 times)
- Run project_reviewer at the end
- If reviewer fails, trigger remediation iteration
- Fully autonomous until success or max iterations

Usage:
    python autonomous_sdlc_with_retry.py --session SESSION_ID --requirement "..." --max-iterations 5
"""

import subprocess
import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class AutonomousSDLC:
    def __init__(self, session_id: str, requirement: str, output_dir: str = None, max_iterations: int = 5, max_retries_per_persona: int = 2):
        self.session_id = session_id
        self.requirement = requirement
        self.output_dir = output_dir or session_id
        self.max_iterations = max_iterations
        self.max_retries_per_persona = max_retries_per_persona
        self.session_file = Path(f"sdlc_sessions/{session_id}.json")

    def run_personas(self, personas: List[str], force: bool = False) -> Dict[str, Any]:
        """Run specified personas and return session results"""
        cmd = [
            "poetry", "run", "python3", "team_execution.py",
            *personas,
            "--session", self.session_id,
            "--output", self.output_dir,
            "--requirement", self.requirement
        ]

        if force:
            cmd.append("--force")

        logger.info(f"🚀 Running: {' '.join(personas)}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

            # Load session results
            if self.session_file.exists():
                with open(self.session_file) as f:
                    session_data = json.load(f)
                return session_data
            else:
                logger.error("Session file not found")
                return {}

        except subprocess.TimeoutExpired:
            logger.error("Execution timed out after 1 hour")
            return {}
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {}

    def get_failed_personas(self, session_data: Dict[str, Any]) -> List[str]:
        """Identify personas that failed quality gates"""
        failed = []
        validation_dir = Path(f"{self.output_dir}/validation_reports")

        if not validation_dir.exists():
            return failed

        for persona_id in session_data.get("completed_personas", []):
            validation_file = validation_dir / f"{persona_id}_validation.json"
            if validation_file.exists():
                with open(validation_file) as f:
                    validation = json.load(f)
                    if not validation.get("passed", True):
                        failed.append(persona_id)

        return failed

    def get_reviewer_recommendation(self) -> str:
        """Get project_reviewer recommendation"""
        metrics_file = Path(f"{self.output_dir}/reviews/metrics_json.json")

        if not metrics_file.exists():
            return "UNKNOWN"

        try:
            with open(metrics_file) as f:
                metrics = json.load(f)
                return metrics.get("overall_metrics", {}).get("recommended_action", "UNKNOWN")
        except:
            return "UNKNOWN"

    def get_completion_percentage(self) -> float:
        """Get overall project completion"""
        metrics_file = Path(f"{self.output_dir}/reviews/metrics_json.json")

        if not metrics_file.exists():
            return 0.0

        try:
            with open(metrics_file) as f:
                metrics = json.load(f)
                return metrics.get("overall_metrics", {}).get("completion_percentage", 0.0)
        except:
            return 0.0

    def run_autonomous_sdlc(self):
        """Main autonomous loop with retry logic"""
        logger.info("="*80)
        logger.info("🤖 AUTONOMOUS SDLC ENGINE - WITH INTELLIGENT RETRY")
        logger.info("="*80)
        logger.info(f"📝 Session: {self.session_id}")
        logger.info(f"🎯 Max Iterations: {self.max_iterations}")
        logger.info(f"🔄 Max Retries per Persona: {self.max_retries_per_persona}")
        logger.info("="*80)

        # Phase 1: Initial Development
        development_personas = ["backend_developer", "frontend_developer", "qa_engineer"]
        retry_counts = {p: 0 for p in development_personas}

        for iteration in range(1, self.max_iterations + 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"🔄 ITERATION {iteration}/{self.max_iterations}")
            logger.info(f"{'='*80}\n")

            # Step 1: Run development personas
            session_data = self.run_personas(development_personas, force=(iteration > 1))

            if not session_data:
                logger.error("❌ Failed to get session data, aborting")
                return False

            # Step 2: Check for quality gate failures
            failed_personas = self.get_failed_personas(session_data)

            if failed_personas:
                logger.warning(f"⚠️  Quality gate failures: {', '.join(failed_personas)}")

                # Retry failed personas if under retry limit
                personas_to_retry = []
                for persona in failed_personas:
                    if retry_counts[persona] < self.max_retries_per_persona:
                        retry_counts[persona] += 1
                        personas_to_retry.append(persona)
                        logger.info(f"🔄 Retrying {persona} (attempt {retry_counts[persona] + 1}/{self.max_retries_per_persona + 1})")
                    else:
                        logger.warning(f"⚠️  {persona} exceeded max retries, skipping")

                if personas_to_retry:
                    logger.info(f"\n🔄 Retrying failed personas: {', '.join(personas_to_retry)}")
                    session_data = self.run_personas(personas_to_retry, force=True)

                    # Reset development personas list to only retry the failed ones in next iteration
                    development_personas = personas_to_retry
                    continue
                else:
                    logger.warning("⚠️  All retries exhausted, proceeding to review")

            # Step 3: Run project_reviewer
            logger.info("\n🔍 Running project_reviewer...")
            session_data = self.run_personas(["project_reviewer"], force=True)

            # Step 4: Check reviewer recommendation
            recommendation = self.get_reviewer_recommendation()
            completion = self.get_completion_percentage()

            logger.info(f"\n{'='*80}")
            logger.info(f"📊 ITERATION {iteration} RESULTS")
            logger.info(f"{'='*80}")
            logger.info(f"Recommendation: {recommendation}")
            logger.info(f"Completion: {completion}%")
            logger.info(f"{'='*80}\n")

            # Step 5: Decide next action
            if recommendation == "GO" or completion >= 95:
                logger.info("✅ ✅ ✅ PROJECT READY FOR PRODUCTION! ✅ ✅ ✅")
                return True
            elif recommendation in ["PROCEED_WITH_REMEDIATION", "CONDITIONAL_GO"]:
                if completion >= 90:
                    logger.info("✅ Project is 90%+ complete and improving. Consider final review.")
                    return True
                else:
                    logger.info("⚠️  Project needs remediation, continuing to next iteration...")
                    # Reset personas for full run in next iteration
                    development_personas = ["backend_developer", "frontend_developer", "qa_engineer"]
                    retry_counts = {p: 0 for p in development_personas}
            else:
                logger.warning(f"⚠️  Reviewer recommendation: {recommendation}")
                logger.info("Continuing remediation...")
                development_personas = ["backend_developer", "frontend_developer", "qa_engineer"]
                retry_counts = {p: 0 for p in development_personas}

        # Max iterations reached
        logger.warning(f"⚠️  Reached max iterations ({self.max_iterations})")
        logger.info(f"📊 Final completion: {completion}%")

        if completion >= 80:
            logger.info("✅ Project is 80%+ complete. Manual review recommended.")
            return True
        else:
            logger.error("❌ Project did not reach acceptable completion level")
            return False


def main():
    parser = argparse.ArgumentParser(description="Autonomous SDLC with Retry Logic")
    parser.add_argument("--session", required=True, help="Session ID")
    parser.add_argument("--requirement", required=True, help="Project requirements")
    parser.add_argument("--output", help="Output directory (defaults to session ID)")
    parser.add_argument("--max-iterations", type=int, default=5, help="Max iterations (default: 5)")
    parser.add_argument("--max-retries", type=int, default=2, help="Max retries per persona (default: 2)")

    args = parser.parse_args()

    engine = AutonomousSDLC(
        session_id=args.session,
        requirement=args.requirement,
        output_dir=args.output,
        max_iterations=args.max_iterations,
        max_retries_per_persona=args.max_retries
    )

    success = engine.run_autonomous_sdlc()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
