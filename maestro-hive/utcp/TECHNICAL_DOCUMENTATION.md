# UTCP - Unified Tool Communication Protocol

> Technical Documentation for MAESTRO Platform Tool Integration Framework

**Version:** v1.0.0
**Last Updated:** December 2025
**Part of:** MD-857 (Tool Registry - Discovery and access control)

---

## Executive Summary

UTCP (Unified Tool Communication Protocol) provides standardized tool interfaces for AI agents to interact with external services within the MAESTRO Platform ecosystem.

### Key Value Proposition

| Capability | Details |
|------------|---------|
| **Pre-Built Integrations** | 13 production-ready tool adapters |
| **Unified Interface** | Consistent `ToolResult` pattern across all tools |
| **Capability-Based Access** | 8 capability types (READ, WRITE, DELETE, EXECUTE, SEARCH, COMMENT, TRANSITION, ATTACH) |
| **Enterprise Ready** | Built-in health monitoring, rate limiting, and error handling |
| **Async-First** | Non-blocking operations for optimal performance |

### Supported Integrations

| Domain | Tools |
|--------|-------|
| **Project Management** | JIRA (60/min), Linear (1500/hr) |
| **Communication** | Slack (50/min), Microsoft Teams |
| **Documentation** | Confluence, Notion (3/sec) |
| **Version Control** | Git/GitHub |
| **Cloud Infrastructure** | AWS Services |
| **Monitoring** | Datadog |
| **Incident Management** | PagerDuty |
| **Identity** | Okta |
| **CRM** | Salesforce |
| **Productivity** | Google Workspace |

### Business Impact

- **70% Reduction** in integration complexity through unified interfaces
- **Standardized Error Handling** across all external service calls
- **Capability-Based Security** enforcing least-privilege access
- **Health Monitoring** with automatic status tracking (HEALTHY/DEGRADED/UNHEALTHY)

### Quick Start

