# Enhanced SDLC Engine V3 - Quick Start Guide

**Get started in 5 minutes** ⚡

---

## ⚡ Fastest Start (No ML)

```bash
# Run V3 without Maestro ML (works like V2)
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build a REST API for blog posts" \
    --personas requirement_analyst backend_developer \
    --output ./blog_api \
    --no-ml
```

**Done!** V3 executes like V2 (JSON integration, auto-ordering, validation).

---

## 🎵 Quick Start (With ML - Recommended)

### Step 1: Start Maestro ML (1 minute)

```bash
# Terminal 1: Start Maestro ML API
cd examples/sdlc_team/maestro_ml
uvicorn maestro_ml.api.main:app --reload --port 8000

# Wait for:
# INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Step 2: Run V3 (30 seconds)

```bash
# Terminal 2: Run V3 with ML
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build a blog platform with user authentication" \
    --output ./blog_project \
    --maestro-ml-url http://localhost:8000
```

### Step 3: Watch the Magic ✨

```bash
# Output:
✅ Maestro ML connected - artifact reuse and analytics enabled
📊 Created Maestro ML project: a1b2c3d4-...

🚀 ENHANCED SDLC ENGINE V3 - Maestro ML Integration
📝 Requirement: Build a blog platform with user authentication...
🆔 Session: sdlc_v3_20251004_103000
👥 Personas to execute: 10

[requirement_analyst] 🔍 Searching for reusable artifacts...
[requirement_analyst] 🎵 Found 2 reusable artifacts (impact score >= 70.0)
[requirement_analyst] 🤖 Starting Requirement Analyst...
[requirement_analyst] ✅ Completed: 3 files in 45.2s

[backend_developer] 🔍 Searching for reusable artifacts...
[backend_developer] 🎵 Found 5 reusable artifacts (impact score >= 70.0)
[backend_developer] 🤖 Starting Backend Developer...
...

📊 SDLC EXECUTION COMPLETE (V3 - Maestro ML)
✅ Success: True
📁 Files created: 24
🎵 MAESTRO ML STATS:
   🔍 Artifacts found: 12
   ✅ Artifacts used: 7
   📈 Artifact reuse rate: 58.3%
```

**Done!** Your project is complete with ML optimization.

---

## 🎯 Common Commands

### Full SDLC (All Personas)

```bash
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build complete e-commerce platform" \
    --output ./ecommerce \
    --maestro-ml-url http://localhost:8000
```

### Specific Personas Only

```bash
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build REST API" \
    --personas requirement_analyst solution_architect backend_developer \
    --output ./api \
    --maestro-ml-url http://localhost:8000
```

### Resume Session

```bash
python3.11 enhanced_sdlc_engine_v3.py \
    --resume blog_v1 \
    --auto-complete \
    --maestro-ml-url http://localhost:8000
```

### With Analytics

```bash
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build task management app" \
    --output ./tasks \
    --show-analytics \
    --maestro-ml-url http://localhost:8000
```

---

## 📋 Command Cheat Sheet

| What You Want | Command |
|---------------|---------|
| **Quick test** | `--personas requirement_analyst --no-ml` |
| **Full SDLC** | `--requirement "..." --output ./dir` |
| **With ML** | `+ --maestro-ml-url http://localhost:8000` |
| **See analytics** | `+ --show-analytics` |
| **Resume work** | `--resume session_id --auto-complete` |
| **List personas** | `--list-personas` |

---

## 🛠️ Prerequisites

### Python Environment

```bash
# Check Python version (need 3.11+)
python3.11 --version

# Install dependencies
pip install httpx  # For Maestro ML client
```

### Maestro ML (Optional but Recommended)

```bash
# Already installed if you have the repository
cd examples/sdlc_team/maestro_ml

# Check it works
uvicorn maestro_ml.api.main:app --reload --port 8000

# In another terminal:
curl http://localhost:8000/
# Should return: {"app": "Maestro ML Platform", "status": "running"}
```

---

## 🎓 5-Minute Tutorial

### Tutorial 1: Build a Simple API

```bash
# 1. Start Maestro ML (Terminal 1)
cd examples/sdlc_team/maestro_ml
uvicorn maestro_ml.api.main:app --reload --port 8000

# 2. Run V3 (Terminal 2)
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build REST API for a todo list with CRUD operations" \
    --personas requirement_analyst solution_architect backend_developer \
    --output ./todo_api \
    --problem-class api \
    --complexity 40

# 3. Check output
ls ./todo_api/
# REQUIREMENTS.md  ARCHITECTURE.md  backend/  sdlc_v3_results.json

# 4. View results
cat ./todo_api/sdlc_v3_results.json
# Shows ML stats: artifacts found, artifacts used, etc.
```

**Time**: ~5 minutes
**Result**: Complete API specification + architecture + backend code

---

### Tutorial 2: Build Full Application (15 min)

```bash
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build a simple blog platform with user auth, posts, and comments" \
    --output ./blog_platform \
    --problem-class web_app \
    --complexity 60 \
    --show-analytics

# Wait for completion...
# Then view analytics:
📊 MAESTRO ML ANALYTICS
⚡ Development Velocity: 72.5/100
📊 GIT METRICS: ...
📊 CI/CD METRICS: ...
```

**Time**: ~15 minutes
**Result**: Complete full-stack application + analytics

---

## 🐛 Quick Troubleshooting

### "Maestro ML not available"

