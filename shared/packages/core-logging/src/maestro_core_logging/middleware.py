"""
Middleware for popular web frameworks to automatically set logging context.
"""

from typing import Callable, Any
import uuid
from .context import LogContext, set_context, clear_context


class LoggingMiddleware:
    """
    Base middleware class for logging context management.
    """

    def __init__(self, app: Any, extract_user_id: Callable = None):
        """
        Initialize middleware.

        Args:
            app: WSGI/ASGI application
            extract_user_id: Function to extract user ID from request
        """
        self.app = app
        self.extract_user_id = extract_user_id or (lambda request: None)

    def _create_context(self, request: Any) -> LogContext:
        """Create logging context from request."""
        # Extract or generate request ID
        request_id = (
            getattr(request, 'headers', {}).get('X-Request-ID') or
            getattr(request, 'META', {}).get('HTTP_X_REQUEST_ID') or
            str(uuid.uuid4())
        )

        # Extract correlation ID
        correlation_id = (
            getattr(request, 'headers', {}).get('X-Correlation-ID') or
            getattr(request, 'META', {}).get('HTTP_X_CORRELATION_ID') or
            str(uuid.uuid4())
        )

        # Extract user ID if function provided
        user_id = self.extract_user_id(request)

        return LogContext(
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=user_id,
            operation=getattr(request, 'method', 'UNKNOWN') + ' ' + getattr(request, 'path', '/')
        )


class FastAPILoggingMiddleware(LoggingMiddleware):
    """
    FastAPI middleware for automatic logging context.

    Usage:
        from fastapi import FastAPI
        from maestro_core_logging import FastAPILoggingMiddleware

        app = FastAPI()
        app.add_middleware(FastAPILoggingMiddleware)
    """

    async def __call__(self, scope, receive, send):
        """Process ASGI request with logging context."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create a mock request object for context creation
        class MockRequest:
            def __init__(self, scope):
                self.headers = {k.decode(): v.decode() for k, v in scope.get("headers", [])}
                self.method = scope.get("method", "")
                self.path = scope.get("path", "/")

        request = MockRequest(scope)
        context = self._create_context(request)
        set_context(context)

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", context.request_id.encode()))
                headers.append((b"x-correlation-id", context.correlation_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            clear_context()


class FlaskLoggingMiddleware(LoggingMiddleware):
    """
    Flask middleware for automatic logging context.

    Usage:
        from flask import Flask
        from maestro_core_logging import FlaskLoggingMiddleware

        app = Flask(__name__)
        FlaskLoggingMiddleware(app)
    """

    def __init__(self, app=None, **kwargs):
        """Initialize Flask middleware."""
        super().__init__(app, **kwargs)
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize with Flask app."""
        app.before_request(self._before_request)
        app.after_request(self._after_request)

    def _before_request(self):
        """Set up logging context before request."""
        from flask import request
        context = self._create_context(request)
        set_context(context)

    def _after_request(self, response):
        """Clean up logging context after request."""
        from .context import get_context
        context = get_context()
        if context:
            response.headers["X-Request-ID"] = context.request_id
            response.headers["X-Correlation-ID"] = context.correlation_id
        clear_context()
        return response


class DjangoLoggingMiddleware(LoggingMiddleware):
    """
    Django middleware for automatic logging context.

    Usage:
        # In settings.py
        MIDDLEWARE = [
            'maestro_core_logging.middleware.DjangoLoggingMiddleware',
            # ... other middleware
        ]
    """

    def __init__(self, get_response):
        """Initialize Django middleware."""
        self.get_response = get_response
        super().__init__(None)

    def __call__(self, request):
        """Process Django request with logging context."""
        context = self._create_context(request)
        set_context(context)

        try:
            response = self.get_response(request)
            response["X-Request-ID"] = context.request_id
            response["X-Correlation-ID"] = context.correlation_id
            return response
        finally:
            clear_context()


class ASGILoggingMiddleware:
    """
    Generic ASGI middleware for logging context.

    Usage:
        from maestro_core_logging import ASGILoggingMiddleware

        app = ASGILoggingMiddleware(your_asgi_app)
    """

    def __init__(self, app, extract_user_id: Callable = None):
        """Initialize ASGI middleware."""
        self.app = app
        self.extract_user_id = extract_user_id or (lambda scope: None)

    async def __call__(self, scope, receive, send):
        """Process ASGI request with logging context."""
        if scope["type"] != "http":
            # Only handle HTTP requests
            await self.app(scope, receive, send)
            return

        # Extract request information from scope
        headers = dict(scope.get("headers", []))
        request_id = (
            headers.get(b"x-request-id", b"").decode() or
            str(uuid.uuid4())
        )
        correlation_id = (
            headers.get(b"x-correlation-id", b"").decode() or
            str(uuid.uuid4())
        )

        context = LogContext(
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=self.extract_user_id(scope),
            operation=scope.get("method", "UNKNOWN") + " " + scope.get("path", "/")
        )

        set_context(context)

        async def send_with_headers(message):
            """Add headers to response."""
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-request-id"] = request_id.encode()
                headers[b"x-correlation-id"] = correlation_id.encode()
                message["headers"] = list(headers.items())
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            clear_context()