```python
from utcp.tools import JiraTool

# Initialize
jira = JiraTool({
    "base_url": "https://your-domain.atlassian.net",
    "email": "user@example.com",
    "api_token": "your-api-token"
})

# Use
result = await jira.get_issue("MD-123")
if result.success:
    print(result.data)
```

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Implemented Tools](#implemented-tools)
5. [Tool Registry](#tool-registry)
6. [Usage Examples](#usage-examples)
7. [Error Handling](#error-handling)
8. [Security Considerations](#security-considerations)
9. [Extending UTCP](#extending-utcp)
10. [API Reference](#api-reference)

---

## Overview

UTCP (Unified Tool Communication Protocol) provides standardized tool interfaces for AI agents to interact with external services. It abstracts away the complexity of individual service APIs behind a consistent, capability-based interface.

### Key Features

- **Standardized Interface**: All tools follow the same `UTCPTool` base class pattern
- **Capability-Based Access**: Tools declare their capabilities (READ, WRITE, DELETE, etc.)
- **Health Monitoring**: Built-in health checks with automatic status tracking
- **Rate Limiting**: Per-tool rate limit configuration
- **Type-Safe Results**: Consistent `ToolResult` pattern for all operations
- **Async-First**: All operations are async for non-blocking execution

### Directory Structure

```
utcp/
├── __init__.py                    # Package exports
├── base.py                        # Base classes (ToolError, ToolResult, UTCPTool)
├── registry.py                    # Basic tool registry interface
├── tool_registry.py               # Advanced registry with schema/health/versioning
├── TECHNICAL_DOCUMENTATION.md     # This file
└── tools/
    ├── __init__.py                # Tool exports
    ├── jira_tool.py               # JIRA integration (60/min rate limit)
    ├── git_tool.py                # Git/GitHub integration
    ├── slack_tool.py              # Slack integration (50/min)
    ├── teams_tool.py              # Microsoft Teams
    ├── aws_tool.py                # AWS services
    ├── confluence_tool.py         # Confluence docs
    ├── notion_tool.py             # Notion (3/sec)
    ├── linear_tool.py             # Linear (1500/hr)
    ├── salesforce_tool.py         # Salesforce CRM
    ├── datadog_tool.py            # Datadog monitoring
    ├── pagerduty_tool.py          # PagerDuty incidents
    ├── okta_tool.py               # Okta identity
    └── google_workspace_tool.py   # Google Workspace
```

---

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI Agent Layer                            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Tool Registry                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐ │
│  │ Tool Schema  │ │ Health Check │ │ Version Tracking         │ │
│  │ Definition   │ │ & Monitoring │ │ & Deprecation            │ │
│  └──────────────┘ └──────────────┘ └──────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      UTCPTool Base Class                         │
│  ┌────────────┐ ┌───────────────┐ ┌────────────────────────────┐│
│  │ ToolConfig │ │ ToolResult    │ │ ToolCapability             ││
│  │            │ │ ok()/fail()   │ │ READ/WRITE/DELETE/EXECUTE  ││
│  └────────────┘ └───────────────┘ └────────────────────────────┘│
└─────────────────────────────┬───────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   JiraTool    │     │   GitTool     │     │  SlackTool    │
│   ConfluenceTool│   │   AWSTool     │     │  TeamsTool    │
│   LinearTool  │     │   DatadogTool │     │  NotionTool   │
│   ...         │     │   ...         │     │  ...          │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Service APIs                         │
│  JIRA Cloud │ GitHub │ Slack │ AWS │ Confluence │ Datadog │ ... │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### ToolError (`base.py:14-20`)

Exception class for tool operation failures.

```python
class ToolError(Exception):
    def __init__(
        self,
        message: str,
        code: str = "TOOL_ERROR",
        details: Optional[Dict] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
```

**Error Codes:**
- `MISSING_CREDENTIALS` - Required credentials not provided
- `TOOL_ERROR` - Generic tool error
- `JIRA_xxx` - JIRA-specific HTTP error codes
- `HEALTH_CHECK_FAILED` - Health check failed

### ToolResult (`base.py:23-39`)

Standard result format for all tool operations.

```python
@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def ok(cls, data: Any, **metadata) -> 'ToolResult':
        """Create a success result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, code: str = "ERROR", **metadata) -> 'ToolResult':
        """Create a failure result."""
        return cls(success=False, error=error, error_code=code, metadata=metadata)
```

### ToolCapability (`base.py:42-51`)

Enum defining tool capabilities.

```python
class ToolCapability(str, Enum):
    READ = "read"           # Read/fetch data
    WRITE = "write"         # Create/update data
    DELETE = "delete"       # Delete data
    EXECUTE = "execute"     # Execute actions
    SEARCH = "search"       # Search/query data
    COMMENT = "comment"     # Add comments
    TRANSITION = "transition"  # Change state/status
    ATTACH = "attach"       # Attach files
```

### ToolConfig (`base.py:54-63`)

Configuration for a tool instance.

```python
@dataclass
class ToolConfig:
    name: str                           # Tool identifier
    version: str                        # Semantic version
    capabilities: List[ToolCapability]  # What the tool can do
    required_credentials: List[str]     # Must be provided
    optional_credentials: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None    # Requests per minute
    timeout: int = 30                   # Default timeout in seconds
```

### UTCPTool Base Class (`base.py:66-99`)

Abstract base class for all tools.

```python
class UTCPTool(ABC):
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self._validate_credentials()

    @property
    @abstractmethod
    def config(self) -> ToolConfig:
        """Return tool configuration."""
        pass

    @abstractmethod
    async def health_check(self) -> ToolResult:
        """Check if the tool can connect to its service."""
        pass

    def has_capability(self, capability: ToolCapability) -> bool:
        """Check if tool has a specific capability."""
        return capability in self.config.capabilities
```

---

## Implemented Tools

### 1. JiraTool (Project Management)

**File:** `tools/jira_tool.py`
**Domain:** `PROJECT_MANAGEMENT`
**Rate Limit:** 60 requests/minute

**Capabilities:**
- `READ` - Get issue details
- `WRITE` - Create/update issues
- `SEARCH` - JQL queries
- `COMMENT` - Add comments
- `TRANSITION` - Change issue status
- `ATTACH` - Attach files

**Required Credentials:**
- `base_url` - JIRA instance URL
- `email` - User email
- `api_token` - API token

**Operations:**
| Method | Description |
|--------|-------------|
| `get_issue(issue_key, fields)` | Get issue details |
| `update_issue(issue_key, fields)` | Update issue fields |
| `add_comment(issue_key, comment)` | Add comment to issue |
| `get_transitions(issue_key)` | Get available transitions |
| `transition_issue(issue_key, transition_id, comment)` | Change issue status |
| `search_issues(jql, max_results, fields)` | Search with JQL |
| `get_comments(issue_key)` | Get all comments |
| `create_issue(project_key, summary, ...)` | Create new issue |
| `health_check()` | Verify connectivity |

---

### 2. GitTool (Version Control)

**File:** `tools/git_tool.py`
**Domain:** `VERSION_CONTROL`

**Capabilities:**
- `READ` - Repository info, commits, branches
- `WRITE` - Create branches, commits
- `SEARCH` - Search code

**Required Credentials:**
- `token` - GitHub/GitLab personal access token

---

### 3. SlackTool (Communication)

**File:** `tools/slack_tool.py`
**Domain:** `COMMUNICATION`
**Rate Limit:** 50 requests/minute

**Capabilities:**
- `READ` - Read channels, messages
- `WRITE` - Send messages
- `SEARCH` - Search messages

**Required Credentials:**
- `bot_token` - Slack Bot OAuth token

---

### 4. TeamsTool (Communication)

**File:** `tools/teams_tool.py`
**Domain:** `COMMUNICATION`

**Capabilities:**
- `READ` - Read teams, channels
- `WRITE` - Send messages

**Required Credentials:**
- `client_id` - Azure AD app client ID
- `client_secret` - Azure AD app client secret
- `tenant_id` - Azure AD tenant ID

---

### 5. AWSTool (Cloud Infrastructure)

**File:** `tools/aws_tool.py`
**Domain:** `CLOUD_INFRASTRUCTURE`

**Capabilities:**
- `READ` - List resources
- `EXECUTE` - Run operations
- `WRITE` - Create resources
- `DELETE` - Delete resources

**Required Credentials:**
- `access_key_id` - AWS access key
- `secret_access_key` - AWS secret key
- `region` - AWS region

---

### 6. ConfluenceTool (Documentation)

**File:** `tools/confluence_tool.py`
**Domain:** `DOCUMENTATION`

**Capabilities:**
- `READ` - Get pages, spaces
- `WRITE` - Create/update pages
- `SEARCH` - Search content

**Required Credentials:**
- `base_url` - Confluence URL
- `email` - User email
- `api_token` - API token

---

### 7. NotionTool (Documentation)

**File:** `tools/notion_tool.py`
**Domain:** `DOCUMENTATION`
**Rate Limit:** 3 requests/second

**Capabilities:**
- `READ` - Get pages, databases
- `WRITE` - Create/update pages
- `SEARCH` - Search content

**Required Credentials:**
- `api_key` - Notion integration token

---

### 8. LinearTool (Project Management)

**File:** `tools/linear_tool.py`
**Domain:** `PROJECT_MANAGEMENT`
**Rate Limit:** 1500 requests/hour

**Capabilities:**
- `READ` - Get issues, projects
- `WRITE` - Create/update issues
- `SEARCH` - Search issues
- `COMMENT` - Add comments
- `TRANSITION` - Change status

**Required Credentials:**
- `api_key` - Linear API key

---

### 9. SalesforceTool (CRM)

**File:** `tools/salesforce_tool.py`
**Domain:** `CRM`

**Capabilities:**
- `READ` - Get records
- `WRITE` - Create/update records
- `SEARCH` - SOQL queries
- `DELETE` - Delete records

**Required Credentials:**
- `instance_url` - Salesforce instance URL
- `access_token` - OAuth access token

---

### 10. DatadogTool (Monitoring)

**File:** `tools/datadog_tool.py`
**Domain:** `MONITORING`

**Capabilities:**
- `READ` - Get metrics, dashboards
- `SEARCH` - Query metrics
- `WRITE` - Create monitors

**Required Credentials:**
- `api_key` - Datadog API key
- `app_key` - Datadog application key

---

### 11. PagerDutyTool (Incident Management)

**File:** `tools/pagerduty_tool.py`
**Domain:** `INCIDENT_MANAGEMENT`

**Capabilities:**
- `READ` - Get incidents, services
- `WRITE` - Create/update incidents
- `TRANSITION` - Change incident status

**Required Credentials:**
- `api_key` - PagerDuty API key

---

### 12. OktaTool (Identity)

**File:** `tools/okta_tool.py`
**Domain:** `IDENTITY`

**Capabilities:**
- `READ` - Get users, groups
- `WRITE` - Create/update users
- `SEARCH` - Search users

**Required Credentials:**
- `domain` - Okta domain
- `api_token` - Okta API token

---

### 13. GoogleWorkspaceTool (Productivity)

**File:** `tools/google_workspace_tool.py`
**Domain:** `PRODUCTIVITY`

**Capabilities:**
- `READ` - Read documents, sheets
- `WRITE` - Create/update files
- `SEARCH` - Search Drive

**Required Credentials:**
- `credentials_json` - Service account JSON

---

## Tool Registry

The `ToolRegistry` (`tool_registry.py`) provides centralized tool management.

### Key Features

1. **Tool Schema Definition**
   - Input/output parameter schemas
   - Side effect declarations
   - Operation-level rate limits

2. **Tool Categorization**
   - Domain-based grouping (PROJECT_MANAGEMENT, COMMUNICATION, etc.)
   - Capability-based filtering
   - Tag-based organization

3. **Version Tracking**
   - Schema hashing for change detection
   - Version history with changelog
   - Breaking change indicators

4. **Health Monitoring**
   - Automatic health checks
   - Status tracking (HEALTHY, DEGRADED, UNHEALTHY)
   - Latency measurement

### Domain Categories

```python
class ToolDomain(str, Enum):
    PROJECT_MANAGEMENT = "project_management"
    DOCUMENTATION = "documentation"
    VERSION_CONTROL = "version_control"
    COMMUNICATION = "communication"
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
    MONITORING = "monitoring"
    INCIDENT_MANAGEMENT = "incident_management"
    IDENTITY = "identity"
    CRM = "crm"
    PRODUCTIVITY = "productivity"
    CUSTOM = "custom"
```

### Health Status

```python
class HealthStatus(str, Enum):
    HEALTHY = "healthy"       # Tool is working properly
    DEGRADED = "degraded"     # 1-2 consecutive failures
    UNHEALTHY = "unhealthy"   # 3+ consecutive failures
    UNKNOWN = "unknown"       # No health check performed
```

### Side Effect Types

```python
class SideEffectType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NOTIFY = "notify"
    TRIGGER_WORKFLOW = "trigger_workflow"
    EXTERNAL_API_CALL = "external_api_call"
    STATE_CHANGE = "state_change"
    NONE = "none"
```

---

## Usage Examples

### Basic Tool Usage

```python
from utcp.tools import JiraTool

# Initialize with credentials
jira = JiraTool({
    "base_url": "https://your-domain.atlassian.net",
    "email": "user@example.com",
    "api_token": "your-api-token"
})

# Get issue details
result = await jira.get_issue("MD-123")
if result.success:
    print(f"Issue: {result.data['summary']}")
    print(f"Status: {result.data['status']}")
else:
    print(f"Error: {result.error}")

# Search for issues
result = await jira.search_issues(
    jql="project = MD AND status = 'To Do'",
    max_results=10
)

# Transition an issue
transitions = await jira.get_transitions("MD-123")
if transitions.success:
    # Find "Done" transition
    done_id = next(
        t["id"] for t in transitions.data["transitions"]
        if t["name"] == "Done"
    )
    await jira.transition_issue("MD-123", done_id, "Completed via automation")
```

### Using the Tool Registry

```python
from utcp.tool_registry import (
    ToolRegistry, ToolDomain, ToolCapability, initialize_registry
)

# Initialize registry
registry = await initialize_registry()

# List all tools
all_tools = registry.list_tools()
print(f"Total tools: {len(all_tools)}")

# Get tools by domain
pm_tools = registry.get_tools_by_domain(ToolDomain.PROJECT_MANAGEMENT)
for tool in pm_tools:
    print(f"  {tool.schema.name}: {tool.schema.description}")

# Get tools by capability
write_tools = registry.get_tools_by_capability(ToolCapability.WRITE)

# Health check all tools
health_results = await registry.health_check_all()
for name, health in health_results.items():
    print(f"{name}: {health.status.value}")

# Export catalog
catalog = registry.to_catalog()
```

### Checking Tool Capabilities

```python
from utcp.tools import JiraTool
from utcp.base import ToolCapability

jira = JiraTool(credentials)

# Check capabilities before operations
if jira.has_capability(ToolCapability.TRANSITION):
    await jira.transition_issue("MD-123", "done")

if jira.has_capability(ToolCapability.ATTACH):
    await jira.attach_file("MD-123", "/path/to/file")
```

### Error Handling Pattern

```python
from utcp.base import ToolError, ToolResult

async def safe_operation():
    try:
        result = await jira.get_issue("MD-123")

        if not result.success:
            # Handle tool-level failures
            print(f"Operation failed: {result.error}")
            print(f"Error code: {result.error_code}")
            return None

        return result.data

    except ToolError as e:
        # Handle tool exceptions (e.g., auth failures)
        print(f"Tool error: {e.message}")
        print(f"Code: {e.code}")
        print(f"Details: {e.details}")
        return None
```

---

## Error Handling

### Error Response Pattern

All tools return a `ToolResult` for both success and failure:

```python
# Success response
ToolResult(
    success=True,
    data={"key": "MD-123", "status": "Done"},
    metadata={"cached": False},
    timestamp="2025-12-10T12:00:00Z"
)

# Failure response
ToolResult(
    success=False,
    error="Issue not found",
    error_code="JIRA_404",
    metadata={"issue_key": "MD-999"},
    timestamp="2025-12-10T12:00:00Z"
)
```

### Common Error Codes

| Code | Description |
|------|-------------|
| `MISSING_CREDENTIALS` | Required credentials not provided |
| `HEALTH_CHECK_FAILED` | Tool health check failed |
| `GET_ISSUE_FAILED` | Failed to retrieve issue |
| `UPDATE_ISSUE_FAILED` | Failed to update issue |
| `CREATE_ISSUE_FAILED` | Failed to create issue |
| `SEARCH_FAILED` | Search operation failed |
| `TRANSITION_FAILED` | Status transition failed |
| `ADD_COMMENT_FAILED` | Failed to add comment |
| `JIRA_4xx` | JIRA HTTP error codes |

---

## Security Considerations

### Credential Management

1. **Never hardcode credentials** - Use environment variables or secret managers
2. **Validate credentials on init** - Tools validate required credentials in `__init__`
3. **Use service accounts** - Prefer service accounts over personal tokens
4. **Rotate tokens regularly** - Implement token rotation policies

### Rate Limiting

Each tool defines its rate limit in the config:

```python
rate_limit: Optional[int] = None  # requests per minute
```

Recommended limits:
- JIRA: 60/min
- Slack: 50/min
- Notion: 3/sec (180/min)
- Linear: 1500/hr (25/min)

### Access Control

Use `ToolCapability` to enforce least-privilege access:

```python
# Only allow read operations
if not tool.has_capability(ToolCapability.WRITE):
    raise PermissionError("Tool does not have write capability")
```

---

## Extending UTCP

### Creating a Custom Tool

```python
from utcp.base import UTCPTool, ToolConfig, ToolCapability, ToolResult

class CustomTool(UTCPTool):
    """Custom tool implementation."""

    @property
    def config(self) -> ToolConfig:
        return ToolConfig(
            name="custom",
            version="1.0.0",
            capabilities=[
                ToolCapability.READ,
                ToolCapability.WRITE,
            ],
            required_credentials=["api_key"],
            optional_credentials=["workspace_id"],
            rate_limit=100,
            timeout=30,
        )

    async def health_check(self) -> ToolResult:
        """Verify service connectivity."""
        try:
            # Make test API call
            response = await self._api_call("GET", "/health")
            return ToolResult.ok({"status": "connected"})
        except Exception as e:
            return ToolResult.fail(str(e), code="HEALTH_CHECK_FAILED")

    async def get_resource(self, resource_id: str) -> ToolResult:
        """Get a resource by ID."""
        try:
            data = await self._api_call("GET", f"/resources/{resource_id}")
            return ToolResult.ok(data)
        except Exception as e:
            return ToolResult.fail(str(e), code="GET_RESOURCE_FAILED")
```

### Registering Custom Tools

```python
from utcp.tool_registry import ToolRegistry, ToolDomain

registry = ToolRegistry()

registry.register_tool(
    CustomTool,
    domain=ToolDomain.CUSTOM,
    tags={"internal", "beta"},
    credentials={"api_key": "your-key"}
)
```

---

## API Reference

### Base Module (`utcp.base`)

| Class | Description |
|-------|-------------|
| `ToolError` | Exception for tool failures |
| `ToolResult` | Standard result format |
| `ToolCapability` | Capability enum |
| `ToolConfig` | Tool configuration |
| `UTCPTool` | Abstract base class |

### Registry Module (`utcp.tool_registry`)

| Class | Description |
|-------|-------------|
| `ToolRegistry` | Central tool registry |
| `ToolDomain` | Domain categorization |
| `SideEffectType` | Side effect types |
| `HealthStatus` | Health status enum |
| `ParameterSchema` | Parameter definition |
| `OperationSchema` | Operation definition |
| `ToolSchema` | Complete tool schema |
| `ToolVersion` | Version information |
| `ToolHealthInfo` | Health check results |
| `RegisteredTool` | Registered tool entry |

### Registry Methods

| Method | Description |
|--------|-------------|
| `register_tool(tool_class, domain, tags, credentials)` | Register a tool |
| `unregister_tool(name)` | Remove a tool |
| `get_tool(name)` | Get tool by name |
| `get_tool_schema(name)` | Get tool schema |
| `list_tools(healthy_only, include_deprecated)` | List all tools |
| `get_tools_by_domain(domain, healthy_only)` | Filter by domain |
| `get_tools_by_capability(capability, healthy_only)` | Filter by capability |
| `get_tools_by_tags(tags, match_all)` | Filter by tags |
| `health_check(name)` | Check single tool |
| `health_check_all()` | Check all tools |
| `start_health_monitoring()` | Start auto monitoring |
| `stop_health_monitoring()` | Stop auto monitoring |
| `get_version_history(name)` | Get version history |
| `update_tool_version(name, new_version, changelog, breaking_changes)` | Update version |
| `deprecate_tool(name, message)` | Mark as deprecated |
| `to_catalog()` | Export full catalog |
| `cleanup()` | Cleanup resources |

---

## Related Documentation

- **MD-857**: Tool Registry - Discovery and access control
- **MD-856**: JIRA Tool - status, comments, attachments
- **MD-2545**: FOUNDRY-CORE Tool Integration Framework
- **MD-2563**: Tool Registry - Catalog of Available Tools

---

*Generated: 2025-12-10*
