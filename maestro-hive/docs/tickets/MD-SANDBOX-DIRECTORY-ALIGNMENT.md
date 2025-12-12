# JIRA Ticket: Sandbox Directory Structure Alignment

**Summary:** Align Sandbox Directory Structure with Dev/Demo Environments
**Type:** Task
**Priority:** Medium
**Component:** Infrastructure / DevOps
**Labels:** sandbox, infrastructure, alignment, tech-debt

---

## Description

The sandbox environment uses a different directory structure than dev and demo servers, causing confusion and maintenance overhead. This ticket addresses the need to standardize directory structures across all environments.

### Current State (Sandbox)

| Service | Sandbox Path | Expected Path |
|---------|--------------|---------------|
| Frontend | `~/projects/maestro-frontend-production` | `~/projects/maestro-platform/maestro-frontend` |
| Engine | `~/projects/maestro-engine-new` | `~/projects/maestro-platform/maestro-engine` |

### Target State (Aligned with Dev/Demo)

All environments should follow the unified structure:
```
~/projects/maestro-platform/
├── maestro-frontend/
├── maestro-engine/
├── maestro-hive/
├── gateway/
├── rag-service/
├── claude_code_api_layer/
└── ... (other services)
```

## Problem Statement

1. **Inconsistent paths** - Scripts, documentation, and CI/CD pipelines reference different paths per environment
2. **Maintenance overhead** - Environment-specific configurations required for identical services
3. **Developer confusion** - Onboarding and debugging complicated by non-standard paths
4. **Deployment risk** - Copy-paste errors when deploying across environments

## Acceptance Criteria

- [ ] **AC-1:** Create migration plan for sandbox directory restructure
- [ ] **AC-2:** Migrate `~/projects/maestro-frontend-production` to `~/projects/maestro-platform/maestro-frontend`
- [ ] **AC-3:** Migrate `~/projects/maestro-engine-new` to `~/projects/maestro-platform/maestro-engine`
- [ ] **AC-4:** Update all systemd services / process managers to use new paths
- [ ] **AC-5:** Update nginx/reverse proxy configurations
- [ ] **AC-6:** Update any cron jobs or scheduled tasks
- [ ] **AC-7:** Verify all services start correctly from new locations
- [ ] **AC-8:** Update SERVICE_PORT_REGISTRY.md with correct sandbox ports (13000 range)
- [ ] **AC-9:** Document any sandbox-specific port mappings

## Technical Implementation Plan

### Phase 1: Discovery & Planning
1. Audit all running services and their current paths
2. Document all configuration files referencing old paths
3. Identify dependencies between services
4. Create rollback plan

### Phase 2: Migration (Maintenance Window)
1. Stop all services gracefully
2. Create symlinks (for backward compatibility during transition):
   ```bash
   ln -s ~/projects/maestro-platform/maestro-frontend ~/projects/maestro-frontend-production
   ln -s ~/projects/maestro-platform/maestro-engine ~/projects/maestro-engine-new
   ```
3. Update service configurations to use canonical paths
4. Test each service individually
5. Remove symlinks after validation period

### Phase 3: Validation
1. Run health checks on all services
2. Execute E2E test suite (MD-3111 tests)
3. Verify frontend accessibility at correct port
4. Confirm API endpoints respond correctly

## Port Alignment Reference

| Environment | Frontend Port | Gateway Port | Engine Port |
|-------------|---------------|--------------|-------------|
| **Dev** | 4200 | 8080 | 5000 |
| **Demo** | 4200 | 8080 | 5000 |
| **Sandbox** | 13000 | 14000 | 15000 |
| **Production** | 443 (nginx) | 443 | Internal |

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Service downtime during migration | Medium | Schedule during low-usage window, use symlinks |
| Broken paths in running processes | High | Test thoroughly before removing old directories |
| CI/CD pipeline failures | Medium | Update pipelines before migration |

## Dependencies

- Access to sandbox server
- Coordination with team for maintenance window
- Backup of current configurations

## Definition of Done

- [ ] All services running from `~/projects/maestro-platform/` structure
- [ ] No references to old paths in active configurations
- [ ] Documentation updated (SERVICE_PORT_REGISTRY.md, DEPLOYMENT.md)
- [ ] E2E tests passing on sandbox
- [ ] Team notified of new paths

## Related Tickets

- MD-3111 (Frontend Integration Tests) - Tests should pass post-migration
- SERVICE_PORT_REGISTRY.md - Needs sandbox port documentation

---

**Estimated Effort:** 4-6 hours (including testing)
**Environment:** Sandbox only
**Requires Maintenance Window:** Yes (15-30 minutes)
