# Demo Server Deployment - Configuration Guide

## 🎯 Ready to Deploy!

The complete automation is ready. I just need the demo server details from you.

---

## 📋 Information Needed

Please provide the following:

### 1. Demo Server Access
```bash
# Server hostname or IP
DEMO_SERVER=your-demo-server.com  # or IP: 123.456.789.0

# SSH username
DEMO_USER=ec2-user  # or ubuntu, admin, etc.

# SSH key (if using key-based auth)
SSH_KEY_PATH=~/.ssh/your-key.pem
```

### 2. Deployment Path (Optional)
```bash
# Where to install on demo server (default: /opt/maestro-platform)
DEMO_PATH=/opt/maestro-platform
```

---

## 🚀 Deployment Methods

### Method 1: Automated Script (Recommended)
```bash
# Set environment variables
export DEMO_SERVER="your-demo-server.com"
export DEMO_USER="ec2-user"

# Run deployment
cd /home/ec2-user/projects/maestro-platform/infrastructure
./deploy-to-demo.sh
```

### Method 2: Manual SSH (if script fails)
```bash
# 1. SSH to demo server
ssh ec2-user@your-demo-server.com

# 2. Run these commands:
sudo mkdir -p /opt/maestro-platform
sudo chown ec2-user:ec2-user /opt/maestro-platform
cd /opt/maestro-platform

# 3. Copy code (from local machine):
rsync -avz --progress \
    /home/ec2-user/projects/maestro-platform/ \
    ec2-user@your-demo-server.com:/opt/maestro-platform/

# 4. On demo server, run deployment:
cd /opt/maestro-platform/infrastructure
./maestro-deploy.sh demo

cd ../quality-fabric
./deploy-centralized.sh
```

### Method 3: Use Current Server as "Demo"
```bash
# If this IS the demo server, just run:
cd /home/ec2-user/projects/maestro-platform/infrastructure
./maestro-deploy.sh demo

cd ../quality-fabric
./deploy-centralized.sh
```

---

## ✅ Pre-Deployment Checklist

Demo server must have:
- [ ] Ubuntu 20.04+ or Amazon Linux 2
- [ ] Docker 20.10+ installed
- [ ] Docker Compose 2.0+ installed
- [ ] At least 20GB free disk space
- [ ] Ports open: 8000, 23000, 25432, 27379, 29090
- [ ] SSH access configured
- [ ] sudo privileges (for docker commands)

---

## 🔐 Security Notes

**IMPORTANT**: Change default passwords in production!

Current defaults (CHANGE THESE):
```bash
MAESTRO_POSTGRES_ADMIN_PASSWORD=maestro_secure_admin_2025_change_me
MAESTRO_REDIS_PASSWORD=maestro_redis_secure_2025
MAESTRO_GRAFANA_ADMIN_PASSWORD=grafana_secure_admin_2025_change_me
JWT_SECRET=demo_jwt_secret_min_32_characters_long_string
```

---

## 📊 What Happens During Deployment

1. **Prerequisites Check** (~30 seconds)
   - Verify SSH connectivity
   - Check Docker installation
   - Check available ports
   - Check disk space

2. **File Transfer** (~2-5 minutes)
   - Transfer infrastructure code
   - Transfer quality-fabric code
   - Transfer maestro-cache package
   - Transfer deployment scripts

3. **Infrastructure Deployment** (~3-5 minutes)
   - Create maestro-network
   - Deploy PostgreSQL with multi-database
   - Deploy Redis with namespaces
   - Deploy Prometheus
   - Deploy Grafana
   - Wait for health checks

4. **Quality Fabric Deployment** (~2-3 minutes)
   - Build Docker image
   - Deploy quality-fabric
   - Run database migrations
   - Start API server
   - Verify connections

5. **Validation** (~1 minute)
   - API health check
   - Grafana health check
   - Prometheus health check
   - Database connectivity test
   - Redis connectivity test

**Total Time**: ~8-15 minutes (fully automated)

---

## 📝 Deployment Log

All actions are logged to:
- `deployment-YYYYMMDD-HHMMSS.log` (full log)
- `deployment-errors-YYYYMMDD-HHMMSS.log` (errors only)

---

## 🆘 If Deployment Fails

The script will:
1. Log all errors to error log
2. Show clear error messages
3. Provide retry options
4. Clean up failed deployments
5. Give you commands to investigate

You can then:
```bash
# View error log
cat deployment-errors-*.log

# Check specific service
ssh ec2-user@demo-server "docker logs quality-fabric"

# Re-run from scratch
./deploy-to-demo.sh
```

---

## 🎯 After Successful Deployment

Access URLs (replace with your server):
- **API**: http://your-demo-server.com:8000
- **API Docs**: http://your-demo-server.com:8000/docs
- **Grafana**: http://your-demo-server.com:23000
- **Prometheus**: http://your-demo-server.com:29090

Default Credentials:
- **Grafana**: admin / grafana_secure_admin_2025_change_me

---

## 🎮 Command Centre (Coming Next)

You mentioned wanting a command centre for deployment management. That's the next phase!

Features planned:
- Web-based deployment dashboard
- Real-time deployment logs
- One-click deployments
- Environment comparison
- Health monitoring
- Rollback capabilities

For now, you can use:
```bash
# Monitor deployment in real-time
./deploy-to-demo.sh | tee deployment.log

# Or follow logs
ssh demo-server "docker logs -f quality-fabric"
```

---

## ⚡ Let's Deploy!

Just provide:
1. Demo server hostname/IP
2. SSH username
3. SSH key path (if needed)

And I'll execute the deployment immediately!

