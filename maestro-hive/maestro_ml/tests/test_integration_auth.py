#!/usr/bin/env python3
"""
Integration tests for authentication flow

Tests the complete authentication system end-to-end:
- User registration
- Login
- Token refresh
- Protected route access
- Logout
"""
import pytest
import asyncio
from httpx import AsyncClient
import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment before importing app
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://maestro:maestro@localhost:15432/maestro_ml"

from maestro_ml.api.main import app


class TestAuthenticationFlow:
    """Test complete authentication flow"""
    
    @pytest.mark.asyncio
    async def test_01_health_check(self):
        """Test that API is running"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["app"] == "Maestro ML Platform"
            assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_02_register_new_user(self):
        """Test user registration"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "integration_test@example.com",
                    "password": "testpassword123",
                    "name": "Integration Test User",
                    "role": "viewer"
                }
            )
            
            assert response.status_code == 201
            data = response.json()
            
            # Verify response structure
            assert "access_token" in data
            assert "refresh_token" in data
            assert "user" in data
            assert data["user"]["email"] == "integration_test@example.com"
            assert data["user"]["name"] == "Integration Test User"
            assert data["user"]["role"] == "viewer"
            
            # Save token for next tests
            pytest.auth_token = data["access_token"]
            pytest.refresh_token = data["refresh_token"]
            pytest.user_id = data["user"]["user_id"]
    
    @pytest.mark.asyncio
    async def test_03_login_with_credentials(self):
        """Test login with email and password"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "integration_test@example.com",
                    "password": "testpassword123"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["user"]["email"] == "integration_test@example.com"
            
            # Update token
            pytest.auth_token = data["access_token"]
    
    @pytest.mark.asyncio
    async def test_04_get_current_user(self):
        """Test getting current user info"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {pytest.auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["email"] == "integration_test@example.com"
            assert data["name"] == "Integration Test User"
            assert data["role"] == "viewer"
            assert data["user_id"] == pytest.user_id
    
    @pytest.mark.asyncio
    async def test_05_access_protected_route_without_auth(self):
        """Test that protected routes reject requests without auth"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/projects",
                json={
                    "name": "Test Project",
                    "problem_class": "classification",
                    "complexity_score": 50,
                    "team_size": 1,
                    "metadata": {}
                }
            )
            
            assert response.status_code == 403
            assert "Not authenticated" in response.text
    
    @pytest.mark.asyncio
    async def test_06_access_protected_route_with_auth(self):
        """Test that protected routes work with valid auth"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {pytest.auth_token}"}
            )
            
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_07_refresh_token(self):
        """Test token refresh"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                headers={"Authorization": f"Bearer {pytest.refresh_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "access_token" in data
            assert "refresh_token" in data
            
            # New tokens should be different
            new_access_token = data["access_token"]
            assert new_access_token != pytest.auth_token
    
    @pytest.mark.asyncio
    async def test_08_login_with_wrong_password(self):
        """Test that login fails with wrong password"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "integration_test@example.com",
                    "password": "wrongpassword"
                }
            )
            
            assert response.status_code == 401
            assert "Invalid email or password" in response.text
    
    @pytest.mark.asyncio
    async def test_09_logout(self):
        """Test logout (token revocation)"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {pytest.auth_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Successfully logged out"
    
    @pytest.mark.asyncio
    async def test_10_access_with_revoked_token(self):
        """Test that revoked tokens don't work"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {pytest.auth_token}"}
            )
            
            # Should fail because token is revoked
            assert response.status_code == 401


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
