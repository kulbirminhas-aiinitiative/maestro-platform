# GitHub Packages Setup Guide

**Registry Choice**: GitHub Packages
**Date**: 2025-10-08

## Prerequisites

Before we can publish packages to GitHub Packages, you need:

1. **GitHub Organization or Username**
   - Where do you want to publish? (e.g., `your-org` or your personal account)
   - Packages will be published under: `https://github.com/YOUR_ORG/maestro-shared`

2. **GitHub Personal Access Token (PAT)**
   - Need a token with `write:packages` and `read:packages` permissions
   - Also needs `repo` scope for private repositories

## Step 1: Create GitHub Personal Access Token

```bash
# Go to: https://github.com/settings/tokens
# Click "Generate new token (classic)"
# Select scopes:
#   ✅ repo (all)
#   ✅ write:packages
#   ✅ read:packages
#   ✅ delete:packages (optional, for cleanup)
# Generate and copy the token
```

## Step 2: Configure Poetry for GitHub Packages

```bash
# Set your GitHub username
export GITHUB_USERNAME="your-username"

# Set your GitHub token (the one you just created)
export GITHUB_TOKEN="ghp_xxxxxxxxxxxx"

# Configure Poetry to use GitHub Packages
poetry config repositories.github https://github.com/YOUR_ORG/maestro-shared

# Configure authentication
poetry config http-basic.github $GITHUB_USERNAME $GITHUB_TOKEN
```

## Step 3: Test Configuration

```bash
# Verify configuration
poetry config --list | grep github

# Should show:
# repositories.github = "https://github.com/YOUR_ORG/maestro-shared"
# http-basic.github.username = "your-username"
```

## For Publishing

When ready to publish packages:

```bash
cd packages/core-api
poetry build
poetry publish --repository github
```

## For Installing

To install from GitHub Packages:

```toml
# pyproject.toml
[[tool.poetry.source]]
name = "github"
url = "https://github.com/YOUR_ORG/maestro-shared"
priority = "supplemental"

[tool.poetry.dependencies]
maestro-core-api = {version = "^0.1.0", source = "github"}
```

## Current Status

- [ ] GitHub organization/username decided: __________________
- [ ] GitHub Personal Access Token created
- [ ] Poetry configured with credentials
- [ ] Configuration tested

## Next Steps

Once configured, we'll:
1. Create maestro-shared repository
2. Move shared packages there
3. Publish to GitHub Packages
4. Update consuming repos to install from GitHub Packages
