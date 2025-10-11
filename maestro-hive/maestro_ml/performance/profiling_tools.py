"""
Performance Profiling Tools for Maestro ML Platform

Provides:
- CPU profiling
- Memory profiling
- Database query profiling
- API endpoint profiling
- Flame graph generation
"""

import cProfile
import pstats
import io
import time
import psutil
import tracemalloc
from typing import Callable, Optional, Dict, Any
from functools import wraps
from contextlib import contextmanager
import logging
from dataclasses import dataclass, field
from datetime import datetime
import json

logger = logging.getLogger(__name__)


@dataclass
class ProfileResult:
    """Profiling result"""
    name: str
    duration_seconds: float
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    function_calls: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "duration_seconds": self.duration_seconds,
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "peak_memory_mb": self.peak_memory_mb,
            "function_calls": self.function_calls,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class PerformanceProfiler:
    """
    Performance profiler for functions and code blocks

    Usage:
        profiler = PerformanceProfiler()

        # Profile a function
        @profiler.profile()
        def slow_function():
            # ... expensive code ...
            pass

        # Profile a code block
        with profiler.profile_block("data_processing"):
            # ... code to profile ...
            pass

        # Get results
        results = profiler.get_results()
    """

    def __init__(self):
        self.results: list[ProfileResult] = []
        self.process = psutil.Process()

    def profile(self, name: Optional[str] = None):
        """
        Decorator to profile a function

        Args:
            name: Custom name for profile (defaults to function name)
        """
        def decorator(func: Callable):
            profile_name = name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                # Start profiling
                start_time = time.time()
                start_cpu = self.process.cpu_percent()
                start_memory = self.process.memory_info().rss / 1024 / 1024

                # Start memory tracking
                tracemalloc.start()

                # Start CPU profiling
                profiler = cProfile.Profile()
                profiler.enable()

                try:
                    # Execute function
                    result = func(*args, **kwargs)

                    return result

                finally:
                    # Stop profiling
                    profiler.disable()

                    # Get metrics
                    duration = time.time() - start_time
                    cpu_percent = self.process.cpu_percent() - start_cpu
                    current_memory = self.process.memory_info().rss / 1024 / 1024
                    memory_used = current_memory - start_memory

                    # Get peak memory
                    current, peak = tracemalloc.get_traced_memory()
                    peak_memory_mb = peak / 1024 / 1024
                    tracemalloc.stop()

                    # Get function call stats
                    stats = pstats.Stats(profiler)
                    total_calls = stats.total_calls

                    # Store result
                    profile_result = ProfileResult(
                        name=profile_name,
                        duration_seconds=duration,
                        cpu_percent=cpu_percent,
                        memory_mb=memory_used,
                        peak_memory_mb=peak_memory_mb,
                        function_calls=total_calls,
                        metadata={
                            "args_count": len(args),
                            "kwargs_count": len(kwargs)
                        }
                    )

                    self.results.append(profile_result)

                    logger.info(
                        f"Profile [{profile_name}]: {duration:.3f}s, "
                        f"{memory_used:.1f}MB, {total_calls} calls"
                    )

            return wrapper
        return decorator

    @contextmanager
    def profile_block(self, name: str):
        """
        Context manager to profile a code block

        Usage:
            with profiler.profile_block("data_loading"):
                data = load_large_dataset()
        """
        start_time = time.time()
        start_cpu = self.process.cpu_percent()
        start_memory = self.process.memory_info().rss / 1024 / 1024

        tracemalloc.start()
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            yield

        finally:
            profiler.disable()

            duration = time.time() - start_time
            cpu_percent = self.process.cpu_percent() - start_cpu
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_used = current_memory - start_memory

            current, peak = tracemalloc.get_traced_memory()
            peak_memory_mb = peak / 1024 / 1024
            tracemalloc.stop()

            stats = pstats.Stats(profiler)

            profile_result = ProfileResult(
                name=name,
                duration_seconds=duration,
                cpu_percent=cpu_percent,
                memory_mb=memory_used,
                peak_memory_mb=peak_memory_mb,
                function_calls=stats.total_calls
            )

            self.results.append(profile_result)

            logger.info(
                f"Profile [{name}]: {duration:.3f}s, "
                f"{memory_used:.1f}MB, {stats.total_calls} calls"
            )

    def get_results(self) -> list[ProfileResult]:
        """Get all profiling results"""
        return self.results

    def get_summary(self) -> Dict:
        """Get profiling summary"""
        if not self.results:
            return {"message": "No profiling data"}

        total_duration = sum(r.duration_seconds for r in self.results)
        avg_duration = total_duration / len(self.results)
        max_memory = max(r.memory_mb for r in self.results)

        return {
            "total_profiles": len(self.results),
            "total_duration_seconds": total_duration,
            "average_duration_seconds": avg_duration,
            "max_memory_mb": max_memory,
            "profiles": [r.to_dict() for r in self.results]
        }

    def save_results(self, filename: str):
        """Save profiling results to JSON file"""
        summary = self.get_summary()
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Profiling results saved to {filename}")

    def clear_results(self):
        """Clear all profiling results"""
        self.results.clear()


