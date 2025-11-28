# Security Guide

## Overview

This document outlines security considerations and best practices for deploying and operating the Real-Time Analytics Platform.

## Authentication & Authorization

### API Authentication

**Current State**: No authentication (development only)

**Production Requirements**:

1. **API Key Authentication**:
   ```python
   # Add to Flask app
   from functools import wraps

   def require_api_key(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           api_key = request.headers.get('X-API-Key')
           if not api_key or not validate_api_key(api_key):
               return jsonify({'error': 'Unauthorized'}), 401
           return f(*args, **kwargs)
       return decorated_function

   @app.route('/api/events', methods=['POST'])
   @require_api_key
   def ingest_event():
       # ...
   ```

2. **OAuth 2.0/JWT**:
   - Implement OAuth 2.0 for user authentication
   - Use JWT tokens for stateless authentication
   - Integrate with identity providers (Auth0, Okta, etc.)

### Kafka Security

1. **Enable SASL/SCRAM Authentication**:
   ```yaml
   KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: SASL_SSL:SASL_SSL
   KAFKA_SASL_MECHANISM_INTER_BROKER_PROTOCOL: SCRAM-SHA-512
   KAFKA_SASL_ENABLED_MECHANISMS: SCRAM-SHA-512
   ```

2. **Configure ACLs**:
   ```bash
   # Create ACL for producer
   kafka-acls --authorizer-properties zookeeper.connect=zookeeper:2181 \
     --add --allow-principal User:producer \
     --operation Write --topic events.*

   # Create ACL for consumer
   kafka-acls --authorizer-properties zookeeper.connect=zookeeper:2181 \
     --add --allow-principal User:stream-processor \
     --operation Read --topic events.* \
     --group stream-processor-group
   ```

## Encryption

### Data in Transit

1. **TLS for Kafka**:
   ```yaml
   # Generate certificates
   openssl req -new -x509 -keyout kafka-server-key.pem \
     -out kafka-server-cert.pem -days 365

   # Kafka configuration
   KAFKA_SSL_KEYSTORE_LOCATION: /etc/kafka/secrets/kafka.keystore.jks
   KAFKA_SSL_KEYSTORE_PASSWORD: changeit
   KAFKA_SSL_KEY_PASSWORD: changeit
   KAFKA_SSL_TRUSTSTORE_LOCATION: /etc/kafka/secrets/kafka.truststore.jks
   KAFKA_SSL_TRUSTSTORE_PASSWORD: changeit
   ```

2. **TLS for PostgreSQL**:
   ```yaml
   # PostgreSQL SSL configuration
   POSTGRES_SSL_MODE: require
   POSTGRES_SSL_CERT: /etc/ssl/certs/server.crt
   POSTGRES_SSL_KEY: /etc/ssl/private/server.key
   ```

3. **HTTPS for Services**:
   ```python
   # Use nginx or API Gateway for TLS termination
   # Or run Flask with SSL
   app.run(ssl_context=('cert.pem', 'key.pem'))
   ```

### Data at Rest

1. **Database Encryption**:
   ```sql
   -- Enable pgcrypto
   CREATE EXTENSION pgcrypto;

   -- Encrypt sensitive columns
   CREATE TABLE sensitive_data (
     id SERIAL PRIMARY KEY,
     data BYTEA NOT NULL
   );

   INSERT INTO sensitive_data (data)
   VALUES (pgp_sym_encrypt('sensitive', 'encryption_key'));
   ```

2. **Disk Encryption**:
   - Use encrypted volumes (AWS EBS encryption, GCP disk encryption)
   - Enable encryption for Kafka data directories
   - Enable encryption for PostgreSQL data directory

## Network Security

### Kubernetes Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: analytics-network-policy
  namespace: analytics-platform
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow producer to receive external traffic
    - from:
        - podSelector:
            matchLabels:
              app: nginx-ingress
      ports:
        - protocol: TCP
          port: 8080
  egress:
    # Allow services to communicate with Kafka
    - to:
        - podSelector:
            matchLabels:
              app: kafka
      ports:
        - protocol: TCP
          port: 9092
```

### Firewall Rules

```bash
# Allow only necessary ports
# Producer: 8080
# API: 8081
# Grafana: 3000

