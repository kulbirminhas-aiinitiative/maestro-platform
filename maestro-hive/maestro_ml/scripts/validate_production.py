#!/usr/bin/env python3
"""
Production Environment Validation

Validates that critical security configurations are set before starting
the application in production mode.

Checks:
- JWT secret keys are not defaults
- Database passwords are not defaults
- Required environment variables are set
- Security settings are production-appropriate
"""
import os
import sys
from typing import List, Tuple


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_jwt_secrets() -> List[Tuple[str, str]]:
    """Validate JWT secret keys are not insecure defaults"""
    errors = []
    
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    jwt_refresh = os.getenv("JWT_REFRESH_SECRET_KEY", "")
    secret_key = os.getenv("SECRET_KEY", "")
    
    # Check for insecure defaults
    insecure_values = [
        "your-jwt-secret-key",
        "your-secret-key",
        "your-jwt-secret",
        "your-secret-key-change-in-production",
        "CHANGEME",
        "",
    ]
    
    if any(insecure in jwt_secret for insecure in insecure_values):
        errors.append(("JWT_SECRET_KEY", "Using insecure default value!"))
    
    if any(insecure in jwt_refresh for insecure in insecure_values):
        errors.append(("JWT_REFRESH_SECRET_KEY", "Using insecure default value!"))
    
    if any(insecure in secret_key for insecure in insecure_values):
        errors.append(("SECRET_KEY", "Using insecure default value!"))
    
    # Check minimum length
    if len(jwt_secret) < 32:
        errors.append(("JWT_SECRET_KEY", f"Too short ({len(jwt_secret)} chars, need 32+)"))
    
    if len(jwt_refresh) < 32:
        errors.append(("JWT_REFRESH_SECRET_KEY", f"Too short ({len(jwt_refresh)} chars, need 32+)"))
    
    if len(secret_key) < 16:
        errors.append(("SECRET_KEY", f"Too short ({len(secret_key)} chars, need 16+)"))
    
    return errors


def validate_database() -> List[Tuple[str, str]]:
    """Validate database configuration"""
    errors = []
    
    db_url = os.getenv("DATABASE_URL", "")
    
    # Check for default passwords
    if "maestro:maestro@" in db_url:
        errors.append(("DATABASE_URL", "Using default password 'maestro'!"))
    
    if not db_url:
        errors.append(("DATABASE_URL", "Not configured!"))
    
    return errors


def validate_environment() -> List[Tuple[str, str]]:
    """Validate environment settings"""
    errors = []
    
    env = os.getenv("ENVIRONMENT", "development")
    debug = os.getenv("DEBUG", "false").lower()
    
    if env == "production" and debug == "true":
        errors.append(("DEBUG", "Should be 'false' in production!"))
    
    return errors


def validate_required_vars() -> List[Tuple[str, str]]:
    """Check all required environment variables are set"""
    errors = []
    
    required = [
        "DATABASE_URL",
        "REDIS_URL",
        "JWT_SECRET_KEY",
        "JWT_REFRESH_SECRET_KEY",
        "SECRET_KEY",
    ]
    
    for var in required:
        if not os.getenv(var):
            errors.append((var, "Not set!"))
    
    return errors


def run_validation(fail_fast: bool = True) -> bool:
    """Run all validations"""
    
    all_errors = []
    
    # Run all checks
    all_errors.extend(validate_jwt_secrets())
    all_errors.extend(validate_database())
    all_errors.extend(validate_environment())
    all_errors.extend(validate_required_vars())
    
    # Report results
    if all_errors:
        print("=" * 70)
        print("🔴 PRODUCTION VALIDATION FAILED")
        print("=" * 70)
        print()
        print(f"Found {len(all_errors)} critical security issues:")
        print()
        
        for var, error in all_errors:
            print(f"  ❌ {var}: {error}")
        
        print()
        print("=" * 70)
        print()
        print("Actions required:")
        print("  1. Run: python scripts/generate_secure_keys.py")
        print("  2. Update .env with generated keys")
        print("  3. Change default database passwords")
        print("  4. Set ENVIRONMENT=production")
        print("  5. Set DEBUG=false")
        print()
        
        if fail_fast:
            sys.exit(1)
        
        return False
    
    else:
        print("=" * 70)
        print("✅ PRODUCTION VALIDATION PASSED")
        print("=" * 70)
        print()
        print("All security checks passed! Safe to deploy.")
        print()
        return True


if __name__ == "__main__":
    # Only validate in production
    env = os.getenv("ENVIRONMENT", "development")
    
    if env == "production":
        run_validation(fail_fast=True)
    else:
        print(f"Skipping validation (ENVIRONMENT={env})")
        print("Set ENVIRONMENT=production to enable validation")
