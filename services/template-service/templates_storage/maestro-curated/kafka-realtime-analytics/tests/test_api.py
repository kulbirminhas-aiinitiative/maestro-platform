"""
Unit tests for API Service
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'api'))

from app import app as flask_app


@pytest.fixture
def client():
    """Create test client"""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def mock_db():
    """Mock database connection"""
    with patch('app.get_db_connection') as mock:
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        mock.return_value = conn
        yield cursor


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch('app.get_redis_client') as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_health_check_success(client, mock_db, mock_redis):
    """Test successful health check"""
    mock_db.execute.return_value = None
    mock_redis.ping.return_value = True

    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['dependencies']['postgres'] == 'connected'
    assert data['dependencies']['redis'] == 'connected'


def test_get_events(client, mock_db):
    """Test get events endpoint"""
    # Mock database response
    mock_db.fetchall.return_value = [
        ('evt_123', 'user_action', datetime(2025, 9, 30, 12, 0, 0),
         {'user_id': 'user_123'}, {'source': 'test'})
    ]

    response = client.get('/api/events?event_type=user_action&limit=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'events' in data
    assert len(data['events']) == 1
    assert data['events'][0]['event_type'] == 'user_action'


def test_get_events_with_filters(client, mock_db):
    """Test get events with filters"""
    mock_db.fetchall.return_value = []

    response = client.get('/api/events?event_type=transaction&start_time=2025-09-30T00:00:00&end_time=2025-09-30T23:59:59&limit=50&offset=10')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['limit'] == 50
    assert data['offset'] == 10


def test_get_aggregations(client, mock_db):
    """Test get aggregations endpoint"""
    # Mock database response
    mock_db.fetchall.return_value = [
        ('transaction', datetime(2025, 9, 30, 12, 0, 0), 1500,
         {'total_value': 150000, 'avg_value': 100}, datetime(2025, 9, 30, 12, 5, 0))
    ]

    response = client.get('/api/aggregations?event_type=transaction')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'aggregations' in data
    assert len(data['aggregations']) == 1
    assert data['aggregations'][0]['count'] == 1500


def test_get_realtime_metrics(client, mock_redis):
    """Test get real-time metrics endpoint"""
    # Mock Redis response
    mock_redis.get.return_value = '12345'
    mock_redis.hgetall.return_value = {'us-east': '5000', 'us-west': '7345'}
    mock_redis.lrange.return_value = [
        json.dumps({'user_id': 'user_123', 'value': 42}),
        json.dumps({'user_id': 'user_456', 'value': 55})
    ]

    response = client.get('/api/metrics/realtime?event_type=user_action')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['event_type'] == 'user_action'
    assert data['total_count'] == 12345
    assert 'region_distribution' in data
    assert len(data['recent_events']) == 2


def test_get_anomalies(client, mock_db):
    """Test get anomalies endpoint"""
    # Mock database response
    mock_db.fetchall.return_value = [
        ('transaction', datetime(2025, 9, 30, 12, 15, 0),
         {'current_value': 9999, 'expected_value': 100})
    ]

    response = client.get('/api/anomalies?event_type=transaction&limit=20')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'anomalies' in data
    assert data['count'] == 1


def test_get_dashboard_summary(client, mock_db, mock_redis):
    """Test dashboard summary endpoint"""
    # Mock database responses
    mock_db.fetchall.side_effect = [
        [('user_action', 1000), ('transaction', 500)],  # event_counts
        [('user_action', 100), ('transaction', 50)],    # recent_aggs
    ]
    mock_db.fetchone.return_value = (15,)  # anomaly_count

    # Mock Redis responses
    mock_redis.get.side_effect = ['1234', '567', '890', '123', '456']

    response = client.get('/api/dashboard/summary')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'summary' in data
    assert 'event_counts_24h' in data['summary']
    assert 'anomalies_24h' in data['summary']


def test_get_stats(client, mock_db):
    """Test system stats endpoint"""
    # Mock database responses
    mock_db.fetchone.side_effect = [
        (1000000,),  # total events
        (5000,),     # total aggregations
        (50,),       # total anomalies
        (1234567890,)  # db size
    ]

    response = client.get('/api/stats')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'stats' in data
    assert data['stats']['total_events'] == 1000000
    assert data['stats']['total_aggregations'] == 5000


def test_error_handling(client, mock_db):
    """Test error handling"""
    mock_db.execute.side_effect = Exception("Database error")

    response = client.get('/api/events')
    assert response.status_code == 500
    data = json.loads(response.data)
    assert 'error' in data