# Artifact Management Stack - Quick Start (5 Minutes)

**Get your full artifact management stack running in 5 minutes!**

---

## Step 1: Configure Passwords (1 minute)

```bash
cd /home/ec2-user/projects/maestro-platform/infrastructure

# Edit .env.infrastructure and set secure passwords
nano .env.infrastructure
```

**Required passwords** (search for `change_me` and replace):
```bash
MINIO_ROOT_PASSWORD=<strong-password-here>
HARBOR_ADMIN_PASSWORD=<strong-password-here>
HARBOR_DB_PASSWORD=<strong-password-here>
HARBOR_CORE_SECRET=<random-string-here>
HARBOR_JOBSERVICE_SECRET=<random-string-here>
HARBOR_REGISTRY_SECRET=<random-string-here>
```

**Quick password generator**:
```bash
# Generate random passwords
openssl rand -base64 32
```

---

## Step 2: Start Infrastructure (2 minutes)

```bash
# Start all services
docker-compose -f docker-compose.infrastructure.yml up -d

# Watch startup (Ctrl+C to exit)
docker-compose -f docker-compose.infrastructure.yml logs -f
```

**Wait for all services to be healthy** (~2 minutes):
```bash
# Check status
docker-compose -f docker-compose.infrastructure.yml ps

# All services should show "Up" and healthy
```

---

## Step 3: Configure Local Environment (1 minute)

```bash
# Configure Docker, npm, and pip to use registries
./scripts/configure-registries.sh --all
```

This configures:
- ✅ Docker to use Harbor
- ✅ npm to use Nexus
- ✅ pip to use Nexus

---

## Step 4: Access Web UIs (1 minute)

Open these URLs in your browser:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Harbor** | http://localhost:28080 | admin / (your HARBOR_ADMIN_PASSWORD) |
| **Nexus** | http://localhost:28081 | admin / admin123 |
| **MLflow** | http://localhost:25000 | (no auth) |
| **MinIO** | http://localhost:29001 | minioadmin / (your MINIO_ROOT_PASSWORD) |

---

## Step 5: Initial Setup (Harbor & Nexus)

### Harbor Setup (2 minutes)

1. Go to http://localhost:28080
2. Login: admin / (your password)
3. Click "**Projects**" → "**+ NEW PROJECT**"
4. Create these projects:
   - `maestro-hive` (Private)
   - `maestro-frontend` (Private)
   - `maestro-engine` (Private)
   - `quality-fabric` (Private)
   - `execution-platform` (Private)

### Nexus Setup (3 minutes)

1. Go to http://localhost:28081
2. Login: admin / admin123
3. **Change password** when prompted
4. Click gear icon → **Repository** → **Repositories**
5. Create **PyPI** repositories:
   - Click "**Create repository**" → "**pypi (proxy)**"
     - Name: `pypi-proxy`
     - Remote storage: `https://pypi.org`
     - Click "**Create repository**"
   - Click "**Create repository**" → "**pypi (hosted)**"
     - Name: `pypi-hosted`
     - Click "**Create repository**"
   - Click "**Create repository**" → "**pypi (group)**"
     - Name: `pypi-group`
     - Members: Select `pypi-proxy` and `pypi-hosted`
     - Click "**Create repository**"
6. Create **npm** repositories:
   - Repeat steps above but with "npm (proxy)", "npm (hosted)", "npm (group)"
   - npm-proxy remote: `https://registry.npmjs.org`

---

## Test It Out!

### Test Harbor (Docker Registry)

```bash
# Login to Harbor
docker login localhost:28080
# Username: admin
# Password: (your HARBOR_ADMIN_PASSWORD)

# Tag and push a test image
docker pull hello-world
docker tag hello-world localhost:28080/maestro-hive/hello-world:test
docker push localhost:28080/maestro-hive/hello-world:test

# ✅ Success! Check Harbor UI → maestro-hive project
```

### Test Nexus (PyPI)

