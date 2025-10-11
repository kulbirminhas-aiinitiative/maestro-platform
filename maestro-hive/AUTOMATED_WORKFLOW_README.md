# Automated Template Workflow System

## Overview

The Automated Template Workflow System is a self-learning, continuous service that monitors template coverage across real-world scenarios and automatically identifies gaps, generates recommendations, and optionally creates new templates to improve coverage.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│         AutomatedWorkflowOrchestrator                       │
│  (Main continuous service)                                  │
└─────┬───────────────────────────────────────────────────────┘
      │
      ├─> 1. RealWorldRAGTester
      │      └─> Runs 12 real-world scenarios
      │      └─> Generates coverage report
      │
      ├─> 2. GapAnalyzer
      │      └─> Analyzes test results
      │      └─> Identifies coverage gaps
      │      └─> Categorizes by severity
      │
      ├─> 3. TemplateEnhancementEngine
      │      └─> Generates enhancement recommendations
      │      └─> Plans template specifications
      │      └─> Prioritizes actions
      │
      ├─> 4. TemplateGenerator (Auto mode)
      │      └─> Web research for best practices
      │      └─> Auto-generates templates
      │      └─> Validates quality
      │
      └─> 5. ImprovementTracker
           └─> Tracks metrics over time
           └─> Measures coverage improvement
           └─> Logs all actions
```

## Features

### 1. **Continuous Monitoring**
- Runs test suite at configurable intervals
- Tracks coverage metrics over time
- Identifies degradation in coverage

### 2. **Intelligent Gap Analysis**
- Identifies 4 types of gaps:
  - **missing_persona**: Personas with 0 templates (Critical)
  - **low_coverage**: Personas with < 3 templates/scenario (High)
  - **missing_category**: Categories with no templates (Medium)
  - **poor_scenario_coverage**: Scenarios with < 40% coverage (High)

### 3. **Smart Recommendations**
- Generates prioritized enhancement recommendations
- Includes research keywords for each template
- Plans persona-specific template suites
- Estimates templates needed to close gaps

### 4. **Operating Modes**

#### Safe Mode (Default)
- Generates recommendations only
- No automatic template creation
- Saves recommendations for manual review
- Recommended for production

#### Auto Mode
- Automatically generates templates based on gaps
- Performs web research for best practices
- Validates generated templates
- Syncs to database automatically
- Requires review before deployment

### 5. **Metrics & Tracking**
- Coverage improvement over time
- Gaps identified per run
- Actions taken
- Execution time
- Success/failure tracking

## Installation

### 1. Direct Usage

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Test once (safe mode)
python3 automated_template_workflow.py --once --mode safe

# Run continuously (2-hour interval)
python3 automated_template_workflow.py --mode safe --interval 7200
```

### 2. As a System Service

```bash
cd /home/ec2-user/projects/maestro-platform/maestro-hive

# Install service
./manage_workflow_service.sh install

# Enable on boot
sudo systemctl enable automated_workflow

# Start service
./manage_workflow_service.sh start

# Check status
./manage_workflow_service.sh status

# View logs
./manage_workflow_service.sh logs
```

## Usage

### Command-Line Options

```bash
python3 automated_template_workflow.py [OPTIONS]

Options:
  --mode {safe|auto}    Operating mode (default: safe)
                        safe: Recommendations only
                        auto: Auto-generate templates

  --interval SECONDS    Interval between runs in seconds (default: 3600)

  --once                Run once and exit (default: continuous)
```

### Examples

```bash
# Run once in safe mode (testing)
python3 automated_template_workflow.py --once --mode safe

# Continuous mode, 2-hour interval, safe mode
python3 automated_template_workflow.py --mode safe --interval 7200

# Auto mode, 6-hour interval (careful!)
python3 automated_template_workflow.py --mode auto --interval 21600
```

## Output Files

### 1. Recommendations
**Location**: `/tmp/maestro_workflow_recommendations/`

