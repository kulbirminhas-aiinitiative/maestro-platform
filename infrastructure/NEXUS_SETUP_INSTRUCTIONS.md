# Nexus Setup Instructions - READY TO COMPLETE

**Status**: ✅ Nexus is running with fresh installation
**Time Required**: 5 minutes
**Action Required**: Complete setup wizard via Web UI

---

## 🎯 Quick Summary

Nexus has been reset and is ready for proper configuration. You now need to complete the setup wizard to assign permissions correctly.

---

## 🔑 Credentials

### Initial Admin Password (ONE-TIME USE)
```
Username: admin
Password: e797357a-7280-4ad6-991e-e78654f29a7c
```

⚠️ **Important**: This password is auto-generated and will be deleted after first login. You'll set a new password during setup.

### New Admin Password (Set During Wizard)
```
Recommended: nexus_admin_2025_change_me
(Or use your own secure password)
```

---

## 🌐 Access Nexus Web UI

### Option 1: SSH Tunnel (Most Secure - Recommended)

**From your local machine:**
```bash
ssh -L 28081:localhost:28081 ec2-user@YOUR_EC2_PUBLIC_IP

# Keep terminal open, then access:
# http://localhost:28081
```

### Option 2: Direct Access (If Security Group is Open)

If port 28081 is open in your AWS Security Group:
```
http://YOUR_EC2_PUBLIC_IP:28081
```

To check/open security group:
```bash
# Run the helper script
cd /home/ec2-user/projects/maestro-platform/infrastructure
./scripts/expose-nexus.sh
```

---

## 📋 Setup Wizard Steps (5 Minutes)

### Step 1: Initial Login

1. Access Nexus UI (see above)
2. Click **"Sign In"** (top right)
3. Enter credentials:
   - **Username**: `admin`
   - **Password**: `e797357a-7280-4ad6-991e-e78654f29a7c`
4. Click **"Sign In"**

### Step 2: Change Admin Password

The wizard will prompt you to change the password:

1. **New Password**: `nexus_admin_2025_change_me`
2. **Confirm Password**: `nexus_admin_2025_change_me`
3. Click **"Next"**

💡 **Tip**: Use a password manager for production deployments

### Step 3: Configure Anonymous Access

**Choose**: **Disable anonymous access**
- Click **"Disable anonymous access"** (recommended for security)
- Click **"Next"**

💡 For development, you can enable it, but we'll use authenticated access for uploads.

### Step 4: Confirm Setup

- Review settings
- Click **"Finish"**

---

## 🔧 Post-Wizard Configuration (CRITICAL)

After the wizard, you MUST enable the Bearer Token Realm:

### Enable npm Bearer Token Realm

1. Click **Settings** icon (⚙️ gear icon, top navigation)
2. Go to **Security** → **Realms**
3. In the **"Available"** column, find:
   - **npm Bearer Token Realm**
4. Select it and click **">"** to move to **"Active"**
5. Click **"Save"**

✅ **This step is CRITICAL** - without it, package uploads will fail with 401 errors!

---

## 🗂️ Create PyPI Repositories

### Option A: Via Web UI (Manual)

1. Go to **Settings** → **Repository** → **Repositories**
2. Click **"Create repository"**

#### Create pypi-proxy:
- **Recipe**: pypi (proxy)
- **Name**: `pypi-proxy`
- **Remote storage**: `https://pypi.org`
- **Blob store**: default
- Click **"Create repository"**

#### Create pypi-hosted:
- **Recipe**: pypi (hosted)
- **Name**: `pypi-hosted`
- **Deployment policy**: Allow redeploy
- **Blob store**: default
- Click **"Create repository"**

#### Create pypi-group:
- **Recipe**: pypi (group)
- **Name**: `pypi-group`
- **Member repositories**:
  - Select `pypi-hosted`
  - Select `pypi-proxy`
- Click **"Create repository"**

### Option B: Via Script (Automated)

After completing the wizard and enabling realms:

```bash
cd /home/ec2-user/projects/maestro-platform/infrastructure
export NEXUS_ADMIN_PASSWORD=nexus_admin_2025_change_me
./scripts/setup-nexus-pypi.sh
```

---

## ✅ Verification

### Test Authentication

```bash
curl -u admin:nexus_admin_2025_change_me http://localhost:28081/service/rest/v1/status

# Should return: (empty response with HTTP 200)
```

### Test Repository Access

```bash
curl -u admin:nexus_admin_2025_change_me \
  http://localhost:28081/service/rest/v1/repositories | \
  python3 -m json.tool

# Should return: JSON array with repositories
```

---

## 🚀 Upload Packages

Once setup is complete:

```bash
cd /home/ec2-user/projects/maestro-platform/shared

# Set password in environment
export NEXUS_ADMIN_PASSWORD=nexus_admin_2025_change_me

# Upload all maestro packages
./publish-to-nexus.sh
```

