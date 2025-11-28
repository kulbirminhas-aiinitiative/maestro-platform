"""
UTCP Git Operations Tool

Provides Git operations for AI agents:
- Clone repositories
- Commit changes
- Push to remote
- Create branches
- Create pull requests (GitHub)

Part of MD-853: Git Operations Tool - commit, push, branch, PR
"""

import asyncio
import os
import aiohttp
from typing import Any, Dict, List, Optional
from ..base import UTCPTool, ToolConfig, ToolCapability, ToolResult, ToolError


class GitTool(UTCPTool):
    """Git integration tool for workflow automation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="git",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
                ToolCapability.EXECUTE,
            ],
            required_credentials=["repo_path"],
            optional_credentials=["github_token", "github_owner", "github_repo"],
            rate_limit=None,
            timeout=60,
        )

    def __init__(self, credentials: Dict[str, str]):
        super().__init__(credentials)
        self.repo_path = credentials["repo_path"]
        self.github_token = credentials.get("github_token")
        self.github_owner = credentials.get("github_owner")
        self.github_repo = credentials.get("github_repo")

    async def _run_git(self, *args: str, cwd: Optional[str] = None) -> str:
        """Run git command and return output."""
        cmd = ["git"] + list(args)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd or self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip() or stdout.decode().strip()
            raise ToolError(
                f"Git command failed: {' '.join(args)} - {error_msg}",
                code="GIT_COMMAND_FAILED"
            )

        return stdout.decode().strip()

    async def health_check(self) -> ToolResult:
        """Check Git repository accessibility."""
        try:
            # Check if repo path exists and is a git repo
            if not os.path.exists(self.repo_path):
                return ToolResult.fail(f"Repository path does not exist: {self.repo_path}", code="REPO_NOT_FOUND")

            # Get current branch
            branch = await self._run_git("rev-parse", "--abbrev-ref", "HEAD")
            commit = await self._run_git("rev-parse", "--short", "HEAD")

            return ToolResult.ok({
                "connected": True,
                "repo_path": self.repo_path,
                "branch": branch,
                "commit": commit,
                "github_configured": bool(self.github_token and self.github_owner and self.github_repo),
            })
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def get_status(self) -> ToolResult:
        """
        Get repository status.

        Returns:
            ToolResult with status info (branch, modified files, etc.)
        """
        try:
            branch = await self._run_git("rev-parse", "--abbrev-ref", "HEAD")
            status = await self._run_git("status", "--porcelain")

            modified = []
            untracked = []
            staged = []

            for line in status.split("\n"):
                if not line:
                    continue
                status_code = line[:2]
                file_path = line[3:]

                if status_code[0] in "MADRC":
                    staged.append(file_path)
                if status_code[1] in "MD":
                    modified.append(file_path)
                if status_code == "??":
                    untracked.append(file_path)

            # Get remote tracking info
            try:
                upstream = await self._run_git("rev-parse", "--abbrev-ref", "@{u}")
                ahead_behind = await self._run_git("rev-list", "--left-right", "--count", f"{upstream}...HEAD")
                behind, ahead = ahead_behind.split()
            except:
                upstream = None
                ahead = 0
                behind = 0

            return ToolResult.ok({
                "branch": branch,
                "modified": modified,
                "untracked": untracked,
                "staged": staged,
                "upstream": upstream,
                "ahead": int(ahead),
                "behind": int(behind),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_STATUS_FAILED")

    async def create_branch(self, branch_name: str, from_branch: Optional[str] = None) -> ToolResult:
        """
        Create a new branch.

        Args:
            branch_name: Name for the new branch
            from_branch: Base branch (defaults to current)

        Returns:
            ToolResult with success status
        """
        try:
            if from_branch:
                await self._run_git("checkout", from_branch)

            await self._run_git("checkout", "-b", branch_name)

            return ToolResult.ok({
                "created": True,
                "branch": branch_name,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_BRANCH_FAILED")

    async def checkout(self, branch_name: str) -> ToolResult:
        """
        Checkout a branch.

        Args:
            branch_name: Branch to checkout

        Returns:
            ToolResult with success status
        """
        try:
            await self._run_git("checkout", branch_name)

            return ToolResult.ok({
                "checked_out": True,
                "branch": branch_name,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CHECKOUT_FAILED")

    async def add(self, files: Optional[List[str]] = None) -> ToolResult:
        """
        Stage files for commit.

        Args:
            files: List of files to stage (None = all)

        Returns:
            ToolResult with staged files
        """
        try:
            if files:
                for file in files:
                    await self._run_git("add", file)
            else:
                await self._run_git("add", "-A")

            # Get staged files
            staged = await self._run_git("diff", "--cached", "--name-only")
            staged_files = [f for f in staged.split("\n") if f]

            return ToolResult.ok({
                "staged": True,
                "files": staged_files,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_FAILED")

    async def commit(self, message: str, author: Optional[str] = None) -> ToolResult:
        """
        Create a commit.

        Args:
            message: Commit message
            author: Optional author (format: "Name <email>")

        Returns:
            ToolResult with commit hash
        """
        try:
            args = ["commit", "-m", message]
            if author:
                args.extend(["--author", author])

            await self._run_git(*args)

            # Get commit hash
            commit_hash = await self._run_git("rev-parse", "--short", "HEAD")

            return ToolResult.ok({
                "committed": True,
                "hash": commit_hash,
                "message": message,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="COMMIT_FAILED")

    async def push(self, remote: str = "origin", branch: Optional[str] = None, set_upstream: bool = False) -> ToolResult:
        """
        Push commits to remote.

        Args:
            remote: Remote name
            branch: Branch to push (defaults to current)
            set_upstream: Set upstream tracking

        Returns:
            ToolResult with success status
        """
        try:
            if not branch:
                branch = await self._run_git("rev-parse", "--abbrev-ref", "HEAD")

            args = ["push", remote, branch]
            if set_upstream:
                args.insert(1, "-u")

            await self._run_git(*args)

            return ToolResult.ok({
                "pushed": True,
                "remote": remote,
                "branch": branch,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="PUSH_FAILED")

    async def pull(self, remote: str = "origin", branch: Optional[str] = None) -> ToolResult:
        """
        Pull changes from remote.

        Args:
            remote: Remote name
            branch: Branch to pull

        Returns:
            ToolResult with success status
        """
        try:
            args = ["pull", remote]
            if branch:
                args.append(branch)

            output = await self._run_git(*args)

            return ToolResult.ok({
                "pulled": True,
                "output": output,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="PULL_FAILED")

    async def get_log(self, count: int = 10, oneline: bool = True) -> ToolResult:
        """
        Get commit log.

        Args:
            count: Number of commits
            oneline: Use oneline format

        Returns:
            ToolResult with commit list
        """
        try:
            args = ["log", f"-{count}"]
            if oneline:
                args.append("--oneline")
            else:
                args.append("--format=%H|%an|%ae|%s|%ai")

            output = await self._run_git(*args)

            commits = []
            for line in output.split("\n"):
                if not line:
                    continue
                if oneline:
                    parts = line.split(" ", 1)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1] if len(parts) > 1 else "",
                    })
                else:
                    parts = line.split("|")
                    if len(parts) >= 5:
                        commits.append({
                            "hash": parts[0],
                            "author_name": parts[1],
                            "author_email": parts[2],
                            "message": parts[3],
                            "date": parts[4],
                        })

            return ToolResult.ok({"commits": commits})
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_LOG_FAILED")

    async def diff(self, staged: bool = False, file: Optional[str] = None) -> ToolResult:
        """
        Get diff of changes.

        Args:
            staged: Show staged changes
            file: Specific file to diff

        Returns:
            ToolResult with diff output
        """
        try:
            args = ["diff"]
            if staged:
                args.append("--cached")
            if file:
                args.append(file)

            output = await self._run_git(*args)

            return ToolResult.ok({
                "diff": output,
                "has_changes": bool(output),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="DIFF_FAILED")

    async def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = "main",
        draft: bool = False
    ) -> ToolResult:
        """
        Create a GitHub pull request.

        Args:
            title: PR title
            body: PR description
            head: Head branch
            base: Base branch
            draft: Create as draft PR

        Returns:
            ToolResult with PR URL and number
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/pulls"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            data = {
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            return ToolResult.ok({
                "number": result["number"],
                "url": result["html_url"],
                "state": result["state"],
                "created": True,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_PR_FAILED")

    async def get_pull_request(self, pr_number: int) -> ToolResult:
        """
        Get pull request details.

        Args:
            pr_number: PR number

        Returns:
            ToolResult with PR details
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/pulls/{pr_number}"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            return ToolResult.ok({
                "number": result["number"],
                "title": result["title"],
                "state": result["state"],
                "url": result["html_url"],
                "head": result["head"]["ref"],
                "base": result["base"]["ref"],
                "mergeable": result.get("mergeable"),
                "author": result["user"]["login"],
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_PR_FAILED")

    # =========================================================================
    # GitHub Repository Setup Methods (MD-634)
    # =========================================================================

    async def set_branch_protection(
        self,
        branch: str = "main",
        required_reviews: int = 1,
        dismiss_stale_reviews: bool = True,
        require_code_owner_reviews: bool = True,
        required_status_checks: Optional[List[str]] = None,
        enforce_admins: bool = False,
        allow_force_pushes: bool = False,
        allow_deletions: bool = False
    ) -> ToolResult:
        """
        Set branch protection rules on a GitHub branch.

        Args:
            branch: Branch name to protect
            required_reviews: Number of required approving reviews
            dismiss_stale_reviews: Dismiss approvals when new commits pushed
            require_code_owner_reviews: Require CODEOWNERS approval
            required_status_checks: List of required CI checks
            enforce_admins: Apply rules to admins too
            allow_force_pushes: Allow force pushes
            allow_deletions: Allow branch deletion

        Returns:
            ToolResult with protection status
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/branches/{branch}/protection"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            data = {
                "required_status_checks": {
                    "strict": True,
                    "contexts": required_status_checks or []
                } if required_status_checks else None,
                "enforce_admins": enforce_admins,
                "required_pull_request_reviews": {
                    "dismissal_restrictions": {},
                    "dismiss_stale_reviews": dismiss_stale_reviews,
                    "require_code_owner_reviews": require_code_owner_reviews,
                    "required_approving_review_count": required_reviews,
                },
                "restrictions": None,
                "allow_force_pushes": allow_force_pushes,
                "allow_deletions": allow_deletions,
            }

            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=data, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            return ToolResult.ok({
                "protected": True,
                "branch": branch,
                "required_reviews": required_reviews,
                "require_code_owner_reviews": require_code_owner_reviews,
                "url": result.get("url"),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="SET_BRANCH_PROTECTION_FAILED")

    async def get_branch_protection(self, branch: str = "main") -> ToolResult:
        """
        Get branch protection rules.

        Args:
            branch: Branch name

        Returns:
            ToolResult with protection rules
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/branches/{branch}/protection"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 404:
                        return ToolResult.ok({
                            "protected": False,
                            "branch": branch,
                        })
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            return ToolResult.ok({
                "protected": True,
                "branch": branch,
                "required_reviews": result.get("required_pull_request_reviews", {}).get("required_approving_review_count", 0),
                "enforce_admins": result.get("enforce_admins", {}).get("enabled", False),
                "required_status_checks": result.get("required_status_checks", {}).get("contexts", []),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_BRANCH_PROTECTION_FAILED")

    async def create_or_update_file(
        self,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None
    ) -> ToolResult:
        """
        Create or update a file in the repository via GitHub API.
        Useful for creating CODEOWNERS, workflows, PR templates, etc.

        Args:
            path: File path in repo (e.g., ".github/CODEOWNERS")
            content: File content
            message: Commit message
            branch: Target branch
            sha: SHA of file to update (required for updates)

        Returns:
            ToolResult with commit info
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            import base64

            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{path}"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }

            # Get existing file SHA if not provided
            if not sha:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=headers, params={"ref": branch}) as response:
                        if response.status == 200:
                            existing = await response.json()
                            sha = existing.get("sha")

            data = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": branch,
            }
            if sha:
                data["sha"] = sha

            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=data, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            return ToolResult.ok({
                "created": sha is None,
                "updated": sha is not None,
                "path": path,
                "sha": result["content"]["sha"],
                "commit_sha": result["commit"]["sha"],
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_OR_UPDATE_FILE_FAILED")

    async def get_file(self, path: str, branch: str = "main") -> ToolResult:
        """
        Get file content from repository.

        Args:
            path: File path in repo
            branch: Branch name

        Returns:
            ToolResult with file content and metadata
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            import base64

            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{path}"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params={"ref": branch}) as response:
                    if response.status == 404:
                        return ToolResult.fail(
                            f"File not found: {path}",
                            code="FILE_NOT_FOUND"
                        )
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            content = base64.b64decode(result["content"]).decode() if result.get("content") else ""

            return ToolResult.ok({
                "path": path,
                "sha": result["sha"],
                "size": result["size"],
                "content": content,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_FILE_FAILED")

    async def list_workflows(self) -> ToolResult:
        """
        List GitHub Actions workflows.

        Returns:
            ToolResult with workflow list
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/workflows"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            workflows = [
                {
                    "id": w["id"],
                    "name": w["name"],
                    "path": w["path"],
                    "state": w["state"],
                }
                for w in result.get("workflows", [])
            ]

            return ToolResult.ok({
                "total_count": result.get("total_count", 0),
                "workflows": workflows,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="LIST_WORKFLOWS_FAILED")

    async def get_workflow_runs(self, workflow_id: Optional[int] = None, status: Optional[str] = None) -> ToolResult:
        """
        Get GitHub Actions workflow runs.

        Args:
            workflow_id: Filter by workflow ID
            status: Filter by status (queued, in_progress, completed)

        Returns:
            ToolResult with workflow runs
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            if workflow_id:
                url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/workflows/{workflow_id}/runs"
            else:
                url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/actions/runs"

            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

            params = {}
            if status:
                params["status"] = status

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            runs = [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "status": r["status"],
                    "conclusion": r.get("conclusion"),
                    "branch": r["head_branch"],
                    "created_at": r["created_at"],
                    "url": r["html_url"],
                }
                for r in result.get("workflow_runs", [])[:20]  # Limit to 20
            ]

            return ToolResult.ok({
                "total_count": result.get("total_count", 0),
                "runs": runs,
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_WORKFLOW_RUNS_FAILED")

    async def add_labels(self, issue_number: int, labels: List[str]) -> ToolResult:
        """
        Add labels to an issue or PR.

        Args:
            issue_number: Issue/PR number
            labels: List of label names

        Returns:
            ToolResult with updated labels
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/issues/{issue_number}/labels"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"labels": labels}, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            return ToolResult.ok({
                "issue_number": issue_number,
                "labels": [l["name"] for l in result],
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="ADD_LABELS_FAILED")

    async def create_label(self, name: str, color: str, description: str = "") -> ToolResult:
        """
        Create a repository label.

        Args:
            name: Label name
            color: Hex color (without #)
            description: Label description

        Returns:
            ToolResult with label info
        """
        if not self.github_token or not self.github_owner or not self.github_repo:
            return ToolResult.fail(
                "GitHub credentials not configured",
                code="GITHUB_NOT_CONFIGURED"
            )

        try:
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/labels"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
            }

            data = {
                "name": name,
                "color": color.lstrip("#"),
                "description": description,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status >= 400:
                        error_text = await response.text()
                        raise ToolError(
                            f"GitHub API error: {response.status} - {error_text}",
                            code=f"GITHUB_{response.status}"
                        )

                    result = await response.json()

            return ToolResult.ok({
                "name": result["name"],
                "color": result["color"],
                "description": result.get("description", ""),
            })
        except ToolError:
            raise
        except Exception as e:
            return ToolResult.fail(str(e), code="CREATE_LABEL_FAILED")
