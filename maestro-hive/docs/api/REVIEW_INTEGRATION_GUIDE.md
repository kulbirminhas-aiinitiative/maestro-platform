# Project Review Integration Guide

## Overview

This guide shows how to integrate the **Hybrid Project Review System** into your SDLC workflows.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              HYBRID REVIEW SYSTEM                   │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────┐         ┌──────────────────┐  │
│  │  Analytical     │         │  AI Agent        │  │
│  │  Tools (Python) │────────▶│  (Reviewer)      │  │
│  │                 │         │                  │  │
│  │  • File counts  │  Data   │  • Interprets    │  │
│  │  • Coverage     │────────▶│  • Identifies    │  │
│  │  • Completeness │         │    gaps          │  │
│  │  • Metrics      │         │  • Recommends    │  │
│  └─────────────────┘         └──────────────────┘  │
│          │                            │             │
│          └────────────┬───────────────┘             │
│                       │                             │
│              ┌────────▼────────┐                    │
│              │  Review Reports │                    │
│              │  • Maturity     │                    │
│              │  • Gaps         │                    │
│              │  • Remediation  │                    │
│              └─────────────────┘                    │
└─────────────────────────────────────────────────────┘
```

## Components

### 1. Analytical Tools (`review_tools.py`)
**Purpose:** Fast, deterministic data collection
**Provides:**
- File counts and structure analysis
- Implementation completeness checks
- Test coverage metrics
- DevOps configuration analysis
- Documentation quality metrics

**Runs in:** Milliseconds
**Output:** Structured JSON data

### 2. Project Reviewer Persona (`project_reviewer_persona.py`)
**Purpose:** AI agent definition with expertise and responsibilities
**Provides:**
- Persona configuration
- Review dimensions and weights
- Maturity level definitions
- System prompt for AI behavior

### 3. Review Engine (`project_review_engine.py`)
**Purpose:** Orchestrator that combines tools + AI agent
**Workflow:**
1. Tools gather quantitative metrics
2. Engine samples key implementation files
3. AI agent interprets metrics + code samples
4. AI agent compares to requirements
5. AI agent generates gap analysis
6. AI agent creates remediation plan
7. Engine saves comprehensive reports

## Usage

### Standalone Review

```bash
# Run review on any project
python project_review_engine.py \
    --project ./sunday_com \
    --requirements requirements_document.md \
    --output-dir ./reviews
```

### Integrated with SDLC Engine

Add to end of your SDLC workflow:

```python
from project_review_engine import ProjectReviewEngine

async def run_sdlc_with_review(requirement: str, output_dir: Path):
    # 1. Run normal SDLC workflow
    engine = EnhancedSDLCEngineV4()
    await engine.run_complete_sdlc(requirement, output_dir)

    # 2. Auto-review the generated project
    reviewer = ProjectReviewEngine()
    review_results = await reviewer.review_project(
        project_path=output_dir,
        requirement_doc="requirements_document.md"
    )

    # 3. Save review results to ML platform
    await ml_client.store_review_results(
        project_id=project_id,
        completion=review_results['completion_percentage'],
        gaps=review_results['analysis']
    )

    print(f"✓ Project created and reviewed!")
    print(f"  Completion: {review_results['completion_percentage']}%")
    print(f"  Review reports: {review_results['reports']}")
```

### Programmatic API

```python
from project_review_engine import ProjectReviewEngine

async def review_project():
    engine = ProjectReviewEngine(api_key="your-key")

    results = await engine.review_project(
        project_path="./my_project",
        requirement_doc="requirements.md"
    )

    # Access results
    completion = results['completion_percentage']
    maturity = results['metrics']['maturity_level']
    gaps = results['analysis']['ai_assessment']

    # Reports are auto-saved to my_project/reviews/
    print(f"Completion: {completion}%")
    print(f"Maturity: {maturity}")
```

### As CI/CD Step

Add to `.github/workflows/review.yml`:

```yaml
name: Project Review

on:
  push:
    branches: [ main ]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Project Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          python project_review_engine.py \
            --project . \
            --requirements requirements_document.md \
            --output-dir ./reviews

      - name: Upload Review Reports
        uses: actions/upload-artifact@v3
        with:
          name: review-reports
          path: reviews/

      - name: Comment on PR
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const metrics = JSON.parse(
              fs.readFileSync('./reviews/LATEST_METRICS.json', 'utf8')
            );

            const comment = `## 📊 Project Review Results

            **Completion:** ${metrics.metrics.completion_percentage}%
            **Maturity Level:** ${metrics.metrics.maturity_level}

            See detailed reports in artifacts.`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

