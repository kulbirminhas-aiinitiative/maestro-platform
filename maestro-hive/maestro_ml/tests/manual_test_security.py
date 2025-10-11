#!/usr/bin/env python3
"""
Manual Test Suite - Security Features
Tests JWT authentication, password hashing, and token blacklist
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_jwt_manager_import():
    """Test 1: JWT Manager import"""
    print("\n🧪 Test 1: JWT Manager Import")
    try:
        from enterprise.auth.jwt_manager import JWTManager
        jwt_manager = JWTManager()
        print(f"  ✅ JWT Manager imported successfully")
        print(f"     Algorithm: {jwt_manager.algorithm}")
        print(f"     Access Token TTL: {jwt_manager.access_token_expire_minutes} minutes")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_jwt_token_creation():
    """Test 2: JWT token creation"""
    print("\n🧪 Test 2: JWT Token Creation")
    try:
        from enterprise.auth.jwt_manager import JWTManager
        
        jwt_manager = JWTManager()
        
        # Create access token
        access_token = jwt_manager.create_access_token(
            data={"sub": "test_user_123", "roles": ["admin"]}
        )
        
        assert access_token is not None
        assert len(access_token) > 50  # JWT tokens are long
        
        print(f"  ✅ JWT token created")
        print(f"     Token length: {len(access_token)} chars")
        print(f"     Token preview: {access_token[:50]}...")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_jwt_token_verification():
    """Test 3: JWT token verification"""
    print("\n🧪 Test 3: JWT Token Verification")
    try:
        from enterprise.auth.jwt_manager import JWTManager
        
        jwt_manager = JWTManager()
        
        # Create and verify token
        access_token = jwt_manager.create_access_token(
            data={"sub": "test_user_456", "roles": ["viewer"]}
        )
        
        payload = jwt_manager.verify_access_token(access_token)
        
        assert payload is not None
        assert payload["sub"] == "test_user_456"
        assert "viewer" in payload.get("roles", [])
        
        print(f"  ✅ JWT token verified")
        print(f"     User ID: {payload['sub']}")
        print(f"     Roles: {payload.get('roles')}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_password_hasher():
    """Test 4: Password hashing"""
    print("\n🧪 Test 4: Password Hashing")
    try:
        from enterprise.auth.password_hasher import PasswordHasher
        
        hasher = PasswordHasher()
        
        # Hash password
        password = "TestPassword123!"
        hashed = hasher.hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt prefix
        
        # Verify password
        is_valid = hasher.verify_password(password, hashed)
        assert is_valid is True
        
        # Verify wrong password
        is_invalid = hasher.verify_password("WrongPassword", hashed)
        assert is_invalid is False
        
        print(f"  ✅ Password hashing working")
        print(f"     Hash length: {len(hashed)} chars")
        print(f"     Hash preview: {hashed[:30]}...")
        print(f"     Correct password: Verified ✅")
        print(f"     Wrong password: Rejected ❌")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_token_pair_creation():
    """Test 5: Token pair creation"""
    print("\n🧪 Test 5: Token Pair Creation")
    try:
        from enterprise.auth.jwt_manager import JWTManager
        
        jwt_manager = JWTManager()
        
        # Create token pair
        tokens = jwt_manager.create_token_pair(user_id="user_789")
        
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert tokens["token_type"] == "bearer"
        
        # Verify both tokens
        access_payload = jwt_manager.verify_access_token(tokens["access_token"])
        refresh_payload = jwt_manager.verify_refresh_token(tokens["refresh_token"])
        
        assert access_payload["sub"] == "user_789"
        assert refresh_payload["sub"] == "user_789"
        
        print(f"  ✅ Token pair created")
        print(f"     Access token: {tokens['access_token'][:50]}...")
        print(f"     Refresh token: {tokens['refresh_token'][:50]}...")
        print(f"     Token type: {tokens['token_type']}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_rbac_integration():
    """Test 6: RBAC integration"""
    print("\n🧪 Test 6: RBAC Integration")
    try:
        from enterprise.rbac.fastapi_integration import get_current_user
        print(f"  ✅ RBAC integration available")
        print(f"     get_current_user function exists")
        print(f"     Ready for FastAPI dependency injection")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 80)
    print("  MAESTRO ML - SECURITY FEATURES TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_jwt_manager_import,
        test_jwt_token_creation,
        test_jwt_token_verification,
        test_password_hasher,
        test_token_pair_creation,
        test_rbac_integration,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    # Summary
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"\n  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}/{total}")
    print(f"  Success Rate: {(passed/total)*100:.1f}%\n")
    
    if passed == total:
        print("  ✅ ALL TESTS PASSED!")
        return 0
    else:
        print("  ❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
