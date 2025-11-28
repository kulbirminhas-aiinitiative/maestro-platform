# PyPI Server to Nexus OSS Migration Guide

## Overview

This guide walks through migrating from the standalone `pypiserver` to Nexus OSS PyPI repository.

**Benefits of Nexus**:
- Unified management of PyPI, npm, Maven, Docker registries
- Caching proxy for faster builds
- Better security and RBAC
- Scheduled tasks and cleanup policies
- Enterprise features (vulnerability scanning coming in Nexus IQ)

---

## Pre-Migration Checklist

- [ ] Nexus OSS is running (http://localhost:28081)
- [ ] Backup existing pypiserver packages
- [ ] Document all projects using pypiserver
- [ ] Test Nexus with one project first

---

## Step 1: Backup Existing Packages

```bash
# Backup all packages from pypiserver
cd /home/ec2-user/projects/maestro-platform/pypi-server
tar -czf pypi-packages-backup-$(date +%Y%m%d).tar.gz packages/

# List all packages
ls -lh packages/
```

---

## Step 2: Configure Nexus PyPI Repositories

### Access Nexus

1. Navigate to http://localhost:28081
2. Login: admin / (password from first-time setup)
3. Click settings (gear icon) → Repository → Repositories

### Create PyPI Proxy Repository

**Purpose**: Caches packages from pypi.org

1. Click "Create repository" → "pypi (proxy)"
2. Configuration:
   ```
   Name: pypi-proxy
   Remote storage: https://pypi.org
   Auto-blocking: Enabled
   Maximum component age: 1440 (1 day)
   Maximum metadata age: 1440 (1 day)
   ```
3. Click "Create repository"

### Create PyPI Hosted Repository

**Purpose**: Hosts your internal/custom Python packages

1. Click "Create repository" → "pypi (hosted)"
2. Configuration:
   ```
   Name: pypi-hosted
   Deployment policy: Allow redeploy
   ```
3. Click "Create repository"

### Create PyPI Group Repository

**Purpose**: Combines proxy + hosted into single endpoint

1. Click "Create repository" → "pypi (group)"
2. Configuration:
   ```
   Name: pypi-group
   Members:
     ☑ pypi-proxy
     ☑ pypi-hosted
   ```
3. Click "Create repository"

---

## Step 3: Upload Existing Packages to Nexus

### Option A: Using twine (Recommended)

```bash
# Install twine if not already installed
pip install twine

# Upload all packages from pypiserver
cd /home/ec2-user/projects/maestro-platform/pypi-server/packages

# Upload each package
for package in *.whl *.tar.gz; do
    echo "Uploading $package..."
    twine upload \
        --repository-url http://localhost:28083/repository/pypi-hosted/ \
        --username admin \
        --password <nexus-admin-password> \
        "$package"
done
```

### Option B: Using Nexus Web UI

1. Navigate to Browse → pypi-hosted
2. Click "Upload component"
3. Select Asset: Choose .whl or .tar.gz file
4. Click "Upload"

### Verify Upload

```bash
# List packages in Nexus
curl -u admin:<password> http://localhost:28081/service/rest/v1/components?repository=pypi-hosted

# Or check in UI: Browse → pypi-hosted
```

---

## Step 4: Update Client Configuration

### Global pip Configuration

```bash
# Linux/Mac
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf <<EOF
[global]
index-url = http://localhost:28083/repository/pypi-group/simple
trusted-host = localhost

[install]
trusted-host = localhost
EOF

# Or use the configure script
cd /home/ec2-user/projects/maestro-platform/infrastructure
./scripts/configure-registries.sh --pip
```

### Project-Specific Configuration

Create `pip.conf` in your project:

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

cat > pip.conf <<EOF
[global]
index-url = http://localhost:28083/repository/pypi-group/simple
trusted-host = localhost
EOF
```

### Update requirements.txt

No changes needed! Packages will be pulled from Nexus automatically:

```txt
# requirements.txt - works with both pypiserver and Nexus
mlflow==2.10.0
pandas==2.1.4
numpy==1.26.3
```

### Update CI/CD Pipelines

**GitHub Actions**:

```yaml
# .github/workflows/ci.yml
- name: Install dependencies
  run: |
    pip install --index-url http://<nexus-host>:28083/repository/pypi-group/simple \
                --trusted-host <nexus-host> \
                -r requirements.txt
```

**GitLab CI**:

```yaml
# .gitlab-ci.yml
variables:
  PIP_INDEX_URL: "http://<nexus-host>:28083/repository/pypi-group/simple"
  PIP_TRUSTED_HOST: "<nexus-host>"

install:
  script:
    - pip install -r requirements.txt
```

---

## Step 5: Test Installation

```bash
# Clear pip cache
pip cache purge

# Install a package from Nexus
pip install requests

# Verify it came from Nexus (check logs)
pip install -v requests 2>&1 | grep -i "nexus\|localhost:28083"

# Test installing your internal package
pip install <your-internal-package>
```

---

## Step 6: Publishing New Packages to Nexus

### Build Package

```bash
cd /home/ec2-user/projects/maestro-platform/my-package

# Build distribution
python setup.py sdist bdist_wheel

# Check dist/ directory
ls -lh dist/
```

### Upload to Nexus

```bash
# Upload using twine
twine upload \
    --repository-url http://localhost:28083/repository/pypi-hosted/ \
    --username admin \
    --password <nexus-password> \
    dist/*
```

### Configure twine for easier uploads

Create `~/.pypirc`:

```ini
[distutils]
index-servers =
    nexus

[nexus]
repository = http://localhost:28083/repository/pypi-hosted/
username = admin
password = <nexus-password>
```

Then upload with:

```bash
twine upload -r nexus dist/*
```

---

## Step 7: Update Dockerfiles

### Before (pypiserver)

```dockerfile
FROM python:3.11-slim

# Install from old pypiserver
RUN pip install --index-url http://pypi-server:8888/simple \
                --trusted-host pypi-server \
                -r requirements.txt
```

### After (Nexus)

```dockerfile
FROM python:3.11-slim

# Install from Nexus
RUN pip install --index-url http://maestro-nexus:8083/repository/pypi-group/simple \
                --trusted-host maestro-nexus \
                -r requirements.txt
```

---

## Step 8: Decommission pypiserver

**Only after verifying all projects work with Nexus!**

```bash
# Stop pypiserver
cd /home/ec2-user/projects/maestro-platform/pypi-server
docker-compose down

# Archive packages
mv packages packages-archived-$(date +%Y%m%d)

# Optional: Remove pypiserver directory
# rm -rf /home/ec2-user/projects/maestro-platform/pypi-server
```

---

## Rollback Plan

If issues arise, roll back to pypiserver:

```bash
# 1. Restore pip.conf
cat > ~/.config/pip/pip.conf <<EOF
[global]
index-url = http://localhost:8888/simple
trusted-host = localhost
EOF

# 2. Restart pypiserver
cd /home/ec2-user/projects/maestro-platform/pypi-server
docker-compose up -d

# 3. Verify connection
pip install --index-url http://localhost:8888/simple <package-name>
```

---

## Advanced: LDAP Integration

For enterprise environments, integrate Nexus with LDAP:

1. Settings → Security → LDAP
2. Configure LDAP connection
3. Map LDAP groups to Nexus roles

---

## Troubleshooting

### Cannot install packages

```bash
# Check Nexus is running
curl http://localhost:28081/service/rest/v1/status

# Check repository exists
curl -u admin:<password> http://localhost:28081/service/rest/v1/repositories

# Verify pip config
pip config list

# Try direct URL
pip install --index-url http://localhost:28083/repository/pypi-group/simple requests
```

### Upload fails

```bash
# Check credentials
curl -u admin:<password> http://localhost:28081/service/rest/v1/status

# Verify repository accepts uploads
# Settings → Repository → pypi-hosted → Deployment policy: Allow redeploy

# Try uploading with verbose output
twine upload --verbose --repository-url http://localhost:28083/repository/pypi-hosted/ dist/*
```

### Package not found in Nexus

```bash
# Check if package is in proxy cache
# Browse → pypi-proxy

# Force download from upstream
pip install --no-cache-dir <package>

# Check Nexus logs
docker logs maestro-nexus | grep -i <package-name>
```

---

## Comparison: pypiserver vs Nexus

| Feature | pypiserver | Nexus OSS |
|---------|-----------|-----------|
| PyPI support | ✅ | ✅ |
| Proxy/cache | ❌ | ✅ |
| npm support | ❌ | ✅ |
| Docker support | ❌ | ✅ |
| Maven support | ❌ | ✅ |
| RBAC | ❌ | ✅ |
| LDAP/AD | ❌ | ✅ |
| Cleanup policies | ❌ | ✅ |
| Scheduled tasks | ❌ | ✅ |
| REST API | Basic | Full |
| Web UI | Basic | Advanced |

---

## Migration Checklist

- [ ] Nexus repositories configured (proxy, hosted, group)
- [ ] Existing packages uploaded to Nexus
- [ ] pip configured to use Nexus
- [ ] Test project can install from Nexus
- [ ] Test publishing to Nexus
- [ ] Update all projects' Dockerfiles
- [ ] Update CI/CD pipelines
- [ ] Verify all repos work with Nexus
- [ ] Archive pypiserver data
- [ ] Decommission pypiserver

---

## Support

- Nexus OSS Docs: https://help.sonatype.com/repomanager3
- #maestro-infrastructure Slack channel
- Infrastructure team: infrastructure@maestro.com
