#!/usr/bin/env python3
"""
Quality Fabric (TaaS) + UTCP Orchestration Demo

Demonstrates Claude orchestrating comprehensive testing workflows
using Quality Fabric (Testing as a Service) and PDF Generator
through UTCP.

This shows the power of UTCP + Claude:
- Discover quality-fabric and pdf-generator services automatically
- Orchestrate multi-step testing workflows
- Generate professional test reports
- All without manual integration!

Prerequisites:
    1. Start quality-fabric UTCP service:
       cd quality-fabric && python utcp_service.py

    2. Start PDF generator UTCP service:
       cd utilities/services/pdf_generator && python utcp_app.py

    3. Set ANTHROPIC_API_KEY environment variable

Usage:
    python taas_orchestration_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add shared library to path
shared_path = Path(__file__).parent.parent.parent / "packages" / "core-api" / "src"
sys.path.insert(0, str(shared_path))

from maestro_core_api.claude_orchestrator import ClaudeUTCPOrchestrator
from maestro_core_logging import get_logger

logger = get_logger(__name__)


async def demo_comprehensive_testing():
    """Demo: Comprehensive testing workflow with PDF report generation"""
    print("\n" + "="*80)
    print("DEMO 1: Comprehensive Testing Workflow")
    print("="*80 + "\n")

    orchestrator = ClaudeUTCPOrchestrator()

    # Initialize with services
    service_urls = [
        "http://localhost:8100",  # quality-fabric
        "http://localhost:8003",  # pdf-generator
    ]

    print("🔍 Discovering services...")
    await orchestrator.initialize(service_urls)

    discovered = orchestrator.registry.list_services()
    print(f"✅ Discovered {len(discovered)} services:")
    for service in discovered:
        print(f"   • {service['name']} - {service['base_url']}")

    print("\n" + "-"*80)
    print("Testing Scenario: E-commerce API Validation")
    print("-"*80 + "\n")

    user_request = """
I'm preparing to deploy my e-commerce API to production. Please run comprehensive
testing including:
1. Unit tests for all core functionality
2. Integration tests for API endpoints
3. End-to-end tests for user checkout flow
4. Security vulnerability scanning
5. Performance load testing with 1000 concurrent users

Then generate a professional PDF test report that I can share with stakeholders.

Project ID: ecommerce-api
Environment: staging
"""

    print("📤 User Request:")
    print(user_request)
    print("\n🤖 Claude Orchestrating...\n")

    try:
        result = await orchestrator.process_request(user_request)

        if result.success:
            print("\n✅ Orchestration Successful!\n")
            print("📊 Claude's Response:")
            print("-"*80)
            print(result.response)
            print("-"*80)

            print("\n📋 Tool Calls Made:")
            for i, call in enumerate(result.tool_calls, 1):
                print(f"{i}. {call['name']}")
                if call.get('input'):
                    print(f"   Input: {call['input']}")

            print(f"\n💰 Tokens Used: {result.tokens_used.get('total', 0)}")
            print(f"🔧 Model: {result.model}")

        else:
            print(f"\n❌ Orchestration failed: {result.error}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def demo_api_testing():
    """Demo: Focused API testing workflow"""
    print("\n" + "="*80)
    print("DEMO 2: API Testing Workflow")
    print("="*80 + "\n")

    orchestrator = ClaudeUTCPOrchestrator()

    # Initialize
    await orchestrator.initialize([
        "http://localhost:8100",  # quality-fabric
    ])

    user_request = """
Test my User Management API comprehensively:

Endpoints:
- POST /api/users (create user)
- GET /api/users (list users)
- GET /api/users/{id} (get user)
- PUT /api/users/{id} (update user)
- DELETE /api/users/{id} (delete user)

Run integration tests and security tests to validate:
- Authentication (JWT tokens)
- Authorization (role-based access)
- Input validation
- SQL injection protection
- Rate limiting

Project: user-management-api
"""

    print("📤 User Request:")
    print(user_request)
    print("\n🤖 Claude Orchestrating...\n")

    try:
        result = await orchestrator.process_request(user_request)

        if result.success:
            print("\n✅ Orchestration Successful!\n")
            print("📊 Response:")
            print(result.response)

            print(f"\n💰 Tokens: {result.tokens_used.get('total', 0)}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def demo_frontend_testing():
    """Demo: Frontend E2E testing"""
    print("\n" + "="*80)
    print("DEMO 3: Frontend E2E Testing Workflow")
    print("="*80 + "\n")

    orchestrator = ClaudeUTCPOrchestrator()

    await orchestrator.initialize([
        "http://localhost:8100",  # quality-fabric
    ])

    user_request = """
Test my React e-commerce checkout flow end-to-end:

