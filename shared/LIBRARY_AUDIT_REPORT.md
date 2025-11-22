# Library and Configuration Audit Report

**Date:** October 2, 2025
**Project:** MAESTRO Shared Libraries
**Location:** `/home/ec2-user/projects/shared`

## Executive Summary

This audit identified **4 categories of issues** requiring attention:
1. Poetry configuration deprecation warnings (8 files affected)
2. Missing file error (1 package)
3. Outdated dependencies (20 packages)
4. Outdated pre-commit hook versions

---

## 1. Poetry Configuration Deprecation Warnings

### Issue Description
All `pyproject.toml` files use deprecated Poetry metadata format. Poetry has adopted PEP 621 standard, and the old `[tool.poetry.*]` metadata fields are now deprecated.

### Affected Files
- `/home/ec2-user/projects/shared/pyproject.toml` (root)
- `/home/ec2-user/projects/shared/packages/core-api/pyproject.toml`
- `/home/ec2-user/projects/shared/packages/core-auth/pyproject.toml`
- `/home/ec2-user/projects/shared/packages/core-config/pyproject.toml`
- `/home/ec2-user/projects/shared/packages/core-db/pyproject.toml`
- `/home/ec2-user/projects/shared/packages/core-logging/pyproject.toml`
- `/home/ec2-user/projects/shared/packages/core-messaging/pyproject.toml`
- `/home/ec2-user/projects/shared/packages/monitoring/pyproject.toml`

### Specific Warnings
For each file, Poetry reports:
```
Warning: [tool.poetry.name] is deprecated. Use [project.name] instead.
Warning: [tool.poetry.version] is set but 'version' is not in [project.dynamic].
         If it is static use [project.version]. If it is dynamic, add 'version' to [project.dynamic].
Warning: [tool.poetry.description] is deprecated. Use [project.description] instead.
Warning: [tool.poetry.readme] is set but 'readme' is not in [project.dynamic].
         If it is static use [project.readme]. If it is dynamic, add 'readme' to [project.dynamic].
Warning: [tool.poetry.authors] is deprecated. Use [project.authors] instead.
```

### Impact
- **Severity:** Medium
- **Functional Impact:** None currently - Poetry still supports old format
- **Future Risk:** High - Old format may be removed in future Poetry versions
- **Build/Install Impact:** No current impact on functionality

### Recommended Action
Migrate all `pyproject.toml` files to PEP 621 format:
- Replace `[tool.poetry.name]` → `[project.name]`
- Replace `[tool.poetry.version]` → `[project.version]`
- Replace `[tool.poetry.description]` → `[project.description]`
- Replace `[tool.poetry.readme]` → `[project.readme]`
- Replace `[tool.poetry.authors]` → `[project.authors]`

---

## 2. Missing README File

### Issue Description
The `core-messaging` package declares a README.md file in its pyproject.toml, but the file does not exist.

### Error Message
```
Error: Declared README file does not exist: README.md
Location: packages/core-messaging/
```

### Impact
- **Severity:** Medium
- **Functional Impact:** Package builds may fail when attempting to include README
- **Distribution Impact:** Cannot publish package to PyPI without README
- **Documentation Impact:** Missing package documentation

### Recommended Action
Create `packages/core-messaging/README.md` with package documentation or remove the readme declaration from `packages/core-messaging/pyproject.toml`.

---

## 3. Outdated Dependencies

### Issue Description
20 installed packages have newer versions available. Using outdated packages may expose the project to security vulnerabilities and miss performance improvements.

### Outdated Packages List

| Package | Current Version | Latest Version | Type |
|---------|----------------|----------------|------|
| cryptography | 46.0.1 | 46.0.2 | Security |
| docutils | 0.21.2 | 0.22.2 | Documentation |
| fastapi | 0.115.14 | 0.118.0 | Core Framework |
| importlib-metadata | 8.5.0 | 8.7.0 | Core |
| isort | 5.13.2 | 6.1.0 | Dev Tool |
| nltk | 3.9.1 | 3.9.2 | NLP Library |
| opentelemetry-api | 1.29.0 | 1.37.0 | Monitoring |
| opentelemetry-instrumentation | 0.50b0 | 0.58b0 | Monitoring |
| opentelemetry-sdk | 1.29.0 | 1.37.0 | Monitoring |
| opentelemetry-semantic-conventions | 0.50b0 | 0.58b0 | Monitoring |
| prometheus-client | 0.21.1 | 0.23.1 | Monitoring |
| pydantic-core | 2.33.2 | 2.40.0 | Core |
| pytest-asyncio | 0.24.0 | 1.2.0 | Testing |
| pytest-cov | 6.3.0 | 7.0.0 | Testing |
| redis | 5.3.1 | 6.4.0 | Core |
| sphinx-autodoc-typehints | 2.5.0 | 3.2.0 | Documentation |
| starlette | 0.46.2 | 0.48.0 | Core Framework |
| structlog | 24.4.0 | 25.4.0 | Logging |
| typing-inspection | 0.4.1 | 0.4.2 | Core |
| uvicorn | 0.34.3 | 0.37.0 | Core Framework |

