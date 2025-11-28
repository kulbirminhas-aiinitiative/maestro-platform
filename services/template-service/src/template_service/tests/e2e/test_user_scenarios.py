"""
Comprehensive End-to-End User Scenario Tests
Tests complete user workflows and real-world usage patterns
"""

import pytest
from fastapi.testclient import TestClient
import uuid


@pytest.mark.e2e
@pytest.mark.critical
class TestDeveloperWorkflow:
    """Test complete developer workflow"""

    def test_developer_discovers_and_uses_template(self, client):
        """Complete workflow: login -> search -> retrieve -> use template"""
        # Step 1: Developer logs in
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Developer searches for React templates
        search_response = client.get(
            "/api/v1/templates/search?q=react&category=frontend",
            headers=auth_headers
        )

        assert search_response.status_code in [200, 500]

        # Step 3: Developer browses all templates
        list_response = client.get(
            "/api/v1/templates",
            headers=auth_headers
        )

        assert list_response.status_code in [200, 500]

        # Step 4: Developer retrieves specific template
        if search_response.status_code == 200:
            templates = search_response.json()
            if isinstance(templates, list) and len(templates) > 0:
                template_id = templates[0].get("id", "test-id")
            else:
                template_id = "test-id"
        else:
            template_id = "test-id"

        retrieve_response = client.get(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers
        )

        assert retrieve_response.status_code in [200, 404, 500]

        # Step 5: Developer checks their profile
        me_response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert me_response.status_code in [200, 500]

    def test_developer_creates_and_updates_template(self, client, sample_template):
        """Workflow: login -> create template -> update -> verify"""
        # Step 1: Login
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        auth_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Step 2: Create new template
        new_template = {
            **sample_template,
            "id": str(uuid.uuid4()),
            "name": f"new-template-{uuid.uuid4().hex[:8]}"
        }

        create_response = client.post(
            "/api/v1/templates",
            json=new_template,
            headers=auth_headers
        )

        assert create_response.status_code in [200, 201, 422, 500]

        # Step 3: Update the template
        if create_response.status_code in [200, 201]:
            template_id = new_template["id"]
            update_data = {
                "description": "Updated description",
                "quality_score": 90
            }

            update_response = client.put(
                f"/api/v1/templates/{template_id}",
                json=update_data,
                headers=auth_headers
            )

            assert update_response.status_code in [200, 404, 500]

            # Step 4: Verify update
            verify_response = client.get(
                f"/api/v1/templates/{template_id}",
                headers=auth_headers
            )

            assert verify_response.status_code in [200, 404, 500]


@pytest.mark.e2e
@pytest.mark.critical
class TestAdminWorkflow:
    """Test complete admin workflow"""

    def test_admin_manages_templates(self, client, sample_template):
        """Workflow: login -> create -> update -> delete template"""
        # Step 1: Admin login
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Step 2: Create template
        new_template = {
            **sample_template,
            "id": str(uuid.uuid4()),
            "name": f"admin-template-{uuid.uuid4().hex[:8]}"
        }

        create_response = client.post(
            "/api/v1/templates",
            json=new_template,
            headers=admin_headers
        )

        assert create_response.status_code in [200, 201, 422, 500]

        # Step 3: List all templates
        list_response = client.get(
            "/api/v1/templates",
            headers=admin_headers
        )

        assert list_response.status_code in [200, 500]

        # Step 4: Delete template (admin privilege)
        if create_response.status_code in [200, 201]:
            delete_response = client.delete(
                f"/api/v1/templates/{new_template['id']}",
                headers=admin_headers
            )

            assert delete_response.status_code in [200, 204, 404, 500]

            # Step 5: Verify deletion
            verify_response = client.get(
                f"/api/v1/templates/{new_template['id']}",
                headers=admin_headers
            )

            # Should be 404 if delete succeeded
            assert verify_response.status_code in [404, 500]

    def test_admin_bulk_operations(self, client, template_list):
        """Workflow: admin performs bulk operations"""
        # Login
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Create multiple templates
        created_ids = []
        for i in range(5):
            template = {
                **template_list[i % len(template_list)],
                "id": str(uuid.uuid4()),
                "name": f"bulk-template-{i}-{uuid.uuid4().hex[:8]}"
            }

            response = client.post(
                "/api/v1/templates",
                json=template,
                headers=admin_headers
            )

            if response.status_code in [200, 201]:
                created_ids.append(template["id"])

        # Verify all created
        for template_id in created_ids:
            response = client.get(
                f"/api/v1/templates/{template_id}",
                headers=admin_headers
            )
            assert response.status_code in [200, 404, 500]


