"""
API Service - Analytics Query Interface
REST API for querying processed analytics and real-time metrics
Enhanced with Prometheus metrics per ADR-006
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import psycopg2
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)

# Prometheus Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

db_connections = Gauge('db_connections', 'Number of active database connections')
cache_hits = Counter('cache_hits_total', 'Total cache hits', ['operation'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['operation'])
events_queried = Counter('events_queried_total', 'Total events queried', ['event_type'])
anomalies_detected = Counter('anomalies_detected_total', 'Total anomalies detected')

# Configuration
SERVICE_PORT = int(os.getenv('SERVICE_PORT', 8081))
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'analytics')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'analytics_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'analytics_pass')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Database connection
db_conn = None
redis_client = None


def get_db_connection():
    """Get or create database connection"""
    global db_conn
    if db_conn is None or db_conn.closed:
        db_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD
        )
    return db_conn


def get_redis_client():
    """Get or create Redis client"""
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
    return redis_client


@app.before_request
def before_request():
    """Track request start time"""
    request.start_time = datetime.now()


@app.after_request
def after_request(response):
    """Track metrics after each request"""
    if hasattr(request, 'start_time'):
        duration = (datetime.now() - request.start_time).total_seconds()
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.path
        ).observe(duration)

    http_requests_total.labels(
        method=request.method,
        endpoint=request.path,
        status_code=response.status_code
    ).inc()

    return response


@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with dependency checks"""
    health_status = {
        'status': 'healthy',
        'service': 'analytics-api',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat(),
        'dependencies': {}
    }

    try:
        # Check database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
        health_status['dependencies']['postgresql'] = {'status': 'healthy', 'required': True}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status['dependencies']['postgresql'] = {'status': 'unhealthy', 'required': True, 'error': str(e)}
        health_status['status'] = 'degraded'

    try:
        # Check Redis
        r = get_redis_client()
        r.ping()
        health_status['dependencies']['redis'] = {'status': 'healthy', 'required': False}
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status['dependencies']['redis'] = {'status': 'unhealthy', 'required': False, 'error': str(e)}
        if health_status['status'] != 'degraded':
            health_status['status'] = 'degraded'

    # Return appropriate status code
    status_code = 200 if health_status['status'] == 'healthy' else 503

    return jsonify(health_status), status_code


