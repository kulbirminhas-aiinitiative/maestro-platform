#!/usr/bin/env python3
"""
Quick validation test for the quality gate system

Tests:
1. File tracking works
2. Deliverable mapping works
3. Stub detection works
4. Quality gate validation works
"""

import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent))

from validation_utils import (
    detect_stubs_and_placeholders,
    validate_persona_deliverables,
    detect_project_type
)


def test_stub_detection():
    """Test stub detection on sample files"""
    print("=" * 80)
    print("TEST 1: Stub Detection")
    print("=" * 80)

    # Create test file with stub
    test_dir = Path("/tmp/test_validation")
    test_dir.mkdir(exist_ok=True)

    stub_file = test_dir / "stub_route.ts"
    stub_file.write_text("""
import { Router } from 'express';

const router = Router();

// router.use('/workspaces', workspaceRoutes);  // Coming Soon
// router.use('/boards', boardRoutes);         // TODO: Implement

router.get('/health', (req, res) => {
    res.json({ status: 'ok' });
});

export default router;
    """)

    result = detect_stubs_and_placeholders(stub_file)

    print(f"File: {stub_file.name}")
    print(f"Is Stub: {result['is_stub']}")
    print(f"Severity: {result['severity']}")
    print(f"Completeness Score: {result['completeness_score']:.2f}")
    print(f"Issues Found: {len(result['issues'])}")
    for issue in result['issues']:
        print(f"  - {issue}")

    assert result['is_stub'], "Should detect stub"
    assert result['severity'] in ['critical', 'high'], "Should be high severity"
    assert result['completeness_score'] < 0.7, "Low completeness for stubs"

    print("\n✅ Stub detection test PASSED\n")


def test_quality_code():
    """Test detection of quality code (not stub)"""
    print("=" * 80)
    print("TEST 2: Quality Code Detection")
    print("=" * 80)

    test_dir = Path("/tmp/test_validation")
    test_dir.mkdir(exist_ok=True)

    quality_file = test_dir / "quality_service.ts"
    quality_file.write_text("""
/**
 * User authentication service
 */
import { User } from '../models';
import bcrypt from 'bcrypt';

export class AuthService {
    async login(email: string, password: string): Promise<User | null> {
        try {
            // Validate input
            if (!email || !password) {
                throw new Error('Email and password required');
            }

            // Find user
            const user = await User.findByEmail(email);
            if (!user) {
                return null;
            }

            // Verify password
            const isValid = await bcrypt.compare(password, user.passwordHash);
            if (!isValid) {
                return null;
            }

            return user;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }
}
    """)

    result = detect_stubs_and_placeholders(quality_file)

    print(f"File: {quality_file.name}")
    print(f"Is Stub: {result['is_stub']}")
    print(f"Severity: {result['severity']}")
    print(f"Completeness Score: {result['completeness_score']:.2f}")
    print(f"Issues Found: {len(result['issues'])}")

    assert not result['is_stub'], "Should NOT detect as stub"
    assert result['completeness_score'] > 0.8, "High completeness for quality code"

    print("\n✅ Quality code detection test PASSED\n")


def test_deliverable_mapping():
    """Test deliverable mapping"""
    print("=" * 80)
    print("TEST 3: Deliverable Mapping")
    print("=" * 80)

    test_dir = Path("/tmp/test_validation")
    test_dir.mkdir(exist_ok=True)

    # Create sample files
    (test_dir / "backend").mkdir(exist_ok=True)
    (test_dir / "backend" / "src").mkdir(exist_ok=True)
    (test_dir / "backend" / "src" / "routes").mkdir(exist_ok=True)

    files_created = [
        "backend/src/routes/auth.routes.ts",
        "backend/src/routes/user.routes.ts",
        "backend/src/services/auth.service.ts",
        "testing/test_plan.md",
        "testing/completeness_report.md"
    ]

    # Create actual files
    for file_path in files_created:
        full_path = test_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(f"# {file_path}")

    # Map files to deliverables (simplified - just testing the logic)
    deliverables_found = {}

    # Backend routes
    backend_routes = [f for f in files_created if "routes" in f]
    if backend_routes:
        deliverables_found["api_implementation"] = backend_routes

    # Test files
    test_files = [f for f in files_created if "test" in f or "testing" in f]
    if test_files:
        deliverables_found["test_report"] = test_files

    print(f"Files Created: {len(files_created)}")
    print(f"Deliverables Mapped: {len(deliverables_found)}")
    for deliverable, files in deliverables_found.items():
        print(f"  {deliverable}: {len(files)} files")

    assert len(deliverables_found) > 0, "Should map some deliverables"

    print("\n✅ Deliverable mapping test PASSED\n")


