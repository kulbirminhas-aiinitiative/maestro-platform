# Maestro ML Platform

**Self-aware ML development platform with meta-learning capabilities**

Maestro ML is a platform that learns from past ML projects to optimize team composition, artifact reuse, and development velocity. It treats reusable ML components as a "music library" and correlates their usage with project success metrics.

## 🎯 Core Concept

Traditional ML platforms focus on *individual* model tracking. Maestro ML focuses on the *development process itself*:

- **Music Library Analogy**: Just as Spotify learns which songs lead to user engagement, Maestro learns which feature pipelines, model templates, and schemas lead to successful ML projects.
- **Team Composition Optimization**: Learns whether 1-person or 10-person teams deliver better outcomes for different problem classes.
- **Meta-Learning**: Builds a meta-model that predicts project success based on team size, complexity, and artifact reuse patterns.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Maestro ML Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Artifact   │  │   Metrics    │  │Meta-Learning │      │
│  │   Registry   │  │  Collector   │  │    Engine    │      │
│  │  (Library)   │  │              │  │  (Phase 3)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │               FastAPI REST API                      │     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │    Redis     │  │   MinIO/S3   │      │
│  │  (Metadata)  │  │   (Cache)    │  │  (Artifacts) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    MLflow    │  │     DVC      │  │    Feast     │      │
│  │ (Experiments)│  │  (Versions)  │  │  (Features)  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Database Schema

### Core Models

**Projects** - ML project tracking
- Team composition (size, roles)
- Problem classification
- Success metrics (model performance, cost, business impact)

**Artifacts** - Reusable ML components ("Music Library")
- Types: feature_pipeline, model_template, schema, notebook
- Impact scores: average contribution to project success
- Usage analytics

**ArtifactUsage** - Usage tracking
- Which artifacts were used in which projects
- Individual impact scores per usage
- Context metadata

**ProcessMetrics** - Development metrics
- Git velocity (commits, PRs, contributors)
- CI/CD performance (pipeline times, success rates)
- MLflow experiments (training times, hyperparameter search)

**Predictions** - Meta-model predictions
- Predicted success score
- Predicted duration and cost
- Confidence intervals

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Poetry 1.7+
- PostgreSQL 14+
- Redis 7+
- MinIO or AWS S3 (optional, for artifact storage)

### Installation

1. **Clone the repository**
```bash
cd examples/sdlc_team/maestro_ml
```

2. **Install Poetry** (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. **Install dependencies**
```bash
poetry install
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. **Initialize database**
```bash
# Start PostgreSQL
docker run -d --name maestro-postgres \
  -e POSTGRES_USER=maestro \
  -e POSTGRES_PASSWORD=maestro \
  -e POSTGRES_DB=maestro_ml \
  -p 5432:5432 \
  postgres:14

# Start Redis
docker run -d --name maestro-redis \
  -p 6379:6379 \
  redis:7
```

5. **Run migrations**
```bash
# Database tables are auto-created on first startup
python -m maestro_ml.api.main
```

### Running the API

**Development mode (with auto-reload):**
```bash
poetry run uvicorn maestro_ml.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**
```bash
poetry run uvicorn maestro_ml.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Docker (Full Stack):**
```bash
docker-compose up -d
```

**Docker (Build only):**
```bash
docker-compose build
```

### Verify Installation

```bash
curl http://localhost:8000/
# Expected: {"app": "Maestro ML Platform", "version": "0.1.0", "status": "running"}
```

## 📖 API Usage

### 1. Create a Project

```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{
    "name": "fraud-detection-v2",
    "problem_class": "classification",
    "complexity_score": 7,
    "team_size": 2,
    "metadata": {
      "description": "Credit card fraud detection model",
      "dataset_size_gb": 50
    }
  }'
```

### 2. Register an Artifact

```bash
curl -X POST http://localhost:8000/api/v1/artifacts \
  -H "Content-Type: application/json" \
  -d '{
    "name": "feature-pipeline-transactions",
    "type": "feature_pipeline",
    "version": "1.0.0",
    "created_by": "data-team",
    "tags": ["transactions", "fraud", "preprocessing"],
    "storage_path": "s3://maestro-artifacts/pipelines/transactions-v1.py",
    "metadata": {
      "description": "Transaction feature engineering pipeline",
      "input_schema": "raw_transactions",
      "output_schema": "features_v1"
    }
  }'
```

### 3. Search Artifacts

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "fraud",
    "type": "feature_pipeline",
    "tags": ["transactions"],
    "min_impact_score": 70.0
  }'
```

### 4. Log Artifact Usage

```bash
curl -X POST http://localhost:8000/api/v1/artifacts/{artifact_id}/use \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-uuid-here"
  }'
```

### 5. Collect Metrics

```bash
# Save a metric
curl -X POST http://localhost:8000/api/v1/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-uuid-here",
    "metric_type": "commits_per_week",
    "metric_value": 15.0,
    "metadata": {"repo": "github.com/org/fraud-detection"}
  }'

# Get project metrics summary
curl http://localhost:8000/api/v1/metrics/{project_id}/summary

# Calculate development velocity
curl http://localhost:8000/api/v1/metrics/{project_id}/velocity
```

