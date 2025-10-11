"""
Security Headers Middleware

Adds security headers to HTTP responses to protect against common vulnerabilities.
"""

import logging
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-Frame-Options: Prevent clickjacking
    - X-XSS-Protection: Enable XSS filter
    - Strict-Transport-Security: Force HTTPS
    - Content-Security-Policy: Control resource loading
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    """

    def __init__(
        self,
        app,
        enable_hsts: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        enable_csp: bool = True,
        csp_directives: Optional[dict[str, str]] = None,
        frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin"
    ):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application
            enable_hsts: Enable HTTP Strict Transport Security
            hsts_max_age: HSTS max age in seconds
            enable_csp: Enable Content Security Policy
            csp_directives: Custom CSP directives
            frame_options: X-Frame-Options value (DENY, SAMEORIGIN, or ALLOW-FROM uri)
            referrer_policy: Referrer-Policy value
        """
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.hsts_max_age = hsts_max_age
        self.enable_csp = enable_csp
        self.frame_options = frame_options
        self.referrer_policy = referrer_policy

        # Default CSP directives
        self.csp_directives = csp_directives or {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust for your needs
            "style-src": "'self' 'unsafe-inline'",
            "img-src": "'self' data: https:",
            "font-src": "'self' data:",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'"
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # X-Content-Type-Options: Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = self.frame_options

        # X-XSS-Protection: Enable XSS filter (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Strict-Transport-Security: Force HTTPS
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # Content-Security-Policy: Control resource loading
        if self.enable_csp:
            csp_header = "; ".join(
                f"{key} {value}" for key, value in self.csp_directives.items()
            )
            response.headers["Content-Security-Policy"] = csp_header

        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = self.referrer_policy

        # Permissions-Policy: Control browser features
        # Restrict potentially dangerous features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), "
            "accelerometer=(), gyroscope=()"
        )

        # X-Permitted-Cross-Domain-Policies: Restrict cross-domain policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Remove potentially sensitive headers
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with security considerations.

    Provides stricter CORS controls than standard FastAPI CORS.
    """

    def __init__(
        self,
        app,
        allowed_origins: list[str] = None,
        allow_credentials: bool = True,
        allowed_methods: list[str] = None,
        allowed_headers: list[str] = None,
        max_age: int = 600,
    ):
        """
        Initialize CORS security middleware.

        Args:
            app: FastAPI application
            allowed_origins: List of allowed origins (exact match)
            allow_credentials: Allow credentials in CORS requests
            allowed_methods: Allowed HTTP methods
            allowed_headers: Allowed headers
            max_age: Preflight cache duration in seconds
        """
        super().__init__(app)
        self.allowed_origins = set(allowed_origins or ["http://localhost:3000"])
        self.allow_credentials = allow_credentials
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or [
            "Content-Type",
            "Authorization",
            "X-User-ID",
            "X-Tenant-ID",
            "X-Request-ID"
        ]
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Handle CORS with security checks.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response with CORS headers
        """
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        # Only add CORS headers if origin is allowed
        if origin and origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            response.headers["Access-Control-Max-Age"] = str(self.max_age)

            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

            # Expose custom headers
            response.headers["Access-Control-Expose-Headers"] = (
                "X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset"
            )
        elif origin:
            # Log unauthorized origin attempts
            logger.warning(f"CORS request from unauthorized origin: {origin}")

        return response


def add_security_headers(
    app,
    enable_hsts: bool = True,
    enable_csp: bool = True,
    csp_directives: Optional[dict[str, str]] = None,
    frame_options: str = "DENY"
):
    """
    Add security headers middleware to FastAPI app.

    Args:
        app: FastAPI application
        enable_hsts: Enable HSTS
        enable_csp: Enable CSP
        csp_directives: Custom CSP directives
        frame_options: X-Frame-Options value

    Example:
        from enterprise.security.headers import add_security_headers

        add_security_headers(app, enable_hsts=True)
    """
    app.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=enable_hsts,
        enable_csp=enable_csp,
        csp_directives=csp_directives,
        frame_options=frame_options
    )


def add_cors_security(
    app,
    allowed_origins: list[str],
    allow_credentials: bool = True
):
    """
    Add CORS security middleware to FastAPI app.

    Args:
        app: FastAPI application
        allowed_origins: List of allowed origins
        allow_credentials: Allow credentials

    Example:
        from enterprise.security.headers import add_cors_security

        add_cors_security(
            app,
            allowed_origins=["https://app.example.com"]
        )
    """
    app.add_middleware(
        CORSSecurityMiddleware,
        allowed_origins=allowed_origins,
        allow_credentials=allow_credentials
    )
