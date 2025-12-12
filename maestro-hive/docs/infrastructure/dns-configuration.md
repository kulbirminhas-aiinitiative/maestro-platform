# DNS Configuration for dev.maestroenterprise.ai

**MD-3004: Part of EPIC MD-3089 - Core Platform Stability & Tooling**

## Overview

This document describes the DNS configuration requirements for the `dev.maestroenterprise.ai` environment.

## DNS Records

### Required Records

| Type | Name | Value | TTL | Notes |
|------|------|-------|-----|-------|
| A | dev.maestroenterprise.ai | [EC2 Public IP] | 300 | Main application endpoint |
| A | api.dev.maestroenterprise.ai | [EC2 Public IP] | 300 | API Gateway endpoint |
| A | auth.dev.maestroenterprise.ai | [EC2 Public IP] | 300 | Authentication service |
| CNAME | www.dev.maestroenterprise.ai | dev.maestroenterprise.ai | 300 | WWW redirect |

### Optional Records

| Type | Name | Value | TTL | Notes |
|------|------|-------|-----|-------|
| A | grafana.dev.maestroenterprise.ai | [EC2 Public IP] | 300 | Monitoring dashboard |
| A | docs.dev.maestroenterprise.ai | [EC2 Public IP] | 300 | Documentation site |
| TXT | _dmarc.dev.maestroenterprise.ai | "v=DMARC1; p=none" | 3600 | Email security |

## Configuration Steps

### 1. Obtain EC2 Public IP

```bash
# Using AWS CLI
aws ec2 describe-instances \
  --filters "Name=tag:Environment,Values=development" \
  --query 'Reservations[].Instances[].PublicIpAddress' \
  --output text

# Or from instance metadata
curl -s http://169.254.169.254/latest/meta-data/public-ipv4
```

### 2. Route 53 Configuration (if using AWS)

```bash
# Create hosted zone (if not exists)
aws route53 create-hosted-zone \
  --name maestroenterprise.ai \
  --caller-reference $(date +%s)

# Get hosted zone ID
ZONE_ID=$(aws route53 list-hosted-zones \
  --query 'HostedZones[?Name==`maestroenterprise.ai.`].Id' \
  --output text | sed 's|/hostedzone/||')

# Create A record
aws route53 change-resource-record-sets \
  --hosted-zone-id $ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "dev.maestroenterprise.ai",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "YOUR_EC2_IP"}]
      }
    }]
  }'
```

### 3. External DNS Provider

If using an external DNS provider (Cloudflare, GoDaddy, etc.):

1. Log into your DNS provider's console
2. Navigate to DNS management for `maestroenterprise.ai`
3. Add the records listed in the Required Records table
4. Set TTL to 300 seconds (5 minutes) for flexibility during development
5. Wait for propagation (can take up to 48 hours, usually faster)

### 4. Verify Configuration

```bash
# Check DNS propagation
dig dev.maestroenterprise.ai +short

# Check from multiple locations
curl -s "https://dns.google/resolve?name=dev.maestroenterprise.ai&type=A" | jq

# Test connectivity
curl -I https://dev.maestroenterprise.ai/health
```

## SSL/TLS Certificates

### Using Let's Encrypt with Certbot

```bash
# Install certbot
sudo yum install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d dev.maestroenterprise.ai \
  -d api.dev.maestroenterprise.ai \
  -d auth.dev.maestroenterprise.ai

# Auto-renewal (cron)
echo "0 0 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### Using AWS Certificate Manager (ACM)

```bash
# Request certificate
aws acm request-certificate \
  --domain-name dev.maestroenterprise.ai \
  --subject-alternative-names "*.dev.maestroenterprise.ai" \
  --validation-method DNS
```

## Nginx Configuration

```nginx
# /etc/nginx/conf.d/dev.maestroenterprise.ai.conf
server {
    listen 443 ssl http2;
    server_name dev.maestroenterprise.ai;

    ssl_certificate /etc/letsencrypt/live/dev.maestroenterprise.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dev.maestroenterprise.ai/privkey.pem;

    location / {
        proxy_pass http://localhost:4100;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name dev.maestroenterprise.ai;
    return 301 https://$server_name$request_uri;
}
```

## Troubleshooting

### DNS Not Resolving

1. Check nameserver configuration:
   ```bash
   whois maestroenterprise.ai | grep "Name Server"
   ```

2. Verify record exists:
   ```bash
   dig @8.8.8.8 dev.maestroenterprise.ai +trace
   ```

3. Clear local DNS cache:
   ```bash
   # Linux
   sudo systemd-resolve --flush-caches

   # macOS
   sudo dscacheutil -flushcache
   ```

### SSL Certificate Issues

1. Check certificate validity:
   ```bash
   openssl s_client -connect dev.maestroenterprise.ai:443 -servername dev.maestroenterprise.ai
   ```

2. Check certificate expiry:
   ```bash
   echo | openssl s_client -servername dev.maestroenterprise.ai -connect dev.maestroenterprise.ai:443 2>/dev/null | openssl x509 -noout -dates
   ```

### Port Access Issues

1. Check security group allows inbound:
   - Port 80 (HTTP)
   - Port 443 (HTTPS)

2. Check local firewall:
   ```bash
   sudo iptables -L -n | grep -E '80|443'
   ```

## Monitoring

### Health Check Endpoints

| Endpoint | Expected Response |
|----------|-------------------|
| https://dev.maestroenterprise.ai/health | 200 OK |
| https://api.dev.maestroenterprise.ai/health | 200 OK |

### Alerts

Configure CloudWatch alarms for:
- Route 53 health check failures
- SSL certificate expiry (< 30 days)
- Endpoint latency > 500ms

## Related Documents

- [Infrastructure Overview](./README.md)
- [Security Configuration](./security.md)
- [Deployment Guide](../deployment/README.md)