```bash
# Install a package (should come from Nexus)
pip install requests

# Check if it came from Nexus
pip install -v requests 2>&1 | grep localhost:28083
# ✅ Should show Nexus URL
```

### Test MLflow

```python
# Create test_mlflow.py
import mlflow

mlflow.set_tracking_uri("http://localhost:25000")
mlflow.set_experiment("quick-test")

with mlflow.start_run():
    mlflow.log_param("test", "success")
    mlflow.log_metric("value", 1.0)
    print(f"✅ Run ID: {mlflow.active_run().info.run_id}")

# Run it
python test_mlflow.py

# Check MLflow UI: http://localhost:25000
```

### Test DVC

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive/maestro_ml

# Install DVC
pip install dvc[s3]

# Initialize
dvc init

# Copy config
cp /home/ec2-user/projects/maestro-platform/infrastructure/templates/dvc/.dvc/config .dvc/config

# Update password in .dvc/config (secret_access_key)

# Create test file
echo "test data" > test_data.txt

# Track with DVC
dvc add test_data.txt

# Push to MinIO
dvc push

# ✅ Check MinIO UI → dvc-storage bucket
```

---

## Verify Everything Works

```bash
# Check all services are running
docker-compose -f docker-compose.infrastructure.yml ps | grep Up

# Expected: 20 services running

# Check MinIO buckets
curl -s http://localhost:29001 | grep -q "MinIO" && echo "✅ MinIO OK"

# Check Harbor API
curl -s http://localhost:28080/api/v2.0/ping | grep -q "Pong" && echo "✅ Harbor OK"

# Check Nexus status
curl -s http://localhost:28081/service/rest/v1/status | grep -q "200" && echo "✅ Nexus OK"

# Check MLflow health
curl -s http://localhost:25000/health | grep -q "OK" && echo "✅ MLflow OK"
```

---

## What You Now Have

✅ **Harbor** - Secure container registry with vulnerability scanning
✅ **Nexus OSS** - Universal repository for PyPI, npm, Maven, Docker
✅ **MLflow** - ML experiment tracking with PostgreSQL backend
✅ **MinIO** - S3-compatible storage for all artifacts
✅ **DVC** - Data version control for large datasets

**All integrated, monitored, and production-ready!**

---

## Next Steps

1. **Read the comprehensive guide**: [ARTIFACT_MANAGEMENT_GUIDE.md](./docs/ARTIFACT_MANAGEMENT_GUIDE.md)
2. **Migrate PyPI packages**: [PYPI_MIGRATION_GUIDE.md](./docs/PYPI_MIGRATION_GUIDE.md)
3. **Set up DVC**: [DVC_QUICKSTART.md](./docs/DVC_QUICKSTART.md)
4. **Update your first project** to use the new registries
5. **Set up CI/CD** to push to Harbor and Nexus

---

## Troubleshooting

**Services not starting?**
```bash
# Check logs
docker-compose -f docker-compose.infrastructure.yml logs <service-name>

# Restart specific service
docker-compose -f docker-compose.infrastructure.yml restart <service-name>
```

**Can't login to Harbor/Nexus?**
```bash
# Verify password in .env.infrastructure
grep HARBOR_ADMIN_PASSWORD .env.infrastructure
grep NEXUS .env.infrastructure

# Reset Harbor password (in database)
docker exec maestro-harbor-database psql -U postgres -d registry -c "UPDATE harbor_user SET password='...' WHERE username='admin';"
```

**Nexus repo not working?**
- Make sure you created the "group" repository
- Clear cache: `pip cache purge` or `npm cache clean --force`

---

## Support

- **Full documentation**: `./docs/`
- **Implementation summary**: `./ARTIFACT_MANAGEMENT_IMPLEMENTATION_SUMMARY.md`
- **Slack**: `#maestro-infrastructure`

---

**You're all set! 🚀**

Now start pushing images to Harbor, packages to Nexus, and tracking experiments in MLflow!
