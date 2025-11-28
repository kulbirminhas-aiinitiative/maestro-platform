# Redis Streams Configuration for Maestro Platform

**Date**: October 26, 2025
**Purpose**: Job queue infrastructure for Automation Service (CARS)
**Redis Instance**: maestro-redis (port 27379)

---

## Configuration

### Redis Streams Setup

```python
# Connection configuration
REDIS_HOST = "maestro-redis"
REDIS_PORT = 6379
REDIS_PASSWORD = "maestro_redis_secure_2025"

# Stream names for different job types
STREAMS = {
    "automation_jobs": "maestro:streams:automation:jobs",
    "test_healing": "maestro:streams:automation:healing",
    "error_monitoring": "maestro:streams:automation:errors",
    "validation": "maestro:streams:automation:validation"
}

# Consumer groups
CONSUMER_GROUPS = {
    "automation_workers": "maestro-automation-workers",
    "healing_workers": "maestro-healing-workers",
    "monitoring_workers": "maestro-monitoring-workers"
}
```

### Stream Configuration Script

```python
#!/usr/bin/env python3
"""
Redis Streams initialization for Maestro Automation Service
"""

import redis

# Connect to Redis
r = redis.Redis(
    host='maestro-redis',
    port=6379,
    password='maestro_redis_secure_2025',
    decode_responses=True
)

# Create streams and consumer groups
def initialize_streams():
    streams = {
        "maestro:streams:automation:jobs": "maestro-automation-workers",
        "maestro:streams:automation:healing": "maestro-healing-workers",
        "maestro:streams:automation:errors": "maestro-monitoring-workers",
        "maestro:streams:automation:validation": "maestro-validation-workers"
    }

    for stream_name, consumer_group in streams.items():
        try:
            # Create consumer group (creates stream if doesn't exist)
            r.xgroup_create(stream_name, consumer_group, id='0', mkstream=True)
            print(f"✅ Created stream: {stream_name} with group: {consumer_group}")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                print(f"⚠️  Stream {stream_name} already exists")
            else:
                raise

if __name__ == "__main__":
    initialize_streams()
```

---

## ✅ Configuration Complete

Redis Streams infrastructure ready for Week 5 Automation Service deployment.