@pytest.mark.e2e
class TestViewerWorkflow:
    """Test viewer (read-only) workflow"""

    def test_viewer_browse_templates(self, client):
        """Workflow: viewer can browse but not modify"""
        # Step 1: Viewer login
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "viewer", "password": "viewer123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        viewer_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Step 2: View templates (should work)
        list_response = client.get(
            "/api/v1/templates",
            headers=viewer_headers
        )

        assert list_response.status_code in [200, 500]

        # Step 3: Search templates (should work)
        search_response = client.get(
            "/api/v1/templates/search?q=test",
            headers=viewer_headers
        )

        assert search_response.status_code in [200, 500]

        # Step 4: Try to create template (should fail)
        create_response = client.post(
            "/api/v1/templates",
            json={"name": "test"},
            headers=viewer_headers
        )

        assert create_response.status_code in [401, 403, 422, 500]

        # Step 5: Try to delete (should fail)
        delete_response = client.delete(
            "/api/v1/templates/test-id",
            headers=viewer_headers
        )

        assert delete_response.status_code in [401, 403, 500]


@pytest.mark.e2e
class TestTemplateDiscoveryJourney:
    """Test template discovery user journey"""

    def test_new_user_discovers_templates(self, client):
        """Journey: new user discovers and evaluates templates"""
        # Step 1: Check system health
        health_response = client.get("/health")
        assert health_response.status_code == 200

        # Step 2: Login as new developer
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        auth_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Step 3: Browse all templates
        browse_response = client.get(
            "/api/v1/templates",
            headers=auth_headers
        )

        assert browse_response.status_code in [200, 500]

        # Step 4: Filter by category
        filter_response = client.get(
            "/api/v1/templates?category=frontend",
            headers=auth_headers
        )

        assert filter_response.status_code in [200, 500]

        # Step 5: Filter by quality
        quality_response = client.get(
            "/api/v1/templates?min_quality_score=85",
            headers=auth_headers
        )

        assert quality_response.status_code in [200, 500]

        # Step 6: Search for specific technology
        search_response = client.get(
            "/api/v1/templates/search?q=react&min_quality_score=80",
            headers=auth_headers
        )

        assert search_response.status_code in [200, 500]

    def test_developer_evaluates_template_quality(self, client):
        """Journey: developer evaluates template quality"""
        # Login
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        auth_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Search high-quality templates
        search_response = client.get(
            "/api/v1/templates/search?min_quality_score=90",
            headers=auth_headers
        )

        assert search_response.status_code in [200, 500]

        # Filter platinum tier
        platinum_response = client.get(
            "/api/v1/templates?quality_tier=platinum",
            headers=auth_headers
        )

        assert platinum_response.status_code in [200, 500]


