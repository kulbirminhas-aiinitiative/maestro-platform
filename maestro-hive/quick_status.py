#!/usr/bin/env python3
"""Quick Status Checker for All 6 Projects"""
import httpx
import asyncio

workflows = {
    "wf-1760179880-5e4b549c": "TastyTalk (B2C)",
    "wf-1760179880-101b14da": "Elth-ai (B2C)",
    "wf-1760179880-e21a8fed": "Elderbi-AI (B2C)",
    "wf-1760179880-6aa8782f": "Footprint360 (B2B)",
    "wf-1760179880-6eb86fde": "DiagnoLink-AI (B2B)",
    "wf-1760179880-fafbe325": "Plotrol (B2B)"
}

async def check_status():
    print("\n" + "="*70)
    print("📊 QUICK STATUS - All 6 Projects")
    print("="*70)

    async with httpx.AsyncClient(timeout=10.0) as client:
        for wf_id, name in workflows.items():
            try:
                resp = await client.get(f"http://localhost:5001/api/workflow/{wf_id}/status")
                data = resp.json()
                status = data.get('status', 'N/A')
                phase = data.get('current_phase', 'N/A')
                progress = data.get('progress', 0)

                emoji = "⏳" if status == "running" else "✅" if status == "completed" else "❌"
                print(f"{emoji} {name:25} | {status:10} | {phase:15} | {progress:5.1f}%")
            except:
                print(f"❌ {name:25} | ERROR")

    print("="*70 + "\n")

asyncio.run(check_status())
