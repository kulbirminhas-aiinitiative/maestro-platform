"""
Adapter Implementations Package

Contains concrete implementations of ITaskAdapter and IDocumentAdapter:
- JiraAdapter: JIRA via internal API
- ConfluenceAdapter: Atlassian Confluence
"""

from .jira_adapter import JiraAdapter
from .confluence_adapter import ConfluenceAdapter

__all__ = [
    'JiraAdapter',
    'ConfluenceAdapter'
]
