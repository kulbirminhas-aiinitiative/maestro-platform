#!/usr/bin/env python3
"""
Execute All 6 Projects in PARALLEL with Quality Fabric Integration
Version: 1.0.0

Runs all B2C and B2B projects concurrently for maximum speed.
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, Any, List
import time


class ParallelProjectExecutor:
    """Execute multiple projects in parallel"""

    def __init__(self, api_url: str = "http://localhost:5001"):
        self.api_url = api_url
        self.results = []

    async def execute_project(
        self,
        project_name: str,
        requirement: str,
        mode: str = "mixed",
        quality_threshold: float = 0.75
    ) -> Dict[str, Any]:
        """Execute a single project through the workflow"""

        print(f"\n🚀 STARTING: {project_name}")
        start_time = time.time()

        try:
            # Execute workflow
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.api_url}/api/workflow/execute",
                    json={
                        "requirement": requirement,
                        "mode": mode,
                        "project_name": project_name,
                        "quality_threshold": quality_threshold
                    }
                )

                if response.status_code != 200:
                    print(f"❌ {project_name}: HTTP {response.status_code}")
                    return {
                        "project_name": project_name,
                        "status": "failed",
                        "error": f"HTTP {response.status_code}",
                        "duration": time.time() - start_time
                    }

                result = response.json()
                workflow_id = result.get("workflow_id")

                print(f"✅ {project_name}: Workflow {workflow_id} created")

                # Monitor in background
                final_status = await self.monitor_workflow(workflow_id, project_name)

                duration = time.time() - start_time

                result_summary = {
                    "project_name": project_name,
                    "workflow_id": workflow_id,
                    "status": final_status.get("status", "unknown"),
                    "current_phase": final_status.get("current_phase", "unknown"),
                    "progress": final_status.get("progress", 0),
                    "duration_seconds": duration,
                }

                print(f"🏁 {project_name}: {result_summary['status']} ({result_summary['progress']:.0f}%) in {duration:.1f}s")

                return result_summary

        except Exception as e:
            duration = time.time() - start_time
            print(f"❌ {project_name}: Exception - {str(e)}")

            return {
                "project_name": project_name,
                "status": "error",
                "error": str(e),
                "duration": duration
            }

    async def monitor_workflow(
        self,
        workflow_id: str,
        project_name: str,
        max_wait: int = 300,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """Monitor workflow execution"""

        elapsed = 0
        last_progress = -1

        async with httpx.AsyncClient(timeout=30.0) as client:
            while elapsed < max_wait:
                try:
                    response = await client.get(
                        f"{self.api_url}/api/workflow/{workflow_id}/status"
                    )

                    if response.status_code == 200:
                        status = response.json()
                        progress = status.get("progress", 0)
                        workflow_status = status.get("status")

                        # Print progress updates
                        if int(progress / 10) != int(last_progress / 10):
                            print(f"   📊 {project_name}: {progress:.0f}%")
                            last_progress = progress

                        # Check if workflow is complete
                        if workflow_status in ["completed", "failed", "error"]:
                            return status

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                except Exception as e:
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

        return {"status": "timeout", "elapsed": elapsed}

    async def execute_all_projects_parallel(self) -> List[Dict[str, Any]]:
        """Execute ALL 6 projects in PARALLEL"""

        print("\n" + "="*80)
        print("🚀 PARALLEL EXECUTION: ALL 6 PROJECTS")
        print("="*80)
        print("Running B2C and B2B projects concurrently...")
        print()

        # Define all 6 projects
        all_projects = [
            # B2C Projects
            {
                "name": "TastyTalk",
                "requirement": """TastyTalk is an AI-powered platform that helps people learn to cook in their own mother tongue.
                By combining regional language understanding, voice interaction, and visual step-by-step guidance, it makes cooking
                easy, personal, and culturally connected. Key features: voice-guided cooking, multi-language support, visual step
                guidance, recipe recommendations, ingredient-based suggestions.""",
                "category": "B2C"
            },
            {
                "name": "Elth-ai",
                "requirement": """Elth.ai is an intelligent health platform designed to simplify how individuals and families manage
                their medical information and wellness journeys. It securely organizes health records, connects insights across lab
                reports and prescriptions, and uses AI to provide personalized health summaries and reminders. Key features: secure
                health records, lab report analysis, prescription tracking, health summaries, family health management.""",
                "category": "B2C"
            },
            {
                "name": "Elderbi-AI",
                "requirement": """Elderbi AI is a warm, language-savvy digital companion designed to bring comfort, connection, and
                conversation to elders. It speaks in their native tongue, in familiar voices of loved ones they trust. Key features:
                native language conversation, voice cloning, routine reminders, entertainment updates, family connection.""",
                "category": "B2C"
            },
            # B2B Projects
            {
                "name": "Footprint360",
                "requirement": """Footprint360 is a business intelligence and process transformation initiative that partners with
                organizations to map, measure, and enhance their operational footprints. Through a structured "Identify–Fix–Support–
                Enhance" model, it helps businesses streamline operations, improve decision-making, and achieve sustainable growth.
                Key features: process mapping, efficiency analysis, opportunity identification, improvement tracking, BI dashboards.""",
                "category": "B2B"
            },
            {
                "name": "DiagnoLink-AI",
                "requirement": """DiagnoLink AI is an intelligent platform that connects diagnostic labs, doctors, and patients into
                a seamless health data network. By using AI to standardize and interpret lab results, it transforms raw diagnostic
                data into actionable insights. Key features: lab integration, result standardization, anomaly detection, patient
                tracking, doctor insights.""",
                "category": "B2B"
            },
            {
                "name": "Plotrol",
                "requirement": """Plotrol is an AI-powered land guardianship platform that offers peace of mind to landowners by
                discreetly monitoring and protecting their plots. Through a network of trained local Guardians, supported by
                technology like geo-tagged reports and AI-based insights, Plotrol ensures property safety. Key features: guardian
                network, geo-tagged monitoring, image verification, AI insights, property reports.""",
                "category": "B2B"
            }
        ]

        # Execute all projects in parallel
        tasks = [
            self.execute_project(
                project_name=project["name"],
                requirement=project["requirement"],
                mode="mixed",
                quality_threshold=0.75
            )
            for project in all_projects
        ]

        # Wait for all to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "project_name": all_projects[i]["name"],
                    "status": "error",
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        self.results = processed_results
        return processed_results

    def generate_summary_report(self) -> None:
        """Generate comprehensive summary report"""

        print("\n" + "="*80)
        print("📈 PARALLEL EXECUTION SUMMARY")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total Projects: {len(self.results)}")
        print()

        # Categorize results
        completed = [r for r in self.results if r.get("status") == "completed"]
        running = [r for r in self.results if r.get("status") == "running"]
        failed = [r for r in self.results if r.get("status") in ["failed", "error"]]

        print(f"✅ Completed: {len(completed)}")
        print(f"⏳ Running: {len(running)}")
        print(f"❌ Failed/Error: {len(failed)}")
        print()

        # B2C Summary
        print("📱 B2C PROJECTS:")
        b2c_names = ["TastyTalk", "Elth-ai", "Elderbi-AI"]
        for result in self.results:
            if result["project_name"] in b2c_names:
                status = result.get("status", "unknown")
                emoji = "✅" if status == "completed" else "⏳" if status == "running" else "❌"
                print(f"   {emoji} {result['project_name']:<20} | {result.get('workflow_id', 'N/A')}")
                print(f"      Status: {status:<15} | Phase: {result.get('current_phase', 'N/A')}")
                print(f"      Progress: {result.get('progress', 0):.1f}% | Duration: {result.get('duration_seconds', 0):.1f}s")
                print()

        # B2B Summary
        print("🏢 B2B PROJECTS:")
        b2b_names = ["Footprint360", "DiagnoLink-AI", "Plotrol"]
        for result in self.results:
            if result["project_name"] in b2b_names:
                status = result.get("status", "unknown")
                emoji = "✅" if status == "completed" else "⏳" if status == "running" else "❌"
                print(f"   {emoji} {result['project_name']:<20} | {result.get('workflow_id', 'N/A')}")
                print(f"      Status: {status:<15} | Phase: {result.get('current_phase', 'N/A')}")
                print(f"      Progress: {result.get('progress', 0):.1f}% | Duration: {result.get('duration_seconds', 0):.1f}s")
                print()

        # Statistics
        if self.results:
            total_duration = max(r.get("duration_seconds", 0) for r in self.results)
            print(f"⏱️  Total Wall Time: {total_duration:.1f}s ({total_duration/60:.1f}m)")
            print(f"⚡ Speedup: ~{len(self.results)}x (parallel execution)")

        # Save results
        output_file = f"/tmp/parallel_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "execution_mode": "parallel",
                "total_projects": len(self.results),
                "completed": len(completed),
                "running": len(running),
                "failed": len(failed),
                "results": self.results
            }, f, indent=2)

        print(f"\n💾 Results saved to: {output_file}")


async def main():
    """Main execution function"""

    print("\n" + "="*80)
    print("⚡ PARALLEL PROJECT EXECUTOR")
    print("="*80)
    print("Universal Contract Protocol with Quality Fabric")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    executor = ParallelProjectExecutor()

    # Execute ALL projects in parallel
    start_time = time.time()

    results = await executor.execute_all_projects_parallel()

    total_time = time.time() - start_time

    # Generate summary
    executor.generate_summary_report()

    print("\n" + "="*80)
    print(f"✅ PARALLEL EXECUTION COMPLETE in {total_time:.1f}s")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
