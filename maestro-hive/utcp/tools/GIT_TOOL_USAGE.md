# UTCP Git Tool - Agent Usage Guide

**MD-634: Epic 43 - GitHub Repository Setup**

The UTCP Git Tool enables AI agents to interact with Git repositories and GitHub APIs for automated repository management, CI/CD operations, and collaborative development workflows.

## Overview

The `GitTool` class provides a comprehensive set of operations for:
- Local Git operations (commit, push, branch, etc.)
- GitHub API operations (PRs, branch protection, file management)
- Repository setup and configuration

## Installation & Configuration

### Required Credentials

```python
credentials = {
    "repo_path": "/path/to/local/repo",  # Required
    "github_token": "ghp_xxxx",          # Optional - for GitHub API
    "github_owner": "organization",       # Optional - GitHub org/user
    "github_repo": "repository-name"      # Optional - GitHub repo name
}
```

### Initialize the Tool

```python
from utcp.tools.git_tool import GitTool

git = GitTool({
    "repo_path": "/home/ec2-user/projects/maestro-frontend-production",
    "github_token": os.environ.get("GITHUB_TOKEN"),
    "github_owner": "fifth-9",
    "github_repo": "maestro-frontend-production"
})
```

## Core Git Operations

### Repository Status

```python
# Get current repository status
result = await git.get_status()
# Returns: branch, modified files, staged files, ahead/behind counts

# Health check
result = await git.health_check()
```

### Branching

```python
# Create new branch
result = await git.create_branch("feature/new-feature", from_branch="main")

# Checkout branch
result = await git.checkout("develop")
```

### Staging & Committing

```python
# Stage files
result = await git.add(["src/file1.ts", "src/file2.ts"])
# or stage all
result = await git.add()

# Commit changes
result = await git.commit(
    message="feat: add new feature",
    author="AI Agent <agent@maestro.ai>"
)
```

### Push & Pull

```python
# Push to remote
result = await git.push(remote="origin", branch="feature/new-feature", set_upstream=True)

# Pull from remote
result = await git.pull(remote="origin", branch="main")
```

### History & Diff

```python
# Get commit log
result = await git.get_log(count=10, oneline=True)

# Get diff
result = await git.diff(staged=False, file="src/app.ts")
```

## GitHub API Operations

### Pull Requests

```python
# Create PR
result = await git.create_pull_request(
    title="feat: implement new feature",
    body="## Summary\nThis PR adds...",
    head="feature/new-feature",
    base="main",
    draft=False
)
# Returns: PR number, URL, state

# Get PR details
result = await git.get_pull_request(pr_number=123)
```

### Branch Protection (MD-634)

```python
# Set branch protection rules
result = await git.set_branch_protection(
    branch="main",
    required_reviews=2,
    dismiss_stale_reviews=True,
    require_code_owner_reviews=True,
    required_status_checks=["CI", "build-check"],
    enforce_admins=False,
    allow_force_pushes=False,
    allow_deletions=False
)

# Get current protection rules
result = await git.get_branch_protection(branch="main")
```

### File Management

```python
# Create or update file via GitHub API
result = await git.create_or_update_file(
    path=".github/CODEOWNERS",
    content="* @fifth-9/core-team",
    message="chore: add CODEOWNERS",
    branch="main"
)

# Get file content
result = await git.get_file(path=".github/workflows/ci.yml", branch="main")
```

### GitHub Actions

```python
# List workflows
result = await git.list_workflows()

# Get workflow runs
result = await git.get_workflow_runs(
    workflow_id=12345,  # optional
    status="completed"   # optional: queued, in_progress, completed
)
```

### Labels

```python
# Create label
result = await git.create_label(
    name="priority:high",
    color="ff0000",
    description="High priority issue"
)

# Add labels to issue/PR
result = await git.add_labels(
    issue_number=123,
    labels=["backend", "bug", "priority:high"]
)
```

## Agent Workflow Examples

### Example 1: Feature Development Flow

```python
async def implement_feature(git: GitTool, feature_name: str, files: dict):
    # 1. Create feature branch
    await git.create_branch(f"feature/{feature_name}", from_branch="main")

    # 2. Make changes (files written by agent)

    # 3. Stage and commit
    await git.add()
    await git.commit(f"feat: {feature_name}")

    # 4. Push branch
    await git.push(set_upstream=True)

    # 5. Create PR
    result = await git.create_pull_request(
        title=f"feat: {feature_name}",
        body=f"## Summary\nImplements {feature_name}",
        head=f"feature/{feature_name}",
        base="main"
    )

    return result.data["url"]
```

### Example 2: Repository Setup (MD-634)

```python
async def setup_repository(git: GitTool):
    # 1. Set branch protection
    await git.set_branch_protection(
        branch="main",
        required_reviews=1,
        require_code_owner_reviews=True,
        required_status_checks=["CI"]
    )

    await git.set_branch_protection(
        branch="develop",
        required_reviews=1,
        required_status_checks=["CI"]
    )

    # 2. Create standard labels
    labels = [
        ("bug", "d73a4a", "Something isn't working"),
        ("enhancement", "a2eeef", "New feature or request"),
        ("documentation", "0075ca", "Improvements to docs"),
        ("backend", "5319e7", "Backend changes"),
        ("frontend", "1d76db", "Frontend changes"),
    ]

    for name, color, desc in labels:
        await git.create_label(name, color, desc)

    # 3. Add CODEOWNERS
    codeowners = """
* @fifth-9/core-team
/backend/ @fifth-9/backend-team
/frontend/ @fifth-9/frontend-team
"""
    await git.create_or_update_file(
        path=".github/CODEOWNERS",
        content=codeowners,
        message="chore: add CODEOWNERS"
    )
```

### Example 3: CI Status Check

```python
async def check_ci_status(git: GitTool, branch: str):
    # Get workflow runs for branch
    result = await git.get_workflow_runs(status="completed")

    if result.success:
        runs = result.data["runs"]
        branch_runs = [r for r in runs if r["branch"] == branch]

        if branch_runs:
            latest = branch_runs[0]
            return {
                "status": latest["conclusion"],
                "url": latest["url"]
            }

    return {"status": "unknown"}
```

## Error Handling

All methods return a `ToolResult` object:

```python
result = await git.commit("message")

if result.success:
    commit_hash = result.data["hash"]
else:
    error_code = result.error_code
    error_message = result.error
```

### Common Error Codes

- `GITHUB_NOT_CONFIGURED` - GitHub credentials missing
- `GIT_COMMAND_FAILED` - Local git command failed
- `GITHUB_404` - Resource not found
- `GITHUB_403` - Permission denied
- `FILE_NOT_FOUND` - File doesn't exist in repo

## Best Practices for Agents

1. **Always check results** - Use `result.success` before accessing `result.data`
2. **Use health_check** - Verify connectivity before operations
3. **Commit messages** - Follow conventional commits format
4. **Branch naming** - Use `feature/`, `fix/`, `chore/` prefixes
5. **PR descriptions** - Include summary, testing notes, related issues

## Integration with Maestro

The GitTool is designed to be used by Maestro agents for:
- Automated code deployment
- PR creation for agent-generated code
- Repository maintenance tasks
- CI/CD pipeline management

Register the tool with the UTCP registry:

```python
from utcp.registry import ToolRegistry

registry = ToolRegistry()
registry.register("git", GitTool, {
    "repo_path": config.REPO_PATH,
    "github_token": config.GITHUB_TOKEN,
    "github_owner": config.GITHUB_OWNER,
    "github_repo": config.GITHUB_REPO
})

# Agent can then use
git = await registry.get_tool("git")
```