Expected output:
```
==================================================
Publishing Maestro Shared Packages to Nexus OSS
==================================================
Target: http://localhost:28081/repository/pypi-hosted/
User: admin

✓ Nexus is accessible

=========================================
Processing: core-logging
=========================================
Building core-logging...
✓ Built
Uploading to Nexus...
✓ Uploaded

... (continues for all 6 packages)

✓ Package publishing complete!
```

---

## 📦 Test Installation

After uploading, test that packages are installable:

```bash
# Install from Nexus
pip install \
  --index-url http://localhost:28081/repository/pypi-group/simple \
  --trusted-host localhost \
  maestro-core-logging==1.0.0

# Should install successfully
```

---

## 🔐 Security Reminders

### After Setup is Complete:

1. **Close public access** to port 28081 (if opened):
   ```bash
   # Via AWS Console: Remove security group rule
   # Or via CLI (see expose-nexus.sh script)
   ```

2. **Use SSH tunnels** for future access:
   ```bash
   ssh -L 28081:localhost:28081 ec2-user@YOUR_EC2_IP
   ```

3. **For Docker builds**: Use internal networking (no public access needed):
   ```dockerfile
   ARG PYPI_INDEX_URL=http://maestro-nexus:8081/repository/pypi-group/simple
   RUN pip install --index-url $PYPI_INDEX_URL --trusted-host maestro-nexus ...
   ```

---

## 🆘 Troubleshooting

### Can't Access UI

**Problem**: Browser shows "Connection refused" or timeout

**Solutions**:
1. Check Nexus is running: `docker ps | grep nexus`
2. Check logs: `docker logs maestro-nexus --tail 50`
3. Use SSH tunnel instead of direct access
4. Verify security group allows port 28081

### Login Fails

**Problem**: "Invalid credentials"

**Solutions**:
1. Verify you're using the initial password: `e797357a-7280-4ad6-991e-e78654f29a7c`
2. Check password wasn't already changed
3. If needed, reset: See "Reset Procedure" below

### Package Upload Fails (401 Unauthorized)

**Problem**: `twine upload` returns 401 error

**Root Cause**: npm Bearer Token Realm not enabled

**Solution**:
1. Go to Settings → Security → Realms
2. Move "npm Bearer Token Realm" to Active
3. Save
4. Retry upload

### Repository Not Found (404)

**Problem**: `pip install` returns 404

**Solution**:
1. Verify repositories exist: Settings → Repository → Repositories
2. Check repository names match (case-sensitive)
3. Run setup-nexus-pypi.sh to create them

---

## 🔄 Reset Procedure (If Needed)

If something goes wrong and you need to start over:

```bash
cd /home/ec2-user/projects/maestro-platform/infrastructure

# Stop and remove
set -a && source .env.infrastructure && set +a
docker-compose -f docker-compose.artifacts-minimal.yml down
docker volume rm maestro_nexus_data

# Start fresh
docker-compose -f docker-compose.artifacts-minimal.yml up -d
sleep 120

# Get new password
docker exec maestro-nexus cat /nexus-data/admin.password
```

---

## 📚 Next Steps

After completing Nexus setup:

1. ✅ **Upload packages**: `./shared/publish-to-nexus.sh`
2. ✅ **Update Dockerfiles**: Configure to use Nexus PyPI
3. ✅ **Test builds**: Verify quality-fabric builds with Nexus
4. ✅ **Document**: Update team wiki with Nexus access instructions
5. ✅ **Secure**: Close public access, use SSH tunnels

---

## 📞 Support

**Documentation**:
- Setup guide: `/infrastructure/docs/NEXUS_PYPI_SETUP.md`
- Migration guide: `/infrastructure/docs/PYPI_MIGRATION_GUIDE.md`
- Public access: `/infrastructure/docs/NEXUS_PUBLIC_ACCESS.md`

**Scripts**:
- Publish packages: `/shared/publish-to-nexus.sh`
- Setup PyPI repos: `/infrastructure/scripts/setup-nexus-pypi.sh`
- Expose publicly: `/infrastructure/scripts/expose-nexus.sh`

**Status**:
- Migration status: `/shared/NEXUS_MIGRATION_STATUS.md`

---

## ✅ Checklist

Use this to track your progress:

- [ ] Access Nexus Web UI
- [ ] Login with initial password (`e797357a-7280-4ad6-991e-e78654f29a7c`)
- [ ] Complete setup wizard
- [ ] Change admin password to `nexus_admin_2025_change_me`
- [ ] Disable anonymous access
- [ ] Enable npm Bearer Token Realm (Settings → Security → Realms)
- [ ] Create PyPI repositories (or run setup-nexus-pypi.sh)
- [ ] Test authentication with curl
- [ ] Upload packages with publish-to-nexus.sh
- [ ] Verify package installation from Nexus
- [ ] Close public access (if opened)
- [ ] Update Dockerfiles to use Nexus

---

**Status**: 🟢 Ready for Setup
**Initial Password**: `e797357a-7280-4ad6-991e-e78654f29a7c`
**Target Password**: `nexus_admin_2025_change_me`
**Time to Complete**: 5-10 minutes

**Let's get it done! 🚀**