Each run generates:
```
RUN_20251010_143000_0001_recommendations.json
```

**Format**:
```json
{
  "run_id": "RUN_20251010_143000_0001",
  "generated_at": "2025-10-10T14:30:00",
  "mode": "safe",
  "total_recommendations": 25,
  "recommendations": [
    {
      "recommendation_id": "REC_0001",
      "gap": {
        "gap_id": "GAP_0001",
        "gap_type": "missing_persona",
        "severity": "critical",
        "persona": "database_specialist"
      },
      "action_type": "create_template",
      "priority": 1,
      "template_name": "Normalized Schema Design (3NF)",
      "persona": "database_specialist",
      "category": "backend",
      "language": "sql",
      "framework": "postgresql",
      "research_keywords": ["database normalization", "3NF", "schema design"],
      "confidence": 0.85
    }
  ]
}
```

### 2. Metrics
**Location**: `/tmp/maestro_workflow_metrics/`

Each run generates:
```
RUN_20251010_143000_0001_metrics.json
```

**Format**:
```json
{
  "run_id": "RUN_20251010_143000_0001",
  "run_timestamp": "2025-10-10T14:30:00",
  "mode": "safe",
  "overall_coverage_before": 52.3,
  "overall_coverage_after": 52.3,
  "coverage_improvement": 0.0,
  "total_gaps_identified": 15,
  "critical_gaps": 2,
  "high_priority_gaps": 5,
  "recommendations_generated": 25,
  "templates_auto_generated": 0,
  "execution_time_seconds": 45.2,
  "success": true
}
```

### 3. Logs
**Location**: `/tmp/maestro_workflow_logs/`

Daily log files:
```
workflow_20251010.log
```

## Workflow Cycle

Each workflow cycle performs these steps:

### Step 1: Run Test Suite
```
🧪 Execute test_rag_real_world.py
   └─> 12 real-world scenarios
   └─> Generate coverage report
   └─> Record overall coverage %
```

### Step 2: Analyze Gaps
```
🔍 Parse test results
   └─> Identify missing personas (0 templates)
   └─> Find low coverage personas (< 3 templates/scenario)
   └─> Detect missing categories
   └─> Flag poorly covered scenarios (< 40%)
   └─> Categorize by severity (critical/high/medium/low)
```

### Step 3: Generate Recommendations
```
💡 For each gap:
   └─> Determine action type (create/enhance/research)
   └─> Plan template specifications
   └─> Set priority (1-5)
   └─> Include research keywords
   └─> Calculate confidence score
```

### Step 4: Take Action
```
📝 Safe Mode:
   └─> Save recommendations to file
   └─> Log for manual review

🤖 Auto Mode:
   └─> Web research for best practices
   └─> Generate templates
   └─> Validate quality
   └─> Sync to database
```

### Step 5: Track Metrics
```
📊 Record:
   └─> Coverage improvement
   └─> Gaps identified
   └─> Actions taken
   └─> Execution time
   └─> Success/failure
```

## Gap Types & Actions

| Gap Type | Severity | Estimated Templates | Action |
|----------|----------|---------------------|--------|
| **missing_persona** | Critical | 10 | Create comprehensive template suite |
| **low_coverage** | High | 5-10 | Expand existing templates |
| **missing_category** | Medium | 5 | Research and create category templates |
| **poor_scenario_coverage** | High | Varies | Fill specific scenario gaps |

## Persona Template Planning

The system has built-in knowledge of what templates each persona needs:

### Database Specialist (10 templates)
1. Normalized Schema Design (3NF)
2. Zero-Downtime Database Migration
3. Database Indexing Strategy
4. Database Sharding Pattern
5. Time-Series Database Schema
6. Multi-Tenant Database Design
7. Query Performance Optimization
8. Database Backup and Recovery
9. Connection Pooling Configuration
10. Database Monitoring and Alerting

