"""
Prometheus Metrics Module
Centralized metrics registry with singleton pattern to avoid duplication issues
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY
import structlog

logger = structlog.get_logger(__name__)

# Use the default registry
_metrics_registry = REGISTRY
_metrics_initialized = False
_metrics = {}


def get_metrics():
    """
    Get or initialize metrics with singleton pattern.
    This prevents duplication errors when metrics are re-imported.
    """
    global _metrics_initialized, _metrics

    if _metrics_initialized:
        return _metrics

    try:
        # Registry requests
        _metrics['registry_requests'] = Counter(
            'registry_requests_total',
            'Total registry requests',
            ['method', 'endpoint', 'status_code'],
            registry=_metrics_registry
        )

        # Request duration
        _metrics['registry_duration'] = Histogram(
            'registry_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint'],
            registry=_metrics_registry
        )

        # Active services
        _metrics['active_services'] = Gauge(
            'active_services_total',
            'Total active services',
            registry=_metrics_registry
        )

        # Port conflicts
        _metrics['port_conflicts'] = Counter(
            'port_conflicts_total',
            'Port conflicts detected',
            registry=_metrics_registry
        )

        # Asset violations
        _metrics['asset_violations'] = Counter(
            'asset_violations_total',
            'Asset violations detected',
            registry=_metrics_registry
        )

        # Template operations
        _metrics['template_operations'] = Counter(
            'template_operations_total',
            'Template operations performed',
            ['operation', 'status'],
            registry=_metrics_registry
        )

        # Template search queries
        _metrics['template_searches'] = Counter(
            'template_searches_total',
            'Template search queries',
            ['category', 'language'],
            registry=_metrics_registry
        )

        # Template downloads
        _metrics['template_downloads'] = Counter(
            'template_downloads_total',
            'Template downloads',
            ['template_id', 'persona'],
            registry=_metrics_registry
        )

        # Database operations
        _metrics['db_operations'] = Histogram(
            'database_operation_duration_seconds',
            'Database operation duration',
            ['operation'],
            registry=_metrics_registry
        )

        # Cache operations
        _metrics['cache_operations'] = Counter(
            'cache_operations_total',
            'Cache operations',
            ['operation', 'hit_miss'],
            registry=_metrics_registry
        )

        _metrics_initialized = True
        logger.info("metrics_initialized", count=len(_metrics))

    except Exception as e:
        # If metrics are already registered, log warning but continue
        logger.warning("metrics_registration_warning", error=str(e))
        # Try to get existing metrics from registry
        for collector in _metrics_registry._collector_to_names.keys():
            for name in _metrics_registry._collector_to_names[collector]:
                if 'registry_requests' in name and 'registry_requests' not in _metrics:
                    _metrics['registry_requests'] = collector
                elif 'registry_duration' in name and 'registry_duration' not in _metrics:
                    _metrics['registry_duration'] = collector
                elif 'active_services' in name and 'active_services' not in _metrics:
                    _metrics['active_services'] = collector
                elif 'port_conflicts' in name and 'port_conflicts' not in _metrics:
                    _metrics['port_conflicts'] = collector
                elif 'asset_violations' in name and 'asset_violations' not in _metrics:
                    _metrics['asset_violations'] = collector
        _metrics_initialized = True

    return _metrics


def record_request(method: str, endpoint: str, status_code: int):
    """Record an API request"""
    metrics = get_metrics()
    if 'registry_requests' in metrics:
        metrics['registry_requests'].labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()


def observe_duration(method: str, endpoint: str, duration: float):
    """Observe request duration"""
    metrics = get_metrics()
    if 'registry_duration' in metrics:
        metrics['registry_duration'].labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)


def set_active_services(count: int):
    """Set number of active services"""
    metrics = get_metrics()
    if 'active_services' in metrics:
        metrics['active_services'].set(count)


def increment_port_conflicts():
    """Increment port conflicts counter"""
    metrics = get_metrics()
    if 'port_conflicts' in metrics:
        metrics['port_conflicts'].inc()


def increment_asset_violations():
    """Increment asset violations counter"""
    metrics = get_metrics()
    if 'asset_violations' in metrics:
        metrics['asset_violations'].inc()


def record_template_operation(operation: str, status: str):
    """Record template operation"""
    metrics = get_metrics()
    if 'template_operations' in metrics:
        metrics['template_operations'].labels(
            operation=operation,
            status=status
        ).inc()


def record_template_search(category: str = "all", language: str = "all"):
    """Record template search"""
    metrics = get_metrics()
    if 'template_searches' in metrics:
        metrics['template_searches'].labels(
            category=category,
            language=language
        ).inc()


def record_template_download(template_id: str, persona: str):
    """Record template download"""
    metrics = get_metrics()
    if 'template_downloads' in metrics:
        metrics['template_downloads'].labels(
            template_id=template_id,
            persona=persona
        ).inc()


def observe_db_operation(operation: str, duration: float):
    """Observe database operation duration"""
    metrics = get_metrics()
    if 'db_operations' in metrics:
        metrics['db_operations'].labels(
            operation=operation
        ).observe(duration)


def record_cache_operation(operation: str, hit_miss: str):
    """Record cache operation"""
    metrics = get_metrics()
    if 'cache_operations' in metrics:
        metrics['cache_operations'].labels(
            operation=operation,
            hit_miss=hit_miss
        ).inc()


# Initialize metrics when module is imported
get_metrics()
