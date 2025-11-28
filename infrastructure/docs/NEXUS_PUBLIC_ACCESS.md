# Nexus Public Access Configuration

**Purpose**: Enable access to Nexus Web UI from public IP for initial setup
**Security**: Temporary access for configuration, should be restricted after setup

---

## Current Status

✅ **Nexus is running**: Port 28081 bound to 0.0.0.0 (all interfaces)
✅ **No local firewall**: No iptables/firewall blocking
✅ **Private IP**: 172.31.36.45

❓ **Security Group**: Need to verify port 28081 is open in AWS Security Group

---

## Quick Access Check

```bash
# Get your public IP
curl -s http://169.254.169.254/latest/meta-data/public-ipv4

# Expected output: Your EC2 public IP (e.g., 54.x.x.x)
```

### Test Access

From your local machine:
```bash
# Replace PUBLIC_IP with your EC2 public IP
curl -I http://PUBLIC_IP:28081

# Expected: HTTP/1.1 200 OK or redirect
# If timeout/connection refused: Security group needs update
```

---

## Option 1: Update AWS Security Group (Recommended for Setup)

### Via AWS Console

1. **Go to EC2 Console**: https://console.aws.amazon.com/ec2/
2. **Select your instance**
3. **Click on Security tab**
4. **Click on the Security Group ID**
5. **Edit Inbound Rules** → **Add Rule**:
   - **Type**: Custom TCP
   - **Port Range**: 28081
   - **Source**:
     - **For testing**: `My IP` (your current IP)
     - **For team access**: Specific CIDR (e.g., `YOUR_OFFICE_IP/32`)
     - **⚠️ NOT RECOMMENDED**: `0.0.0.0/0` (entire internet)
6. **Save rules**

### Via AWS CLI

```bash
# Get instance ID
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

# Get security group ID
SG_ID=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' \
  --output text)

# Get your current public IP
MY_IP=$(curl -s https://ifconfig.me)

# Add rule for Nexus port
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 28081 \
  --cidr ${MY_IP}/32 \
  --description "Nexus Web UI - Temporary Setup Access"

echo "✓ Security group updated: Port 28081 open for $MY_IP"
```

---

## Option 2: SSH Tunnel (More Secure - Recommended for Production)

### From Your Local Machine

```bash
# Create SSH tunnel
ssh -L 28081:localhost:28081 ec2-user@YOUR_EC2_PUBLIC_IP

# Keep this terminal open
# In another terminal or browser, access:
# http://localhost:28081
```

This method:
- ✅ More secure (no public exposure)
- ✅ Works even if security group is locked down
- ✅ No infrastructure changes needed
- ❌ Requires SSH key access

---

## Option 3: Use Nginx Reverse Proxy with Authentication (Production)

For production environments, set up nginx with:
- HTTPS (Let's Encrypt)
- Basic authentication
- IP whitelisting
- Rate limiting

See: `/infrastructure/docs/NGINX_REVERSE_PROXY.md` (to be created)

---

## Access Nexus Web UI

Once port is open or tunnel is established:

1. **Navigate to**:
   - Direct: `http://YOUR_PUBLIC_IP:28081`
   - Tunnel: `http://localhost:28081`

2. **Login**:
   - Username: `admin`
   - Password: `nexus_admin_2025_change_me`

3. **Complete Setup**:
   - Follow: `/infrastructure/docs/NEXUS_PYPI_SETUP.md`

---

## Security Best Practices

### After Initial Setup

1. **Remove public access** to port 28081:
   ```bash
   aws ec2 revoke-security-group-ingress \
     --group-id $SG_ID \
     --protocol tcp \
     --port 28081 \
     --cidr YOUR_IP/32
   ```

2. **Use SSH tunnels** for ongoing access

3. **Set up VPN** for team access (if applicable)

4. **Configure nginx reverse proxy** with HTTPS for production

### Ongoing Access Methods

**For administrators**:
```bash
# SSH tunnel method (always secure)
ssh -L 28081:localhost:28081 ec2-user@YOUR_EC2_IP
```

**For CI/CD**:
- Use private network access (within VPC)
- Docker networks (container-to-container)
- No public exposure needed

**For Docker builds**:
```dockerfile
# Dockerfiles will use internal container networking
ARG PYPI_INDEX_URL=http://maestro-nexus:8081/repository/pypi-group/simple
```

---

## Troubleshooting

### "Connection Refused"

**Cause**: Security group not updated

**Solution**: Follow Option 1 above to open port 28081

### "Connection Timeout"

**Cause**: Network ACL or upstream firewall blocking

**Solution**:
1. Check Network ACLs in AWS Console
2. Check corporate firewall if on VPN
3. Use SSH tunnel (Option 2) instead

### "Can't Login"

**Cause**: Wrong password or password expired

**Solution**:
```bash
# Get current password from environment
grep NEXUS_ADMIN_PASSWORD /home/ec2-user/projects/maestro-platform/infrastructure/.env.infrastructure

# Should show: nexus_admin_2025_change_me
```

### "404 Not Found"

**Cause**: Nexus not fully started

**Solution**:
```bash
# Check Nexus status
docker ps | grep nexus
docker logs maestro-nexus --tail 50

# Restart if needed
docker restart maestro-nexus
sleep 60  # Wait for full startup
```

---

## Quick Reference

### Check if Port is Open

From local machine:
```bash
nc -zv YOUR_EC2_PUBLIC_IP 28081
# Or
telnet YOUR_EC2_PUBLIC_IP 28081
```

### Current Network Configuration

```bash
# On EC2 instance
docker port maestro-nexus

# Expected output:
# 8081/tcp -> 0.0.0.0:28081  ← Bound to all interfaces ✓
```

### Get Connection Information

```bash
# Public IP
curl -s http://169.254.169.254/latest/meta-data/public-ipv4

# Private IP
curl -s http://169.254.169.254/latest/meta-data/local-ipv4

# Hostname
curl -s http://169.254.169.254/latest/meta-data/public-hostname
```

---

## Next Steps

1. ✅ **Choose access method** (Security Group or SSH Tunnel)
2. ✅ **Open Nexus Web UI**
3. ✅ **Complete setup** (NEXUS_PYPI_SETUP.md)
4. ✅ **Upload packages** (`./publish-to-nexus.sh`)
5. ✅ **Secure access** (remove public access or use tunnel)
6. ✅ **Update Dockerfiles** (use Nexus for pip installs)

---

**Recommended**: Use SSH Tunnel for maximum security, or open port 28081 temporarily for your IP only.

