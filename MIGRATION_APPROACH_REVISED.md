# Revised Migration Approach: Local Path Dependencies

**Decision**: Use local path dependencies during migration, publish packages later

## Why This Works Better

1. **Faster Migration** - No need to wait for package registry setup
2. **Easier Testing** - Can test changes immediately without publishing
3. **Common Pattern** - Standard approach during migrations
4. **Publish Later** - Once everything works, we publish to registry

## Approach

### During Migration (Now)
```toml
# In consuming repos (maestro-engine, quality-fabric, etc.)
[tool.poetry.dependencies]
maestro-core-api = {path = "../maestro-shared/packages/core-api", develop = true}
maestro-core-logging = {path = "../maestro-shared/packages/core-logging", develop = true}
# etc.
```

### After Migration (Later)
```toml
# Once published to GitHub Packages
[tool.poetry.dependencies]
maestro-core-api = "^0.1.0"
maestro-core-logging = "^0.1.0"

[[tool.poetry.source]]
name = "maestro-shared"
url = "https://pypi.pkg.github.com/kulbirminhas-aiinitiative"
```

## Benefits

- ✅ Continue migration immediately
- ✅ Test everything locally first
- ✅ Fix any issues before publishing
- ✅ Publish when stable
- ✅ No blocking on GitHub token setup

## Repository Structure

```
/home/ec2-user/projects/
├── maestro-shared/              # Shared packages (source)
├── maestro-engine/              # References maestro-shared via path
├── maestro-frontend/            # Independent
├── quality-fabric/              # References maestro-shared via path
├── maestro-hive/                # References maestro-shared via path
└── maestro-ml-platform/         # Independent
```

## Publishing Later

Once migration is complete and tested:
1. Fix GitHub token scopes
2. Publish all packages to GitHub Packages
3. Update consuming repos to use published versions
4. Remove local path dependencies

## Next Steps

1. ✅ maestro-shared repository created
2. ➡️ Extract quality-fabric (use path dependencies)
3. ➡️ Extract maestro-engine (use path dependencies)
4. ➡️ Extract maestro-frontend (no dependencies needed)
5. ➡️ Test everything works
6. ➡️ Publish packages (later, when token is fixed)

---

**This approach is more practical and lets us continue the migration now!**
