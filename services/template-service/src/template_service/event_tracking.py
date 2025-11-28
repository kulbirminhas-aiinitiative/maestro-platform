"""
Event Tracking Integration for Maestro Templates
Provides event tracking capabilities using the quality-fabric template tracker.

This module bridges maestro-templates with the template tracking system,
publishing usage events to Redis Streams for analysis.
"""

import sys
import os
import logging
from typing import Optional

# Quality-fabric integration (disabled for standalone deployment)
# Uncomment when quality-fabric is available
# quality_fabric_path = os.path.join(
#     os.path.dirname(__file__),
#     '../../../quality-fabric'
# )
# sys.path.insert(0, quality_fabric_path)
# from services.template_tracker.publisher import EventPublisher

# Stub EventPublisher for standalone deployment
class EventPublisher:
    """Stub event publisher for standalone mode"""
    def __init__(self, **kwargs):
        pass

    async def initialize(self):
        pass

    async def publish_search(self, **kwargs):
        logger.debug(f"Event tracking (stub): search event - {kwargs}")

    async def publish_retrieval(self, **kwargs):
        logger.debug(f"Event tracking (stub): retrieval event - {kwargs}")

    async def publish_download(self, **kwargs):
        logger.debug(f"Event tracking (stub): download event - {kwargs}")

    async def publish_feedback(self, **kwargs):
        logger.debug(f"Event tracking (stub): feedback event - {kwargs}")

logger = logging.getLogger(__name__)

# Global publisher instance
_event_publisher: Optional[EventPublisher] = None


async def get_event_publisher() -> EventPublisher:
    """
    Get or create the global event publisher instance.

    Returns:
        Initialized EventPublisher instance
    """
    global _event_publisher

    if _event_publisher is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _event_publisher = EventPublisher(
            redis_url=redis_url,
            stream_name="template_events",
            fallback_to_logging=True
        )
        try:
            await _event_publisher.initialize()
            logger.info("Event publisher initialized for template tracking")
        except Exception as e:
            logger.warning(f"Failed to initialize event publisher: {e}")

    return _event_publisher


async def track_template_search(
    query: Optional[str],
    results_count: int,
    category_filter: Optional[str] = None,
    language_filter: Optional[str] = None,
    framework_filter: Optional[str] = None,
    tags_filter: Optional[list] = None,
    min_quality_score: Optional[float] = None,
    search_duration_ms: float = 0.0,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Track template search event.

    Args:
        query: Search query string
        results_count: Number of results returned
        category_filter: Category filter applied
        language_filter: Language filter applied
        framework_filter: Framework filter applied
        tags_filter: Tags filter applied
        min_quality_score: Minimum quality score filter
        search_duration_ms: Search duration in milliseconds
        user_id: User ID
        session_id: Session ID
    """
    try:
        publisher = await get_event_publisher()
        await publisher.publish_search(
            query=query or "",
            results_count=results_count,
            category_filter=category_filter,
            language_filter=language_filter,
            framework_filter=framework_filter,
            tags_filter=tags_filter or [],
            min_quality_score=min_quality_score,
            search_duration_ms=search_duration_ms,
            user_id=user_id,
            session_id=session_id,
            service_name="maestro-templates",
            environment=os.getenv("ENVIRONMENT", "development")
        )
    except Exception as e:
        logger.warning(f"Failed to track search event: {e}")


async def track_template_retrieval(
    template_id: str,
    template_name: str,
    template_version: Optional[str] = None,
    template_category: Optional[str] = None,
    retrieval_method: str = "api",
    retrieval_duration_ms: float = 0.0,
    discovered_via: str = "search",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Track template retrieval event.

    Args:
        template_id: Template ID
        template_name: Template name
        template_version: Template version
        template_category: Template category
        retrieval_method: How template was retrieved (api, web, cli)
        retrieval_duration_ms: Retrieval duration in milliseconds
        discovered_via: How user found template (search, direct, recommendation)
        user_id: User ID
        session_id: Session ID
    """
    try:
        publisher = await get_event_publisher()
        await publisher.publish_retrieval(
            template_id=template_id,
            template_name=template_name,
            template_version=template_version,
            template_category=template_category,
            retrieval_method=retrieval_method,
            retrieval_duration_ms=retrieval_duration_ms,
            discovered_via=discovered_via,
            user_id=user_id,
            session_id=session_id,
            service_name="maestro-templates",
            environment=os.getenv("ENVIRONMENT", "development")
        )
    except Exception as e:
        logger.warning(f"Failed to track retrieval event: {e}")


async def track_template_download(
    template_id: str,
    template_name: str,
    template_version: str,
    download_format: str,
    download_size_mb: float,
    download_duration_ms: float = 0.0,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None
):
    """
    Track template download event.

    Args:
        template_id: Template ID
        template_name: Template name
        template_version: Template version downloaded
        download_format: Download format (zip, tar.gz)
        download_size_mb: Download size in MB
        download_duration_ms: Download duration in milliseconds
        user_id: User ID
        session_id: Session ID
    """
    try:
        publisher = await get_event_publisher()
        await publisher.publish_download(
            template_id=template_id,
            template_name=template_name,
            template_version=template_version,
            download_format=download_format,
            download_size_mb=download_size_mb,
            download_duration_ms=download_duration_ms,
            user_id=user_id,
            session_id=session_id,
            service_name="maestro-templates",
            environment=os.getenv("ENVIRONMENT", "development")
        )
    except Exception as e:
        logger.warning(f"Failed to track download event: {e}")


async def track_template_feedback(
    template_id: str,
    template_name: str,
    feedback_type: str,
    overall_rating: Optional[int] = None,
    comment: Optional[str] = None,
    would_recommend: Optional[bool] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs
):
    """
    Track template feedback event.

    Args:
        template_id: Template ID
        template_name: Template name
        feedback_type: Type of feedback (rating, comment, issue)
        overall_rating: Overall rating (1-5)
        comment: User comment
        would_recommend: Would user recommend
        user_id: User ID
        session_id: Session ID
        **kwargs: Additional feedback fields
    """
    try:
        publisher = await get_event_publisher()
        await publisher.publish_feedback(
            template_id=template_id,
            template_name=template_name,
            feedback_type=feedback_type,
            overall_rating=overall_rating,
            comment=comment,
            would_recommend=would_recommend,
            user_id=user_id,
            session_id=session_id,
            service_name="maestro-templates",
            environment=os.getenv("ENVIRONMENT", "development"),
            **kwargs
        )
    except Exception as e:
        logger.warning(f"Failed to track feedback event: {e}")