### 6. Get Recommendations (Phase 3 - Placeholder)

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "problem_class": "classification",
    "complexity_score": 7,
    "team_size": 2
  }'
```

## 🎯 Development Phases

### Phase 1: Foundational MLOps (Months 1-6) ✅ COMPLETE
- ✅ Database schema
- ✅ Artifact registry service
- ✅ Metrics collection framework
- ✅ REST API
- ⏳ Infrastructure (Docker, Kubernetes, Terraform)
- ⏳ CI/CD pipelines

### Phase 2: Music Library (Months 7-12)
- ⏳ Artifact impact scoring
- ⏳ Usage analytics
- ⏳ Search and recommendation UI
- ⏳ Integration with Git, CI/CD, MLflow

### Phase 3: Meta-Learning Optimization Engine (Months 13-18)
- ⏳ Meta-model training pipeline
- ⏳ Team composition recommendations
- ⏳ Success prediction
- ⏳ A/B testing framework

## 🗂️ Project Structure

```
maestro_ml/
├── api/
│   ├── __init__.py
│   └── main.py              # FastAPI application
├── config/
│   ├── __init__.py
│   └── settings.py          # Environment configuration
├── core/
│   ├── __init__.py
│   └── database.py          # Database connection
├── models/
│   ├── __init__.py
│   └── database.py          # SQLAlchemy models
├── services/
│   ├── __init__.py
│   ├── artifact_registry.py # Artifact management
│   └── metrics_collector.py # Metrics collection
├── requirements.txt
├── .env.example
└── README.md
```

## 🔬 Example Workflow

1. **Start a new ML project**
   - Create project in Maestro ML
   - Search artifact library for relevant components
   - Log which artifacts you're using

2. **During development**
   - Maestro collects Git metrics (commit frequency, collaboration)
   - CI/CD metrics are tracked (pipeline times, success rates)
   - MLflow experiments are monitored

3. **After deployment**
   - Update project with success metrics (model performance, business impact)
   - Maestro calculates impact scores for artifacts used
   - Meta-model learns patterns for future recommendations

4. **Next project**
   - Maestro recommends optimal team size
   - Suggests high-impact artifacts to reuse
   - Predicts expected outcomes (success score, duration, cost)

## 🤝 Integration Points

### MLflow
- Experiment tracking
- Model registry
- Artifact storage

### DVC
- Data versioning
- Pipeline versioning
- Reproducibility

### Feast
- Feature store
- Feature serving
- Feature discovery

### Git
- Commit history analysis
- Collaboration metrics
- Code churn tracking

### CI/CD (GitHub Actions, Jenkins)
- Pipeline duration
- Success rates
- Resource usage

## 📊 Metrics Tracked

**Development Process:**
- Commits per week
- Average PR merge time
- Unique contributors
- Code churn rate

**CI/CD:**
- Pipeline duration
- Success rate
- CPU/GPU hours consumed

**ML Experiments:**
- Total experiments run
- Best model performance
- Average training time
- Hyperparameter iterations

**Artifact Usage:**
- Reuse count
- Reuse rate (%)
- Impact scores

**Success Metrics:**
- Model performance (accuracy, F1, etc.)
- Business impact (revenue, cost savings)
- Time to deployment
- Total compute cost

## 🛠️ Configuration

All configuration is managed via environment variables. See `.env.example` for the full list.

**Key configurations:**
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `S3_BUCKET`: Object storage bucket for artifacts
- `MLFLOW_TRACKING_URI`: MLflow server URL
- `META_MODEL_RETRAIN_DAYS`: How often to retrain the meta-model

## 🧪 Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=maestro_ml --cov-report=html

# Run specific test file
poetry run pytest tests/test_api.py -v
```

## 📈 Monitoring

**Prometheus Metrics:**
- API request rates
- Database query performance
- Artifact search latency
- Metrics collection success

**Grafana Dashboards:**
- Project success overview
- Artifact impact leaderboard
- Development velocity trends
- Meta-model prediction accuracy

## 🤔 FAQ

**Q: How is this different from MLflow?**
A: MLflow tracks *individual experiments*. Maestro tracks the *development process* and learns which patterns lead to successful projects.

**Q: What's the "music library" concept?**
A: Just as Spotify learns which songs lead to engagement, Maestro learns which ML artifacts (feature pipelines, model templates) lead to project success.

**Q: Can I use this for 1-person teams?**
A: Yes! Maestro optimizes for both small (1-person) and large (10+ person) teams by learning which approach works best for different problem types.

**Q: When will Phase 3 (meta-learning) be ready?**
A: The meta-learning engine is planned for months 13-18. Phases 1-2 provide immediate value through artifact reuse and metrics tracking.

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

Built on the foundation of the AI-Orchestrated Team Management System, extending its team optimization concepts to ML development workflows.

## 📞 Support

For questions or issues, please open a GitHub issue or contact the Maestro ML team.

---

**Status**: Phase 1 Backend Complete (85%)
**Next Steps**: Infrastructure setup (Docker, Kubernetes, Terraform)