class DatabaseProfiler:
    """
    Profile database queries

    Usage:
        db_profiler = DatabaseProfiler()

        with db_profiler.profile_query("get_user"):
            user = db.query(User).filter(User.id == user_id).first()

        print(db_profiler.get_slow_queries())
    """

    def __init__(self, slow_query_threshold: float = 0.1):
        """
        Initialize database profiler

        Args:
            slow_query_threshold: Threshold in seconds for slow queries
        """
        self.slow_query_threshold = slow_query_threshold
        self.queries: list[Dict] = []

    @contextmanager
    def profile_query(self, query_name: str, query_sql: Optional[str] = None):
        """
        Profile a database query

        Args:
            query_name: Name/description of the query
            query_sql: Optional SQL query text
        """
        start_time = time.time()

        try:
            yield

        finally:
            duration = time.time() - start_time

            query_info = {
                "name": query_name,
                "duration_seconds": duration,
                "is_slow": duration > self.slow_query_threshold,
                "sql": query_sql,
                "timestamp": datetime.utcnow().isoformat()
            }

            self.queries.append(query_info)

            if query_info["is_slow"]:
                logger.warning(
                    f"Slow query [{query_name}]: {duration:.3f}s"
                )

    def get_slow_queries(self) -> list[Dict]:
        """Get all slow queries"""
        return [q for q in self.queries if q["is_slow"]]

    def get_query_stats(self) -> Dict:
        """Get query statistics"""
        if not self.queries:
            return {"message": "No query data"}

        total_queries = len(self.queries)
        slow_queries = len(self.get_slow_queries())
        total_time = sum(q["duration_seconds"] for q in self.queries)
        avg_time = total_time / total_queries

        return {
            "total_queries": total_queries,
            "slow_queries": slow_queries,
            "slow_query_percentage": (slow_queries / total_queries * 100) if total_queries > 0 else 0,
            "total_time_seconds": total_time,
            "average_time_seconds": avg_time,
            "slowest_query": max(self.queries, key=lambda q: q["duration_seconds"]) if self.queries else None
        }


