"""
Shared dependencies for FastAPI routers
Provides access to global service instances
"""

from fastapi import Request

# These will be set by the main app during startup
_db_pool = None
_redis_client = None
_git_manager = None
_cache_manager = None


def set_dependencies(db_pool, redis_client, git_manager, cache_manager):
    """Set global dependencies - called from main app lifespan."""
    global _db_pool, _redis_client, _git_manager, _cache_manager
    _db_pool = db_pool
    _redis_client = redis_client
    _git_manager = git_manager
    _cache_manager = cache_manager


async def get_db_pool(request: Request = None):
    """Get database pool dependency."""
    if request and hasattr(request.app.state, 'db_pool'):
        return request.app.state.db_pool
    return _db_pool


async def get_redis_client(request: Request = None):
    """Get Redis client dependency."""
    if request and hasattr(request.app.state, 'redis_client'):
        return request.app.state.redis_client
    return _redis_client


async def get_git_manager(request: Request = None):
    """Get Git manager dependency."""
    if request and hasattr(request.app.state, 'git_manager'):
        return request.app.state.git_manager
    return _git_manager


async def get_cache_manager(request: Request = None):
    """Get Cache manager dependency."""
    if request and hasattr(request.app.state, 'cache_manager'):
        return request.app.state.cache_manager
    return _cache_manager