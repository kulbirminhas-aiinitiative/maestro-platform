"""
Producer Service - Real-Time Data Ingestion
Ingests data from multiple sources and publishes to Kafka topics
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any
from flask import Flask, request, jsonify
from kafka import KafkaProducer
from kafka.errors import KafkaError
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
SERVICE_PORT = int(os.getenv('SERVICE_PORT', 8080))

# Initialize Kafka producer
producer = None


def create_kafka_producer():
    """Create and configure Kafka producer with retry logic"""
    max_retries = 10
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            prod = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                max_in_flight_requests_per_connection=1,
                compression_type='gzip'
            )
            logger.info(f"Successfully connected to Kafka at {KAFKA_BOOTSTRAP_SERVERS}")
            return prod
        except Exception as e:
            logger.error(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise


@app.before_request
def initialize_producer():
    """Initialize producer before first request"""
    global producer
    if producer is None:
        producer = create_kafka_producer()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'producer',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/events', methods=['POST'])
def ingest_event():
    """Ingest a single event and publish to Kafka"""
    try:
        event_data = request.json

        if not event_data:
            return jsonify({'error': 'No data provided'}), 400

        # Enrich event with metadata
        enriched_event = {
            'event_id': event_data.get('event_id', f"evt_{int(time.time() * 1000)}"),
            'timestamp': event_data.get('timestamp', datetime.utcnow().isoformat()),
            'event_type': event_data.get('event_type', 'generic'),
            'data': event_data.get('data', {}),
            'metadata': {
                'source': 'producer-service',
                'ingestion_time': datetime.utcnow().isoformat()
            }
        }

        # Determine topic based on event type
        topic = f"events.{enriched_event['event_type']}"
        key = enriched_event['event_id']

        # Send to Kafka
        future = producer.send(topic, key=key, value=enriched_event)

        # Wait for confirmation (with timeout)
        record_metadata = future.get(timeout=10)

        logger.info(f"Event published: topic={record_metadata.topic}, partition={record_metadata.partition}, offset={record_metadata.offset}")

        return jsonify({
            'status': 'success',
            'event_id': enriched_event['event_id'],
            'topic': record_metadata.topic,
            'partition': record_metadata.partition,
            'offset': record_metadata.offset
        }), 201

    except KafkaError as e:
        logger.error(f"Kafka error: {e}")
        return jsonify({'error': 'Failed to publish event', 'details': str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/events/batch', methods=['POST'])
def ingest_batch():
    """Ingest a batch of events"""
    try:
        events = request.json

        if not isinstance(events, list):
            return jsonify({'error': 'Expected array of events'}), 400

        results = []

        for event_data in events:
            enriched_event = {
                'event_id': event_data.get('event_id', f"evt_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"),
                'timestamp': event_data.get('timestamp', datetime.utcnow().isoformat()),
                'event_type': event_data.get('event_type', 'generic'),
                'data': event_data.get('data', {}),
                'metadata': {
                    'source': 'producer-service',
                    'ingestion_time': datetime.utcnow().isoformat()
                }
            }

            topic = f"events.{enriched_event['event_type']}"
            key = enriched_event['event_id']

            future = producer.send(topic, key=key, value=enriched_event)
            results.append({
                'event_id': enriched_event['event_id'],
                'status': 'submitted'
            })

        # Flush to ensure all messages are sent
        producer.flush(timeout=10)

        logger.info(f"Batch of {len(events)} events published successfully")

        return jsonify({
            'status': 'success',
            'count': len(events),
            'results': results
        }), 201

    except Exception as e:
        logger.error(f"Batch ingestion error: {e}")
        return jsonify({'error': 'Batch ingestion failed', 'details': str(e)}), 500


@app.route('/api/simulate', methods=['POST'])
def simulate_traffic():
    """Simulate traffic for testing"""
    try:
        config = request.json or {}
        num_events = config.get('num_events', 100)
        event_type = config.get('event_type', 'user_action')

        event_types = ['user_action', 'transaction', 'page_view', 'error', 'system_metric']

        for i in range(num_events):
            event = {
                'event_id': f"sim_{int(time.time() * 1000)}_{i}",
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': random.choice(event_types) if event_type == 'random' else event_type,
                'data': {
                    'user_id': f"user_{random.randint(1, 1000)}",
                    'value': random.randint(1, 100),
                    'metric': random.choice(['clicks', 'views', 'purchases', 'errors']),
                    'region': random.choice(['us-east', 'us-west', 'eu-west', 'ap-south'])
                },
                'metadata': {
                    'source': 'simulator',
                    'ingestion_time': datetime.utcnow().isoformat()
                }
            }

            topic = f"events.{event['event_type']}"
            producer.send(topic, key=event['event_id'], value=event)

        producer.flush()

        return jsonify({
            'status': 'success',
            'events_generated': num_events
        }), 200

    except Exception as e:
        logger.error(f"Simulation error: {e}")
        return jsonify({'error': 'Simulation failed', 'details': str(e)}), 500


@app.route('/metrics', methods=['GET'])
def metrics():
    """Expose metrics for monitoring"""
    if producer:
        metrics_dict = producer.metrics()
        return jsonify({
            'producer_metrics': {
                'record_send_rate': metrics_dict.get('record-send-rate', {}).get('value', 0),
                'record_error_rate': metrics_dict.get('record-error-rate', {}).get('value', 0),
                'request_latency_avg': metrics_dict.get('request-latency-avg', {}).get('value', 0)
            }
        }), 200
    return jsonify({'error': 'Producer not initialized'}), 503


if __name__ == '__main__':
    logger.info(f"Starting Producer Service on port {SERVICE_PORT}")
    app.run(host='0.0.0.0', port=SERVICE_PORT, debug=False)