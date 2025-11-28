# Nexus PyPI Setup Guide - Production Ready

**Status**: Manual UI Setup Required (Automation in Progress)
**Version**: Nexus OSS 3.85.0-03
**Last Updated**: 2025-10-24

---

## Issue Summary

Nexus OSS Community Edition 3.85.0-03 requires initial setup through the Web UI before PyPI uploads via twine will work. The REST API authentication for write operations requires specific realm configuration that must be done via the UI.

## One-Time Setup (5 minutes)

### Step 1: Access Nexus Web UI

```bash
# Open in browser
http://localhost:28081

# Or if on remote server, create SSH tunnel:
ssh -L 28081:localhost:28081 ec2-user@your-server
# Then access http://localhost:28081 locally
```

### Step 2: Login

**Username**: `admin`
**Password**: `nexus_admin_2025_change_me` (from .env.infrastructure)

If password doesn't work, get it from:
```bash
docker exec maestro-nexus cat /nexus-data/admin.password
```

### Step 3: Enable PyPI Realm for Authentication

1. Click the **Settings** icon (gear) in top navigation
2. Navigate to **Security** → **Realms**
3. In **Available** realms, find and select:
   - `npm Bearer Token Realm` (enables token auth for all repos)
4. Click **>** to move it to **Active** realms
5. Click **Save**

### Step 4: Enable Anonymous Access (Optional - for Pull Only)

1. Still in Settings, go to **Security** → **Anonymous Access**
2. Check **Allow anonymous users to access the server**
3. Click **Save**

Note: This allows unauthenticated package downloads but NOT uploads.

### Step 5: Verify Repository Configuration

1. Go to **Repository** → **Repositories**
2. Verify these exist:
   - `pypi-proxy` (type: proxy) - caches from pypi.org
   - `pypi-hosted` (type: hosted) - for internal packages
   - `pypi-group` (type: group) - combines both

3. Click on `pypi-hosted`, verify:
   - **Deployment policy**: Allow redeploy
   - **Blob store**: default
   - Status: Online

### Step 6: Create Deployment User (Recommended for CI/CD)

1. Go to **Security** → **Users**
2. Click **Create local user**
3. Fill in:
   - **ID**: `deployer`
   - **First Name**: `Deployment`
   - **Last Name**: `User`
   - **Email**: `deployer@maestro.local`
   - **Password**: `deployer_secure_2025` (or generate strong password)
   - **Status**: Active
   - **Roles**: Select `nx-admin` (or create custom role with deploy permissions)
4. Click **Create**

---

## Testing the Setup

### Test 1: Verify Authentication

```bash
# Test with admin user
curl -u admin:nexus_admin_2025_change_me http://localhost:28081/service/rest/v1/status

# Test with deployer user
curl -u deployer:deployer_secure_2025 http://localhost:28081/service/rest/v1/status

# Both should return empty response with HTTP 200
```

### Test 2: Upload a Package

```bash
cd /home/ec2-user/projects/maestro-platform/shared/packages/core-logging

# Build if not already built
poetry build

# Upload to Nexus
twine upload \
  --repository-url http://localhost:28081/repository/pypi-hosted/ \
  --username deployer \
  --password deployer_secure_2025 \
  dist/maestro_core_logging-1.0.0-py3-none-any.whl

# Should see: "Uploading... 100%"
```

### Test 3: Install from Nexus

```bash
pip install \
  --index-url http://localhost:28081/repository/pypi-group/simple \
  --trusted-host localhost \
  maestro-core-logging==1.0.0

# Should install successfully
```

---

## Publish All Maestro Packages

Once setup is complete, run:

```bash
cd /home/ec2-user/projects/maestro-platform/shared
./publish-to-nexus.sh
```

This will:
- Build all 6 maestro packages
- Upload to `pypi-hosted` repository
- Make them available via `pypi-group`

---

## Troubleshooting

### Issue: 401 Unauthorized on Upload

**Cause**: Realms not configured or user lacks permissions

**Solution**:
1. Verify **npm Bearer Token Realm** is Active (Step 3 above)
2. Verify user has `nx-admin` role or `nx-repository-admin-*-*-*` role
3. Try with admin user first to rule out user permissions

### Issue: Repository Not Found

**Cause**: Repository doesn't exist or is offline

**Solution**:
```bash
# Check repositories via UI or API
curl -u admin:nexus_admin_2025_change_me \
  http://localhost:28081/service/rest/v1/repositories | jq '.[] | {name, format, type}'
```

### Issue: Can't Access Web UI

**Cause**: Nexus not started or port not exposed

**Solution**:
```bash
# Check Nexus is running
docker ps | grep nexus

# Check Nexus logs
docker logs maestro-nexus --tail 50

# Restart if needed
docker restart maestro-nexus
sleep 60  # Wait for startup
```

### Issue: Forgot Admin Password

**Solution**:
```bash
# For Nexus that was already configured (admin.password deleted)
# You'll need to reset via database or recreate container

# Option 1: Get from environment
grep NEXUS_ADMIN_PASSWORD /home/ec2-user/projects/maestro-platform/infrastructure/.env.infrastructure

# Option 2: Reset by recreating Nexus (loses data)
cd /home/ec2-user/projects/maestro-platform/infrastructure
docker-compose -f docker-compose.artifacts-minimal.yml down
docker volume rm maestro_nexus_data
docker-compose -f docker-compose.artifacts-minimal.yml up -d
# Wait 2 minutes, then get new password:
docker exec maestro-nexus cat /nexus-data/admin.password
```

---

## Production Deployment Checklist

- [ ] Complete One-Time Setup (Steps 1-6)
- [ ] Change default admin password to strong password
- [ ] Create deployer user with limited permissions
- [ ] Configure `.pypirc` on build servers with deployer credentials
- [ ] Upload all maestro packages to Nexus
- [ ] Test package installation from Nexus
- [ ] Update Dockerfiles to use Nexus as PyPI index
- [ ] Document credentials in secure vault (not in code)
- [ ] Set up Nexus backup strategy
- [ ] Configure Nexus cleanup policies for old versions

---

## Next Steps

1. **Complete this setup** - Follow Steps 1-6 above
2. **Run publish script** - `./shared/publish-to-nexus.sh`
3. **Update Dockerfiles** - Configure to use Nexus PyPI
4. **Test builds** - Verify Docker builds use Nexus successfully
5. **Document** - Add credentials to team vault

---

## Alternative: Automated Setup (Advanced)

If you need to automate this for multiple environments, consider:

1. **Nexus Scripting API**: Use Groovy scripts via `/service/rest/v1/script`
2. **Terraform Provider**: Use `terraform-provider-nexus`
3. **Ansible**: Use `ansible-nexus3-oss` role
4. **Configuration as Code**: Store in terraform/configuration management

---

**Status**: Ready for manual setup ✓
**Estimated Time**: 5-10 minutes
**Support**: See infrastructure team or #maestro-infrastructure Slack

