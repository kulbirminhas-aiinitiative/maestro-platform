"""
Rate Limiting Middleware for FastAPI

Implements sliding window rate limiting with configurable limits per user/IP.
"""

import time
from typing import Dict, Tuple, Optional
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import jwt
from jwt.exceptions import InvalidTokenError


class RateLimiter:
    """
    Sliding window rate limiter using in-memory storage

    Can be extended to use Redis for distributed deployments.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        authenticated_multiplier: int = 5
    ):
        """
        Initialize rate limiter

        Args:
            requests_per_minute: Base limit for requests per minute
            requests_per_hour: Base limit for requests per hour
            authenticated_multiplier: Multiplier for authenticated users
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.authenticated_multiplier = authenticated_multiplier

        # Storage: key -> deque of request timestamps
        self.minute_buckets: Dict[str, deque] = defaultdict(lambda: deque())
        self.hour_buckets: Dict[str, deque] = defaultdict(lambda: deque())

    def _clean_old_requests(self, bucket: deque, window_seconds: int, current_time: float):
        """Remove requests older than window"""
        cutoff_time = current_time - window_seconds
        while bucket and bucket[0] < cutoff_time:
            bucket.popleft()

    def _get_limits(self, is_authenticated: bool) -> Tuple[int, int]:
        """Get rate limits based on authentication status"""
        multiplier = self.authenticated_multiplier if is_authenticated else 1
        return (
            self.requests_per_minute * multiplier,
            self.requests_per_hour * multiplier
        )

    def is_rate_limited(self, key: str, is_authenticated: bool = False) -> Tuple[bool, Dict]:
        """
        Check if key has exceeded rate limit

        Returns:
            Tuple of (is_limited, info_dict)
        """
        current_time = time.time()
        minute_limit, hour_limit = self._get_limits(is_authenticated)

        # Clean old requests
        self._clean_old_requests(self.minute_buckets[key], 60, current_time)
        self._clean_old_requests(self.hour_buckets[key], 3600, current_time)

        # Count current requests
        minute_count = len(self.minute_buckets[key])
        hour_count = len(self.hour_buckets[key])

        # Check limits
        if minute_count >= minute_limit:
            # Calculate reset time (next minute)
            oldest_request = self.minute_buckets[key][0]
            reset_time = int(oldest_request + 60)
            return True, {
                "limit": minute_limit,
                "remaining": 0,
                "reset": reset_time,
                "window": "minute"
            }

        if hour_count >= hour_limit:
            # Calculate reset time (next hour)
            oldest_request = self.hour_buckets[key][0]
            reset_time = int(oldest_request + 3600)
            return True, {
                "limit": hour_limit,
                "remaining": 0,
                "reset": reset_time,
                "window": "hour"
            }

        # Not limited - add request
        self.minute_buckets[key].append(current_time)
        self.hour_buckets[key].append(current_time)

        return False, {
            "limit": minute_limit,
            "remaining": minute_limit - minute_count - 1,
            "reset": int(current_time + 60),
            "window": "minute"
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting

    Applies different limits for authenticated vs anonymous users.
    Uses user_id for authenticated users, IP address for anonymous.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        authenticated_multiplier: int = 5,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_hour=requests_per_hour,
            authenticated_multiplier=authenticated_multiplier
        )
        # Exclude health checks and docs from rate limiting
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json", "/"]

    def _get_client_identifier(self, request: Request) -> Tuple[str, bool]:
        """
        Extract client identifier from request

        Returns:
            Tuple of (identifier, is_authenticated)
        """
        # Try to extract user from JWT token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                # Decode without verification (verification happens in auth middleware)
                # We just want to extract user_id for rate limiting key
                payload = jwt.decode(token, options={"verify_signature": False})
                user_id = payload.get("sub") or payload.get("user_id")
                if user_id:
                    return f"user:{user_id}", True
            except (InvalidTokenError, Exception):
                pass

        # Try API key
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            # Use hash of API key as identifier
            return f"apikey:{hash(api_key)}", True

        # Fall back to IP address for anonymous users
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        return f"ip:{client_ip}", False

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get client identifier
        identifier, is_authenticated = self._get_client_identifier(request)

        # Check rate limit
        is_limited, rate_info = self.limiter.is_rate_limited(identifier, is_authenticated)

        if is_limited:
            # Rate limit exceeded
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Too many requests per {rate_info['window']}.",
                    "details": {
                        "limit": rate_info["limit"],
                        "window": rate_info["window"],
                        "reset_at": rate_info["reset"]
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(rate_info["reset"] - int(time.time()))
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_info["reset"])

        return response