@app.route('/api/events', methods=['GET'])
def get_events():
    """Query raw events"""
    try:
        # Query parameters
        event_type = request.args.get('event_type')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))

        conn = get_db_connection()
        cursor = conn.cursor()

        # Build query
        query = "SELECT event_id, event_type, timestamp, data, metadata FROM raw_events WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)

        if start_time:
            query += " AND timestamp >= %s"
            params.append(start_time)

        if end_time:
            query += " AND timestamp <= %s"
            params.append(end_time)

        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        events = []
        for row in rows:
            events.append({
                'event_id': row[0],
                'event_type': row[1],
                'timestamp': row[2].isoformat() if row[2] else None,
                'data': row[3],
                'metadata': row[4]
            })

        cursor.close()

        return jsonify({
            'events': events,
            'count': len(events),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        logger.error(f"Error querying events: {e}")
        return jsonify({'error': 'Failed to query events', 'details': str(e)}), 500


@app.route('/api/aggregations', methods=['GET'])
def get_aggregations():
    """Query aggregated data"""
    try:
        event_type = request.args.get('event_type')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        limit = int(request.args.get('limit', 100))

        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT event_type, window_start, count, metrics, computed_at FROM aggregations WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)

        if start_time:
            query += " AND window_start >= %s"
            params.append(start_time)

        if end_time:
            query += " AND window_start <= %s"
            params.append(end_time)

        query += " ORDER BY window_start DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        aggregations = []
        for row in rows:
            aggregations.append({
                'event_type': row[0],
                'window_start': row[1].isoformat() if row[1] else None,
                'count': row[2],
                'metrics': row[3],
                'computed_at': row[4].isoformat() if row[4] else None
            })

        cursor.close()

        return jsonify({
            'aggregations': aggregations,
            'count': len(aggregations)
        }), 200

    except Exception as e:
        logger.error(f"Error querying aggregations: {e}")
        return jsonify({'error': 'Failed to query aggregations', 'details': str(e)}), 500


@app.route('/api/metrics/realtime', methods=['GET'])
def get_realtime_metrics():
    """Get real-time metrics from Redis"""
    try:
        event_type = request.args.get('event_type', 'user_action')
        r = get_redis_client()

        # Get counts
        count = r.get(f"metrics:count:{event_type}") or 0

        # Get region distribution
        region_dist = r.hgetall(f"metrics:region:{event_type}")

        # Get recent events
        recent_events = r.lrange(f"metrics:recent:{event_type}", 0, 9)
        recent_parsed = [json.loads(e) for e in recent_events]

        return jsonify({
            'event_type': event_type,
            'total_count': int(count),
            'region_distribution': region_dist,
            'recent_events': recent_parsed,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error getting real-time metrics: {e}")
        return jsonify({'error': 'Failed to get metrics', 'details': str(e)}), 500


@app.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    """Query detected anomalies"""
    try:
        event_type = request.args.get('event_type')
        limit = int(request.args.get('limit', 50))

        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT event_type, detected_at, details FROM anomalies WHERE 1=1"
        params = []

        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)

        query += " ORDER BY detected_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        anomalies = []
        for row in rows:
            anomalies.append({
                'event_type': row[0],
                'detected_at': row[1].isoformat() if row[1] else None,
                'details': row[2]
            })

        cursor.close()

        return jsonify({
            'anomalies': anomalies,
            'count': len(anomalies)
        }), 200

    except Exception as e:
        logger.error(f"Error querying anomalies: {e}")
        return jsonify({'error': 'Failed to query anomalies', 'details': str(e)}), 500


@app.route('/api/dashboard/summary', methods=['GET'])
def get_dashboard_summary():
    """Get dashboard summary data"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total events in last 24 hours
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM raw_events
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY event_type
        """)
        event_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Recent aggregations
        cursor.execute("""
            SELECT event_type, SUM(count) as total
            FROM aggregations
            WHERE window_start >= NOW() - INTERVAL '1 hour'
            GROUP BY event_type
        """)
        recent_aggs = {row[0]: row[1] for row in cursor.fetchall()}

        # Recent anomalies
        cursor.execute("""
            SELECT COUNT(*) FROM anomalies
            WHERE detected_at >= NOW() - INTERVAL '24 hours'
        """)
        anomaly_count = cursor.fetchone()[0]

        cursor.close()

        # Redis metrics
        r = get_redis_client()
        redis_metrics = {}
        for event_type in ['user_action', 'transaction', 'page_view', 'error', 'system_metric']:
            count = r.get(f"metrics:count:{event_type}") or 0
            redis_metrics[event_type] = int(count)

        return jsonify({
            'summary': {
                'event_counts_24h': event_counts,
                'recent_aggregations_1h': recent_aggs,
                'anomalies_24h': anomaly_count,
                'realtime_counts': redis_metrics
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error generating dashboard summary: {e}")
        return jsonify({'error': 'Failed to generate summary', 'details': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total events
        cursor.execute("SELECT COUNT(*) FROM raw_events")
        total_events = cursor.fetchone()[0]

        # Total aggregations
        cursor.execute("SELECT COUNT(*) FROM aggregations")
        total_aggregations = cursor.fetchone()[0]

        # Total anomalies
        cursor.execute("SELECT COUNT(*) FROM anomalies")
        total_anomalies = cursor.fetchone()[0]

        # Database size
        cursor.execute("SELECT pg_database_size(%s)", (POSTGRES_DB,))
        db_size = cursor.fetchone()[0]

        cursor.close()

        return jsonify({
            'stats': {
                'total_events': total_events,
                'total_aggregations': total_aggregations,
                'total_anomalies': total_anomalies,
                'database_size_bytes': db_size
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Failed to get stats', 'details': str(e)}), 500


if __name__ == '__main__':
    logger.info(f"Starting API Service on port {SERVICE_PORT}")
    app.run(host='0.0.0.0', port=SERVICE_PORT, debug=False)