## Output Files

After review, you'll get:

```
reviews/
├── PROJECT_MATURITY_REPORT_20250104_143022.md
├── GAP_ANALYSIS_20250104_143022.md
├── REMEDIATION_PLAN_20250104_143022.md
├── METRICS_20250104_143022.json
├── LATEST_MATURITY.md          # Symlink to latest
├── LATEST_GAP.md
├── LATEST_REMEDIATION.md
└── LATEST_METRICS.json
```

### Sample Maturity Report

```markdown
# Project Maturity Report

**Project:** sunday_com
**Overall Completion:** 18.5%
**Maturity Level:** Concept/Planning

## Executive Summary
This project is in early planning/documentation phase with minimal
implementation. Excellent documentation foundation but requires
significant development work.

## Component Status
| Component      | Status          | Notes                    |
|----------------|-----------------|--------------------------|
| Documentation  | 🟢 Excellent    | 29,332 lines, comprehensive |
| Implementation | 🔴 Needs Work   | 2 endpoints, stubs only  |
| Testing        | 🔴 Minimal      | 6 test files             |
| DevOps         | 🟢 Excellent    | Full K8s/Terraform setup |

## AI Agent Assessment
[Detailed analysis from AI agent...]

## Gap Analysis
- ✗ Workspace management (not implemented)
- ✗ Board CRUD operations (not implemented)
- ✗ Task/item management (not implemented)
- ✗ Real-time collaboration (not implemented)
...
```

### Sample Gap Analysis

```markdown
# Gap Analysis Report

## Critical Gaps (Blockers)
1. **No workspace CRUD operations**
   - Location: backend/src/routes/workspace.routes.ts (commented out)
   - Impact: Core feature non-functional
   - Effort: 2-3 days

2. **Board management not implemented**
   - Location: backend/src/routes/board.routes.ts (missing)
   - Impact: Primary user workflow blocked
   - Effort: 5-7 days
...
```

### Sample Remediation Plan

```markdown
# Remediation Plan - Next Iteration

## Phase 1: Core Features (2-3 weeks)
**Goal:** Get to 40% completion - Early Development stage

### Priority 1: Workspace Management
- [ ] Implement workspace CRUD endpoints
- [ ] Add workspace service layer
- [ ] Create workspace UI pages
- [ ] Write workspace tests (target: 85% coverage)
- **Estimated effort:** 1 week
- **Blockers:** None
- **Dependencies:** Database schema already exists

### Priority 2: Board Management
- [ ] Implement board CRUD endpoints
- [ ] Add board-workspace associations
- [ ] Create board UI (list and detail views)
- [ ] Implement basic board views (Table only for MVP)
- **Estimated effort:** 1.5 weeks
- **Blockers:** Requires workspace completion
...
```

## Iterative Review Workflow

### Recommended Process

```
1. Initial SDLC Run
   ↓
2. Auto-Review (this system)
   ↓
3. Review Reports Generated
   ↓
4. Team Reviews Gaps & Priorities
   ↓
5. Implement Top Priorities
   ↓
6. Re-run Review (measure progress)
   ↓
7. Compare metrics (improvement tracking)
   ↓
8. Repeat until Production Ready
```

### Tracking Progress Across Iterations

```python
# Track completion over time
reviews = []

# Iteration 1
review_1 = await engine.review_project(project_path)
reviews.append({
    'iteration': 1,
    'date': datetime.now(),
    'completion': review_1['completion_percentage']
})

# ... implement priorities from remediation plan ...

# Iteration 2
review_2 = await engine.review_project(project_path)
reviews.append({
    'iteration': 2,
    'date': datetime.now(),
    'completion': review_2['completion_percentage']
})

# Calculate progress
progress = review_2['completion_percentage'] - review_1['completion_percentage']
print(f"Progress: +{progress}% in iteration 2")
```

## Customization

### Adjust Completion Weights

Edit `review_tools.py`:

```python
weights = {
    'documentation': 0.10,    # Reduce from 0.15
    'implementation': 0.50,   # Increase from 0.40
    'testing': 0.20,          # Keep same
    'devops': 0.10,           # Reduce from 0.15
    'security': 0.10          # Keep same
}
```

### Add Custom Metrics

```python
# In review_tools.py
class CustomMetricsAnalyzer:
    @staticmethod
    def analyze(project_path: Path) -> CustomMetrics:
        # Your custom analysis
        return CustomMetrics(...)

# In ProjectReviewTools.gather_all_metrics():
metrics["custom"] = CustomMetricsAnalyzer.analyze(project_path)
```