# Block direct access to:
# - Kafka: 9092
# - PostgreSQL: 5432
# - Redis: 6379
# - Zookeeper: 2181
```

## Secrets Management

### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: analytics-secrets
  namespace: analytics-platform
type: Opaque
stringData:
  POSTGRES_PASSWORD: <strong-password>
  KAFKA_SASL_PASSWORD: <strong-password>
  API_KEY: <strong-api-key>
```

### External Secrets Management

**HashiCorp Vault**:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: vault-auth
  namespace: analytics-platform
---
apiVersion: v1
kind: Secret
metadata:
  name: vault-secret
  annotations:
    vault.hashicorp.com/agent-inject: "true"
    vault.hashicorp.com/role: "analytics-platform"
    vault.hashicorp.com/agent-inject-secret-database: "secret/data/database"
```

**AWS Secrets Manager**:
```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

## Input Validation

### Request Validation

```python
from jsonschema import validate, ValidationError

# Event schema
event_schema = {
    "type": "object",
    "properties": {
        "event_type": {"type": "string", "maxLength": 100},
        "data": {"type": "object"},
        "timestamp": {"type": "string", "format": "date-time"}
    },
    "required": ["event_type", "data"]
}

@app.route('/api/events', methods=['POST'])
def ingest_event():
    try:
        validate(instance=request.json, schema=event_schema)
    except ValidationError as e:
        return jsonify({'error': 'Invalid input', 'details': str(e)}), 400
    # Process event...
```

### SQL Injection Prevention

```python
# Always use parameterized queries
cursor.execute(
    "SELECT * FROM raw_events WHERE event_type = %s AND timestamp > %s",
    (event_type, start_time)
)

# NEVER do this:
# cursor.execute(f"SELECT * FROM raw_events WHERE event_type = '{event_type}'")
```

## Rate Limiting

### Application Level

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["1000 per hour"]
)

@app.route('/api/events', methods=['POST'])
@limiter.limit("100 per minute")
def ingest_event():
    # ...
```

### Kubernetes Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: analytics-ingress
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/limit-rps: "10"
spec:
  rules:
    - host: analytics.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: producer
                port:
                  number: 8080
```

## Monitoring & Auditing

### Security Logging

```python
import logging

security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

@app.route('/api/events', methods=['POST'])
def ingest_event():
    security_logger.info(f"Event ingestion from {request.remote_addr}")
    # ...
```

### Audit Trail

```sql
-- Create audit table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    action VARCHAR(100),
    resource VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    details JSONB
);

-- Log all actions
INSERT INTO audit_log (user_id, action, resource, ip_address, details)
VALUES (%s, %s, %s, %s, %s);
```

## Vulnerability Management

### Dependency Scanning

```bash
# Python dependencies
pip install safety
safety check -r requirements.txt

# Docker images
docker scan analytics-producer:latest
```

### Regular Updates

```bash
# Update base images
docker pull python:3.11-slim

# Update dependencies
pip list --outdated
pip install --upgrade <package>
```

## Compliance

### GDPR Considerations

1. **Data Minimization**: Only collect necessary data
2. **Right to Erasure**: Implement data deletion endpoints
3. **Data Portability**: Provide data export functionality
4. **Consent Management**: Track and respect user consent

### PCI DSS (if handling payment data)

1. **Network Segmentation**: Isolate payment processing
2. **Encryption**: Encrypt all payment data
3. **Access Control**: Restrict access to cardholder data
4. **Logging**: Comprehensive audit logging

## Security Checklist

- [ ] Enable authentication on all endpoints
- [ ] Enable TLS for all network communication
- [ ] Encrypt data at rest
- [ ] Implement rate limiting
- [ ] Configure network policies
- [ ] Use secrets management
- [ ] Enable audit logging
- [ ] Implement input validation
- [ ] Regular security updates
- [ ] Vulnerability scanning
- [ ] Backup and disaster recovery
- [ ] Incident response plan
- [ ] Security training for team

## Incident Response

### Security Incident Procedure

1. **Detection**: Monitor logs and alerts
2. **Containment**: Isolate affected systems
3. **Investigation**: Analyze logs and traces
4. **Eradication**: Remove threat
5. **Recovery**: Restore normal operations
6. **Lessons Learned**: Document and improve

### Contact Information

- Security Team: security@example.com
- On-Call: +1-XXX-XXX-XXXX
- Incident Portal: https://incidents.example.com