User Journey:
1. Browse product catalog
2. Add items to cart
3. Proceed to checkout
4. Enter shipping information
5. Enter payment details (Stripe)
6. Complete order
7. Receive confirmation email

Validate across browsers:
- Chrome (desktop)
- Firefox (desktop)
- Safari (desktop)
- Chrome (mobile)

Include visual regression testing and accessibility checks.

Project: ecommerce-frontend
Environment: staging
"""

    print("📤 User Request:")
    print(user_request)
    print("\n🤖 Claude Orchestrating...\n")

    try:
        result = await orchestrator.process_request(user_request)

        if result.success:
            print("\n✅ Orchestration Successful!\n")
            print("📊 Response:")
            print(result.response)

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def demo_microservices_testing():
    """Demo: Microservices architecture testing"""
    print("\n" + "="*80)
    print("DEMO 4: Microservices Architecture Testing")
    print("="*80 + "\n")

    orchestrator = ClaudeUTCPOrchestrator()

    await orchestrator.initialize([
        "http://localhost:8100",  # quality-fabric
        "http://localhost:8003",  # pdf-generator
    ])

    user_request = """
Test my microservices architecture comprehensively:

Services:
- API Gateway (Kong) - Port 8000
- User Service (FastAPI) - Port 8001
- Product Service (Node.js) - Port 8002
- Order Service (Python) - Port 8003
- Payment Service (Go) - Port 8004

Testing Requirements:
1. Integration tests for service-to-service communication
2. Performance testing (10K requests/second target)
3. Chaos engineering (kill random services, validate recovery)
4. Security scanning (all services)
5. API contract testing

Then generate a comprehensive architecture test report PDF.

Project: microservices-platform
Environment: staging
"""

    print("📤 User Request:")
    print(user_request)
    print("\n🤖 Claude Orchestrating...\n")

    try:
        result = await orchestrator.process_request(user_request)

        if result.success:
            print("\n✅ Orchestration Successful!\n")
            print("📊 Response:")
            print(result.response)

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def demo_continuous_quality():
    """Demo: Set up continuous quality monitoring"""
    print("\n" + "="*80)
    print("DEMO 5: Continuous Quality Monitoring Setup")
    print("="*80 + "\n")

    orchestrator = ClaudeUTCPOrchestrator()

    await orchestrator.initialize([
        "http://localhost:8100",  # quality-fabric
    ])

    user_request = """
Set up continuous quality monitoring for my application:

Schedule:
- Smoke tests: Every hour
- Regression tests: Every 4 hours
- Performance tests: Daily at 2 AM
- Security scans: Daily at 3 AM

Generate weekly quality report with:
- Test pass/fail trends
- Performance metrics
- Code coverage trends
- Security vulnerability status
- Recommendations for improvement

Project: production-app
Environment: production
"""

    print("📤 User Request:")
    print(user_request)
    print("\n🤖 Claude Orchestrating...\n")

    try:
        result = await orchestrator.process_request(user_request)

        if result.success:
            print("\n✅ Orchestration Successful!\n")
            print("📊 Response:")
            print(result.response)

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def demo_capabilities_discovery():
    """Demo: Discover testing capabilities"""
    print("\n" + "="*80)
    print("DEMO: Service Capabilities Discovery")
    print("="*80 + "\n")

    orchestrator = ClaudeUTCPOrchestrator()

    await orchestrator.initialize([
        "http://localhost:8100",  # quality-fabric
        "http://localhost:8003",  # pdf-generator
    ])

    user_request = """
What testing capabilities are available?
Show me all supported test types, frameworks, and features.
"""

    print("📤 User Request:")
    print(user_request)
    print("\n🤖 Claude Orchestrating...\n")

    try:
        result = await orchestrator.process_request(user_request)

        if result.success:
            print("\n✅ Response:")
            print(result.response)

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("Quality Fabric (TaaS) + UTCP Orchestration Demos")
    print("="*80)
    print("\nThese demos show Claude automatically orchestrating comprehensive")
    print("testing workflows using Quality Fabric and PDF Generator via UTCP.\n")

    # Check API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nPlease set your API key:")
        print("  export ANTHROPIC_API_KEY='your-key-here'")
        return

    print("Prerequisites:")
    print("  ✓ ANTHROPIC_API_KEY is set")
    print("\nMake sure services are running:")
    print("  • quality-fabric: http://localhost:8100")
    print("  • pdf-generator: http://localhost:8003")
    print()

    try:
        # Run capabilities discovery first
        await demo_capabilities_discovery()

        # Run comprehensive demo
        await demo_comprehensive_testing()

        # Uncomment to run more demos:
        # await demo_api_testing()
        # await demo_frontend_testing()
        # await demo_microservices_testing()
        # await demo_continuous_quality()

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())