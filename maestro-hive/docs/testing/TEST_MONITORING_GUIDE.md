# Dog Marketplace DAG Test - Monitoring Guide

## Test Status

**Test ID:** dog-marketplace-20251011
**Start Time:** 2025-10-11 11:46:36
**Expected Duration:** 30-60 minutes
**Current Status:** 🟢 RUNNING IN BACKGROUND
**PID:** Check with `ps aux | grep test_dog_marketplace`

---

## Quick Monitoring Commands

```bash
# Check if test is still running
ps aux | grep "[t]est_dog_marketplace.py"

# Monitor progress
./monitor_test.sh

# Watch live logs
tail -f dog_marketplace_test.log

# Check latest progress (last 20 lines)
tail -20 dog_marketplace_test.log

# Full log output
cat dog_marketplace_test.log
```

---

## Phase Progress

The test executes 5 SDLC phases:

1. **Requirements** ⏳ (In Progress)
   - Requirement Analyst
   - Backend Developer (for requirements)
   - Frontend Developer (for requirements)
   - QA Engineer (for requirements)

2. **Design** ⏸️ (Pending)
   - System Architecture
   - API Design
   - Database Schema
   - UI/UX Design

3. **Implementation** ⏸️ (Pending - Will Run in Parallel)
   - Backend Development
   - Frontend Development
   - (These should run concurrently in DAG_PARALLEL mode)

4. **Testing** ⏸️ (Pending)
   - Unit Tests
   - Integration Tests
   - E2E Tests
   - Performance Testing

5. **Deployment** ⏸️ (Pending)
   - Docker Configuration
   - CI/CD Setup
   - Deployment Scripts

---

## What to Expect

### During Execution

Each persona execution takes **5-15 minutes** depending on Claude Code performance:
- 4 personas per phase minimum
- 5 phases total
- Expected total time: **30-60 minutes**

You'll see log entries like:
```
🎭 Executing Persona: Requirements Analyst
🤖 Executing with AI...
✅ Persona execution completed
```

### Completion Indicators

The test is complete when you see:
```
================================================================================
  STEP 4: REPORT GENERATION
================================================================================
✅ Generated report: ./DOG_MARKETPLACE_TEST_REPORT.md
✅ Generated issues log: ./issues_identified.md
✅ Generated JSON data: ./dog_marketplace_test_data.json

================================================================================
  TEST COMPLETE
================================================================================
```

---

## Generated Files (When Complete)

After successful completion, you'll find:

### Reports
- **`DOG_MARKETPLACE_TEST_REPORT.md`** - Comprehensive test report
- **`issues_identified.md`** - All issues found during execution
- **`dog_marketplace_test_data.json`** - Machine-readable test data

### Logs
- **`dog_marketplace_test.log`** - Detailed execution log
- **`test_output.log`** - Standard output/error

### Artifacts
- **`generated_dog_marketplace/`** - All generated project files
  - Requirements documents
  - Design specifications
  - Backend code
  - Frontend code
  - Tests
  - Deployment configs

### Checkpoints
- **`checkpoints_dog_marketplace/`** - State checkpoints for each phase

---

## Monitoring the Test

### Option 1: Use the Monitor Script

```bash
./monitor_test.sh
```

This shows:
- Running status
- Phase progress
- Latest log entries
- Generated files

### Option 2: Watch Logs in Real-Time

```bash
# Watch all logs
tail -f dog_marketplace_test.log

# Watch only phase transitions
tail -f dog_marketplace_test.log | grep -E "PHASE|Phase completed|✅|❌"

# Watch errors and warnings
tail -f dog_marketplace_test.log | grep -E "ERROR|WARNING|❌|⚠️"
```

### Option 3: Check Phase Progress

```bash
# Count completed phases
grep -c "Phase completed successfully" dog_marketplace_test.log

# List completed phases
grep "PHASE.*:" dog_marketplace_test.log | grep -v "Pending"

# Current activity
tail -5 dog_marketplace_test.log
```

---

## If Something Goes Wrong

### Test Hangs or Freezes

```bash
# Check if process is alive
ps aux | grep "[t]est_dog_marketplace.py"

# Check CPU/memory usage
top -p $(pgrep -f test_dog_marketplace)

# If truly hung (no CPU activity for >5 min), restart:
pkill -f test_dog_marketplace.py
python3 test_dog_marketplace.py &
```