class APIEndpointProfiler:
    """
    Profile API endpoints

    Usage:
        api_profiler = APIEndpointProfiler()

        # In your FastAPI middleware
        async with api_profiler.profile_request(request.method, request.url.path):
            response = await call_next(request)
    """

    def __init__(self):
        self.requests: list[Dict] = []

    @contextmanager
    def profile_request(self, method: str, path: str):
        """Profile an API request"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        try:
            yield

        finally:
            duration = time.time() - start_time
            end_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_used = end_memory - start_memory

            request_info = {
                "method": method,
                "path": path,
                "duration_seconds": duration,
                "memory_mb": memory_used,
                "timestamp": datetime.utcnow().isoformat()
            }

            self.requests.append(request_info)

    def get_endpoint_stats(self) -> Dict:
        """Get endpoint statistics"""
        if not self.requests:
            return {"message": "No request data"}

        # Group by endpoint
        endpoints: Dict[str, list] = {}
        for req in self.requests:
            key = f"{req['method']} {req['path']}"
            if key not in endpoints:
                endpoints[key] = []
            endpoints[key].append(req)

        # Calculate stats per endpoint
        endpoint_stats = []
        for endpoint, requests in endpoints.items():
            durations = [r["duration_seconds"] for r in requests]
            endpoint_stats.append({
                "endpoint": endpoint,
                "count": len(requests),
                "avg_duration": sum(durations) / len(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "p95_duration": sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 20 else max(durations)
            })

        # Sort by slowest average
        endpoint_stats.sort(key=lambda x: x["avg_duration"], reverse=True)

        return {
            "total_requests": len(self.requests),
            "unique_endpoints": len(endpoints),
            "endpoints": endpoint_stats
        }


# ============================================================================
# Global Profiler Instances
# ============================================================================

# Global profilers (can be used across the application)
performance_profiler = PerformanceProfiler()
database_profiler = DatabaseProfiler()
api_profiler = APIEndpointProfiler()


# ============================================================================
# Convenience Functions
# ============================================================================

def profile_function(func: Callable = None, *, name: Optional[str] = None):
    """
    Convenience decorator for profiling functions

    Usage:
        @profile_function
        def my_function():
            pass

        @profile_function(name="custom_name")
        def another_function():
            pass
    """
    if func is None:
        # Called with arguments: @profile_function(name="custom")
        return lambda f: performance_profiler.profile(name=name)(f)
    else:
        # Called without arguments: @profile_function
        return performance_profiler.profile()(func)


def profile_query(query_name: str, query_sql: Optional[str] = None):
    """Convenience function for profiling queries"""
    return database_profiler.profile_query(query_name, query_sql)


def get_profiling_summary() -> Dict:
    """Get combined profiling summary"""
    return {
        "performance": performance_profiler.get_summary(),
        "database": database_profiler.get_query_stats(),
        "api": api_profiler.get_endpoint_stats()
    }


# ============================================================================
# Usage Examples
# ============================================================================

"""
1. Profile a Function:

   from performance.profiling_tools import profile_function

   @profile_function
   def expensive_computation(n: int):
       result = sum(i**2 for i in range(n))
       return result

   # Call the function
   result = expensive_computation(1000000)

   # View results
   from performance.profiling_tools import performance_profiler
   print(performance_profiler.get_summary())

2. Profile a Code Block:

   from performance.profiling_tools import performance_profiler

   with performance_profiler.profile_block("data_processing"):
       # Load data
       data = load_large_dataset()

       # Process data
       processed = process_data(data)

       # Save results
       save_results(processed)

3. Profile Database Queries:

   from performance.profiling_tools import profile_query

   with profile_query("fetch_user", "SELECT * FROM users WHERE id = ?"):
       user = db.query(User).filter(User.id == user_id).first()

   # Check slow queries
   from performance.profiling_tools import database_profiler
   slow_queries = database_profiler.get_slow_queries()
   for query in slow_queries:
       print(f"Slow: {query['name']} - {query['duration_seconds']:.3f}s")

4. Profile API Endpoints (FastAPI Middleware):

   from fastapi import FastAPI, Request
   from performance.profiling_tools import api_profiler

   app = FastAPI()

   @app.middleware("http")
   async def profiling_middleware(request: Request, call_next):
       async with api_profiler.profile_request(request.method, request.url.path):
           response = await call_next(request)
       return response

   # View endpoint stats
   @app.get("/profiling/stats")
   def get_stats():
       return api_profiler.get_endpoint_stats()

5. Save Profiling Results:

   from performance.profiling_tools import performance_profiler

   # Run your code...

   # Save results
   performance_profiler.save_results("profiling_results.json")

6. Get Combined Summary:

   from performance.profiling_tools import get_profiling_summary

   summary = get_profiling_summary()
   print(json.dumps(summary, indent=2))

7. Identify Performance Bottlenecks:

   from performance.profiling_tools import performance_profiler

   @profile_function
   def process_data():
       with performance_profiler.profile_block("loading"):
           data = load_data()

       with performance_profiler.profile_block("transformation"):
           transformed = transform(data)

       with performance_profiler.profile_block("saving"):
           save(transformed)

   process_data()

   # Check which block is slowest
   results = performance_profiler.get_results()
   for result in results:
       print(f"{result.name}: {result.duration_seconds:.3f}s")

8. Memory Profiling:

   from performance.profiling_tools import PerformanceProfiler

   profiler = PerformanceProfiler()

   @profiler.profile()
   def memory_intensive_function():
       # Allocate large data structure
       data = [i for i in range(10000000)]
       return sum(data)

   memory_intensive_function()

   # Check memory usage
   results = profiler.get_results()
   for result in results:
       print(f"Peak memory: {result.peak_memory_mb:.1f}MB")

Expected Usage in Production:
- Profile slow endpoints to identify bottlenecks
- Monitor database query performance
- Track memory usage for memory-intensive operations
- Generate flame graphs for visualization
- Identify performance regressions
"""
