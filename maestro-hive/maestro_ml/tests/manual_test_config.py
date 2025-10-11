#!/usr/bin/env python3
"""
Manual Test Suite - Configuration & Settings
Tests settings loading, environment variables, and configuration
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_settings_import():
    """Test 1: Basic settings import"""
    print("\n🧪 Test 1: Settings Import")
    try:
        from maestro_ml.config.settings import get_settings
        settings = get_settings()
        assert settings is not None
        print(f"  ✅ Settings loaded successfully")
        print(f"     Environment: {settings.ENVIRONMENT}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_jwt_configuration():
    """Test 2: JWT configuration"""
    print("\n🧪 Test 2: JWT Configuration")
    try:
        from maestro_ml.config.settings import get_settings
        settings = get_settings()
        
        assert len(settings.JWT_SECRET_KEY) > 20, "JWT secret too short"
        assert len(settings.JWT_REFRESH_SECRET_KEY) > 20, "JWT refresh secret too short"
        assert settings.JWT_ALGORITHM == "HS256", "Wrong JWT algorithm"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15, "Wrong token expiry"
        
        print(f"  ✅ JWT configuration valid")
        print(f"     Secret Key Length: {len(settings.JWT_SECRET_KEY)} chars")
        print(f"     Algorithm: {settings.JWT_ALGORITHM}")
        print(f"     Access Token TTL: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
        print(f"     Refresh Token TTL: {settings.REFRESH_TOKEN_EXPIRE_DAYS} days")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_database_configuration():
    """Test 3: Database configuration"""
    print("\n🧪 Test 3: Database Configuration")
    try:
        from maestro_ml.config.settings import get_settings
        settings = get_settings()
        
        assert settings.DATABASE_URL is not None
        assert "postgresql" in settings.DATABASE_URL or "sqlite" in settings.DATABASE_URL
        assert settings.POSTGRES_USER == "maestro"
        assert len(settings.POSTGRES_PASSWORD) > 10
        
        print(f"  ✅ Database configuration valid")
        print(f"     Database URL: {settings.DATABASE_URL[:50]}...")
        print(f"     User: {settings.POSTGRES_USER}")
        print(f"     Password Length: {len(settings.POSTGRES_PASSWORD)} chars")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_feature_flags():
    """Test 4: Feature flags"""
    print("\n🧪 Test 4: Feature Flags")
    try:
        from maestro_ml.config.settings import get_settings
        settings = get_settings()
        
        assert settings.ENABLE_MULTI_TENANCY is True
        assert settings.ENABLE_AUDIT_LOGGING is True
        assert settings.ENABLE_RATE_LIMITING is True
        
        print(f"  ✅ Feature flags configured")
        print(f"     Multi-tenancy: {settings.ENABLE_MULTI_TENANCY}")
        print(f"     Audit Logging: {settings.ENABLE_AUDIT_LOGGING}")
        print(f"     Rate Limiting: {settings.ENABLE_RATE_LIMITING}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_cors_configuration():
    """Test 5: CORS configuration"""
    print("\n🧪 Test 5: CORS Configuration")
    try:
        from maestro_ml.config.settings import get_settings
        settings = get_settings()
        
        origins = settings.cors_origins_list
        assert len(origins) > 0, "No CORS origins configured"
        assert any("localhost" in origin for origin in origins), "No localhost in CORS"
        
        print(f"  ✅ CORS configuration valid")
        print(f"     Origins: {', '.join(origins)}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def test_encryption_keys():
    """Test 6: Encryption keys"""
    print("\n🧪 Test 6: Encryption Keys")
    try:
        from maestro_ml.config.settings import get_settings
        settings = get_settings()
        
        assert len(settings.ENCRYPTION_KEY) > 20
        assert len(settings.API_SECRET_KEY) > 20
        
        print(f"  ✅ Encryption keys configured")
        print(f"     Encryption Key: {len(settings.ENCRYPTION_KEY)} chars")
        print(f"     API Secret Key: {len(settings.API_SECRET_KEY)} chars")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 80)
    print("  MAESTRO ML - CONFIGURATION TEST SUITE")
    print("=" * 80)
    
    tests = [
        test_settings_import,
        test_jwt_configuration,
        test_database_configuration,
        test_feature_flags,
        test_cors_configuration,
        test_encryption_keys,
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