```bash
# Option 1: Start Maestro ML
cd examples/sdlc_team/maestro_ml
uvicorn maestro_ml.api.main:app --reload --port 8000

# Option 2: Run without ML
python3.11 enhanced_sdlc_engine_v3.py --no-ml ...
```

### "ModuleNotFoundError: No module named 'httpx'"

```bash
pip install httpx
```

### "Persona 'X' not found"

```bash
# List available personas
python3.11 enhanced_sdlc_engine_v3.py --list-personas
```

### "No artifacts found"

**This is normal for first project!**
- First project: Creates artifacts
- Second+ projects: Reuses artifacts

---

## 📊 Understanding Output

### sdlc_v3_results.json

```json
{
  "success": true,
  "session_id": "sdlc_v3_20251004_103000",
  "personas_executed": 3,
  "file_count": 12,
  "duration_seconds": 95.3,

  // V3 ML features
  "ml_project_id": "a1b2c3d4-...",
  "artifacts_found": 8,      // Artifacts available for reuse
  "artifacts_used": 5,        // Artifacts actually used
  "ml_enabled": true
}
```

### Key Metrics to Watch

| Metric | Good | Fair | Needs Attention |
|--------|------|------|-----------------|
| **Success Rate** | 100% | 80-99% | <80% |
| **Artifact Reuse** | 50%+ | 20-50% | <20% |
| **Velocity Score** | 80+ | 60-80 | <60 |

---

## 🎯 Next Steps

### After First Project

1. **View results**:
   ```bash
   cat ./your_project/sdlc_v3_results.json
   ```

2. **Check artifacts registered**:
   ```bash
   curl http://localhost:8000/api/v1/artifacts/search -X POST \
     -H "Content-Type: application/json" \
     -d '{"min_impact_score": 0}'
   ```

3. **Run second project** - Will reuse artifacts!

### Build Your Artifact Library

```bash
# Run 3-5 diverse projects to build library
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build API" \
    --personas requirement_analyst backend_developer \
    --output ./api1

python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build web app" \
    --personas requirement_analyst frontend_developer \
    --output ./webapp1

python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build ML pipeline" \
    --personas requirement_analyst backend_developer \
    --output ./ml1

# Now you have artifacts! Future projects 30-40% faster!
```

### Enable Analytics

```bash
# Run project with analytics
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "..." \
    --output ./dir \
    --show-analytics

# Or view analytics for existing project
# (Add get_analytics endpoint call)
```

---

## 🎓 Learning Resources

### Essential Reading

1. **V3_MAESTRO_ML_INTEGRATION.md** - Complete V3 guide
2. **VERSION_COMPARISON.md** - V1 vs V2 vs V3
3. **V2_QUICK_REFERENCE.md** - Command reference

### API Documentation

- **Maestro ML API**: `maestro_ml/api/main.py`
- **Artifact Registry**: `maestro_ml/services/artifact_registry.py`
- **Metrics Collector**: `maestro_ml/services/metrics_collector.py`

---

## 💡 Pro Tips

### Tip 1: Start Small

```bash
# First project: Just 1-2 personas to learn
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Simple API" \
    --personas requirement_analyst \
    --output ./test \
    --maestro-ml-url http://localhost:8000
```

### Tip 2: Use Problem Class

```bash
# Helps ML learn patterns
--problem-class api          # For REST APIs
--problem-class web_app      # For web applications
--problem-class ml_pipeline  # For ML/data pipelines
--problem-class general      # Default
```

### Tip 3: Set Complexity

```bash
# Helps ML predict duration/cost (Phase 3)
--complexity 30   # Simple CRUD
--complexity 50   # Moderate (default)
--complexity 70   # Complex business logic
--complexity 90   # Very complex system
```

### Tip 4: Check Status

```bash
# View session file for status
cat ./your_project/.session_v3.json

{
  "version": "3.0",
  "session_id": "sdlc_v3_...",
  "completed_personas": ["requirement_analyst", "backend_developer"],
  "ml_project_id": "a1b2c3d4-..."
}
```

---

## 🚀 Ready to Go!

### Recommended First Command

```bash
# Start here - simple but complete
python3.11 enhanced_sdlc_engine_v3.py \
    --requirement "Build a REST API for managing books with CRUD operations" \
    --personas requirement_analyst solution_architect backend_developer \
    --output ./bookstore_api \
    --problem-class api \
    --complexity 40 \
    --maestro-ml-url http://localhost:8000 \
    --show-analytics
```

**This gives you**:
- Complete API specification
- Architecture design
- Backend implementation
- ML tracking and learning
- Analytics dashboard
- Artifacts for future reuse

**In ~8 minutes!** ⚡

---

## 📞 Getting Help

### Check These First

1. **List personas**: `--list-personas`
2. **Check ML connection**: `curl http://localhost:8000/`
3. **View logs**: In terminal output
4. **Check results**: `cat ./output/.sdlc_v3_results.json`

### Common Questions

**Q: Do I need Maestro ML?**
A: No! Use `--no-ml` to run without it. But ML features are recommended.

**Q: Can I use V3 like V2?**
A: Yes! 100% backward compatible. ML features are optional.

**Q: How long does it take?**
A: 3-5 personas: ~5-8 minutes. Full SDLC (10 personas): ~20-25 minutes.

**Q: Where are files created?**
A: In `--output` directory (default: `./sdlc_v3_output`)

---

**Happy Building!** 🎉

For full documentation, see: **V3_MAESTRO_ML_INTEGRATION.md**

**Version**: 3.0 | **Date**: 2025-10-04
