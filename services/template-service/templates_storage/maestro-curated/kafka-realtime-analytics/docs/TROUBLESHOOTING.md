# Troubleshooting Guide

## Common Issues and Solutions

### Service Startup Issues

#### Kafka fails to start

**Symptoms**:
- Kafka container keeps restarting
- Error: "Connection to zookeeper failed"

**Solutions**:
```bash
# Check Zookeeper is running
docker-compose ps zookeeper

# Check Zookeeper logs
docker-compose logs zookeeper

# Restart Zookeeper first, then Kafka
docker-compose restart zookeeper
sleep 30
docker-compose restart kafka

# If persistent, clean volumes and restart
docker-compose down -v
docker-compose up -d
```

#### Producer service won't connect to Kafka

**Symptoms**:
- Producer service logs show "Failed to connect to Kafka"
- Health check fails

**Solutions**:
```bash
# Verify Kafka is running
docker-compose ps kafka

# Check Kafka broker is accessible
docker exec -it kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Check network connectivity
docker exec -it producer ping kafka

# Verify environment variables
docker exec -it producer env | grep KAFKA

# Increase retry timeout in producer configuration
```

#### PostgreSQL connection issues

**Symptoms**:
- "could not connect to server"
- "password authentication failed"

**Solutions**:
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker exec -it postgres psql -U analytics_user -d analytics -c "SELECT 1;"

# Verify credentials
docker exec -it postgres env | grep POSTGRES

# Reset database if needed
docker-compose down postgres
docker volume rm <volume_name>
docker-compose up -d postgres
```

### Performance Issues

#### High latency

**Symptoms**:
- API responses taking > 1 second
- Events processing slowly

**Diagnostics**:
```bash
# Check system resources
docker stats

# Check Kafka lag
docker exec -it kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group stream-processor-group

# Check PostgreSQL performance
docker exec -it postgres psql -U analytics_user -d analytics \
  -c "SELECT * FROM pg_stat_activity;"

# Check Redis memory
docker exec -it redis redis-cli INFO memory
```

**Solutions**:
- Scale up services: `docker-compose up -d --scale stream-processor=3`
- Increase batch sizes in stream processor
- Add indexes to frequently queried columns
- Increase Redis max memory
- Tune Kafka partitions

#### High memory usage

**Symptoms**:
- OOM kills
- Services crashing

**Solutions**:
```bash
# Limit container memory
docker-compose.yml:
  producer:
    mem_limit: 512m
    mem_reservation: 256m

# Tune JVM heap for Kafka
KAFKA_HEAP_OPTS: "-Xmx2G -Xms2G"

# Optimize PostgreSQL
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET work_mem = '16MB';
```

### Data Issues

#### Events not appearing in database

**Symptoms**:
- Producer returns success but events not in DB
- Count mismatch between Kafka and PostgreSQL

**Diagnostics**:
```bash
# Check Kafka topics
docker exec -it kafka kafka-topics --list --bootstrap-server localhost:9092

# Check topic messages
docker exec -it kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic events.user_action \
  --from-beginning \
  --max-messages 10

# Check stream processor logs
docker-compose logs stream-processor | grep -i error

# Check database
docker exec -it postgres psql -U analytics_user -d analytics \
  -c "SELECT COUNT(*), event_type FROM raw_events GROUP BY event_type;"
```

**Solutions**:
- Verify stream processor is running: `docker-compose ps stream-processor`
- Check for processing errors in logs
- Verify consumer group is active
- Check database connectivity from stream processor

#### Missing aggregations

**Symptoms**:
- Raw events exist but no aggregations
- Windows not being flushed

**Diagnostics**:
```bash
# Check aggregation table
docker exec -it postgres psql -U analytics_user -d analytics \
  -c "SELECT COUNT(*), event_type FROM aggregations GROUP BY event_type;"

# Check window processing in logs
docker-compose logs stream-processor | grep -i "flushed window"

# Check time synchronization
docker exec -it stream-processor date
```

**Solutions**:
- Verify stream processor time window configuration
- Check system time is synchronized
- Manually trigger window flush (wait 5+ minutes)
- Verify Redis connectivity for window state

#### Anomalies not detected

**Symptoms**:
- Known anomalies not appearing in anomalies table

**Diagnostics**:
```bash
# Check recent events
docker exec -it redis redis-cli LRANGE metrics:recent:transaction 0 -1

# Check anomaly detection logs
docker-compose logs stream-processor | grep -i anomaly

# Verify threshold configuration
```

**Solutions**:
- Ensure sufficient historical data (at least 10 events)
- Adjust anomaly detection threshold
- Verify calculation logic in stream processor

### Monitoring Issues

#### Grafana not showing data

**Symptoms**:
- Dashboards empty
- "No data" errors

**Solutions**:
```bash
# Check Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Verify datasource connection in Grafana
curl -u admin:admin http://localhost:3000/api/datasources