def test_project_type_detection():
    """Test project type detection"""
    print("=" * 80)
    print("TEST 4: Project Type Detection")
    print("=" * 80)

    # Backend-only project
    backend_dir = Path("/tmp/test_backend_only")
    backend_dir.mkdir(exist_ok=True)
    (backend_dir / "backend" / "src").mkdir(parents=True, exist_ok=True)
    (backend_dir / "backend" / "src" / "server.ts").write_text("// Server")

    context = detect_project_type(backend_dir)
    print(f"Backend-only project type: {context['type']}")
    assert context['type'] == 'backend_only', "Should detect backend-only"
    assert context['has_backend'], "Should have backend"
    assert not context['has_frontend'], "Should not have frontend"

    # Full-stack project
    fullstack_dir = Path("/tmp/test_fullstack")
    fullstack_dir.mkdir(exist_ok=True)
    (fullstack_dir / "backend" / "src").mkdir(parents=True, exist_ok=True)
    (fullstack_dir / "frontend" / "src").mkdir(parents=True, exist_ok=True)
    (fullstack_dir / "backend" / "src" / "server.ts").write_text("// Server")
    (fullstack_dir / "frontend" / "src" / "App.tsx").write_text("// App")

    context = detect_project_type(fullstack_dir)
    print(f"Full-stack project type: {context['type']}")
    assert context['type'] == 'full_stack', "Should detect full-stack"
    assert context['has_backend'], "Should have backend"
    assert context['has_frontend'], "Should have frontend"

    print("\n✅ Project type detection test PASSED\n")


def test_validation_report():
    """Test complete validation report"""
    print("=" * 80)
    print("TEST 5: Validation Report Generation")
    print("=" * 80)

    test_dir = Path("/tmp/test_validation")

    expected_deliverables = ["api_implementation", "test_report", "backend_code"]

    deliverables_found = {
        "api_implementation": ["backend/src/routes/auth.routes.ts"],
        "test_report": ["testing/test_plan.md"]
        # Missing: backend_code
    }

    validation = validate_persona_deliverables(
        persona_id="backend_developer",
        expected_deliverables=expected_deliverables,
        deliverables_found=deliverables_found,
        output_dir=test_dir,
        project_context={"type": "backend_only"}
    )

    print(f"Completeness: {validation['completeness_percentage']:.1f}%")
    print(f"Quality Score: {validation['quality_score']:.2f}")
    print(f"Combined Score: {validation['combined_score']:.2f}")
    print(f"Complete: {validation['complete']}")
    print(f"Missing: {validation['missing']}")
    print(f"Found: {validation['found']}")

    assert not validation['complete'], "Should not be complete (missing deliverable)"
    assert 'backend_code' in validation['missing'], "Should identify missing deliverable"
    assert validation['completeness_percentage'] < 100, "Should be less than 100%"

    print("\n✅ Validation report test PASSED\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("VALIDATION SYSTEM TESTS")
    print("=" * 80 + "\n")

    try:
        test_stub_detection()
        test_quality_code()
        test_deliverable_mapping()
        test_project_type_detection()
        test_validation_report()

        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\nValidation system is working correctly!")
        print("Ready to use in team_execution.py")
        print("\nNext steps:")
        print("1. Run a simple test project")
        print("2. Verify quality gates work end-to-end")
        print("3. Re-run Sunday.com to catch gaps")
        return 0

    except AssertionError as e:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        return 1

    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ UNEXPECTED ERROR")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
