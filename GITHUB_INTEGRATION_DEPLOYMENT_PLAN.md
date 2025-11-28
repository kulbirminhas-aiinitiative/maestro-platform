# MAESTRO Platform - GitHub Integration & Deployment Plan

**Created**: 2025-10-25  
**Objective**: Deploy all services with full GitHub integration  
**Services**: Quality Fabric, Maestro Templates, Gateway, Conductor

---

## Current Status Audit

### ✅ Quality Fabric
- **GitHub**: ✅ Connected (https://github.com/kulbirminhas-aiinitiative/quality-fabric.git)
- **Branch**: feature/shared-libraries-phase1
- **Workflows**: 3 (ci.yml, maestro-cicd.yml, quality-fabric-ci.yml)
- **Pre-commit**: ✅ Configured
- **Nexus Docker**: ❌ **NEEDS CREATION**
- **Status**: **READY FOR NEXUS INTEGRATION**

### ✅ Maestro Templates
- **GitHub**: ✅ Connected (https://github.com/kulbirminhas-aiinitiative/maestro-templates.git)
- **Branch**: main
- **Workflows**: 4 (ci-cd.yml, deploy-prod.yml, deploy-uat.yml, security-scan.yml)
- **Pre-commit**: ✅ Configured
- **Nexus Docker**: ❌ **NEEDS CREATION**
- **Status**: **READY FOR NEXUS INTEGRATION**

### ⚠️ Maestro Gateway
- **GitHub**: ⚠️ No remote configured
- **Branch**: master
- **Workflows**: 3 (ci.yml, code-quality.yml, deploy.yml)
- **Pre-commit**: ✅ Configured
- **Nexus Docker**: ❌ **NEEDS CREATION**
- **Status**: **NEEDS GITHUB REMOTE + NEXUS**

### ❌ Conductor MLOps
- **GitHub**: ❌ Not initialized
- **Workflows**: 8 (including conductor-cicd-nexus.yml ✅)
- **Pre-commit**: ✅ Configured
- **Nexus Docker**: ✅ Already created
- **Nexus Compose**: ✅ Already created
- **Status**: **NEEDS GIT INIT + PUSH**

---

## Effort Estimation

### Phase 1: Nexus Integration (2-3 hours)
**Tasks**:
1. Create Dockerfile.nexus for Quality Fabric
2. Create docker-compose.nexus.yml for Quality Fabric
3. Create .env.nexus for Quality Fabric
4. Create Dockerfile.nexus for Maestro Templates
5. Create docker-compose.nexus.yml for Maestro Templates
6. Create .env.nexus for Maestro Templates
7. Create Dockerfile.gateway.nexus for Maestro Gateway
8. Create docker-compose.gateway.nexus.yml for Gateway
9. Create .env.nexus for Gateway

**Effort**: ~20 minutes per service = 1 hour total

### Phase 2: GitHub Setup (30 minutes)
**Tasks**:
1. Initialize git in conductor
2. Add GitHub remote to maestro-gateway
3. Verify all remotes are correct
4. Create/verify GitHub secrets for Nexus

**Effort**: ~30 minutes

### Phase 3: Local Testing (1-2 hours)
**Tasks**:
1. Test quality-fabric build with Nexus
2. Test maestro-templates build with Nexus
3. Test maestro-gateway build with Nexus
4. Test conductor build with Nexus
5. Test all services together on maestro-network

**Effort**: ~15-20 minutes per service = 1-2 hours

### Phase 4: GitHub Push & CI/CD (30 minutes)
**Tasks**:
1. Commit and push quality-fabric changes
2. Commit and push maestro-templates changes
3. Commit and push maestro-gateway changes
4. Initialize and push conductor
5. Verify GitHub Actions run successfully

**Effort**: ~30 minutes

### Phase 5: Demo Server Deployment (1 hour)
**Tasks**:
1. Deploy quality-fabric to demo server
2. Deploy maestro-templates to demo server
3. Deploy maestro-gateway to demo server
4. Deploy conductor to demo server
5. Verify all services are healthy
6. Test end-to-end integration

**Effort**: ~1 hour

---

## Total Effort: 4-6 hours

**Breakdown**:
- Nexus Integration: 1 hour
- GitHub Setup: 30 minutes
- Local Testing: 1-2 hours
- GitHub Push: 30 minutes
- Demo Deployment: 1 hour
- Buffer: 30 minutes

---

## Execution Plan

### Step 1: Create Nexus Dockerfiles (Quality Fabric)
```bash
cd /home/ec2-user/projects/maestro-platform/quality-fabric
# Create Dockerfile.nexus
# Create docker-compose.nexus.yml
# Create .env.nexus
```

### Step 2: Create Nexus Dockerfiles (Maestro Templates)
```bash
cd /home/ec2-user/projects/maestro-platform/maestro-templates
# Create Dockerfile.nexus
# Create docker-compose.nexus.yml
# Create .env.nexus
```

### Step 3: Create Nexus Dockerfiles (Maestro Gateway)
```bash
cd /home/ec2-user/projects/maestro-platform/maestro-engine
# Already have Dockerfile.gateway.nexus from earlier work
# Create docker-compose.gateway.nexus.yml if not exists
# Create .env.nexus if not exists
```

### Step 4: Initialize Git for Conductor
```bash
cd /home/ec2-user/projects/conductor
git init
git add .
git commit -m "feat: Initial commit with Nexus deployment"
git remote add origin https://github.com/kulbirminhas-aiinitiative/conductor.git
```

### Step 5: Add Remote for Maestro Gateway
```bash
cd /home/ec2-user/projects/maestro-platform/maestro-engine
git remote add origin https://github.com/kulbirminhas-aiinitiative/maestro-engine.git
```

### Step 6: Local Testing
```bash
# Test each service
cd quality-fabric && docker-compose -f docker-compose.nexus.yml up --build -d
cd maestro-templates && docker-compose -f docker-compose.nexus.yml up --build -d
cd maestro-engine && docker-compose -f docker-compose.gateway.nexus.yml up --build -d
cd conductor && docker-compose -f docker-compose.nexus.yml up --build -d

# Verify all services
curl http://localhost:8000/health  # quality-fabric
curl http://localhost:9600/health  # maestro-templates
curl http://localhost:8080/health  # maestro-gateway
curl http://localhost:8003/health  # conductor
```

### Step 7: GitHub Push
```bash
# Quality Fabric
cd /home/ec2-user/projects/maestro-platform/quality-fabric
git add Dockerfile.nexus docker-compose.nexus.yml .env.nexus
git commit -m "feat: Add Nexus deployment configuration"
git push

# Maestro Templates
cd /home/ec2-user/projects/maestro-platform/maestro-templates
git add Dockerfile.nexus docker-compose.nexus.yml .env.nexus
git commit -m "feat: Add Nexus deployment configuration"
git push

# Maestro Gateway
cd /home/ec2-user/projects/maestro-platform/maestro-engine
git add Dockerfile.gateway.nexus docker-compose.gateway.nexus.yml .env.nexus
git commit -m "feat: Add Nexus deployment configuration"
git push -u origin master

# Conductor
cd /home/ec2-user/projects/conductor
git push -u origin main
```

### Step 8: Demo Server Deployment
```bash
# SSH to demo server
ssh ec2-user@18.134.157.225

# Create directories
mkdir -p ~/quality-fabric ~/maestro-templates ~/maestro-gateway ~/conductor

# Deploy from local machine
scp -r /home/ec2-user/projects/maestro-platform/quality-fabric/* ec2-user@18.134.157.225:~/quality-fabric/
scp -r /home/ec2-user/projects/maestro-platform/maestro-templates/* ec2-user@18.134.157.225:~/maestro-templates/
scp -r /home/ec2-user/projects/maestro-platform/maestro-engine/* ec2-user@18.134.157.225:~/maestro-gateway/
scp -r /home/ec2-user/projects/conductor/* ec2-user@18.134.157.225:~/conductor/

# On demo server, deploy each service
cd ~/quality-fabric && docker-compose -f docker-compose.nexus.yml up -d
cd ~/maestro-templates && docker-compose -f docker-compose.nexus.yml up -d
cd ~/maestro-gateway && docker-compose -f docker-compose.gateway.nexus.yml up -d
cd ~/conductor && docker-compose -f docker-compose.nexus.yml up -d
```

---

## Success Criteria

### ✅ Local Success
- [ ] All 4 services build successfully with Nexus
- [ ] All services start without errors
- [ ] All health endpoints return 200 OK
- [ ] Services can communicate via maestro-network

### ✅ GitHub Success
- [ ] All repositories have Nexus Dockerfiles
- [ ] All repositories have docker-compose.nexus.yml
- [ ] All GitHub Actions workflows pass
- [ ] No security vulnerabilities detected

### ✅ Demo Server Success
- [ ] All 4 services running on demo server
- [ ] All health endpoints accessible externally
- [ ] Gateway routes to quality-fabric and templates
- [ ] Conductor can access other services

---

## Risk Mitigation

### Risk 1: Nexus Connection Issues
**Mitigation**: Test Nexus connectivity before building
```bash
curl http://172.21.25.59:28081/repository/pypi-group/simple/
```

### Risk 2: Port Conflicts
**Mitigation**: Document all ports in use
- Quality Fabric: 8000
- Templates: 9600-9601
- Gateway: 8080
- Conductor: 8003 (+ 35432, 36379, 39000, 39090, 33000)

### Risk 3: Service Dependencies
**Mitigation**: Start services in order
1. Infrastructure (postgres, redis, minio)
2. Quality Fabric
3. Maestro Templates
4. Maestro Gateway
5. Conductor

### Risk 4: GitHub Secrets Not Configured
**Mitigation**: Verify secrets before pushing
```bash
# Required secrets for each repo:
- NEXUS_PYPI_INDEX_URL
- NEXUS_PYPI_TRUSTED_HOST
```

---

## Rollback Plan

If issues occur:

1. **Stop problematic service**: `docker-compose down`
2. **Check logs**: `docker-compose logs`
3. **Rollback to previous image**: Use existing Dockerfiles
4. **Restore configuration**: Keep backups of .env files

---

## Post-Deployment Tasks

1. **Documentation**: Update each service's README with Nexus deployment
2. **Monitoring**: Set up centralized monitoring dashboard
3. **Alerts**: Configure health check alerts
4. **Backup**: Set up automated backups for databases
5. **GitOps Migration**: Plan transition to full GitHub-based deployment

---

**Status**: ✅ READY TO EXECUTE  
**Owner**: Development Team  
**Timeline**: 4-6 hours
