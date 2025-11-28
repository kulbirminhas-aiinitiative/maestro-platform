# Real Provider Comparison Test Results

**Date**: 2025-10-11T21:05:00.316332

## Test Configurations

### A_FullClaude_REAL

- **Duration**: 0ms
- **Phases**: 4/4
- **Tokens**: 0
- **Success**: ✓

**Provider Usage:**

| Phase | Provider | Duration |
|-------|----------|----------|
| requirements | claude_agent | 0ms |
| architecture | claude_agent | 0ms |
| implementation | claude_agent | 0ms |
| review | claude_agent | 0ms |

**Output Samples:**

*requirements*: [claude_agent_stub] Analyze this requirement and create a detailed requirements document

Context:

...

*architecture*: [claude_agent_stub] Design the system architecture

Context:
[claude_agent_stub] Analyze this requir...

*implementation*: [claude_agent_stub] Create an implementation plan

Context:
[claude_agent_stub] Design the system ar...

*review*: [claude_agent_stub] Review the implementation plan for quality

Context:
[claude_agent_stub] Create ...

### B_Mixed_REAL

- **Duration**: 19958ms
- **Phases**: 4/4
- **Tokens**: 0
- **Success**: ✓

**Provider Usage:**

| Phase | Provider | Duration |
|-------|----------|----------|
| requirements | claude_agent | 0ms |
| architecture | openai | 11494ms |
| implementation | claude_agent | 0ms |
| review | openai | 8464ms |

**Output Samples:**

*requirements*: [claude_agent_stub] Analyze requirement

Context:

Create a RESTful API for a todo/task management s...

*architecture*: Designing a RESTful API for a todo/task management system involves careful consideration of the arch...

*implementation*: [claude_agent_stub] Implementation plan

Context:
Designing a RESTful API for a todo/task management...

*review*: ### Review of the Implementation Plan for a Todo/Task Management System API

The implementation plan...

### C_FullOpenAI_REAL

- **Duration**: 42520ms
- **Phases**: 4/4
- **Tokens**: 0
- **Success**: ✓

**Provider Usage:**

| Phase | Provider | Duration |
|-------|----------|----------|
| requirements | openai | 11444ms |
| architecture | openai | 11530ms |
| implementation | openai | 8736ms |
| review | openai | 10809ms |

**Output Samples:**

*requirements*: Creating a RESTful API for a todo/task management system involves several key components, including ...

*architecture*: ```json
     "date (ISO 8601)",
     "reminder": "date (ISO 8601, optional)",
     "completed": "boo...

*implementation*: API endpoints to mitigate brute force attacks and abuse.
3. **CORS Policy**: Set up a strict CORS po...

*review*: developers can easily understand and utilize the API.
    - Provide clear examples for each endpoint...

## Performance Comparison

- **Fastest**: 0ms
- **Slowest**: 42520ms
- **Average**: 20826ms
- **Token Range**: 0 - 0
