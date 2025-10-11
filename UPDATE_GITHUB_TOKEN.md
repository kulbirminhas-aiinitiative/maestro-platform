# GitHub Token Update Guide

Your current GitHub token needs additional permissions to publish packages.

## Quick Method: Device Flow

1. **Copy this code**: `56D9-DA0C`
2. **Open**: https://github.com/login/device
3. **Paste the code** and click Continue
4. **Authorize** the additional scopes

## Alternative: Create New Token Manually

1. **Go to**: https://github.com/settings/tokens/new
2. **Token name**: `maestro-shared-publishing`
3. **Select scopes**:
   - ✅ `repo` (all)
   - ✅ `write:packages`
   - ✅ `read:packages`
   - ✅ `delete:packages` (optional)
   - ✅ `workflow`
   - ✅ `read:org`
   - ✅ `gist`
4. **Generate token** and copy it
5. **Run in terminal**:
   ```bash
   export GITHUB_TOKEN="ghp_your_new_token_here"
   gh auth login --with-token <<< "$GITHUB_TOKEN"
   ```

## After Token Update

Run this to verify:
```bash
gh auth status
```

Should show:
```
Token scopes: 'gist', 'read:org', 'repo', 'workflow', 'write:packages', 'read:packages'
```

Then we can continue publishing packages!
