"""FastAPI middleware for automatic metrics collection"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically track HTTP metrics"""
    
    def __init__(self, app, http_requests_counter, http_duration_histogram):
        super().__init__(app)
        self.http_requests = http_requests_counter
        self.http_duration = http_duration_histogram
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        
        self.http_requests.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        self.http_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        return response
