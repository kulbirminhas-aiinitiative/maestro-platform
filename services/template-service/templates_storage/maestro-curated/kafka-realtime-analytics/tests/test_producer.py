"""
Unit tests for Producer Service
"""

import json
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'producer'))

from app import app as flask_app


@pytest.fixture
def client():
    """Create test client"""
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def mock_producer():
    """Mock Kafka producer"""
    with patch('app.producer') as mock:
        future_mock = Mock()
        future_mock.get.return_value = Mock(
            topic='events.test',
            partition=0,
            offset=123
        )
        mock.send.return_value = future_mock
        mock.flush.return_value = None
        yield mock


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'producer'


@patch('app.producer')
def test_ingest_event_success(mock_producer, client):
    """Test successful event ingestion"""
    # Setup mock
    future_mock = Mock()
    future_mock.get.return_value = Mock(
        topic='events.user_action',
        partition=0,
        offset=123
    )
    mock_producer.send.return_value = future_mock

    # Send request
    event = {
        'event_type': 'user_action',
        'data': {
            'user_id': 'user_123',
            'action': 'click'
        }
    }
    response = client.post('/api/events',
                          json=event,
                          content_type='application/json')

    # Assertions
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'event_id' in data
    assert data['topic'] == 'events.user_action'
    assert data['partition'] == 0
    assert data['offset'] == 123


def test_ingest_event_no_data(client):
    """Test event ingestion with no data"""
    response = client.post('/api/events',
                          data='',
                          content_type='application/json')
    assert response.status_code == 400


@patch('app.producer')
def test_ingest_batch_success(mock_producer, client):
    """Test successful batch ingestion"""
    # Setup mock
    future_mock = Mock()
    future_mock.get.return_value = Mock(
        topic='events.test',
        partition=0,
        offset=123
    )
    mock_producer.send.return_value = future_mock
    mock_producer.flush.return_value = None

    # Send request
    events = [
        {'event_type': 'transaction', 'data': {'amount': 100}},
        {'event_type': 'page_view', 'data': {'page': '/home'}}
    ]
    response = client.post('/api/events/batch',
                          json=events,
                          content_type='application/json')

    # Assertions
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['count'] == 2
    assert len(data['results']) == 2


def test_ingest_batch_invalid_format(client):
    """Test batch ingestion with invalid format"""
    response = client.post('/api/events/batch',
                          json={'not': 'array'},
                          content_type='application/json')
    assert response.status_code == 400


@patch('app.producer')
def test_simulate_traffic(mock_producer, client):
    """Test traffic simulation"""
    # Setup mock
    future_mock = Mock()
    mock_producer.send.return_value = future_mock
    mock_producer.flush.return_value = None

    # Send request
    response = client.post('/api/simulate',
                          json={'num_events': 10, 'event_type': 'user_action'},
                          content_type='application/json')

    # Assertions
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['events_generated'] == 10


@patch('app.producer')
def test_metrics_endpoint(mock_producer, client):
    """Test metrics endpoint"""
    # Setup mock
    mock_producer.metrics.return_value = {
        'record-send-rate': {'value': 100.5},
        'record-error-rate': {'value': 0.1},
        'request-latency-avg': {'value': 50.3}
    }

    response = client.get('/metrics')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'producer_metrics' in data
    assert data['producer_metrics']['record_send_rate'] == 100.5


def test_metrics_endpoint_no_producer(client):
    """Test metrics endpoint when producer not initialized"""
    with patch('app.producer', None):
        response = client.get('/metrics')
        assert response.status_code == 503