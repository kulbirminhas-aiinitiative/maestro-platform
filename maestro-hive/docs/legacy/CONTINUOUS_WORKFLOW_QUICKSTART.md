# Continuous Intelligent Template Workflow - Quick Start

## ✅ System Status: FULLY OPERATIONAL

The automated template workflow system is **running continuously every 5 minutes** with full intelligence capabilities until 80% coverage is achieved.

---

## 🎯 Current Goal

- **Target Coverage**: 80% across all templates
- **Current Coverage**: 32%
- **Remaining**: 48 percentage points
- **Run Interval**: Every 5 minutes (300 seconds)

---

## 📊 What Happens Every 5 Minutes

1. **Run Test Suite** - Executes 12 real-world scenarios
2. **Analyze Gaps** - Identifies missing/low-coverage templates
3. **Intelligent Decisions**:
   - **REUSE** (≥80% similarity): Parameterize existing template
   - **VARIANT** (50-79% similarity): Fork and modify existing template
   - **CREATE_NEW** (<50% similarity): Create fundamentally new template
4. **Save Recommendations** - JSON files with full intelligence metadata
5. **Track Metrics** - Coverage progress, intelligence decisions, trends

---

## 🧠 Intelligence Features

### Similarity Analysis
- TF-IDF text analysis (50% weight)
- Structural matching (30% weight) - language, framework, category
- Semantic patterns (20% weight)
- **614 unique terms** analyzed across **65 templates**

### Decision Thresholds (Industry Best Practice)
```
REUSE:      >= 80% similarity → Use existing template
VARIANT:    50-79% similarity → Fork and modify
CREATE_NEW: < 50% similarity  → Build from scratch
```

### Quality Gates (5-stage validation)
- Syntax validation (25%)
- Best practices (20%)
- Completeness (25%)
- Security scan (20%)
- SDLC integration (10%)
- **Passing score**: 70/100

---

## 📈 Monitoring Commands

### Check Progress
```bash
bash /home/ec2-user/projects/maestro-platform/maestro-hive/monitor_coverage_progress.sh
```

### Watch Live Logs
```bash
sudo journalctl -u automated_workflow -f
```

### Check Service Status
```bash
sudo systemctl status automated_workflow
```

### View Latest Recommendations
```bash
ls -t /tmp/maestro_workflow_recommendations/*.json | head -1 | xargs cat | python3 -m json.tool | less
```

### View Latest Metrics
```bash
ls -t /tmp/maestro_workflow_metrics/*.json | head -1 | xargs cat | python3 -m json.tool
```

---

## 🔄 After Reaching 80% Coverage

Once you achieve 80% coverage and are satisfied, slow down the interval:

### Switch to 2-hour interval
```bash
sudo sed -i 's/--interval 300/--interval 7200/g' /etc/systemd/system/automated_workflow.service
sudo systemctl daemon-reload
sudo systemctl restart automated_workflow
```

### Switch to daily runs
```bash
sudo sed -i 's/--interval 300/--interval 86400/g' /etc/systemd/system/automated_workflow.service
sudo systemctl daemon-reload
sudo systemctl restart automated_workflow
```

### Switch to weekly runs
```bash
sudo sed -i 's/--interval 300/--interval 604800/g' /etc/systemd/system/automated_workflow.service
sudo systemctl daemon-reload
sudo systemctl restart automated_workflow
```

---

## 📁 Output Files

### Recommendations
**Location**: `/tmp/maestro_workflow_recommendations/`

Each file contains:
- Gap analysis results
- Intelligent recommendations (REUSE/VARIANT/CREATE_NEW)
- Similarity scores
- Base template information (if applicable)
- Research keywords
- Confidence scores

### Metrics
**Location**: `/tmp/maestro_workflow_metrics/`

Each file tracks:
- Coverage percentage
- Gap counts (critical, high, medium)
- Intelligence decisions (reuse, variant, new)
- Similarity checks performed
- Average similarity scores
- Execution time

---

## 🛠️ Service Management

### Start/Stop/Restart
```bash
sudo systemctl start automated_workflow
sudo systemctl stop automated_workflow
sudo systemctl restart automated_workflow
```

### Enable/Disable Auto-Start
```bash
sudo systemctl enable automated_workflow   # Start on boot
sudo systemctl disable automated_workflow  # Don't start on boot
```

### View Recent Logs
```bash
sudo journalctl -u automated_workflow -n 50 --no-pager
```

---

## ✅ Verification Checklist

- [x] Service installed and enabled
- [x] Running continuously every 5 minutes
- [x] Intelligence layer activated (65 templates loaded)
- [x] Similarity analysis functional
- [x] Variant decision engine working
- [x] Quality gates implemented
- [x] Metrics tracking operational
- [x] Auto-restart on failure configured
- [x] Monitoring tools available

---

## 🎯 Success Criteria

The system will continue running every 5 minutes until:
1. **Overall coverage >= 80%**
2. **Critical gaps = 0** (no personas with zero templates)
3. **All key scenarios covered** (at least 70% coverage each)

Once achieved, you can switch to less frequent monitoring (2-hour, daily, or weekly).

---

## 🔍 Troubleshooting

### Check if service is running
```bash
sudo systemctl is-active automated_workflow
```

### Check for errors
```bash
sudo journalctl -u automated_workflow -p err --no-pager
```

### Restart service if needed
```bash
sudo systemctl restart automated_workflow
sudo systemctl status automated_workflow
```

### View full service configuration
```bash
cat /etc/systemd/system/automated_workflow.service
```

---

## 📞 Key Information

- **Service Name**: `automated_workflow.service`
- **Working Directory**: `/home/ec2-user/projects/maestro-platform/maestro-hive`
- **Main Script**: `automated_template_workflow.py`
- **Intelligence Module**: `template_intelligence.py`
- **Current Mode**: Safe (recommendations only, no auto-creation)
- **Run Interval**: 300 seconds (5 minutes)
- **Auto-Restart**: Enabled (60 second delay)

---

**Last Updated**: 2025-10-10
**System Version**: 1.0.0 with Intelligence Layer
**Status**: ✅ Fully Operational - Running Continuously
