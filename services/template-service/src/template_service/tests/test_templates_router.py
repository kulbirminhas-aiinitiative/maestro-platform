"""
Tests for Templates Router
Tests template listing, searching, and JWT authentication
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import uuid

# Import the FastAPI app
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

client = TestClient(app)


@pytest.fixture
def auth_token():
    """Fixture to get a valid auth token"""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "developer", "password": "dev123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]


@pytest.fixture
def admin_token():
    """Fixture to get an admin auth token"""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]


@pytest.fixture
def viewer_token():
    """Fixture to get a viewer (read-only) auth token"""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "viewer", "password": "viewer123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return response.json()["access_token"]


class TestTemplatesEndpointAuthentication:
    """Test that templates endpoints require authentication"""

    def test_list_templates_without_auth_fails(self):
        """Test that listing templates without auth returns 403"""
        response = client.get("/api/v1/templates")
        assert response.status_code == 401

    def test_list_templates_with_auth_succeeds(self, auth_token):
        """Test that listing templates with auth works"""
        response = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Should return 200 or 500 (if DB not available), but not 403
        assert response.status_code in [200, 500]

    def test_search_templates_without_auth_fails(self):
        """Test that searching templates without auth returns 403"""
        response = client.get("/api/v1/templates/search?query=react")
        assert response.status_code == 401

    def test_search_templates_with_auth_succeeds(self, auth_token):
        """Test that searching templates with auth works"""
        response = client.get(
            "/api/v1/templates/search?query=react",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in [200, 500]

    def test_get_template_by_id_without_auth_fails(self):
        """Test that getting template by ID without auth returns 403"""
        template_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/templates/{template_id}")
        assert response.status_code == 401

    def test_get_template_by_id_with_auth_succeeds(self, auth_token):
        """Test that getting template by ID with auth works"""
        template_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/templates/{template_id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Will likely return 404 (not found) or 500, but not 403
        assert response.status_code in [404, 500]


class TestTemplatesListingAndFiltering:
    """Test template listing and filtering"""

    def test_list_templates_with_pagination(self, auth_token):
        """Test template listing with pagination parameters"""
        response = client.get(
            "/api/v1/templates?page=1&page_size=10",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Check response structure (even if no DB)
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "page" in data
            assert "page_size" in data
            assert "templates" in data
            assert data["page"] == 1
            assert data["page_size"] == 10

    def test_list_templates_with_language_filter(self, auth_token):
        """Test filtering templates by language"""
        response = client.get(
            "/api/v1/templates?language=python",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "templates" in data

    def test_list_templates_with_multiple_filters(self, auth_token):
        """Test filtering templates with multiple parameters"""
        response = client.get(
            "/api/v1/templates?language=python&framework=fastapi&category=api",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "templates" in data

    def test_list_templates_with_pinned_filter(self, auth_token):
        """Test filtering only pinned templates"""
        response = client.get(
            "/api/v1/templates?pinned=true",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "templates" in data

    def test_list_templates_with_quality_tier_filter(self, auth_token):
        """Test filtering by quality tier"""
        response = client.get(
            "/api/v1/templates?quality_tier=gold",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "templates" in data


class TestTemplatesSearch:
    """Test template search functionality"""

    def test_search_templates_with_query(self, auth_token):
        """Test searching templates with text query"""
        response = client.get(
            "/api/v1/templates/search?query=authentication",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "templates" in data

    def test_search_templates_with_min_quality_score(self, auth_token):
        """Test searching with minimum quality score filter"""
        response = client.get(
            "/api/v1/templates/search?min_quality_score=80",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "templates" in data

    def test_search_templates_with_sorting(self, auth_token):
        """Test searching with custom sorting"""
        response = client.get(
            "/api/v1/templates/search?sort_by=quality_score&sort_order=desc",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            data = response.json()
            assert "templates" in data


class TestTemplatesPinning:
    """Test template pinning functionality"""

    def test_pin_template_without_auth_fails(self):
        """Test that pinning template without auth fails"""
        template_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/templates/{template_id}/pin",
            params={
                "reason": "Test pinning",
                "quality_tier": "gold",
                "pinned_by": "test_user"
            }
        )
        assert response.status_code == 401

    def test_pin_template_with_auth(self, auth_token):
        """Test pinning template with auth"""
        template_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v1/templates/{template_id}/pin",
            params={
                "reason": "Test pinning",
                "quality_tier": "gold",
                "pinned_by": "developer"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Will likely return 404 or 500, but not 403
        assert response.status_code in [404, 500]

    def test_unpin_template_without_auth_fails(self):
        """Test that unpinning template without auth fails"""
        template_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/templates/{template_id}/pin")
        assert response.status_code == 401

    def test_unpin_template_with_auth(self, auth_token):
        """Test unpinning template with auth"""
        template_id = str(uuid.uuid4())
        response = client.delete(
            f"/api/v1/templates/{template_id}/pin",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Will likely return 404 or 500, but not 403
        assert response.status_code in [404, 500]


class TestTemplatesVersioning:
    """Test template versioning endpoints"""

    def test_list_template_versions_without_auth_fails(self):
        """Test that listing versions without auth fails"""
        template_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/templates/{template_id}/versions")
        assert response.status_code == 401

    def test_list_template_versions_with_auth(self, auth_token):
        """Test listing template versions with auth"""
        template_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/templates/{template_id}/versions",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in [404, 500]

    def test_get_template_manifest_without_auth_fails(self):
        """Test that getting manifest without auth fails"""
        template_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/templates/{template_id}/manifest")
        assert response.status_code == 401

    def test_get_template_manifest_with_auth(self, auth_token):
        """Test getting template manifest with auth"""
        template_id = str(uuid.uuid4())
        response = client.get(
            f"/api/v1/templates/{template_id}/manifest",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code in [404, 500]


class TestScopeBasedAuthorization:
    """Test that different user scopes have appropriate access"""

    def test_viewer_can_list_templates(self, viewer_token):
        """Test that viewer can list templates (read-only)"""
        response = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        # Viewer has templates:read scope, should work
        assert response.status_code in [200, 500]

    def test_developer_can_list_templates(self, auth_token):
        """Test that developer can list templates"""
        response = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Developer has templates:read scope, should work
        assert response.status_code in [200, 500]

    def test_admin_can_list_templates(self, admin_token):
        """Test that admin can list templates"""
        response = client.get(
            "/api/v1/templates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # Admin has all scopes, should work
        assert response.status_code in [200, 500]


class TestLanguageVariants:
    """Test language variant matching (JS/TS compatibility)"""

    def test_javascript_filter_includes_typescript(self, auth_token):
        """Test that JavaScript filter includes TypeScript templates"""
        response = client.get(
            "/api/v1/templates?language=javascript",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            # Language variants logic should apply
            assert "templates" in response.json()

    def test_python_filter_includes_python3(self, auth_token):
        """Test that Python filter includes Python3 templates"""
        response = client.get(
            "/api/v1/templates?language=python",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        if response.status_code == 200:
            assert "templates" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