# Check metrics endpoints
curl http://localhost:8080/metrics
curl http://localhost:8081/metrics

# Restart Grafana
docker-compose restart grafana
```

#### Prometheus not scraping metrics

**Symptoms**:
- Targets down in Prometheus UI
- Missing metrics

**Solutions**:
```bash
# Check Prometheus config
docker exec -it prometheus cat /etc/prometheus/prometheus.yml

# Verify network connectivity
docker exec -it prometheus wget -O- http://producer:8080/metrics

# Check service discovery
docker-compose ps

# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload
```

### Kubernetes Issues

#### Pods not starting

**Symptoms**:
- Pods in CrashLoopBackOff
- ImagePullBackOff errors

**Diagnostics**:
```bash
# Check pod status
kubectl get pods -n analytics-platform

# Describe pod
kubectl describe pod <pod-name> -n analytics-platform

# Check logs
kubectl logs <pod-name> -n analytics-platform

# Check events
kubectl get events -n analytics-platform --sort-by='.lastTimestamp'
```

**Solutions**:
```bash
# Fix image pull issues
kubectl create secret docker-registry regcred \
  --docker-server=<registry> \
  --docker-username=<user> \
  --docker-password=<pass>

# Fix resource constraints
kubectl edit deployment <deployment-name> -n analytics-platform

# Fix config issues
kubectl edit configmap <configmap-name> -n analytics-platform
kubectl rollout restart deployment/<deployment> -n analytics-platform
```

#### Services not accessible

**Symptoms**:
- LoadBalancer external IP pending
- Cannot reach services

**Diagnostics**:
```bash
# Check service
kubectl get svc -n analytics-platform

# Check endpoints
kubectl get endpoints -n analytics-platform

# Check ingress
kubectl get ingress -n analytics-platform
```

**Solutions**:
```bash
# Use port-forward for testing
kubectl port-forward svc/producer 8080:8080 -n analytics-platform

# Check LoadBalancer provisioning
kubectl describe svc producer -n analytics-platform

# Use NodePort as alternative
kubectl patch svc producer -n analytics-platform -p '{"spec":{"type":"NodePort"}}'
```

### Network Issues

#### Cannot connect to services

**Symptoms**:
- Connection refused errors
- Timeout errors

**Diagnostics**:
```bash
# Check service is listening
netstat -tlnp | grep 8080

# Check firewall rules
iptables -L -n

# Test with curl
curl -v http://localhost:8080/health

# Check DNS resolution
nslookup kafka
```

**Solutions**:
- Verify correct hostnames in configuration
- Check network policies in Kubernetes
- Verify security groups in cloud environments
- Use IP addresses instead of hostnames for testing

### Data Consistency Issues

#### Kafka consumer lag increasing

**Symptoms**:
- Consumer lag growing
- Events delayed

**Diagnostics**:
```bash
# Check consumer lag
docker exec -it kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --describe \
  --group stream-processor-group

# Check consumer throughput
docker-compose logs stream-processor | tail -100
```

**Solutions**:
- Scale stream processor replicas
- Increase Kafka partitions
- Optimize processing logic
- Increase consumer batch size

## Debug Mode

Enable debug logging:

```bash
# Docker Compose
docker-compose down
LOG_LEVEL=DEBUG docker-compose up -d

# Kubernetes
kubectl set env deployment/producer LOG_LEVEL=DEBUG -n analytics-platform
kubectl set env deployment/stream-processor LOG_LEVEL=DEBUG -n analytics-platform
kubectl set env deployment/api LOG_LEVEL=DEBUG -n analytics-platform
```

## Getting Help

1. Check logs: `docker-compose logs -f`
2. Check system resources: `docker stats`
3. Review configuration files
4. Search GitHub issues
5. Contact support: support@example.com

## Recovery Procedures

### Complete System Reset

```bash
# Stop all services
docker-compose down -v

# Clean Docker system
docker system prune -a -f

# Restart fresh
docker-compose up -d
```

### Database Recovery

```bash
# Backup database
docker exec -it postgres pg_dump -U analytics_user analytics > backup.sql

# Restore database
docker exec -i postgres psql -U analytics_user analytics < backup.sql

# Rebuild indexes
docker exec -it postgres psql -U analytics_user -d analytics -c "REINDEX DATABASE analytics;"
```

### Kafka Topic Reset

```bash
# Delete and recreate topics
docker exec -it kafka kafka-topics --delete --topic events.user_action --bootstrap-server localhost:9092
docker exec -it kafka kafka-topics --create --topic events.user_action --partitions 3 --replication-factor 1 --bootstrap-server localhost:9092

# Reset consumer group offsets
docker exec -it kafka kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group stream-processor-group \
  --reset-offsets --to-earliest --topic events.user_action --execute
```