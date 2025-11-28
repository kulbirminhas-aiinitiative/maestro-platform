# Security Recommendations
## User Management REST API - Implementation Guidance

**Project:** User Management REST API
**Phase:** Design
**Document Date:** 2025-10-12
**Security Specialist:** Security Specialist
**Workflow ID:** workflow-20251012-130125
**Classification:** CONFIDENTIAL

---

## Executive Summary

This document provides comprehensive security recommendations for implementing a secure user management REST API. These recommendations are based on industry best practices, OWASP guidelines, and security audit findings.

**Purpose:** Guide the development team in implementing security controls that protect user data, prevent unauthorized access, and ensure system resilience against attacks.

**Priority:** All CRITICAL and HIGH priority recommendations must be implemented before production deployment.

---

## Table of Contents

1. [Authentication Security](#1-authentication-security)
2. [Authorization & Access Control](#2-authorization--access-control)
3. [Password Management](#3-password-management)
4. [Input Validation & Sanitization](#4-input-validation--sanitization)
5. [API Security](#5-api-security)
6. [Data Protection](#6-data-protection)
7. [Rate Limiting & DoS Protection](#7-rate-limiting--dos-protection)
8. [Session Management](#8-session-management)
9. [Error Handling & Logging](#9-error-handling--logging)
10. [Security Monitoring & Incident Response](#10-security-monitoring--incident-response)
11. [Infrastructure Security](#11-infrastructure-security)
12. [Compliance & Privacy](#12-compliance--privacy)
13. [Security Testing](#13-security-testing)
14. [Secure Development Practices](#14-secure-development-practices)

---

## 1. Authentication Security

### 1.1 Implement JWT-Based Authentication

**Priority:** CRITICAL

**Recommendation:**
Implement JSON Web Token (JWT) authentication with access tokens and refresh tokens.

**Implementation Guidelines:**

```python
# JWT Configuration
JWT_ALGORITHM = "RS256"  # Use asymmetric encryption
JWT_ACCESS_TOKEN_EXPIRES = 15  # 15 minutes
JWT_REFRESH_TOKEN_EXPIRES = 7  # 7 days

# Token Structure
{
  "sub": "user_id",  # Subject (user identifier)
  "exp": 1234567890,  # Expiration timestamp
  "iat": 1234567000,  # Issued at timestamp
  "jti": "unique_token_id",  # JWT ID for revocation
  "type": "access",  # Token type
  "scope": ["read:user", "write:user"]  # Permissions
}
```

**Security Requirements:**
- Use RS256 (RSA Signature with SHA-256) for signing
- Short-lived access tokens (15-30 minutes)
- Longer-lived refresh tokens (7-30 days)
- Store private keys securely (HSM, Key Vault, or encrypted storage)
- Implement token revocation mechanism
- Use secure random for token generation

**Example Implementation:**
```python
from datetime import datetime, timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

class TokenManager:
    def __init__(self, private_key_path, public_key_path):
        with open(private_key_path, 'rb') as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )
        with open(public_key_path, 'rb') as f:
            self.public_key = serialization.load_pem_public_key(
                f.read(), backend=default_backend()
            )

    def create_access_token(self, user_id, scopes):
        payload = {
            'sub': str(user_id),
            'exp': datetime.utcnow() + timedelta(minutes=15),
            'iat': datetime.utcnow(),
            'jti': secrets.token_urlsafe(32),
            'type': 'access',
            'scope': scopes
        }
        return jwt.encode(payload, self.private_key, algorithm='RS256')

    def verify_token(self, token):
        try:
            payload = jwt.decode(token, self.public_key, algorithms=['RS256'])
            # Check if token is revoked (check against revocation list)
            if self.is_token_revoked(payload['jti']):
                raise InvalidTokenError("Token has been revoked")
            return payload
        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("Token has expired")
        except jwt.InvalidTokenError:
            raise InvalidTokenError("Invalid token")
```

**Benefits:**
- Stateless authentication (no server-side session storage)
- Scalable across multiple servers
- Contains user information and permissions
- Can be verified without database lookup

**Risks Mitigated:**
- Session hijacking
- Unauthorized access
- Replay attacks (via jti and expiration)

---

### 1.2 Implement Secure Login Endpoint

**Priority:** CRITICAL

**Recommendation:**
Design secure authentication endpoint with proper error handling and security controls.

**API Endpoint Design:**
```
POST /api/v1/auth/login
Content-Type: application/json

Request:
{
  "username": "user@example.com",
  "password": "SecurePassword123!",
  "mfa_code": "123456"  // Optional, if MFA enabled
}

Response (Success):
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 900  // 15 minutes in seconds
}

Response (Failure):
{
  "error": "invalid_credentials",
  "error_description": "Invalid username or password"
}
```

**Security Controls:**
1. **Generic Error Messages:** Don't reveal if username exists
2. **Rate Limiting:** 5 attempts per 15 minutes per IP
3. **Account Lockout:** After 5 failed attempts, lock for 15 minutes
4. **Timing Attack Prevention:** Use constant-time password comparison
5. **IP Logging:** Log all login attempts with IP addresses
6. **CAPTCHA:** Trigger after 3 failed attempts

**Example Implementation:**
```python
from werkzeug.security import check_password_hash
import secrets
import time

@app.route('/api/v1/auth/login', methods=['POST'])
@rate_limit(limit=5, period=900)  # 5 requests per 15 minutes
def login():
    data = request.get_json()

    # Validate input
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'invalid_credentials',
                       'error_description': 'Invalid username or password'}), 401

    # Check if IP is blocked
    if is_ip_blocked(request.remote_addr):
        log_security_event('blocked_ip_login_attempt', username, request.remote_addr)
        return jsonify({'error': 'too_many_attempts',
                       'error_description': 'Too many failed attempts. Try again later.'}), 429

    # Retrieve user
    user = User.query.filter_by(username=username).first()

    # Constant-time comparison (prevent timing attacks)
    if user:
        password_valid = check_password_hash(user.password_hash, password)
    else:
        # Perform dummy hash to maintain constant time
        check_password_hash('$2b$12$dummy_hash', password)
        password_valid = False

    if not user or not password_valid:
        # Increment failed login attempts
        increment_failed_login(username, request.remote_addr)

        # Check if account should be locked
        if get_failed_login_count(username) >= 5:
            lock_account(username, duration_minutes=15)
            log_security_event('account_locked', username, request.remote_addr)

        log_security_event('failed_login', username, request.remote_addr)
        return jsonify({'error': 'invalid_credentials',
                       'error_description': 'Invalid username or password'}), 401

    # Check if account is locked
    if user.is_locked():
        log_security_event('locked_account_login_attempt', username, request.remote_addr)
        return jsonify({'error': 'account_locked',
                       'error_description': 'Account is temporarily locked. Try again later.'}), 403

    # Check if MFA is required
    if user.mfa_enabled:
        mfa_code = data.get('mfa_code')
        if not mfa_code or not verify_mfa_code(user, mfa_code):
            log_security_event('failed_mfa', username, request.remote_addr)
            return jsonify({'error': 'invalid_mfa',
                           'error_description': 'Invalid MFA code'}), 401

    # Generate tokens
    access_token = token_manager.create_access_token(user.id, user.get_scopes())
    refresh_token = token_manager.create_refresh_token(user.id)

    # Reset failed login attempts
    reset_failed_login_count(username)

    # Update last login
    user.last_login = datetime.utcnow()
    user.last_login_ip = request.remote_addr
    db.session.commit()

    # Log successful login
    log_security_event('successful_login', username, request.remote_addr)

    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': 900
    }), 200
```

**Testing Requirements:**
- Test with valid credentials
- Test with invalid username
- Test with invalid password
- Test rate limiting (6th attempt should be blocked)
- Test account lockout (5 failed attempts)
- Test constant-time comparison (timing attack resistance)
- Test MFA flow

---

### 1.3 Implement Multi-Factor Authentication (MFA)

**Priority:** HIGH

**Recommendation:**
Implement TOTP-based MFA for enhanced security, especially for administrative accounts.

**Implementation Options:**

**Option 1: TOTP (Time-Based One-Time Password) - RECOMMENDED**
```python
import pyotp
import qrcode
from io import BytesIO

class MFAManager:
    @staticmethod
    def generate_secret():
        """Generate a secret key for TOTP"""
        return pyotp.random_base32()

    @staticmethod
    def generate_qr_code(user, secret):
        """Generate QR code for authenticator app"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.email,
            issuer_name="User Management API"
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        return img

    @staticmethod
    def verify_code(secret, code):
        """Verify TOTP code"""
        totp = pyotp.TOTP(secret)
        # Allow 1 time step before and after (30 seconds window)
        return totp.verify(code, valid_window=1)

# Enrollment endpoint
@app.route('/api/v1/users/me/mfa/enable', methods=['POST'])
@require_auth
def enable_mfa():
    user = get_current_user()

    # Generate secret
    secret = MFAManager.generate_secret()

    # Store secret (encrypted)
    user.mfa_secret = encrypt(secret)
    db.session.commit()

    # Generate QR code
    qr_image = MFAManager.generate_qr_code(user, secret)

    # Return QR code and backup codes
    backup_codes = generate_backup_codes(user)

    return jsonify({
        'qr_code': encode_image_base64(qr_image),
        'secret': secret,  # For manual entry
        'backup_codes': backup_codes
    }), 200

# Verification endpoint
@app.route('/api/v1/users/me/mfa/verify', methods=['POST'])
@require_auth
def verify_mfa_enrollment():
    user = get_current_user()
    code = request.json.get('code')

    secret = decrypt(user.mfa_secret)
    if MFAManager.verify_code(secret, code):
        user.mfa_enabled = True
        db.session.commit()
        log_security_event('mfa_enabled', user.username, request.remote_addr)
        return jsonify({'message': 'MFA enabled successfully'}), 200
    else:
        return jsonify({'error': 'Invalid code'}), 400
```

**Option 2: SMS/Email Codes - ACCEPTABLE**
```python
def send_mfa_code(user, method='sms'):
    """Send one-time code via SMS or email"""
    code = f"{secrets.randbelow(1000000):06d}"  # 6-digit code

    # Store code with expiration
    redis_client.setex(
        f"mfa_code:{user.id}",
        300,  # 5 minutes expiration
        code
    )

    if method == 'sms':
        send_sms(user.phone_number, f"Your verification code is: {code}")
    else:
        send_email(user.email, "Verification Code", f"Your code is: {code}")

    log_security_event('mfa_code_sent', user.username, request.remote_addr)
```

**MFA Policy Recommendations:**
- **Mandatory for Admins:** All administrative accounts must use MFA
- **Optional for Users:** Encourage but don't mandate for regular users
- **Backup Codes:** Provide 10 one-time backup codes
- **Recovery Process:** Secure account recovery if MFA device is lost

**Benefits:**
- Significantly reduces account takeover risk
- Protects against password compromise
- Industry best practice for sensitive operations

---

## 2. Authorization & Access Control

### 2.1 Implement Role-Based Access Control (RBAC)

**Priority:** CRITICAL

**Recommendation:**
Implement a robust RBAC system with clearly defined roles and permissions.

**Role Definitions:**

```python
# Database schema
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    permissions = db.relationship('Permission', secondary='role_permissions')

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    resource = db.Column(db.String(50))  # e.g., 'user'
    action = db.Column(db.String(50))     # e.g., 'read', 'write', 'delete'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role')

# Predefined roles
ROLES = {
    'admin': {
        'description': 'Full system access',
        'permissions': [
            'user:read', 'user:write', 'user:delete',
            'admin:read', 'admin:write',
            'audit:read'
        ]
    },
    'user': {
        'description': 'Standard user',
        'permissions': [
            'user:read_own', 'user:write_own'
        ]
    },
    'read_only': {
        'description': 'Read-only access',
        'permissions': [
            'user:read_own'
        ]
    }
}
```

**Authorization Decorator:**
```python
from functools import wraps
from flask import request, jsonify

def require_permission(permission):
    """Decorator to check if user has required permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get current user from token
            token = extract_token_from_request(request)
            user = get_user_from_token(token)

            if not user:
                return jsonify({'error': 'unauthorized'}), 401

            # Check permission
            if not user.has_permission(permission):
                log_security_event('authorization_failure', user.username,
                                 request.remote_addr, {'permission': permission})
                return jsonify({'error': 'forbidden',
                              'message': 'Insufficient permissions'}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Usage
@app.route('/api/v1/users', methods=['GET'])
@require_permission('user:read')
def list_users():
    # Implementation
    pass
```

**Resource-Level Authorization:**
```python
def check_resource_ownership(user_id, resource_user_id):
    """Check if user owns the resource or is admin"""
    current_user = get_current_user()

    # Admins can access all resources
    if current_user.has_permission('admin:read'):
        return True

    # Users can only access their own resources
    if current_user.id == resource_user_id:
        return True

    return False

@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    current_user = get_current_user()

    # Authorization check
    if not check_resource_ownership(current_user.id, user_id):
        log_security_event('unauthorized_access_attempt', current_user.username,
                         request.remote_addr, {'target_user_id': user_id})
        return jsonify({'error': 'forbidden'}), 403

    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200
```

**Best Practices:**
- **Principle of Least Privilege:** Grant minimum permissions needed
- **Separation of Duties:** No single user should have complete control
- **Default Deny:** Access is denied unless explicitly granted
- **Audit All Authorization Decisions:** Log both successes and failures

---

### 2.2 Prevent Insecure Direct Object References (IDOR)

**Priority:** CRITICAL

**Recommendation:**
Implement authorization checks on all resource access to prevent IDOR vulnerabilities.

**Anti-Pattern (VULNERABLE):**
```python
# BAD - No authorization check
@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200
# Vulnerability: Any authenticated user can access any user_id
```

**Secure Pattern:**
```python
# GOOD - With authorization check
@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    current_user = get_current_user()

    # Critical authorization check
    if current_user.id != user_id and not current_user.is_admin:
        log_security_event('idor_attempt', current_user.username,
                         request.remote_addr, {'target_user_id': user_id})
        return jsonify({'error': 'forbidden'}), 403

    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200
```

**Alternative: Use UUIDs Instead of Sequential IDs:**
```python
import uuid

class User(db.Model):
    # Use UUID instead of integer
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), unique=True, nullable=False)

# API endpoint
@app.route('/api/v1/users/<uuid:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    current_user = get_current_user()

    # Still need authorization check
    if str(current_user.id) != str(user_id) and not current_user.is_admin:
        return jsonify({'error': 'forbidden'}), 403

    user = User.query.get_or_404(str(user_id))
    return jsonify(user.to_dict()), 200
```

**Benefits of UUIDs:**
- Non-sequential (harder to enumerate)
- Globally unique
- No information leakage about user count

**Authorization Checklist:**
- [ ] Every GET request checks user owns resource
- [ ] Every PUT/PATCH request checks user can modify resource
- [ ] Every DELETE request checks user can delete resource
- [ ] Admin bypass is explicitly coded and logged
- [ ] Authorization failures are logged

---

## 3. Password Management

### 3.1 Implement Secure Password Hashing

**Priority:** CRITICAL

**Recommendation:**
Use Argon2id for password hashing (current industry standard).

**Implementation:**
```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

class PasswordManager:
    def __init__(self):
        # Argon2id configuration
        self.ph = PasswordHasher(
            time_cost=3,          # Number of iterations
            memory_cost=65536,    # 64 MB memory usage
            parallelism=4,        # Number of parallel threads
            hash_len=32,          # Length of hash
            salt_len=16           # Length of random salt
        )

    def hash_password(self, password):
        """Hash password using Argon2id"""
        return self.ph.hash(password)

    def verify_password(self, password_hash, password):
        """Verify password against hash"""
        try:
            self.ph.verify(password_hash, password)

            # Check if rehashing is needed (parameters changed)
            if self.ph.check_needs_rehash(password_hash):
                return True, self.hash_password(password)

            return True, None
        except VerifyMismatchError:
            return False, None

# Usage in user registration
@app.route('/api/v1/users', methods=['POST'])
def register_user():
    data = request.get_json()
    password = data.get('password')

    # Validate password strength
    if not is_password_strong(password):
        return jsonify({'error': 'weak_password'}), 400

    # Hash password
    pm = PasswordManager()
    password_hash = pm.hash_password(password)

    user = User(
        username=data['username'],
        email=data['email'],
        password_hash=password_hash
    )
    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201

# Usage in login
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()

    if not user:
        return jsonify({'error': 'invalid_credentials'}), 401

    pm = PasswordManager()
    valid, new_hash = pm.verify_password(user.password_hash, data['password'])

    if not valid:
        return jsonify({'error': 'invalid_credentials'}), 401

    # Rehash if needed
    if new_hash:
        user.password_hash = new_hash
        db.session.commit()

    # Generate token and return
    token = generate_token(user)
    return jsonify({'token': token}), 200
```

**Alternative: Bcrypt (Also Acceptable):**
```python
import bcrypt

def hash_password_bcrypt(password):
    # Work factor of 12 (2^12 iterations)
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

def verify_password_bcrypt(password_hash, password):
    return bcrypt.checkpw(password.encode('utf-8'), password_hash)
```

**DO NOT USE:**
- MD5 (extremely fast, easily cracked)
- SHA1 (fast, vulnerable)
- SHA256/SHA512 without salt and iterations (too fast)
- Plaintext (obviously insecure)

**Password Storage Checklist:**
- [ ] Using Argon2id or bcrypt
- [ ] Unique salt per password (automatic with Argon2/bcrypt)
- [ ] Adequate work factor/memory cost
- [ ] Password never stored in plaintext
- [ ] Password never logged
- [ ] Old hashes migrated to new algorithm

---

### 3.2 Enforce Strong Password Policy

**Priority:** HIGH

**Recommendation:**
Implement comprehensive password strength requirements.

**Password Policy:**
```python
import re
import requests

class PasswordValidator:
    # Common passwords list (load from file or API)
    COMMON_PASSWORDS = None

    @classmethod
    def load_common_passwords(cls):
        """Load common passwords list (top 10,000)"""
        if cls.COMMON_PASSWORDS is None:
            # Load from file or use haveibeenpwned API
            cls.COMMON_PASSWORDS = set(load_common_passwords_file())

    @staticmethod
    def validate_password(password, username=None, email=None):
        """
        Validate password strength
        Returns: (is_valid, error_message)
        """
        errors = []

        # Minimum length
        if len(password) < 12:
            errors.append("Password must be at least 12 characters long")

        # Maximum length (prevent DoS)
        if len(password) > 128:
            errors.append("Password must not exceed 128 characters")

        # Complexity requirements
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

        # Check against common passwords
        PasswordValidator.load_common_passwords()
        if password.lower() in PasswordValidator.COMMON_PASSWORDS:
            errors.append("Password is too common. Please choose a stronger password")

        # Check password is not similar to username or email
        if username and username.lower() in password.lower():
            errors.append("Password must not contain username")

        if email:
            email_local = email.split('@')[0].lower()
            if email_local in password.lower():
                errors.append("Password must not contain email address")

        # Check for sequential characters
        if has_sequential_characters(password):
            errors.append("Password must not contain sequential characters (e.g., '123', 'abc')")

        # Check for repeated characters
        if has_repeated_characters(password, max_repeats=3):
            errors.append("Password must not contain more than 3 repeated characters")

        if errors:
            return False, errors
        return True, None

    @staticmethod
    def check_password_pwned(password):
        """
        Check if password has been pwned using HaveIBeenPwned API
        Returns: (is_pwned, count)
        """
        import hashlib
        sha1 = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        url = f"https://api.pwnedpasswords.com/range/{prefix}"
        response = requests.get(url)

        if response.status_code == 200:
            hashes = response.text.splitlines()
            for hash_line in hashes:
                hash_suffix, count = hash_line.split(':')
                if hash_suffix == suffix:
                    return True, int(count)

        return False, 0

def has_sequential_characters(password, length=3):
    """Check for sequential characters"""
    sequences = ['0123456789', 'abcdefghijklmnopqrstuvwxyz']
    password_lower = password.lower()

    for seq in sequences:
        for i in range(len(seq) - length + 1):
            if seq[i:i+length] in password_lower or seq[i:i+length][::-1] in password_lower:
                return True
    return False

def has_repeated_characters(password, max_repeats=3):
    """Check for repeated characters"""
    count = 1
    for i in range(1, len(password)):
        if password[i] == password[i-1]:
            count += 1
            if count > max_repeats:
                return True
        else:
            count = 1
    return False

# Usage in registration endpoint
@app.route('/api/v1/users', methods=['POST'])
def register_user():
    data = request.get_json()
    password = data.get('password')
    username = data.get('username')
    email = data.get('email')

    # Validate password
    is_valid, errors = PasswordValidator.validate_password(password, username, email)
    if not is_valid:
        return jsonify({'error': 'weak_password', 'details': errors}), 400

    # Optional: Check against HaveIBeenPwned
    is_pwned, count = PasswordValidator.check_password_pwned(password)
    if is_pwned:
        log_security_event('pwned_password_attempted', username, request.remote_addr, {'count': count})
        return jsonify({
            'error': 'compromised_password',
            'message': f'This password has been exposed in {count} data breaches. Please choose a different password.'
        }), 400

    # Create user
    user = create_user(username, email, password)
    return jsonify(user.to_dict()), 201
```

**Password Policy Summary:**
- Minimum 12 characters
- Mix of uppercase, lowercase, digits, special characters
- Not in common password list
- Not similar to username/email
- No sequential characters (123, abc)
- No excessive repeated characters (aaa)
- Optional: Not in HaveIBeenPwned database

---

### 3.3 Implement Secure Password Reset

**Priority:** HIGH

**Recommendation:**
Design a secure password reset mechanism to prevent account takeover.

**Implementation:**
```python
import secrets
from datetime import datetime, timedelta

class PasswordResetManager:
    @staticmethod
    def generate_reset_token():
        """Generate cryptographically secure reset token"""
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_reset_request(user):
        """Create password reset request"""
        token = PasswordResetManager.generate_reset_token()
        expires_at = datetime.utcnow() + timedelta(minutes=60)

        # Store token in database
        reset_request = PasswordResetRequest(
            user_id=user.id,
            token=token,
            expires_at=expires_at,
            used=False
        )
        db.session.add(reset_request)
        db.session.commit()

        # Send email with reset link
        reset_url = f"https://example.com/reset-password?token={token}"
        send_email(
            to=user.email,
            subject="Password Reset Request",
            body=f"Click the link to reset your password: {reset_url}\n\nThis link expires in 60 minutes."
        )

        log_security_event('password_reset_requested', user.username, None)

        return token

    @staticmethod
    def verify_reset_token(token):
        """Verify reset token is valid"""
        reset_request = PasswordResetRequest.query.filter_by(token=token).first()

        if not reset_request:
            return None, "Invalid reset token"

        if reset_request.used:
            log_security_event('reset_token_reuse_attempt', reset_request.user.username, None)
            return None, "Reset token has already been used"

        if datetime.utcnow() > reset_request.expires_at:
            return None, "Reset token has expired"

        return reset_request, None

# Request password reset
@app.route('/api/v1/auth/password-reset/request', methods=['POST'])
@rate_limit(limit=3, period=3600)  # 3 requests per hour
def request_password_reset():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'email_required'}), 400

    user = User.query.filter_by(email=email).first()

    # Always return success (don't reveal if email exists)
    if user:
        PasswordResetManager.create_reset_request(user)

    # Log attempt regardless
    log_security_event('password_reset_request_attempt', email, request.remote_addr)

    return jsonify({
        'message': 'If an account exists with this email, a password reset link has been sent.'
    }), 200

# Reset password
@app.route('/api/v1/auth/password-reset/confirm', methods=['POST'])
def confirm_password_reset():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')

    if not token or not new_password:
        return jsonify({'error': 'token_and_password_required'}), 400

    # Verify token
    reset_request, error = PasswordResetManager.verify_reset_token(token)
    if error:
        return jsonify({'error': error}), 400

    user = reset_request.user

    # Validate new password
    is_valid, errors = PasswordValidator.validate_password(new_password, user.username, user.email)
    if not is_valid:
        return jsonify({'error': 'weak_password', 'details': errors}), 400

    # Check password not same as current
    pm = PasswordManager()
    if pm.verify_password(user.password_hash, new_password)[0]:
        return jsonify({'error': 'password_reuse',
                       'message': 'New password must be different from current password'}), 400

    # Update password
    user.password_hash = pm.hash_password(new_password)
    user.password_changed_at = datetime.utcnow()

    # Mark reset request as used
    reset_request.used = True
    reset_request.used_at = datetime.utcnow()

    db.session.commit()

    # Invalidate all existing sessions
    invalidate_all_user_sessions(user.id)

    # Send confirmation email
    send_email(
        to=user.email,
        subject="Password Changed",
        body="Your password has been successfully changed. If you did not make this change, please contact support immediately."
    )

    log_security_event('password_reset_completed', user.username, request.remote_addr)

    return jsonify({'message': 'Password has been reset successfully'}), 200
```

**Security Requirements:**
- Cryptographically random tokens (32+ bytes)
- Token expiration (30-60 minutes)
- One-time use tokens
- Rate limiting on reset requests (3 per hour)
- Don't reveal if email exists
- Invalidate all sessions after password change
- Send confirmation email
- Log all reset activities

---

## 4. Input Validation & Sanitization

### 4.1 Prevent SQL Injection

**Priority:** CRITICAL

**Recommendation:**
Always use parameterized queries or ORM with proper escaping.

**VULNERABLE Code (Never do this):**
```python
# BAD - SQL Injection vulnerability
username = request.args.get('username')
query = f"SELECT * FROM users WHERE username = '{username}'"
result = db.engine.execute(query)
```

**SECURE Code:**
```python
# GOOD - Parameterized query (raw SQL)
username = request.args.get('username')
query = "SELECT * FROM users WHERE username = ?"
result = db.engine.execute(query, (username,))

# BETTER - ORM with proper escaping
from sqlalchemy import text
username = request.args.get('username')
result = db.session.execute(
    text("SELECT * FROM users WHERE username = :username"),
    {"username": username}
)

# BEST - ORM query builder
username = request.args.get('username')
user = User.query.filter_by(username=username).first()
```

**SQL Injection Testing:**
```python
# Test with these payloads
test_payloads = [
    "' OR '1'='1' --",
    "admin'--",
    "' OR 1=1--",
    "'; DROP TABLE users; --",
    "1' UNION SELECT null, username, password FROM users--"
]

# All should be safely handled
for payload in test_payloads:
    user = User.query.filter_by(username=payload).first()
    # Should return None, not bypass authentication
```

**Checklist:**
- [ ] All database queries use parameterized statements
- [ ] No string concatenation in SQL queries
- [ ] ORM used for all data access
- [ ] Dynamic queries use query builders
- [ ] SQL injection testing completed

---

### 4.2 Implement Comprehensive Input Validation

**Priority:** CRITICAL

**Recommendation:**
Validate all user input against strict schemas.

**Implementation:**
```python
from marshmallow import Schema, fields, validate, ValidationError, validates

class UserRegistrationSchema(Schema):
    username = fields.Str(
        required=True,
        validate=[
            validate.Length(min=3, max=20),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$', error="Username can only contain letters, numbers, underscore, and hyphen")
        ]
    )
    email = fields.Email(required=True)
    password = fields.Str(
        required=True,
        validate=validate.Length(min=12, max=128)
    )
    full_name = fields.Str(
        validate=validate.Length(max=100)
    )

    @validates('username')
    def validate_username_unique(self, value):
        if User.query.filter_by(username=value).first():
            raise ValidationError("Username already exists")

class UserUpdateSchema(Schema):
    username = fields.Str(
        validate=[
            validate.Length(min=3, max=20),
            validate.Regexp(r'^[a-zA-Z0-9_-]+$')
        ]
    )
    email = fields.Email()
    full_name = fields.Str(validate=validate.Length(max=100))
    # Note: password not updateable via this endpoint

# Usage in endpoint
@app.route('/api/v1/users', methods=['POST'])
def register_user():
    schema = UserRegistrationSchema()

    try:
        # Validate and deserialize input
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': 'validation_error', 'details': err.messages}), 400

    # Input is now validated and safe to use
    user = create_user(**data)
    return jsonify(user.to_dict()), 201
```

**Input Validation Rules:**
- **Username:** 3-20 characters, alphanumeric with underscore/hyphen only
- **Email:** Valid email format (RFC 5322)
- **Password:** 12-128 characters
- **Phone:** Valid phone number format
- **URL:** Valid URL format, optional whitelist of domains
- **Dates:** Valid date format (ISO 8601)
- **IDs:** Valid integer or UUID format

**Sanitization:**
```python
import bleach
from markupsafe import escape

def sanitize_html(text):
    """Remove all HTML tags"""
    return bleach.clean(text, tags=[], strip=True)

def sanitize_user_input(text):
    """Escape HTML entities"""
    return escape(text)

# Example
@app.route('/api/v1/users/<int:user_id>/bio', methods=['PUT'])
@require_auth
def update_bio(user_id):
    data = request.get_json()
    bio = data.get('bio', '')

    # Sanitize HTML
    clean_bio = sanitize_html(bio)

    # Enforce length limit
    if len(clean_bio) > 500:
        return jsonify({'error': 'bio_too_long'}), 400

    user = User.query.get_or_404(user_id)
    user.bio = clean_bio
    db.session.commit()

    return jsonify(user.to_dict()), 200
```

---

## 5. API Security

### 5.1 Implement API Rate Limiting

**Priority:** CRITICAL

**Recommendation:**
Implement multi-layer rate limiting to prevent abuse and DoS attacks.

**Implementation:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis

# Redis-backed rate limiter
redis_client = redis.Redis(host='localhost', port=6379, db=0)

limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379",
    default_limits=["1000 per hour", "100 per minute"]
)

# Endpoint-specific rate limits
@app.route('/api/v1/auth/login', methods=['POST'])
@limiter.limit("5 per 15 minutes")
def login():
    # Login implementation
    pass

@app.route('/api/v1/auth/password-reset/request', methods=['POST'])
@limiter.limit("3 per hour")
def request_password_reset():
    # Password reset implementation
    pass

@app.route('/api/v1/users', methods=['POST'])
@limiter.limit("10 per hour")
def register_user():
    # Registration implementation
    pass

@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
@limiter.limit("60 per minute")
@require_auth
def get_user(user_id):
    # Get user implementation
    pass

# Custom rate limiter with user-based limits
class CustomRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client

    def check_rate_limit(self, key, limit, period):
        """
        Check if rate limit is exceeded
        Args:
            key: Rate limit key (e.g., 'login:192.168.1.1' or 'api:user:123')
            limit: Number of requests allowed
            period: Time period in seconds
        Returns:
            (allowed, remaining, reset_time)
        """
        current = int(time.time())
        window_key = f"rate_limit:{key}:{current // period}"

        # Increment counter
        count = self.redis.incr(window_key)

        # Set expiration on first request
        if count == 1:
            self.redis.expire(window_key, period)

        remaining = max(0, limit - count)
        reset_time = (current // period + 1) * period

        return count <= limit, remaining, reset_time

# Usage
rate_limiter = CustomRateLimiter(redis_client)

@app.route('/api/v1/users/<int:user_id>', methods=['GET'])
@require_auth
def get_user(user_id):
    current_user = get_current_user()

    # Check user-specific rate limit
    allowed, remaining, reset_time = rate_limiter.check_rate_limit(
        f"api:user:{current_user.id}",
        limit=100,
        period=60
    )

    if not allowed:
        return jsonify({
            'error': 'rate_limit_exceeded',
            'message': 'Too many requests',
            'retry_after': reset_time - int(time.time())
        }), 429

    # Add rate limit headers
    response = jsonify(get_user_data(user_id))
    response.headers['X-RateLimit-Limit'] = '100'
    response.headers['X-RateLimit-Remaining'] = str(remaining)
    response.headers['X-RateLimit-Reset'] = str(reset_time)

    return response
```

**Rate Limit Strategy:**

| Endpoint | Limit | Period | Reason |
|----------|-------|--------|--------|
| POST /auth/login | 5 | 15 min | Prevent brute force |
| POST /auth/register | 10 | 1 hour | Prevent spam registration |
| POST /auth/password-reset | 3 | 1 hour | Prevent abuse |
| GET /users | 60 | 1 min | Prevent data scraping |
| PUT /users/{id} | 30 | 1 hour | Prevent abuse |
| DELETE /users/{id} | 10 | 1 hour | Critical operation |
| Global (authenticated) | 1000 | 1 hour | Overall limit |
| Global (unauthenticated) | 100 | 1 hour | Stricter for anon |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1609459200
Retry-After: 60
```

---

### 5.2 Implement Security Headers

**Priority:** HIGH

**Recommendation:**
Configure HTTP security headers to protect against common attacks.

**Implementation:**
```python
from flask import Flask, Response
from functools import wraps

def add_security_headers(response):
    """Add security headers to response"""
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'

    # XSS Protection (legacy, but still useful)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Force HTTPS
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Content Security Policy
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; object-src 'none'"

    # Referrer Policy
    response.headers['Referrer-Policy'] = 'no-referrer'

    # Permissions Policy
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

    # Remove server header
    response.headers.pop('Server', None)

    return response

# Apply to all responses
@app.after_request
def apply_security_headers(response):
    return add_security_headers(response)
```

---

### 5.3 Implement CORS Securely

**Priority:** MEDIUM

**Recommendation:**
Configure CORS with specific allowed origins, not wildcard.

**Implementation:**
```python
from flask_cors import CORS

# BAD - Allows all origins
CORS(app, origins="*")

# GOOD - Specific allowed origins
ALLOWED_ORIGINS = [
    'https://example.com',
    'https://app.example.com',
    'https://admin.example.com'
]

CORS(app,
     origins=ALLOWED_ORIGINS,
     methods=['GET', 'POST', 'PUT', 'DELETE'],
     allowed_headers=['Content-Type', 'Authorization'],
     expose_headers=['X-RateLimit-Limit', 'X-RateLimit-Remaining'],
     supports_credentials=True,
     max_age=3600
)

# Dynamic CORS validation
@app.after_request
def validate_cors(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
```

---

## 6. Data Protection

### 6.1 Implement TLS/HTTPS

**Priority:** CRITICAL

**Recommendation:**
Enforce HTTPS for all API communications.

**Requirements:**
- TLS 1.3 (or minimum TLS 1.2)
- Strong cipher suites only
- Valid SSL certificate (Let's Encrypt or commercial CA)
- HSTS header (Strict-Transport-Security)
- Redirect HTTP to HTTPS

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Host $host;
    }
}
```

---

### 6.2 Implement Database Encryption

**Priority:** HIGH

**Recommendation:**
Encrypt sensitive data at rest and in transit.

**Database Connection (TLS):**
```python
# PostgreSQL with SSL
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://user:password@localhost/dbname',
    connect_args={
        'sslmode': 'require',
        'sslcert': '/path/to/client-cert.pem',
        'sslkey': '/path/to/client-key.pem',
        'sslrootcert': '/path/to/ca-cert.pem'
    }
)
```

**Field-Level Encryption:**
```python
from cryptography.fernet import Fernet
import base64

class EncryptionManager:
    def __init__(self, key):
        self.cipher = Fernet(key)

    def encrypt(self, plaintext):
        """Encrypt plaintext"""
        if plaintext is None:
            return None
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext):
        """Decrypt ciphertext"""
        if ciphertext is None:
            return None
        return self.cipher.decrypt(ciphertext.encode()).decode()

# Usage for sensitive fields
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    _ssn = db.Column('ssn', db.String(200))  # Encrypted

    encryption_manager = EncryptionManager(os.getenv('ENCRYPTION_KEY'))

    @property
    def ssn(self):
        return self.encryption_manager.decrypt(self._ssn)

    @ssn.setter
    def ssn(self, value):
        self._ssn = self.encryption_manager.encrypt(value)
```

---

## 7. Rate Limiting & DoS Protection

*(Covered in section 5.1 - see above)*

---

## 8. Session Management

### 8.1 Implement Secure Token Storage

**Priority:** HIGH

**Recommendation:**
Store tokens securely using HttpOnly cookies.

**Implementation:**
```python
@app.route('/api/v1/auth/login', methods=['POST'])
def login():
    # ... authentication logic ...

    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    response = jsonify({'message': 'Login successful'})

    # Store access token in HttpOnly cookie
    response.set_cookie(
        'access_token',
        value=access_token,
        max_age=900,  # 15 minutes
        secure=True,  # HTTPS only
        httponly=True,  # Not accessible via JavaScript
        samesite='Strict'  # CSRF protection
    )

    # Store refresh token in HttpOnly cookie
    response.set_cookie(
        'refresh_token',
        value=refresh_token,
        max_age=604800,  # 7 days
        secure=True,
        httponly=True,
        samesite='Strict'
    )

    return response
```

---

### 8.2 Implement Token Refresh Mechanism

**Priority:** HIGH

**Implementation:**
```python
@app.route('/api/v1/auth/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.cookies.get('refresh_token')

    if not refresh_token:
        return jsonify({'error': 'refresh_token_required'}), 401

    try:
        payload = jwt.decode(refresh_token, PUBLIC_KEY, algorithms=['RS256'])

        # Check token type
        if payload.get('type') != 'refresh':
            raise InvalidTokenError("Invalid token type")

        # Check if token is revoked
        if is_token_revoked(payload['jti']):
            raise InvalidTokenError("Token has been revoked")

        user_id = payload['sub']

        # Generate new tokens
        new_access_token = create_access_token(user_id)
        new_refresh_token = create_refresh_token(user_id)

        # Revoke old refresh token (token rotation)
        revoke_token(payload['jti'])

        response = jsonify({'message': 'Token refreshed'})
        response.set_cookie('access_token', new_access_token, ...)
        response.set_cookie('refresh_token', new_refresh_token, ...)

        return response

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'refresh_token_expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'invalid_refresh_token'}), 401
```

---

## 9. Error Handling & Logging

### 9.1 Implement Secure Error Handling

**Priority:** HIGH

**Recommendation:**
Return generic error messages to users, log detailed errors internally.

**Implementation:**
```python
@app.errorhandler(Exception)
def handle_exception(e):
    # Log detailed error internally
    app.logger.error(f"Unhandled exception: {str(e)}", exc_info=True)

    # Return generic error to user
    return jsonify({
        'error': 'internal_server_error',
        'message': 'An unexpected error occurred. Please try again later.'
    }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'error': 'not_found',
        'message': 'Resource not found'
    }), 404

@app.errorhandler(403)
def forbidden(e):
    return jsonify({
        'error': 'forbidden',
        'message': 'Access denied'
    }), 403
```

---

### 9.2 Implement Security Logging

**Priority:** HIGH

**Recommendation:**
Log all security-relevant events for monitoring and incident response.

**Implementation:**
```python
import logging
import json
from datetime import datetime

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)

        # File handler for security events
        handler = logging.FileHandler('/var/log/app/security.log')
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def log_event(self, event_type, username, ip_address, details=None):
        """Log security event"""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'username': username,
            'ip_address': ip_address,
            'details': details or {}
        }
        self.logger.info(json.dumps(event))

security_logger = SecurityLogger()

# Log security events
def log_security_event(event_type, username, ip_address, details=None):
    security_logger.log_event(event_type, username, ip_address, details)

# Usage examples
log_security_event('login_success', 'john_doe', '192.168.1.1')
log_security_event('login_failure', 'admin', '192.168.1.100', {'reason': 'invalid_password'})
log_security_event('authorization_failure', 'john_doe', '192.168.1.1', {'resource': '/users/456'})
log_security_event('account_locked', 'admin', '192.168.1.100', {'failed_attempts': 5})
```

**Events to Log:**
- Authentication (success/failure)
- Authorization failures
- Password changes
- Account lockouts
- MFA events
- Rate limit violations
- Input validation failures
- Administrative actions
- Data access (especially bulk access)
- Configuration changes

---

## 10. Security Monitoring & Incident Response

### 10.1 Implement Real-Time Security Monitoring

**Priority:** MEDIUM

**Recommendation:**
Implement automated monitoring and alerting for security events.

**Implementation:**
```python
class SecurityMonitor:
    def __init__(self):
        self.alert_thresholds = {
            'failed_logins': {'count': 10, 'window': 60},  # 10 failures in 60 seconds
            'rate_limit_violations': {'count': 5, 'window': 60},
            'authorization_failures': {'count': 20, 'window': 60}
        }

    def check_alert_threshold(self, event_type, identifier):
        """Check if alert threshold is exceeded"""
        window = self.alert_thresholds[event_type]['window']
        threshold = self.alert_thresholds[event_type]['count']

        # Count events in time window
        count = count_events_in_window(event_type, identifier, window)

        if count >= threshold:
            self.trigger_alert(event_type, identifier, count)

    def trigger_alert(self, event_type, identifier, count):
        """Trigger security alert"""
        alert = {
            'timestamp': datetime.utcnow().isoformat(),
            'severity': 'HIGH',
            'event_type': event_type,
            'identifier': identifier,
            'count': count,
            'message': f"Threshold exceeded: {count} {event_type} events"
        }

        # Send to SIEM
        send_to_siem(alert)

        # Send notification
        send_alert_notification(alert)

        # Log alert
        security_logger.log_event('security_alert', None, None, alert)
```

---

## 11. Infrastructure Security

### 11.1 Secure Configuration Management

**Priority:** HIGH

**Recommendation:**
Store sensitive configuration in environment variables or secrets management system.

**Implementation:**
```python
import os
from dotenv import load_dotenv

# Load from .env file (development)
load_dotenv()

class Config:
    # Security settings
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_PRIVATE_KEY_PATH = os.getenv('JWT_PRIVATE_KEY_PATH')
    JWT_PUBLIC_KEY_PATH = os.getenv('JWT_PUBLIC_KEY_PATH')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')

    # Never hardcode secrets
    # BAD: SECRET_KEY = 'hardcoded-secret-123'
    # GOOD: SECRET_KEY = os.getenv('SECRET_KEY')

    # Validate required config
    @classmethod
    def validate(cls):
        required = ['SECRET_KEY', 'DATABASE_URL', 'JWT_PRIVATE_KEY_PATH']
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
```

---

## 12. Compliance & Privacy

### 12.1 Implement GDPR/CCPA Compliance

**Priority:** HIGH

**Recommendation:**
Implement data subject rights and privacy controls.

**Implementation:**
```python
# Right to access
@app.route('/api/v1/users/me/data-export', methods=['POST'])
@require_auth
def export_user_data():
    user = get_current_user()

    # Collect all user data
    data = {
        'user_info': user.to_dict(),
        'login_history': get_login_history(user.id),
        'audit_log': get_audit_log(user.id)
    }

    # Generate export file
    export_file = generate_json_export(data)

    log_security_event('data_export', user.username, request.remote_addr)

    return send_file(export_file, as_attachment=True)

# Right to erasure
@app.route('/api/v1/users/me', methods=['DELETE'])
@require_auth
@require_mfa
def delete_user_account():
    user = get_current_user()

    # Anonymize or delete user data
    anonymize_user_data(user)

    # Mark account as deleted
    user.is_deleted = True
    user.deleted_at = datetime.utcnow()
    db.session.commit()

    log_security_event('account_deleted', user.username, request.remote_addr)

    return jsonify({'message': 'Account deleted successfully'}), 200
```

---

## 13. Security Testing

### 13.1 Implement Automated Security Testing

**Priority:** HIGH

**Recommendation:**
Integrate security testing into CI/CD pipeline.

**Testing Checklist:**
- [ ] Static Application Security Testing (SAST)
- [ ] Dependency vulnerability scanning
- [ ] SQL injection testing
- [ ] XSS testing
- [ ] Authentication bypass testing
- [ ] Authorization testing
- [ ] Rate limiting testing
- [ ] Input validation testing

**CI/CD Integration:**
```yaml
# .github/workflows/security.yml
name: Security Testing

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Run Bandit (SAST)
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json

      - name: Dependency Vulnerability Scan
        run: |
          pip install safety
          safety check --json

      - name: OWASP ZAP Scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: 'http://localhost:5000'
```

---

## 14. Secure Development Practices

### 14.1 Security Code Review Checklist

**Priority:** HIGH

**Checklist:**
- [ ] All inputs validated
- [ ] Parameterized queries used
- [ ] Authentication implemented
- [ ] Authorization checks on all endpoints
- [ ] Passwords hashed with Argon2id/bcrypt
- [ ] Rate limiting implemented
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] Sensitive data not logged
- [ ] Error messages don't leak information
- [ ] Dependencies up to date
- [ ] Security tests passing

---

## Summary

This comprehensive security recommendations document provides detailed guidance for implementing a secure user management REST API. All CRITICAL and HIGH priority recommendations must be implemented before production deployment.

**Key Priorities:**
1. Implement authentication (JWT with RS256)
2. Implement authorization (RBAC with resource ownership)
3. Use Argon2id for password hashing
4. Implement rate limiting
5. Use parameterized queries (prevent SQL injection)
6. Enforce HTTPS (TLS 1.3)
7. Implement security logging
8. Conduct security testing

**Next Steps:**
1. Review and approve these recommendations
2. Incorporate into system design
3. Implement security controls during development
4. Conduct security code review
5. Perform security testing
6. Schedule penetration testing before production

---

## Document Control

**Version:** 1.0
**Classification:** CONFIDENTIAL
**Review Date:** Before Implementation Phase

**Prepared by:** Security Specialist
**Date:** 2025-10-12
**Workflow ID:** workflow-20251012-130125

**END OF RECOMMENDATIONS**