### Test Fails

```bash
# Check the error
tail -50 dog_marketplace_test.log | grep -A5 "ERROR\|Exception"

# Review the last phase that ran
grep "PHASE" dog_marketplace_test.log | tail -1

# Check if partial report was generated
ls -lh *REPORT.md *issues*.md
```

### Out of Memory

```bash
# Check memory usage
free -h

# Check process memory
ps aux --sort=-%mem | head -10

# If needed, reduce parallel workers (edit test script):
# Change: os.environ['MAESTRO_ENABLE_PARALLEL_EXECUTION'] = 'false'
```

---

## After Test Completes

### 1. Check Overall Status

```bash
# View the main report
cat DOG_MARKETPLACE_TEST_REPORT.md

# Or open in your editor/browser
code DOG_MARKETPLACE_TEST_REPORT.md
```

### 2. Review Issues

```bash
# Check issues identified
cat issues_identified.md

# Count issues by severity
grep -E "CRITICAL|ERROR|WARNING" issues_identified.md
```

### 3. Inspect Generated Project

```bash
# List all generated files
find generated_dog_marketplace -type f

# Check key artifacts
ls -lh generated_dog_marketplace/requirements/
ls -lh generated_dog_marketplace/design/
ls -lh generated_dog_marketplace/src/
```

### 4. Verify Parallel Execution

```bash
# Check if backend/frontend ran in parallel
grep -A10 "Implementation phase" dog_marketplace_test.log | grep -E "Backend|Frontend"

# Look for parallel execution indicators
grep "parallel" dog_marketplace_test.log -i
```

### 5. Analyze Performance

```bash
# View phase durations
grep "Duration:" dog_marketplace_test.log

# Total execution time
grep "Total Duration\|Test STATUS" DOG_MARKETPLACE_TEST_REPORT.md
```

---

## Expected Results

### Success Criteria

✅ All 5 phases complete
✅ Quality scores above 70%
✅ Backend & Frontend phases run in parallel (Implementation)
✅ All artifacts generated
✅ No critical errors

### Deliverables

**Requirements Phase:**
- User stories
- Acceptance criteria
- Requirements document

**Design Phase:**
- System architecture diagram
- API specifications (OpenAPI/Swagger)
- Database schema (ERD)
- UI wireframes/mockups

**Implementation Phase:**
- Backend code (Node.js/Express, PostgreSQL)
- Frontend code (React)
- Integration points
- Configuration files

**Testing Phase:**
- Unit tests
- Integration tests
- E2E tests
- Test reports

**Deployment Phase:**
- Dockerfile
- Docker Compose configuration
- CI/CD pipelines (GitHub Actions)
- Deployment documentation

---

## Troubleshooting

### Common Issues

**Issue:** "Module not found" errors
```bash
# Solution: Ensure all dependencies installed
pip install -r requirements.txt
# OR
poetry install
```

**Issue:** Claude Code CLI not responding
```bash
# Solution: Check Claude Code availability
claude --version

# Ensure API key is set
echo $ANTHROPIC_API_KEY
```

**Issue:** Test taking too long (>2 hours)
```bash
# This might indicate an issue. Check:
# 1. If process is still active (CPU usage)
# 2. Last log entry timestamp
# 3. If Claude Code CLI is waiting for input

# Consider restarting with debug mode
```

---

## Manual Review Checklist

After the test completes, manually review:

- [ ] All 5 phases completed
- [ ] Quality scores meet threshold (≥70%)
- [ ] Artifacts generated for each phase
- [ ] No critical errors in logs
- [ ] Implementation phase shows parallel execution
- [ ] Generated code follows best practices
- [ ] Tests are comprehensive
- [ ] Deployment config is production-ready
- [ ] Documentation is complete

---

## Next Steps

1. **Review the main report:** `DOG_MARKETPLACE_TEST_REPORT.md`
2. **Check for issues:** `issues_identified.md`
3. **Inspect generated code:** `generated_dog_marketplace/`
4. **Validate artifacts:** Ensure all expected files are present
5. **Test the application:** Run the generated code
6. **Deploy if ready:** Use the deployment configurations

---

**Last Updated:** 2025-10-11
**Estimated Completion:** ~12:15 - 12:45 (30-60 min from 11:46)
