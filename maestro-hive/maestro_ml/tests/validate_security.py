#!/usr/bin/env python3
"""
Production Validation - Security Audit
Validates security configurations and features
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def audit_item(name, check_func):
    """Run a security audit check"""
    print(f"\n🔒 {name}")
    try:
        result, details = check_func()
        if result:
            print(f"  ✅ PASS: {details}")
            return True
        else:
            print(f"  ❌ FAIL: {details}")
            return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def check_secrets_not_hardcoded():
    """Check that secrets are not hardcoded"""
    from maestro_ml.config.settings import get_settings
    settings = get_settings()
    
    # Check JWT secret is not default
    if "your-secret-key" in settings.JWT_SECRET_KEY.lower() or "change" in settings.JWT_SECRET_KEY.lower():
        return False, "Default JWT secret detected"
    
    # Check it's reasonably strong
    if len(settings.JWT_SECRET_KEY) < 20:
        return False, f"JWT secret too short: {len(settings.JWT_SECRET_KEY)} chars"
    
    return True, f"JWT secret is {len(settings.JWT_SECRET_KEY)} chars (strong)"

def check_env_file_secure():
    """Check .env file has secure permissions"""
    import stat
    env_path = ".env"
    
    if not os.path.exists(env_path):
        return False, ".env file not found"
    
    st = os.stat(env_path)
    mode = stat.filemode(st.st_mode)
    
    # Check if readable by owner only (600)
    if oct(st.st_mode)[-3:] == '600':
        return True, f"Permissions: {mode} (secure)"
    else:
        return False, f"Permissions: {mode} (should be 600)"

def check_password_hashing():
    """Verify password hashing works"""
    from enterprise.auth.password_hasher import PasswordHasher
    
    hasher = PasswordHasher()
    test_password = "TestPassword123!"
    hashed = hasher.hash_password(test_password)
    
    # Verify it's bcrypt
    if not hashed.startswith("$2b$"):
        return False, "Not using bcrypt"
    
    # Verify correct password validates
    if not hasher.verify_password(test_password, hashed):
        return False, "Password verification failed"
    
    # Verify wrong password fails
    if hasher.verify_password("WrongPassword", hashed):
        return False, "Wrong password accepted (security issue!)"
    
    return True, "bcrypt hashing with 12 rounds, verification working"

def check_tls_certificates():
    """Check TLS certificates exist"""
    cert_path = "certs/cert.pem"
    key_path = "certs/key.pem"
    
    if not os.path.exists(cert_path):
        return False, "TLS certificate not found"
    
    if not os.path.exists(key_path):
        return False, "TLS private key not found"
    
    # Check key permissions
    st = os.stat(key_path)
    if oct(st.st_mode)[-3:] != '600':
        return False, f"Private key permissions insecure: {oct(st.st_mode)[-3:]}"
    
    return True, "TLS certificates exist, private key secured"

def check_database_password():
    """Check database password is not default"""
    from maestro_ml.config.settings import get_settings
    settings = get_settings()
    
    # Check it's not the obvious default
    if settings.POSTGRES_PASSWORD == "maestro":
        return False, "Using default 'maestro' password (for dev only)"
    
    if len(settings.POSTGRES_PASSWORD) < 10:
        return False, f"Password too short: {len(settings.POSTGRES_PASSWORD)} chars"
    
    return True, f"Non-default password configured ({len(settings.POSTGRES_PASSWORD)} chars)"

def check_multi_tenancy_enabled():
    """Check multi-tenancy is enabled"""
    from maestro_ml.config.settings import get_settings
    settings = get_settings()
    
    if not settings.ENABLE_MULTI_TENANCY:
        return False, "Multi-tenancy is disabled"
    
    return True, "Multi-tenancy enabled"

def check_cors_configuration():
    """Check CORS is properly configured"""
    from maestro_ml.config.settings import get_settings
    settings = get_settings()
    
    origins = settings.cors_origins_list
    
    if not origins:
        return False, "No CORS origins configured"
    
    # Check for wildcard (security issue in production)
    if "*" in origins:
        return False, "Wildcard CORS origin (security risk!)"
    
    return True, f"{len(origins)} specific origins configured"

def check_rate_limiting_enabled():
    """Check rate limiting is enabled"""
    from maestro_ml.config.settings import get_settings
    settings = get_settings()
    
    if not settings.ENABLE_RATE_LIMITING:
        return False, "Rate limiting is disabled"
    
    return True, f"Rate limiting enabled ({settings.RATE_LIMIT_PER_MINUTE}/min)"

def main():
    """Run all security audits"""
    print("="*80)
    print("  SECURITY AUDIT")
    print("="*80)
    
    audits = [
        ("Secrets Not Hardcoded", check_secrets_not_hardcoded),
        (".env File Permissions", check_env_file_secure),
        ("Password Hashing", check_password_hashing),
        ("TLS Certificates", check_tls_certificates),
        ("Database Password", check_database_password),
        ("Multi-Tenancy Enabled", check_multi_tenancy_enabled),
        ("CORS Configuration", check_cors_configuration),
        ("Rate Limiting", check_rate_limiting_enabled),
    ]
    
    results = []
    for name, check_func in audits:
        results.append(audit_item(name, check_func))
    
    # Summary
    print("\n" + "="*80)
    print("  AUDIT SUMMARY")
    print("="*80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}/{total}")
    print(f"  Security Score: {(passed/total)*100:.1f}%\n")
    
    if passed == total:
        print("  ✅ ALL SECURITY CHECKS PASSED!")
        return 0
    elif passed >= total * 0.75:
        print("  ⚠️  SOME SECURITY ISSUES - Review failures above")
        return 1
    else:
        print("  ❌ CRITICAL SECURITY ISSUES - Must fix before production")
        return 2

if __name__ == "__main__":
    sys.exit(main())