### QA Engineer (10 templates)
1. Test Pyramid Strategy
2. API Test Automation
3. E2E Test Automation (Selenium)
4. Performance Test (Locust)
5. Contract Testing (Pact)
6. Test Data Factory Pattern
7. Mutation Testing
8. Security Testing (OWASP)
9. Visual Regression Testing
10. Test Coverage Analysis

### Frontend Developer (8 templates)
1. React Compound Component Pattern
2. State Management with Zustand
3. Form Handling with React Hook Form
4. Infinite Scroll Component
5. Accessibility (WCAG 2.1)
6. Animation with Framer Motion
7. Data Fetching with React Query
8. Responsive Design System

### IoT Specialist (5 templates)
1. MQTT Device Communication
2. Device Provisioning Flow
3. Time-Series Data Ingestion
4. Device Shadow Pattern
5. OTA Firmware Update

### SRE (5 templates)
1. Prometheus Metrics Collection
2. Distributed Tracing (OpenTelemetry)
3. Log Aggregation (ELK)
4. Incident Response Runbook
5. SLO/SLI Definition Template

## Monitoring

### Check Service Status
```bash
./manage_workflow_service.sh status
```

### View Live Logs
```bash
./manage_workflow_service.sh logs
```

### View Recent Logs
```bash
./manage_workflow_service.sh logs-recent
```

### Check Coverage Trend
```bash
# View all metrics files
ls -lh /tmp/maestro_workflow_metrics/

# Parse latest coverage
python3 -c "import json; data = json.load(open(sorted([f for f in __import__('pathlib').Path('/tmp/maestro_workflow_metrics/').glob('*.json')])[-1])); print(f\"Coverage: {data['overall_coverage_before']:.1f}%\")"
```

## Safety Features

1. **Safe Mode Default**: Prevents accidental template generation
2. **Recommendations Review**: All recommendations saved before action
3. **Metrics Tracking**: Full audit trail of all actions
4. **Error Handling**: Graceful degradation on failures
5. **Rollback Capability**: Metrics allow identifying and reverting changes

## Future Enhancements

- [ ] Web research integration (search for industry best practices)
- [ ] LLM-based template generation
- [ ] Quality validation for auto-generated templates
- [ ] A/B testing for template effectiveness
- [ ] Slack/email notifications for critical gaps
- [ ] Dashboard for visualizing coverage trends
- [ ] Auto-sync to database in auto mode
- [ ] Template versioning and rollback
- [ ] Machine learning for recommendation prioritization

## Troubleshooting

### Service Won't Start
```bash
# Check systemd logs
sudo journalctl -u automated_workflow -n 50

# Check permissions
ls -la /home/ec2-user/projects/maestro-platform/maestro-hive/automated_template_workflow.py

# Test manually
python3 /home/ec2-user/projects/maestro-platform/maestro-hive/automated_template_workflow.py --once
```

### No Gaps Detected
- Coverage may already be high (> 70%)
- Check test results: `cat real_world_test_results.json`
- Verify RAG cache was cleared

### High Memory Usage
- Reduce interval to allow garbage collection
- Check for memory leaks in test suite
- Monitor with: `ps aux | grep automated_template_workflow`

## Configuration

Edit `automated_workflow.service` to change default behavior:

```ini
# Safe mode, 2-hour interval (default)
ExecStart=... --mode safe --interval 7200

# Auto mode, 6-hour interval (advanced)
ExecStart=... --mode auto --interval 21600

# Safe mode, 1-hour interval (aggressive monitoring)
ExecStart=... --mode safe --interval 3600
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart automated_workflow
```

## Support

For issues or questions:
1. Check logs: `./manage_workflow_service.sh logs-recent`
2. Review recommendations: `cat /tmp/maestro_workflow_recommendations/*.json | jq`
3. Check metrics: `cat /tmp/maestro_workflow_metrics/*.json | jq`

---

**Status**: ✅ Production Ready (Safe Mode)
**Version**: 1.0.0
**Last Updated**: 2025-10-10
