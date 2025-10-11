#!/usr/bin/env python3
"""
Generate Secure Keys for Maestro ML Platform

Generates cryptographically secure random keys for:
- JWT_SECRET_KEY
- JWT_REFRESH_SECRET_KEY  
- SECRET_KEY

Usage:
    python scripts/generate_secure_keys.py

Output:
    Prints keys that can be added to .env file
"""
import secrets


def generate_keys():
    """Generate secure random keys"""
    
    print("=" * 70)
    print("MAESTRO ML - SECURE KEY GENERATION")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT: These keys are cryptographically secure.")
    print("    Store them safely and never commit to version control!")
    print()
    print("=" * 70)
    print()
    
    # Generate keys
    jwt_secret = secrets.token_urlsafe(64)
    jwt_refresh_secret = secrets.token_urlsafe(64)
    app_secret = secrets.token_urlsafe(32)
    
    # Print keys
    print("# Add these to your .env file:")
    print()
    print(f"JWT_SECRET_KEY={jwt_secret}")
    print(f"JWT_REFRESH_SECRET_KEY={jwt_refresh_secret}")
    print(f"SECRET_KEY={app_secret}")
    print()
    print("=" * 70)
    print()
    print("✅ Keys generated successfully!")
    print()
    print("Next steps:")
    print("  1. Copy the keys above to your .env file")
    print("  2. Restart the API server")
    print("  3. Verify authentication still works")
    print("  4. NEVER commit .env to git!")
    print()


if __name__ == "__main__":
    generate_keys()
