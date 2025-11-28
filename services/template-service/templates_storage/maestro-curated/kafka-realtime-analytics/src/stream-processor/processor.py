"""
Stream Processor - Real-Time Analytics Engine
Processes Kafka streams with windowed aggregations and anomaly detection
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict
import psycopg2
import redis
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'analytics')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'analytics_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'analytics_pass')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# Topics to consume
TOPICS = [
    'events.user_action',
    'events.transaction',
    'events.page_view',
    'events.error',
    'events.system_metric'
]


class StreamProcessor:
    """Real-time stream processor with windowed aggregations"""

    def __init__(self):
        self.consumer = None
        self.db_conn = None
        self.redis_client = None
        self.window_data = defaultdict(lambda: defaultdict(list))
        self.window_size = timedelta(minutes=5)

    def initialize(self):
        """Initialize connections with retry logic"""
        # Kafka Consumer
        max_retries = 10
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                self.consumer = KafkaConsumer(
                    *TOPICS,
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    auto_offset_reset='earliest',
                    enable_auto_commit=True,
                    group_id='stream-processor-group',
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    max_poll_records=500,
                    session_timeout_ms=30000
                )
                logger.info(f"Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
                break
            except Exception as e:
                logger.error(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise

        # PostgreSQL
        for attempt in range(max_retries):
            try:
                self.db_conn = psycopg2.connect(
                    host=POSTGRES_HOST,
                    database=POSTGRES_DB,
                    user=POSTGRES_USER,
                    password=POSTGRES_PASSWORD
                )
                logger.info("Connected to PostgreSQL")
                break
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise

        # Redis
        for attempt in range(max_retries):
            try:
                self.redis_client = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    decode_responses=True
                )
                self.redis_client.ping()
                logger.info("Connected to Redis")
                break
            except Exception as e:
                logger.error(f"Failed to connect to Redis (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise

    def process_message(self, message):
        """Process individual message"""
        try:
            event = message.value
            event_type = event.get('event_type')
            timestamp = datetime.fromisoformat(event.get('timestamp'))
            data = event.get('data', {})

            # Store raw event
            self.store_raw_event(event)

            # Add to windowed aggregation
            self.add_to_window(event_type, timestamp, data)

            # Real-time metrics
            self.update_realtime_metrics(event_type, data)

            # Anomaly detection
            self.detect_anomalies(event_type, data)

            logger.debug(f"Processed event: {event.get('event_id')}")

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def store_raw_event(self, event: Dict[str, Any]):
        """Store raw event in PostgreSQL"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO raw_events (event_id, event_type, timestamp, data, metadata)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                event.get('event_id'),
                event.get('event_type'),
                event.get('timestamp'),
                json.dumps(event.get('data')),
                json.dumps(event.get('metadata'))
            ))
            self.db_conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error storing raw event: {e}")
            self.db_conn.rollback()

    def add_to_window(self, event_type: str, timestamp: datetime, data: Dict[str, Any]):
        """Add event to windowed aggregation"""
        window_key = self.get_window_key(timestamp)
        self.window_data[event_type][window_key].append(data)

        # Check if window is complete
        current_time = datetime.utcnow()
        if current_time - timestamp > self.window_size:
            self.flush_window(event_type, window_key)

    def get_window_key(self, timestamp: datetime) -> str:
        """Get window key for timestamp"""
        # 5-minute windows
        window_start = timestamp.replace(second=0, microsecond=0)
        window_start = window_start.replace(minute=(window_start.minute // 5) * 5)
        return window_start.isoformat()

    def flush_window(self, event_type: str, window_key: str):
        """Flush completed window and compute aggregations"""
        if window_key not in self.window_data[event_type]:
            return

        events = self.window_data[event_type][window_key]

        if not events:
            return

        # Compute aggregations
        aggregation = self.compute_aggregations(event_type, window_key, events)

        # Store aggregation
        self.store_aggregation(aggregation)

        # Clear window data
        del self.window_data[event_type][window_key]

        logger.info(f"Flushed window: {event_type} @ {window_key} ({len(events)} events)")

    def compute_aggregations(self, event_type: str, window_key: str, events: List[Dict]) -> Dict[str, Any]:
        """Compute aggregations for window"""
        aggregation = {
            'event_type': event_type,
            'window_start': window_key,
            'count': len(events),
            'computed_at': datetime.utcnow().isoformat()
        }

        # Event-type specific aggregations
        if event_type == 'transaction':
            values = [e.get('value', 0) for e in events]
            aggregation['total_value'] = sum(values)
            aggregation['avg_value'] = sum(values) / len(values) if values else 0
            aggregation['max_value'] = max(values) if values else 0
            aggregation['min_value'] = min(values) if values else 0

        elif event_type == 'page_view':
            regions = [e.get('region') for e in events]
            aggregation['region_distribution'] = {
                region: regions.count(region) for region in set(regions)
            }

        elif event_type == 'error':
            error_types = [e.get('error_type') for e in events]
            aggregation['error_distribution'] = {
                error: error_types.count(error) for error in set(error_types)
            }

        return aggregation

    def store_aggregation(self, aggregation: Dict[str, Any]):
        """Store computed aggregation"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO aggregations (event_type, window_start, count, metrics, computed_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                aggregation.get('event_type'),
                aggregation.get('window_start'),
                aggregation.get('count'),
                json.dumps(aggregation),
                aggregation.get('computed_at')
            ))
            self.db_conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error storing aggregation: {e}")
            self.db_conn.rollback()

    def update_realtime_metrics(self, event_type: str, data: Dict[str, Any]):
        """Update real-time metrics in Redis"""
        try:
            # Increment event counter
            self.redis_client.incr(f"metrics:count:{event_type}")

            # Update by region
            region = data.get('region', 'unknown')
            self.redis_client.hincrby(f"metrics:region:{event_type}", region, 1)

            # Recent events (sliding window)
            self.redis_client.lpush(f"metrics:recent:{event_type}", json.dumps(data))
            self.redis_client.ltrim(f"metrics:recent:{event_type}", 0, 999)

            # Set TTL
            self.redis_client.expire(f"metrics:count:{event_type}", 3600)
            self.redis_client.expire(f"metrics:region:{event_type}", 3600)
            self.redis_client.expire(f"metrics:recent:{event_type}", 3600)

        except Exception as e:
            logger.error(f"Error updating real-time metrics: {e}")

    def detect_anomalies(self, event_type: str, data: Dict[str, Any]):
        """Simple anomaly detection"""
        try:
            # Get historical average
            recent_values_json = self.redis_client.lrange(f"metrics:recent:{event_type}", 0, 99)
            if len(recent_values_json) < 10:
                return

            recent_values = [json.loads(v).get('value', 0) for v in recent_values_json]
            avg_value = sum(recent_values) / len(recent_values)
            current_value = data.get('value', 0)

            # Simple threshold-based detection
            threshold = 3.0
            if avg_value > 0 and abs(current_value - avg_value) > threshold * avg_value:
                anomaly = {
                    'event_type': event_type,
                    'detected_at': datetime.utcnow().isoformat(),
                    'current_value': current_value,
                    'expected_value': avg_value,
                    'deviation': abs(current_value - avg_value) / avg_value
                }
                self.store_anomaly(anomaly)
                logger.warning(f"Anomaly detected: {anomaly}")

        except Exception as e:
            logger.error(f"Error in anomaly detection: {e}")

    def store_anomaly(self, anomaly: Dict[str, Any]):
        """Store detected anomaly"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT INTO anomalies (event_type, detected_at, details)
                VALUES (%s, %s, %s)
            """, (
                anomaly.get('event_type'),
                anomaly.get('detected_at'),
                json.dumps(anomaly)
            ))
            self.db_conn.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error storing anomaly: {e}")
            self.db_conn.rollback()

    def run(self):
        """Main processing loop"""
        logger.info("Starting stream processor...")
        self.initialize()

        try:
            for message in self.consumer:
                self.process_message(message)

        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        if self.consumer:
            self.consumer.close()
        if self.db_conn:
            self.db_conn.close()
        if self.redis_client:
            self.redis_client.close()
        logger.info("Cleanup complete")


if __name__ == '__main__':
    processor = StreamProcessor()
    processor.run()