### Modify AI Behavior

Edit persona in `project_reviewer_persona.py`:

```python
"system_prompt": """You are a [YOUR CUSTOM ROLE].

Focus on:
1. [Your priority 1]
2. [Your priority 2]
...

Be especially critical about: [YOUR FOCUS AREAS]
"""
```

## Integration with Maestro ML Platform

Store review results for ML-powered recommendations:

```python
# After review
await ml_client.store_project_review(
    project_id=project_id,
    completion_percentage=results['completion_percentage'],
    maturity_level=results['metrics']['maturity_level'],
    gap_analysis=results['analysis'],
    metrics=results['metrics']
)

# Later: Find similar projects with similar gaps
similar = await ml_client.find_projects_with_similar_gaps(
    current_gaps=current_project_gaps,
    threshold=0.7
)

# Reuse solutions from similar projects that were completed
```

## Benefits of Hybrid Approach

### ✅ What You Get

1. **Speed:** Tools gather metrics in seconds
2. **Accuracy:** AI interprets nuances ("coming soon" vs real code)
3. **Consistency:** Same metrics calculated every time
4. **Intelligence:** AI provides context-aware recommendations
5. **Actionability:** Specific priorities for next iteration
6. **Tracking:** JSON metrics for progress over time
7. **Automation:** Can run in CI/CD without human intervention

### 🎯 Use Cases

- **Post-SDLC Review:** Auto-review after generation
- **Sprint Planning:** Use gaps to plan next sprint
- **Progress Tracking:** Run weekly to measure progress
- **Quality Gates:** Block merges if completion < threshold
- **Documentation:** Auto-generate status reports
- **Stakeholder Updates:** Share maturity reports with business

## Example: End-to-End Integration

```python
#!/usr/bin/env python3.11
"""
Complete SDLC with Automated Review
"""

async def sdlc_with_iterative_review(requirement: str):
    """Run SDLC with automatic review and gap-filling iterations"""

    # Phase 1: Initial Generation
    print("Phase 1: Initial SDLC Generation")
    engine = EnhancedSDLCEngineV4()
    output_dir = await engine.run_complete_sdlc(requirement)

    # Phase 2: Initial Review
    print("Phase 2: Initial Review")
    reviewer = ProjectReviewEngine()
    review_1 = await reviewer.review_project(output_dir)

    print(f"Initial Completion: {review_1['completion_percentage']}%")

    # Phase 3: Iterative Improvements
    iteration = 2
    max_iterations = 5
    target_completion = 80.0

    while (review_1['completion_percentage'] < target_completion and
           iteration <= max_iterations):

        print(f"\nPhase {iteration + 1}: Gap-Filling Iteration {iteration}")

        # Extract top 3 priorities from remediation plan
        priorities = extract_priorities(review_1['analysis'])

        # Run focused SDLC for each priority
        for priority in priorities[:3]:
            await engine.execute_focused_task(
                output_dir=output_dir,
                task=priority
            )

        # Re-review
        review_n = await reviewer.review_project(output_dir)
        progress = review_n['completion_percentage'] - review_1['completion_percentage']

        print(f"Iteration {iteration} Completion: {review_n['completion_percentage']}%")
        print(f"Progress: +{progress}%")

        review_1 = review_n
        iteration += 1

    print(f"\n✓ Final Completion: {review_1['completion_percentage']}%")
    print(f"  Maturity: {review_1['metrics']['maturity_level']}")
    print(f"  Iterations: {iteration - 1}")

    return output_dir, review_1

# Run it
asyncio.run(sdlc_with_iterative_review(
    "Build a project management platform like Monday.com"
))
```

## Troubleshooting

### Issue: Low completion percentage despite good implementation

**Cause:** Weights may not match your project type
**Solution:** Adjust weights in `review_tools.py`

### Issue: AI agent not providing specific recommendations

**Cause:** Not enough code samples
**Solution:** Increase sample size in `_sample_implementation()`

### Issue: Review takes too long

**Cause:** Too many files being analyzed
**Solution:** Add more directories to ignore list in tools

## Summary

**When to use:**
- ✅ After SDLC generation
- ✅ End of each sprint
- ✅ Before major releases
- ✅ For stakeholder reports
- ✅ To plan next iteration

**What you get:**
- 📊 Quantitative metrics
- 🧠 Qualitative insights
- 📝 Gap analysis
- 🎯 Remediation plan
- 📈 Progress tracking

**Hybrid advantage:**
- Tools = Fast + Accurate
- AI = Smart + Contextual
- Combined = Comprehensive + Actionable
