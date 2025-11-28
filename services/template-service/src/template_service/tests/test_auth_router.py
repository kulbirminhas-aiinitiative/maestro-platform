"""
Tests for Authentication Router
Tests JWT/OAuth2 authentication endpoints
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import jwt

# Import the FastAPI app
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from auth import SECRET_KEY, ALGORITHM, create_access_token

client = TestClient(app)


class TestAuthenticationEndpoints:
    """Test authentication endpoints"""

    def test_health_endpoint_no_auth_required(self):
        """Health endpoint should not require authentication"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_login_with_oauth2_token_endpoint_success(self):
        """Test successful login via OAuth2 token endpoint"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800  # 30 minutes

    def test_login_with_json_endpoint_success(self):
        """Test successful login via JSON endpoint"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "developer", "password": "dev123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "wrong_password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_login_with_nonexistent_user(self):
        """Test login with nonexistent user"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "nonexistent", "password": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 401

    def test_get_current_user_with_valid_token(self):
        """Test getting current user info with valid token"""
        # First, login to get token
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]

        # Then, get current user
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "developer"
        assert data["email"] == "dev@maestro-platform.com"
        assert "templates:read" in data["scopes"]
        assert "templates:write" in data["scopes"]
        assert data["is_admin"] is False

    def test_get_current_user_without_token(self):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401  # Unauthorized without auth header

    def test_get_current_user_with_invalid_token(self):
        """Test getting current user with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 401

    def test_get_current_user_with_expired_token(self):
        """Test getting current user with expired token"""
        # Create an expired token
        expired_token = create_access_token(
            data={"sub": "developer", "email": "dev@maestro-platform.com", "scopes": []},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    def test_refresh_token_endpoint(self):
        """Test token refresh endpoint"""
        # Login first
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        old_token = login_response.json()["access_token"]

        # Wait a second to ensure different iat timestamp
        import time
        time.sleep(1)

        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {old_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        # Note: Token might be same if iat rounds to same second, but endpoint works
        assert data["token_type"] == "bearer"

    def test_logout_endpoint(self):
        """Test logout endpoint"""
        # Login first
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"
        assert data["username"] == "developer"


class TestAdminPrivileges:
    """Test admin-specific functionality"""

    def test_admin_login(self):
        """Test admin user can login"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Verify admin status
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.json()["is_admin"] is True
        assert "admin" in me_response.json()["scopes"]

    def test_viewer_has_limited_scopes(self):
        """Test viewer user has read-only scopes"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "viewer", "password": "viewer123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        assert response.status_code == 200
        token = response.json()["access_token"]

        # Verify viewer scopes
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        data = me_response.json()
        assert data["is_admin"] is False
        assert data["scopes"] == ["templates:read"]
        assert "templates:write" not in data["scopes"]


class TestJWTTokenValidation:
    """Test JWT token validation"""

    def test_token_contains_correct_claims(self):
        """Test that JWT token contains correct claims"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        token = response.json()["access_token"]

        # Decode token (without verification for testing)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == "developer"
        assert payload["email"] == "dev@maestro-platform.com"
        assert "templates:read" in payload["scopes"]
        assert "templates:write" in payload["scopes"]
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_token_expiration_time(self):
        """Test token expiration is set correctly"""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "developer", "password": "dev123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        token = response.json()["access_token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        exp_time = datetime.fromtimestamp(payload["exp"])
        iat_time = datetime.fromtimestamp(payload["iat"])

        # Should expire in approximately 30 minutes
        time_diff = (exp_time - iat_time).total_seconds()
        assert 1790 <= time_diff <= 1810  # Allow small variance


class TestDevUserCreation:
    """Test dev user creation endpoint (should be hidden in prod)"""

    def test_dev_create_user_endpoint_exists(self):
        """Test that dev user creation endpoint exists"""
        # This endpoint should exist but be hidden from docs
        response = client.post(
            "/api/v1/auth/dev/create-user",
            params={
                "username": "testuser",
                "password": "testpass123",
                "email": "test@example.com",
                "is_admin": False
            }
        )

        # Should either succeed or fail auth, but endpoint should exist
        assert response.status_code in [200, 401, 400]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
