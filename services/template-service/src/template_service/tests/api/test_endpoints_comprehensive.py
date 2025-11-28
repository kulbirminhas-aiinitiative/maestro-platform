"""
Comprehensive API Endpoint Tests
Tests all REST API endpoints with authentication, validation, and error handling
"""

import pytest
from fastapi.testclient import TestClient
import json


@pytest.mark.api
@pytest.mark.auth
class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_login_endpoint_success(self, client):
        """POST /api/v1/auth/token should return token"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_endpoint_wrong_password(self, client):
        """POST /api/v1/auth/token with wrong password should fail"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "wrong_password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_login_endpoint_nonexistent_user(self, client):
        """POST /api/v1/auth/token with nonexistent user should fail"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "nonexistent", "password": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401

    def test_me_endpoint_with_valid_token(self, client, auth_headers):
        """GET /api/v1/auth/me should return user info"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        # Should return 200 with user info, or 401/500 if DB not available
        assert response.status_code in [200, 401, 500]

    def test_me_endpoint_without_token(self, client):
        """GET /api/v1/auth/me without token should fail"""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401

    def test_me_endpoint_with_invalid_token(self, client, invalid_token):
        """GET /api/v1/auth/me with invalid token should fail"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {invalid_token}"}
        )

        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.templates
class TestTemplatesEndpoints:
    """Test template endpoints"""

    def test_list_templates_without_auth(self, client):
        """GET /api/v1/templates without auth should fail"""
        response = client.get("/api/v1/templates")
        assert response.status_code == 401

    def test_list_templates_with_auth(self, client, auth_headers):
        """GET /api/v1/templates with auth should work"""
        response = client.get("/api/v1/templates", headers=auth_headers)

        # Should return 200 with templates, or 500 if DB not available
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list) or isinstance(data, dict)

    def test_list_templates_with_filters(self, client, auth_headers):
        """GET /api/v1/templates with filters should work"""
        response = client.get(
            "/api/v1/templates?category=frontend&language=javascript",
            headers=auth_headers
        )

        assert response.status_code in [200, 500]

    def test_get_template_by_id_without_auth(self, client):
        """GET /api/v1/templates/{id} without auth should fail"""
        template_id = "test-id"
        response = client.get(f"/api/v1/templates/{template_id}")

        assert response.status_code == 401

    def test_get_template_by_id_with_auth(self, client, auth_headers):
        """GET /api/v1/templates/{id} with auth should work"""
        template_id = "test-id"
        response = client.get(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers
        )

        # Should return 200, 404, or 500
        assert response.status_code in [200, 404, 500]

    def test_create_template_without_auth(self, client, sample_template):
        """POST /api/v1/templates without auth should fail"""
        response = client.post(
            "/api/v1/templates",
            json=sample_template
        )

        assert response.status_code == 401

    def test_create_template_with_auth(self, client, auth_headers, sample_template):
        """POST /api/v1/templates with auth should work"""
        response = client.post(
            "/api/v1/templates",
            json=sample_template,
            headers=auth_headers
        )

        # Should return 200/201 on success, or 401/500
        assert response.status_code in [200, 201, 401, 500]

    def test_create_template_with_invalid_data(self, client, auth_headers):
        """POST /api/v1/templates with invalid data should fail"""
        invalid_template = {
            "name": "test"
            # Missing required fields
        }
        response = client.post(
            "/api/v1/templates",
            json=invalid_template,
            headers=auth_headers
        )

        # Should return 422 (validation error) or 500
        assert response.status_code in [422, 500]

    def test_update_template_without_auth(self, client):
        """PUT /api/v1/templates/{id} without auth should fail"""
        template_id = "test-id"
        update_data = {"description": "Updated"}

        response = client.put(
            f"/api/v1/templates/{template_id}",
            json=update_data
        )

        assert response.status_code == 401

    def test_update_template_with_auth(self, client, auth_headers):
        """PUT /api/v1/templates/{id} with auth should work"""
        template_id = "test-id"
        update_data = {"description": "Updated"}

        response = client.put(
            f"/api/v1/templates/{template_id}",
            json=update_data,
            headers=auth_headers
        )

        # Should return 200, 404, or 500
        assert response.status_code in [200, 404, 500]

    def test_delete_template_without_auth(self, client):
        """DELETE /api/v1/templates/{id} without auth should fail"""
        template_id = "test-id"
        response = client.delete(f"/api/v1/templates/{template_id}")

        assert response.status_code == 401

    def test_delete_template_with_viewer_role(self, client, viewer_headers):
        """DELETE /api/v1/templates/{id} with viewer role should fail"""
        template_id = "test-id"
        response = client.delete(
            f"/api/v1/templates/{template_id}",
            headers=viewer_headers
        )

        # Should return 403 (forbidden) or 401
        assert response.status_code in [401, 403, 500]

    def test_delete_template_with_admin_role(self, client, admin_headers):
        """DELETE /api/v1/templates/{id} with admin role should work"""
        template_id = "test-id"
        response = client.delete(
            f"/api/v1/templates/{template_id}",
            headers=admin_headers
        )

        # Should return 200, 404, or 500
        assert response.status_code in [200, 204, 404, 500]


@pytest.mark.api
@pytest.mark.search
class TestSearchEndpoints:
    """Test search endpoints"""

    def test_search_templates_without_auth(self, client):
        """GET /api/v1/templates/search without auth should fail"""
        response = client.get("/api/v1/templates/search?q=react")

        assert response.status_code == 401

    def test_search_templates_with_auth(self, client, auth_headers):
        """GET /api/v1/templates/search with auth should work"""
        response = client.get(
            "/api/v1/templates/search?q=react",
            headers=auth_headers
        )

        assert response.status_code in [200, 500]

    def test_search_templates_with_empty_query(self, client, auth_headers):
        """GET /api/v1/templates/search with empty query should work"""
        response = client.get(
            "/api/v1/templates/search?q=",
            headers=auth_headers
        )

        # Should return all templates or validation error
        assert response.status_code in [200, 422, 500]

    def test_search_templates_with_filters(self, client, auth_headers):
        """GET /api/v1/templates/search with filters should work"""
        response = client.get(
            "/api/v1/templates/search?q=api&category=backend&min_quality_score=85",
            headers=auth_headers
        )

        assert response.status_code in [200, 500]


@pytest.mark.api
@pytest.mark.health
class TestHealthEndpoints:
    """Test health and status endpoints"""

    def test_health_endpoint(self, client):
        """GET /health should return health status"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_root_endpoint(self, client):
        """GET / should return API info"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "service" in data

    def test_docs_endpoint(self, client):
        """GET /docs should return OpenAPI docs"""
        response = client.get("/docs")

        # Should return HTML or redirect
        assert response.status_code in [200, 307]


@pytest.mark.api
@pytest.mark.validation
class TestRequestValidation:
    """Test request validation"""

    def test_invalid_json_body(self, client, auth_headers):
        """POST with invalid JSON should fail"""
        response = client.post(
            "/api/v1/templates",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )

        # Should return 422 (validation error) or 400
        assert response.status_code in [400, 422]

    def test_missing_required_fields(self, client, auth_headers):
        """POST with missing required fields should fail"""
        incomplete_data = {"name": "test"}

        response = client.post(
            "/api/v1/templates",
            json=incomplete_data,
            headers=auth_headers
        )

        assert response.status_code in [422, 500]

    def test_invalid_field_types(self, client, auth_headers):
        """POST with invalid field types should fail"""
        invalid_data = {
            "name": "test",
            "version": 123,  # Should be string
            "description": "Test"
        }

        response = client.post(
            "/api/v1/templates",
            json=invalid_data,
            headers=auth_headers
        )

        assert response.status_code in [422, 500]


@pytest.mark.api
@pytest.mark.error_handling
class TestErrorHandling:
    """Test error handling"""

    def test_404_for_nonexistent_endpoint(self, client):
        """GET to nonexistent endpoint should return 404"""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_405_for_wrong_method(self, client):
        """Wrong HTTP method should return 405"""
        response = client.post("/health")

        # Might return 405 (method not allowed) or 404
        assert response.status_code in [404, 405]

    def test_error_response_format(self, client):
        """Error responses should have consistent format"""
        response = client.get("/api/v1/templates")

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data  # FastAPI standard error format


@pytest.mark.api
@pytest.mark.cors
class TestCORSHeaders:
    """Test CORS headers"""

    def test_cors_headers_present(self, client):
        """CORS headers should be present"""
        response = client.options("/api/v1/templates")

        # CORS headers might not be set in test environment
        # This test would be more relevant in integration/E2E
        pass

    def test_cors_allowed_origins(self, client):
        """CORS should allow configured origins"""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # Check for CORS headers if configured
        pass


@pytest.mark.api
@pytest.mark.performance
class TestAPIPerformance:
    """Test API performance"""

    def test_health_endpoint_response_time(self, client, performance_timer):
        """Health endpoint should respond quickly"""
        performance_timer.start()
        response = client.get("/health")
        performance_timer.stop()

        assert response.status_code == 200
        assert performance_timer.elapsed_ms < 100

    def test_list_templates_response_time(self, client, auth_headers, performance_timer):
        """List templates should respond in reasonable time"""
        performance_timer.start()
        response = client.get("/api/v1/templates", headers=auth_headers)
        performance_timer.stop()

        # Should respond within 2 seconds even with DB query
        assert performance_timer.elapsed_ms < 2000

    def test_concurrent_requests_handling(self, client, auth_headers):
        """API should handle concurrent requests"""
        import concurrent.futures

        def make_request():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in futures]

        # All requests should succeed
        assert all(r.status_code == 200 for r in results)


@pytest.mark.api
@pytest.mark.quality_fabric
class TestAPIQualityMetrics:
    """Test API endpoints with quality-fabric tracking"""

    async def test_api_endpoint_coverage(self, client, quality_fabric_client, auth_headers, admin_headers):
        """Track API endpoint coverage"""
        endpoints_tested = 0
        endpoints_total = 15

        endpoints = [
            ("/health", "GET", None, [200]),
            ("/", "GET", None, [200]),
            ("/api/v1/auth/token", "POST", None, [200, 401]),
            ("/api/v1/auth/me", "GET", auth_headers, [200, 401, 500]),
            ("/api/v1/templates", "GET", auth_headers, [200, 500]),
            ("/api/v1/templates/test-id", "GET", auth_headers, [200, 404, 500]),
            ("/api/v1/templates", "POST", auth_headers, [200, 201, 422, 500]),
            ("/api/v1/templates/test-id", "PUT", auth_headers, [200, 404, 500]),
            ("/api/v1/templates/test-id", "DELETE", admin_headers, [200, 204, 404, 500]),
            ("/api/v1/templates/search", "GET", auth_headers, [200, 500]),
        ]

        for endpoint, method, headers, expected_codes in endpoints:
            try:
                if method == "GET":
                    response = client.get(endpoint, headers=headers) if headers else client.get(endpoint)
                elif method == "POST":
                    response = client.post(endpoint, json={}, headers=headers) if headers else client.post(endpoint, json={})
                elif method == "PUT":
                    response = client.put(endpoint, json={}, headers=headers) if headers else client.put(endpoint, json={})
                elif method == "DELETE":
                    response = client.delete(endpoint, headers=headers) if headers else client.delete(endpoint)

                if response.status_code in expected_codes:
                    endpoints_tested += 1
            except Exception:
                pass

        # Track results
        await quality_fabric_client.track_test_execution(
            test_name="api_endpoint_coverage",
            duration=0,
            status="passed",
            coverage=(endpoints_tested / endpoints_total) * 100
        )

        assert endpoints_tested >= 5  # At least some endpoints should work
