# Knowledge Sharing & Deliverables Matching Analysis

## How Knowledge Sharing Works on Rerun

### Current Implementation

#### 1. Session Context Building
When a persona runs, it receives context about previously completed work:

**Location:** `session_manager.py` lines 259-279
```python
def get_session_context(self, session: SDLCSession) -> str:
    # Builds context from:
    - Session ID
    - Requirement
    - Completed personas list
    - Files created by each persona (up to 5 per persona)
```

**What Agents See:**
- List of completed personas
- Files created by EACH previous persona (limited to first 5 files)
- If persona created 10 files, only first 5 are mentioned in context

#### 2. File System Access
Agents have FULL access to the file system via Claude Code tools:
- **Read tool**: Can read ANY file in the output directory
- **Bash tool**: Can run commands like `ls`, `find`, `grep`
- **List files**: Can discover all files, not just those in context

**Key Point:** Even though context only shows 5 files per persona, agents can:
1. List all files: `ls -la`
2. Read any file: Read tool
3. Search files: `grep -r "pattern" .`

#### 3. On Rerun Behavior

**Scenario:** requirement_analyst runs again after initial run

**What Happens:**
1. Session already has requirement_analyst in `completed_personas`
2. If `--force-rerun` is used, it runs anyway
3. Agent sees in context:
   ```
   Completed Personas: requirement_analyst, solution_architect, ...
   requirement_analyst created 5 files:
     - requirements_document.md
     - user_stories.md
     - acceptance_criteria.md
     - requirement_backlog.md
     - (... only 5 shown)
   ```
4. Agent can READ all existing files using Read tool
5. Agent creates NEW files (overwrites or creates new ones)
6. Session tracks files via filesystem snapshot:
   - `before_files = set(self.output_dir.rglob("*"))`
   - `after_files = set(self.output_dir.rglob("*"))`
   - `new_files = after_files - before_files`

**File Tracking:**
- Only NEW files (created during this run) are tracked
- If agent modifies existing file, it's NOT tracked as "created"
- If agent creates new file, it IS tracked

**Result:**
- Agents see ALL files in directory (not just latest)
- Session context shows limited file list (5 per persona)
- Agents can discover and read all files independently

## Deliverables Matching Issue

### Question: Do deliverable definitions match between contract and code?

### Answer: YES, they match! ✅

#### Solution Architect Example

**Deliverables defined in `team_organization.py`** (lines 871-876):
```python
"solution_architect": [
    "architecture_document",
    "tech_stack",
    "database_design",
    "api_specifications",
    "system_design"
]
```

**File patterns in `team_execution.py`** (lines 843-848):
```python
deliverable_patterns = {
    "architecture_document": ["*architecture*.md", "ARCHITECTURE.md"],
    "tech_stack": ["*tech_stack*.md", "*technology*.md"],
    "database_design": ["*database*.md", "*schema*.md", "*erd*.md"],
    "api_specifications": ["*api*.md", "*openapi*.yaml", "*swagger*.yaml"],
    "system_design": ["*system_design*.md", "*design*.md"],
}
```

**Match:** ✅ Perfect alignment

#### All Personas Checked:

| Persona | Deliverables Match | File Patterns Match |
|---------|-------------------|---------------------|
| requirement_analyst | ✅ Yes | ✅ Yes |
| solution_architect | ✅ Yes | ✅ Yes |
| security_specialist | ✅ Yes | ✅ Yes |
| backend_developer | ✅ Yes | ✅ Yes |
| frontend_developer | ✅ Yes | ✅ Yes |
| devops_engineer | ✅ Yes | ✅ Yes |
| qa_engineer | ✅ Yes | ✅ Yes |
| technical_writer | ✅ Yes | ✅ Yes |
| deployment_specialist | ✅ Yes | ✅ Yes |
| project_reviewer | ✅ Yes | ✅ Yes |

## Potential Issues

### 1. Session Context Limitation
**Issue:** Only 5 files per persona shown in context
**Impact:** Agents may not know about all deliverables in context
**Mitigation:** Agents can still discover files via Read/Bash tools

### 2. File Modification Not Tracked
**Issue:** If agent edits existing file, it's not tracked as "created"
**Impact:** Session won't show updated files in next persona's context
**Mitigation:** Agents can still read the modified file

### 3. Rerun Creates New Files
**Issue:** On rerun, if agent creates NEW file (different name), both old and new exist
**Impact:** Project may have duplicate/conflicting files
**Example:**
- First run: `requirements_document.md`
- Second run: `REQUIREMENTS.md`
- Result: Both files exist

## Recommendations

### 1. Increase Context File Limit
Change limit from 5 to all files (or higher number):
```python
# session_manager.py line 274
for file_path in files[:5]:  # ← Increase this
```

### 2. Track File Modifications
Add modification tracking to session:
```python
modified_files = [f for f in after_files if f in before_files and f.stat().st_mtime changed]
```

### 3. Add Cleanup on Rerun
Before rerunning persona, optionally clean up their previous files:
```python
if force_rerun:
    # Remove files created by this persona in previous run
    old_files = session.get_files_by_persona(persona_id)
    for f in old_files:
        (output_dir / f).unlink(missing_ok=True)
```

### 4. Better Context Summary
Instead of listing individual files, summarize deliverables:
```python
requirement_analyst completed with:
  ✅ requirements_document (requirements_document.md)
  ✅ user_stories (user_stories.md)  
  ✅ acceptance_criteria (acceptance_criteria.md)
  ⚠️  requirement_backlog (PARTIAL)
```

## Current Behavior Summary

**On Initial Run:**
1. Agent receives context about previous personas
2. Agent reads existing files via Read tool
3. Agent creates deliverables
4. New files tracked in session
5. Next agent receives updated context

**On Rerun (force-rerun):**
1. Agent receives SAME context (previous run info)
2. Agent can read ALL existing files (old + new)
3. Agent may create NEW files or overwrite existing
4. Only NEW files tracked (modifications ignored)
5. Result: May have multiple versions of same deliverable

**Knowledge Flow:**
```
Persona 1 Run 1 → [files A, B, C]
                     ↓
Persona 2 Run 1 ← [can see A, B, C via Read tool]
                     ↓
Persona 1 Run 2 → [can see A, B, C + creates D, E]
                     ↓  
Persona 2 Run 2 ← [can see A, B, C, D, E via Read tool]
```