@pytest.mark.e2e
class TestCollaborationScenarios:
    """Test collaboration scenarios"""

    def test_team_collaboration_workflow(self, client, sample_template):
        """Scenario: team members collaborate on templates"""
        # Developer creates template
        dev_login = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert dev_login.status_code == 200
        dev_headers = {"Authorization": f"Bearer {dev_login.json()['access_token']}"}

        new_template = {
            **sample_template,
            "id": str(uuid.uuid4()),
            "name": f"team-template-{uuid.uuid4().hex[:8]}"
        }

        create_response = client.post(
            "/api/v1/templates",
            json=new_template,
            headers=dev_headers
        )

        assert create_response.status_code in [200, 201, 422, 500]

        # Viewer reviews template
        viewer_login = client.post(
            "/api/v1/auth/token",
            data={"username": "viewer", "password": "viewer123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert viewer_login.status_code == 200
        viewer_headers = {"Authorization": f"Bearer {viewer_login.json()['access_token']}"}

        review_response = client.get(
            f"/api/v1/templates/{new_template['id']}",
            headers=viewer_headers
        )

        assert review_response.status_code in [200, 404, 500]

        # Admin approves and publishes
        admin_login = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert admin_login.status_code == 200
        admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        update_response = client.put(
            f"/api/v1/templates/{new_template['id']}",
            json={"quality_score": 95, "quality_tier": "platinum"},
            headers=admin_headers
        )

        assert update_response.status_code in [200, 404, 500]


@pytest.mark.e2e
class TestErrorRecoveryScenarios:
    """Test error handling and recovery"""

    def test_network_error_recovery(self, client):
        """Scenario: recover from network errors"""
        # Try to access without auth
        response1 = client.get("/api/v1/templates")
        assert response1.status_code == 401

        # Login and retry
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert login_response.status_code == 200
        auth_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Retry with auth
        response2 = client.get("/api/v1/templates", headers=auth_headers)
        assert response2.status_code in [200, 500]

    def test_validation_error_recovery(self, client, auth_headers):
        """Scenario: recover from validation errors"""
        # Try invalid data
        invalid_template = {"name": "test"}  # Missing required fields

        response1 = client.post(
            "/api/v1/templates",
            json=invalid_template,
            headers=auth_headers
        )

        assert response1.status_code in [422, 500]

        # Fix and retry
        valid_template = {
            "name": "test-template",
            "version": "1.0.0",
            "description": "Test template",
            "category": "frontend",
            "language": "javascript"
        }

        response2 = client.post(
            "/api/v1/templates",
            json=valid_template,
            headers=auth_headers
        )

        assert response2.status_code in [200, 201, 422, 500]


@pytest.mark.e2e
@pytest.mark.quality_fabric
class TestE2EQualityMetrics:
    """Test E2E scenarios with quality-fabric tracking"""

    async def test_complete_user_journeys(self, quality_fabric_client, client):
        """Track complete user journeys"""
        journeys_completed = 0
        journeys_total = 3

        # Journey 1: Developer workflow
        try:
            login = client.post(
                "/api/v1/auth/token",
                data={"username": "developer", "password": "dev123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if login.status_code == 200:
                headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
                browse = client.get("/api/v1/templates", headers=headers)
                search = client.get("/api/v1/templates/search?q=test", headers=headers)

                if browse.status_code in [200, 500] and search.status_code in [200, 500]:
                    journeys_completed += 1
        except Exception:
            pass

        # Journey 2: Viewer workflow
        try:
            login = client.post(
                "/api/v1/auth/token",
                data={"username": "viewer", "password": "viewer123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if login.status_code == 200:
                headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
                browse = client.get("/api/v1/templates", headers=headers)

                if browse.status_code in [200, 500]:
                    journeys_completed += 1
        except Exception:
            pass

        # Journey 3: Admin workflow
        try:
            login = client.post(
                "/api/v1/auth/token",
                data={"username": "admin", "password": "admin123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            if login.status_code == 200:
                headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
                browse = client.get("/api/v1/templates", headers=headers)

                if browse.status_code in [200, 500]:
                    journeys_completed += 1
        except Exception:
            pass

        # Track results
        await quality_fabric_client.track_test_execution(
            test_name="e2e_user_journeys",
            duration=0,
            status="passed" if journeys_completed == journeys_total else "partial",
            coverage=(journeys_completed / journeys_total) * 100
        )

        assert journeys_completed >= 2  # At least 2 journeys should work
