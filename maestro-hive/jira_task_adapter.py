#!/usr/bin/env python3
"""
JIRA Task Adapter - Bridge between JIRA and TeamExecutionEngineV2

Enables running JIRA tasks through the AI-driven team execution system.

Usage:
    from jira_task_adapter import JiraTaskAdapter

    adapter = JiraTaskAdapter()
    requirement = await adapter.task_to_requirement("MD-131")

    # Then feed to TeamExecutionEngineV2
    engine = TeamExecutionEngineV2()
    result = await engine.execute(requirement=requirement)
"""

import os
import re
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import subprocess

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class JiraTask:
    """Represents a JIRA task with all relevant fields"""
    key: str
    summary: str
    description: str
    priority: str
    status: str
    issue_type: str
    labels: List[str]
    parent_key: Optional[str] = None
    parent_summary: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    attachments: List[Dict[str, str]] = field(default_factory=list)
    created: Optional[str] = None
    updated: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None

    # Extracted from description
    technical_requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


@dataclass
class JiraConfig:
    """JIRA configuration loaded from .jira-config"""
    base_url: str
    email: str
    api_token: str
    project_key: str


# =============================================================================
# JIRA TASK ADAPTER
# =============================================================================

class JiraTaskAdapter:
    """
    Adapts JIRA tasks for use with TeamExecutionEngineV2.

    Features:
    - Fetches task details via JIRA API
    - Converts JIRA fields to requirement format
    - Extracts acceptance criteria
    - Maps JIRA status to execution state
    - Updates JIRA with execution results
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize adapter with JIRA configuration"""
        self.config = self._load_config(config_path)
        logger.info(f"JiraTaskAdapter initialized for {self.config.base_url}")

    def _load_config(self, config_path: Optional[str] = None) -> JiraConfig:
        """Load JIRA configuration from file or environment"""
        # Try multiple config paths
        paths_to_try = [
            config_path,
            os.environ.get('JIRA_CONFIG_PATH'),
            '/home/ec2-user/projects/maestro-frontend-production/.jira-config',
            Path(__file__).parent.parent / '.jira-config',
            Path.home() / '.jira-config'
        ]

        config_content = None
        for path in paths_to_try:
            if path and Path(path).exists():
                config_content = Path(path).read_text()
                logger.info(f"Loaded JIRA config from {path}")
                break

        if not config_content:
            # Fall back to environment variables
            return JiraConfig(
                base_url=os.environ.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'),
                email=os.environ.get('JIRA_EMAIL', ''),
                api_token=os.environ.get('JIRA_API_TOKEN', ''),
                project_key=os.environ.get('JIRA_PROJECT_KEY', 'MD')
            )

        # Parse config file
        config = {}
        for line in config_content.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip()

        return JiraConfig(
            base_url=config.get('JIRA_BASE_URL', 'https://fifth9.atlassian.net'),
            email=config.get('JIRA_EMAIL', ''),
            api_token=config.get('JIRA_API_TOKEN', ''),
            project_key=config.get('JIRA_PROJECT_KEY', 'MD')
        )

    def _jira_request(self, endpoint: str, method: str = 'GET', body: Optional[Dict] = None) -> Dict:
        """Make a request to JIRA API"""
        url = f"{self.config.base_url}{endpoint}"

        cmd = [
            'curl', '-s', '-X', method,
            '-H', 'Content-Type: application/json',
            '-u', f'{self.config.email}:{self.config.api_token}'
        ]

        if body:
            # Write body to temp file to avoid escaping issues
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(body, f)
                temp_file = f.name
            cmd.extend(['-d', f'@{temp_file}'])

        cmd.append(url)

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if body:
                os.unlink(temp_file)

            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
            else:
                logger.error(f"JIRA API error: {result.stderr}")
                return {}
        except Exception as e:
            logger.error(f"JIRA request failed: {e}")
            return {}

    async def fetch_task(self, task_key: str) -> Optional[JiraTask]:
        """
        Fetch a JIRA task by key.

        Args:
            task_key: JIRA task key (e.g., "MD-131")

        Returns:
            JiraTask object or None if not found
        """
        logger.info(f"Fetching JIRA task: {task_key}")

        # Fetch task with all relevant fields
        result = self._jira_request(
            f'/rest/api/3/issue/{task_key}?fields=summary,description,priority,status,labels,issuetype,parent,subtasks,attachment,created,updated,assignee,reporter'
        )

        if not result or 'key' not in result:
            logger.error(f"Task {task_key} not found")
            return None

        fields = result.get('fields', {})

        # Extract description text from ADF
        description = self._extract_text_from_adf(fields.get('description', {}))

        # Extract acceptance criteria from description
        acceptance_criteria = self._extract_acceptance_criteria(description)

        # Extract technical requirements
        technical_requirements = self._extract_technical_requirements(description)

        # Extract dependencies
        dependencies = self._extract_dependencies(description)

        # Build task object
        task = JiraTask(
            key=result['key'],
            summary=fields.get('summary', ''),
            description=description,
            priority=fields.get('priority', {}).get('name', 'Medium'),
            status=fields.get('status', {}).get('name', 'To Do'),
            issue_type=fields.get('issuetype', {}).get('name', 'Task'),
            labels=fields.get('labels', []),
            parent_key=fields.get('parent', {}).get('key') if fields.get('parent') else None,
            parent_summary=fields.get('parent', {}).get('fields', {}).get('summary') if fields.get('parent') else None,
            subtasks=[st['key'] for st in fields.get('subtasks', [])],
            acceptance_criteria=acceptance_criteria,
            attachments=[
                {'filename': att['filename'], 'url': att['content']}
                for att in fields.get('attachment', [])
            ],
            created=fields.get('created'),
            updated=fields.get('updated'),
            assignee=fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
            reporter=fields.get('reporter', {}).get('displayName') if fields.get('reporter') else None,
            technical_requirements=technical_requirements,
            dependencies=dependencies
        )

        logger.info(f"  ✅ Fetched: {task.key} - {task.summary[:50]}...")
        logger.info(f"     Priority: {task.priority}, Status: {task.status}")
        logger.info(f"     Acceptance Criteria: {len(task.acceptance_criteria)}")

        return task

    def _extract_text_from_adf(self, adf: Any) -> str:
        """Extract plain text from Atlassian Document Format"""
        if not adf:
            return ''
        if isinstance(adf, str):
            return adf

        text_parts = []

        def traverse(node):
            if isinstance(node, dict):
                if node.get('text'):
                    text_parts.append(node['text'])
                if node.get('content'):
                    for child in node['content']:
                        traverse(child)
                    # Add newlines for block elements
                    if node.get('type') in ['paragraph', 'heading', 'listItem', 'bulletList', 'orderedList']:
                        text_parts.append('\n')
            elif isinstance(node, list):
                for item in node:
                    traverse(item)

        traverse(adf)
        return ''.join(text_parts).strip()

    def _extract_acceptance_criteria(self, description: str) -> List[str]:
        """Extract acceptance criteria from description"""
        criteria = []

        # Look for acceptance criteria section
        patterns = [
            r'acceptance criteria[:\s]*\n((?:[-*•]\s*.+\n?)+)',
            r'criteria[:\s]*\n((?:[-*•]\s*.+\n?)+)',
            r'requirements?[:\s]*\n((?:[-*•]\s*.+\n?)+)',
            r'must[:\s]*\n((?:[-*•]\s*.+\n?)+)'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                items = re.findall(r'[-*•]\s*(.+)', match)
                criteria.extend([item.strip() for item in items if item.strip()])

        return criteria

    def _extract_technical_requirements(self, description: str) -> List[str]:
        """Extract technical requirements from description"""
        requirements = []

        # Look for technical sections
        patterns = [
            r'technical[:\s]*\n((?:[-*•]\s*.+\n?)+)',
            r'implementation[:\s]*\n((?:[-*•]\s*.+\n?)+)',
            r'architecture[:\s]*\n((?:[-*•]\s*.+\n?)+)'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                items = re.findall(r'[-*•]\s*(.+)', match)
                requirements.extend([item.strip() for item in items if item.strip()])

        return requirements

    def _extract_dependencies(self, description: str) -> List[str]:
        """Extract dependencies from description"""
        dependencies = []

        # Look for dependency mentions
        patterns = [
            r'depends on[:\s]*(.+)',
            r'requires[:\s]*(.+)',
            r'blocked by[:\s]*(.+)',
            r'dependencies?[:\s]*\n((?:[-*•]\s*.+\n?)+)'
        ]

        for pattern in patterns:
            matches = re.findall(pattern, description, re.IGNORECASE)
            for match in matches:
                if '\n' in match:
                    items = re.findall(r'[-*•]\s*(.+)', match)
                    dependencies.extend([item.strip() for item in items])
                else:
                    dependencies.append(match.strip())

        return dependencies

    async def task_to_requirement(self, task_key: str) -> str:
        """
        Convert a JIRA task to a requirement string for TeamExecutionEngineV2.

        Args:
            task_key: JIRA task key

        Returns:
            Formatted requirement string
        """
        task = await self.fetch_task(task_key)
        if not task:
            raise ValueError(f"Task {task_key} not found")

        # Build structured requirement
        requirement = f"""# JIRA Task: {task.key}
**Priority**: {task.priority}
**Type**: {task.issue_type}
**Status**: {task.status}

## Summary
{task.summary}

## Description
{task.description}
"""

        if task.parent_key:
            requirement += f"""
## Epic Context
**Epic**: {task.parent_key} - {task.parent_summary}
"""

        if task.acceptance_criteria:
            requirement += """
## Acceptance Criteria
"""
            for criterion in task.acceptance_criteria:
                requirement += f"- [ ] {criterion}\n"

        if task.technical_requirements:
            requirement += """
## Technical Requirements
"""
            for req in task.technical_requirements:
                requirement += f"- {req}\n"

        if task.dependencies:
            requirement += """
## Dependencies
"""
            for dep in task.dependencies:
                requirement += f"- {dep}\n"

        if task.labels:
            requirement += f"""
## Labels
{', '.join(task.labels)}
"""

        requirement += f"""
## Metadata
- Created: {task.created}
- Updated: {task.updated}
- Assignee: {task.assignee or 'Unassigned'}
- Reporter: {task.reporter or 'Unknown'}
"""

        return requirement

    async def update_task_status(self, task_key: str, status: str) -> bool:
        """
        Update JIRA task status.

        Args:
            task_key: JIRA task key
            status: Target status name (e.g., "In Progress", "Done")

        Returns:
            True if successful
        """
        # Get available transitions
        transitions_result = self._jira_request(f'/rest/api/3/issue/{task_key}/transitions')
        transitions = transitions_result.get('transitions', [])

        # Find matching transition
        status_map = {
            'inProgress': ['In Progress', 'Start Progress', 'Start'],
            'done': ['Done', 'Complete', 'Resolve', 'Close'],
            'toDo': ['To Do', 'Backlog', 'Open', 'Reopen']
        }

        target_names = status_map.get(status, [status])
        transition = None

        for t in transitions:
            if any(name.lower() in t['name'].lower() for name in target_names):
                transition = t
                break

        if not transition:
            logger.warning(f"No transition found for {task_key} to {status}")
            return False

        # Execute transition
        result = self._jira_request(
            f'/rest/api/3/issue/{task_key}/transitions',
            method='POST',
            body={'transition': {'id': transition['id']}}
        )

        logger.info(f"Transitioned {task_key} to {transition['name']}")
        return True

    async def add_comment(self, task_key: str, comment: str) -> bool:
        """
        Add a comment to a JIRA task.

        Args:
            task_key: JIRA task key
            comment: Comment text

        Returns:
            True if successful
        """
        result = self._jira_request(
            f'/rest/api/3/issue/{task_key}/comment',
            method='POST',
            body={
                'body': {
                    'type': 'doc',
                    'version': 1,
                    'content': [{
                        'type': 'paragraph',
                        'content': [{'type': 'text', 'text': comment}]
                    }]
                }
            }
        )

        return 'id' in result

    async def add_execution_result_comment(
        self,
        task_key: str,
        result: Dict[str, Any],
        branch: Optional[str] = None,
        pr_url: Optional[str] = None
    ) -> bool:
        """
        Add a detailed execution result comment to JIRA task.

        Args:
            task_key: JIRA task key
            result: Execution result from TeamExecutionEngineV2
            branch: Git branch name
            pr_url: Pull request URL

        Returns:
            True if successful
        """
        # Build comment based on result
        if result.get('success', False):
            icon = "✅"
            status = "SUCCESS"
        else:
            icon = "❌"
            status = "FAILED"

        comment = f"""{icon} **Automated Execution {status}**

**Execution Summary**
- Duration: {result.get('execution', {}).get('total_duration', 0):.1f}s
- Quality Score: {result.get('quality', {}).get('overall_quality_score', 0):.0%}
- Time Savings: {result.get('execution', {}).get('time_savings_percent', 0):.0%}
- Parallelization: {result.get('execution', {}).get('parallelization_achieved', 0):.0%}

**Classification**
- Type: {result.get('classification', {}).get('type', 'Unknown')}
- Complexity: {result.get('classification', {}).get('complexity', 'Unknown')}
- Confidence: {result.get('classification', {}).get('confidence', 0):.0%}

**Blueprint**
- Pattern: {result.get('blueprint', {}).get('name', 'Unknown')}
- Match Score: {result.get('blueprint', {}).get('match_score', 0):.0%}

**Team**
- Size: {result.get('team', {}).get('size', 0)} personas
- Members: {', '.join(result.get('team', {}).get('personas', []))}

**Contracts**
- Total: {result.get('quality', {}).get('contracts_total', 0)}
- Fulfilled: {result.get('quality', {}).get('contracts_fulfilled', 0)}
"""

        if branch:
            comment += f"\n**Branch**: `{branch}`"

        if pr_url:
            comment += f"\n**Pull Request**: {pr_url}"

        comment += "\n\n---\n🤖 *Generated by TeamExecutionEngineV2*"

        return await self.add_comment(task_key, comment)

    async def fetch_epic_tasks(self, epic_key: str) -> List[JiraTask]:
        """
        Fetch all tasks under an epic.

        Args:
            epic_key: JIRA epic key

        Returns:
            List of JiraTask objects
        """
        result = self._jira_request(
            '/rest/api/3/search/jql',
            method='POST',
            body={
                'jql': f'project = {self.config.project_key} AND parent = {epic_key} ORDER BY priority DESC, created ASC',
                'maxResults': 100,
                'fields': ['key', 'summary', 'description', 'priority', 'status', 'labels', 'issuetype', 'parent']
            }
        )

        tasks = []
        for issue in result.get('issues', []):
            task = await self.fetch_task(issue['key'])
            if task:
                tasks.append(task)

        return tasks


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def execute_jira_task(task_key: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute a JIRA task using TeamExecutionEngineV2.

    This is a convenience function that combines JiraTaskAdapter and TeamExecutionEngineV2.

    Args:
        task_key: JIRA task key (e.g., "MD-131")
        output_dir: Output directory for generated files

    Returns:
        Execution result dictionary
    """
    # Import here to avoid circular imports
    from team_execution_v2 import TeamExecutionEngineV2

    # Create adapter and engine
    adapter = JiraTaskAdapter()
    engine = TeamExecutionEngineV2(output_dir=output_dir)

    # Convert task to requirement
    requirement = await adapter.task_to_requirement(task_key)

    # Update task status to In Progress
    await adapter.update_task_status(task_key, 'inProgress')

    # Execute
    result = await engine.execute(
        requirement=requirement,
        constraints={
            'jira_task_key': task_key,
            'prefer_parallel': True,
            'quality_threshold': 0.85
        }
    )

    # Post result to JIRA
    await adapter.add_execution_result_comment(task_key, result)

    # Update status based on result
    if result.get('success', False):
        await adapter.update_task_status(task_key, 'done')

    return result


# =============================================================================
# CLI
# =============================================================================

async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="JIRA Task Adapter - Execute JIRA tasks with AI-driven teams"
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Fetch command
    fetch_parser = subparsers.add_parser('fetch', help='Fetch task details')
    fetch_parser.add_argument('task_key', help='JIRA task key (e.g., MD-131)')

    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert task to requirement')
    convert_parser.add_argument('task_key', help='JIRA task key')

    # Execute command
    execute_parser = subparsers.add_parser('execute', help='Execute task with team')
    execute_parser.add_argument('task_key', help='JIRA task key')
    execute_parser.add_argument('--output', help='Output directory')

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    adapter = JiraTaskAdapter()

    if args.command == 'fetch':
        task = await adapter.fetch_task(args.task_key)
        if task:
            print(json.dumps({
                'key': task.key,
                'summary': task.summary,
                'priority': task.priority,
                'status': task.status,
                'acceptance_criteria': task.acceptance_criteria,
                'technical_requirements': task.technical_requirements,
                'dependencies': task.dependencies
            }, indent=2))

    elif args.command == 'convert':
        requirement = await adapter.task_to_requirement(args.task_key)
        print(requirement)

    elif args.command == 'execute':
        result = await execute_jira_task(args.task_key, args.output)
        print(json.dumps(result, indent=2, default=str))

    else:
        parser.print_help()


if __name__ == '__main__':
    asyncio.run(main())