### Impact
- **Severity:** Medium to High (especially for security-related packages)
- **Security Impact:** `cryptography` update available (security-critical)
- **Functionality Impact:** Potential bug fixes and performance improvements missed
- **Compatibility Impact:** Some major version jumps may require code changes (e.g., isort 5.x → 6.x, pytest-asyncio 0.24 → 1.2)

### Recommended Action
1. **Immediate Priority:** Update `cryptography` (security package)
2. **High Priority:** Update OpenTelemetry packages (monitoring improvements)
3. **Medium Priority:** Update core framework packages (FastAPI, Starlette, Uvicorn)
4. **Testing Required:** Major version updates (isort, pytest-asyncio) - review changelogs for breaking changes

**Update Command:**
```bash
poetry update cryptography                    # Security fix
poetry update opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation opentelemetry-semantic-conventions  # Monitoring
poetry update fastapi starlette uvicorn       # Framework updates
poetry update redis structlog prometheus-client  # Infrastructure
```

---

## 4. Outdated Pre-commit Hooks

### Issue Description
The `.pre-commit-config.yaml` file contains outdated versions of pre-commit hooks. Newer versions may include bug fixes, security improvements, and support for newer Python features.

### Outdated Hook Versions

| Hook Repository | Current Version | Status |
|----------------|-----------------|---------|
| psf/black | 23.9.1 | Outdated (latest: 25.x) |
| pycqa/isort | 5.12.0 | Outdated (latest: 6.x) |
| charliermarsh/ruff-pre-commit | v0.1.0 | Very outdated (latest: 0.13.x) |
| pre-commit/mirrors-mypy | v1.6.0 | Outdated (latest: 1.18.x) |
| PyCQA/bandit | 1.7.5 | Outdated (latest: 1.8.x) |
| pycqa/pydocstyle | 6.3.0 | Check for updates |
| pre-commit/pre-commit-hooks | v4.4.0 | Outdated (latest: 4.6.x) |
| Lucas-C/pre-commit-hooks-safety | v1.3.2 | Check for updates |
| Yelp/detect-secrets | v1.4.0 | Outdated (latest: 1.5.x) |

### Impact
- **Severity:** Low to Medium
- **Functionality Impact:** Missing bug fixes and new features
- **Security Impact:** Outdated security scanning tools (bandit, safety, detect-secrets)
- **Python 3.11+ Support:** Some hooks may not fully support newer Python features

### Recommended Action
Run pre-commit autoupdate:
```bash
pre-commit autoupdate
```

---

## 5. Architectural Findings (No Action Required)

### Database Fallback Pattern
**Location:** `packages/core-db/src/maestro_core_db/manager.py:164-166`

The database manager implements a fallback pattern where the write engine is used for read operations when no read replicas are configured:
```python
# Use write engine as read fallback if no read replicas
if not self._read_engines:
    self._read_engines = [self._write_engine]
```

**Status:** ✅ This is intentional architecture, not an issue.

### Password Hash Deprecation Field
**Location:** `packages/core-api/src/maestro_core_api/config.py:33`

The security configuration includes a field for deprecated password hash schemes:
```python
password_hash_deprecated: List[str] = Field(default=["auto"])
```

**Status:** ✅ This is a configuration field for managing password hash migration, not a deprecation warning.

---

## 6. Environment Status

### Python Environment
- **Python Version:** 3.11.13 ✅
- **Implementation:** CPython ✅
- **Virtual Environment:** Active and valid ✅
- **Location:** `/home/ec2-user/.cache/pypoetry/virtualenvs/maestro-shared-wbumiht6-py3.11`

### Tools Status
- **Poetry:** Installed and functional ✅
- **Pre-commit:** ⚠️ Not installed in current environment
  - Available in dev dependencies but not activated
  - **Action Required:** Run `poetry install --with dev` to enable pre-commit hooks

---

## 7. Code Quality Findings

### No Runtime Warnings Detected
- ✅ No deprecation warnings during module imports
- ✅ No explicit warning calls in application code
- ✅ No Python compatibility issues detected

### Dependency Integrity
- ✅ No dependency conflicts detected
- ✅ All required dependencies properly installed
- ✅ Package "deprecated" (v1.2.18) is a legitimate dependency (used by OpenTelemetry), not a warning

---

## Summary of Actions Required

### Priority 1 (Immediate)
1. ❗ Update `cryptography` package (security)
2. ❗ Create missing `packages/core-messaging/README.md`

### Priority 2 (Within 1 Week)
3. ⚠️ Migrate all `pyproject.toml` files to PEP 621 format
4. ⚠️ Update OpenTelemetry packages (monitoring improvements)
5. ⚠️ Update pre-commit hooks (`pre-commit autoupdate`)

### Priority 3 (Within 1 Month)
6. 📋 Review and update core framework packages (FastAPI, Starlette, Uvicorn)
7. 📋 Update remaining outdated packages
8. 📋 Test major version updates (isort 6.x, pytest-asyncio 1.x)

### Optional
9. 💡 Install pre-commit in environment: `poetry install --with dev && pre-commit install`

---

## Audit Methodology

This audit was performed using:
- `poetry check` - Configuration validation
- `poetry show --outdated` - Dependency version checking
- `grep` searches for warning patterns in code
- Manual review of configuration files
- Import testing for runtime warnings

**No functional issues or service unavailability detected.**
**All warnings are configuration/version-related and do not affect current operations.**

---

*Report generated on October 2, 2025*
