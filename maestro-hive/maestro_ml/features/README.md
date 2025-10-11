# Feature Discovery Service

**Status**: ✅ Complete
**Quick Win**: #5
**Effort**: 2 weeks
**Version**: 1.0.0

Automated feature analysis and discovery service for ML model development.

---

## 🎯 Features

- ✅ **Dataset Profiling**: Statistical summaries, data quality metrics
- ✅ **Correlation Analysis**: Pearson, Spearman, Kendall correlations
- ✅ **Feature Importance**: Random Forest, Gradient Boosting, Permutation, Mutual Information
- ✅ **Smart Recommendations**: AI-powered feature suggestions
- ✅ **Insights Generation**: Automatic insight extraction
- ✅ **Multiple Interfaces**: CLI, Python API, REST API

---

## 🚀 Quick Start

### CLI Usage

```bash
# Complete feature discovery
python -m features.cli discover data.csv --target price

# Dataset profiling only
python -m features.cli profile data.csv

# Correlation analysis
python -m features.cli correlate data.csv --target price
```

### Python API

```python
from features.discovery_engine import FeatureDiscoveryEngine
import pandas as pd

# Load data
df = pd.read_csv("data.csv")

# Initialize engine
engine = FeatureDiscoveryEngine()

# Run complete discovery
report = engine.discover(df, target="price")

# View top features
print(f"Top features: {report.importance.top_features}")

# View insights
for insight in report.insights:
    print(f"  {insight}")

# Get recommendations
for rec in report.recommendations[:10]:
    print(f"  {rec.feature}: {rec.reason}")
```

### REST API

```bash
# Upload CSV and discover features
curl -X POST http://localhost:8000/api/v1/features/discover \
  -F "file=@data.csv" \
  -F "target=price" \
  -F "importance_method=random_forest"

# Profile dataset
curl -X POST http://localhost:8000/api/v1/features/profile \
  -F "file=@data.csv"

# Analyze correlations
curl -X POST http://localhost:8000/api/v1/features/correlate \
  -F "file=@data.csv" \
  -F "target=price" \
  -F "method=pearson"
```

---

## 📚 Components

### 1. Dataset Profiler

Analyzes dataset statistics and quality metrics.

```python
from features.analysis import DatasetProfiler

profiler = DatasetProfiler()
profile = profiler.profile(df, dataset_name="my_data")

print(f"Rows: {profile.num_rows}")
print(f"Features: {profile.num_features}")
print(f"Missing: {profile.null_percentage:.2f}%")

# Per-feature stats
for feat in profile.features:
    print(f"{feat.name}: {feat.type.value}")
    if feat.type == "numerical":
        print(f"  Mean: {feat.mean:.2f}, Std: {feat.std:.2f}")
```

### 2. Correlation Analyzer

Calculates feature correlations using various methods.

```python
from features.analysis import CorrelationAnalyzer
from features.models import CorrelationMethod

analyzer = CorrelationAnalyzer(correlation_threshold=0.5)

corr_matrix = analyzer.analyze(
    df,
    target="price",
    method=CorrelationMethod.PEARSON
)

# High correlations
print(f"Found {len(corr_matrix.high_correlations)} high correlations")

# Target correlations
target_corrs = analyzer.get_target_correlations(corr_matrix, "price", top_n=10)
for pair in target_corrs:
    print(f"{pair.feature1} ↔ {pair.feature2}: {pair.correlation:.3f}")
```

### 3. Importance Calculator

Calculates feature importance using ML algorithms.

```python
from features.analysis import ImportanceCalculator
from features.models import ImportanceMethod

calculator = ImportanceCalculator()

X = df.drop("price", axis=1)
y = df["price"]

importance = calculator.calculate(
    X, y,
    method=ImportanceMethod.RANDOM_FOREST,
    is_classification=False
)

# Top features
for imp in importance.importances[:10]:
    print(f"#{imp.rank} {imp.feature}: {imp.importance:.4f}")
```

### 4. Discovery Engine (Orchestrator)

Runs complete analysis and generates recommendations.

```python
from features.discovery_engine import FeatureDiscoveryEngine

engine = FeatureDiscoveryEngine()

# Complete discovery
report = engine.discover(
    df,
    target="price",
    dataset_name="housing",
    run_profiling=True,
    run_correlation=True,
    run_importance=True
)

# Or quick discover with defaults
report = engine.quick_discover(df, target="price")

# Access results
print(f"Profile: {report.profile.num_features} features")
print(f"Correlations: {len(report.correlations.high_correlations)} high")
print(f"Top features: {report.importance.top_features}")
print(f"Recommendations: {len(report.recommendations)}")
print(f"Insights: {len(report.insights)}")
```

---

## 🎨 CLI Commands

### `discover`

Complete feature discovery analysis.

```bash
python -m features.cli discover data.csv \
  --target price \
  --method random_forest \
  --correlation pearson \
  --output report.json
```

**Options**:
- `--target, -t`: Target variable name
- `--method, -m`: Importance method (random_forest, gradient_boosting, mutual_info)
- `--correlation, -c`: Correlation method (pearson, spearman, kendall)
- `--classification/--regression`: Task type
- `--output, -o`: Save report to JSON file

### `profile`

Profile dataset statistics.

```bash
python -m features.cli profile data.csv
```

**Output**: Per-feature statistics, data quality metrics

### `correlate`

Analyze feature correlations.

```bash
python -m features.cli correlate data.csv \
  --target price \
  --method pearson \
  --threshold 0.5
```

**Options**:
- `--target, -t`: Focus on correlations with this feature
- `--method, -m`: Correlation method
- `--threshold`: Correlation threshold for "high" correlations

---

## 📊 Analysis Methods

### Correlation Methods

1. **Pearson** (default): Linear correlations, requires normality
2. **Spearman**: Rank-based, handles non-linear monotonic relationships
3. **Kendall**: Rank-based, robust to outliers

### Importance Methods

1. **Random Forest** (default): Tree-based importance, fast
2. **Gradient Boosting**: Similar to RF but sequential
3. **Permutation**: Model-agnostic, slower but reliable
4. **Mutual Information**: Information theory-based, handles non-linear

---

## 🎯 Use Cases

1. **EDA (Exploratory Data Analysis)**: Quick dataset understanding
2. **Feature Selection**: Identify most important features
3. **Data Quality**: Detect missing values, outliers
4. **Multicollinearity**: Find highly correlated features
5. **Feature Engineering**: Get recommendations for new features

---

## 📈 Example Output

### Insights

```
⚠️ High missing data: 12.3% of values are null
🔗 Found 8 feature pairs with high correlation (>0.5) - consider removing redundant features
⭐ Top 5 features account for 87.2% of importance - consider focusing on these
🗑️ 15 features have very low importance (<0.01) - candidates for removal
💡 Generated 18 feature recommendations based on analysis
```

### Top Features

```
#1  bedrooms                      0.3521
#2  bathrooms                     0.2841
#3  sqft_living                   0.2103
#4  grade                         0.0892
#5  sqft_above                    0.0643
```

### Recommendations

```
• bedrooms                        (score: 0.352)
  High feature importance (rank #1, random_forest)

• sqft_living                     (score: 0.210)
  High feature importance (rank #3, random_forest)

• grade                           (score: 0.089)
  Strong correlation with target (0.667)
```

---

## 🔧 Configuration

### Engine Parameters

```python
engine = FeatureDiscoveryEngine(
    correlation_threshold=0.5,        # Threshold for high correlations
    max_unique_for_categorical=50,    # Max unique values for categorical
    random_state=42                   # Random seed
)
```

### Discovery Options

```python
report = engine.discover(
    df,
    target="price",
    run_profiling=True,               # Run dataset profiling
    run_correlation=True,             # Run correlation analysis
    run_importance=True,              # Calculate feature importance
    correlation_method="pearson",     # Correlation method
    importance_method="random_forest",# Importance method
    is_classification=False,          # Task type
    top_n_features=20                 # Number of top features
)
```

---

## 📖 Data Models

All analyses return Pydantic models:

- `DatasetProfile`: Dataset statistics
- `CorrelationMatrix`: Correlation results
- `ImportanceAnalysis`: Feature importance scores
- `FeatureDiscoveryReport`: Complete report with recommendations

Serialize to JSON:
```python
json_str = report.model_dump_json(indent=2)
```

---

## 🏗️ Architecture

```
Feature Discovery Service
    ↓
┌───┴────────┬────────────┬─────────────┐
↓            ↓            ↓             ↓
Profiler  Correlations  Importance  Recommender
    ↓            ↓            ↓             ↓
Statistics  Pearson/     Random Forest   Smart
Quality    Spearman/     Gradient Boost  Feature
Metrics    Kendall       Permutation     Suggestions
                         Mutual Info
```

---

## 🚀 Integration

### With REST API

Feature discovery endpoints are automatically available:

- `POST /api/v1/features/discover`
- `POST /api/v1/features/profile`
- `POST /api/v1/features/correlate`
- `POST /api/v1/features/importance`

### With Model Registry

```python
# Future: Auto-analyze datasets before training
from maestro_ml import MaestroClient

client = MaestroClient()
dataset = client.datasets.get("housing")

# Discover features
report = client.features.discover(dataset, target="price")

# Use top features for training
features_to_use = report.importance.top_features[:10]
```

---

## 🐛 Troubleshooting

### Issue: "No numerical features found"

**Solution**: Dataset only has categorical features. Use encoding:

```python
df_encoded = pd.get_dummies(df, drop_first=True)
```

### Issue: "Target not found in DataFrame"

**Solution**: Check target column name:

```python
print(df.columns.tolist())
```

### Issue: "Not enough samples for correlation"

**Solution**: Ensure dataset has at least 3 rows

---

## 📊 Performance

- **Profiling**: O(n*m) where n=rows, m=columns
- **Correlation**: O(m²) for m features
- **Importance**: O(n*m*t) where t=trees (Random Forest)

**Recommendations**:
- For large datasets (>1M rows): Sample before analysis
- For many features (>1000): Use correlation-based filtering first
- For production: Cache results and analyze incrementally

---

## ✅ Quick Win #5 Status

**Progress**: 100% Complete ✅

- [x] Dataset profiling engine
- [x] Correlation analysis (3 methods)
- [x] Feature importance (4 methods)
- [x] Recommendation system
- [x] Insight generation
- [x] CLI tool (3 commands)
- [x] Python API
- [x] REST API endpoints
- [x] Documentation

**Completion Date**: 2025-10-04
**Actual Effort**: 2 weeks

---

**Built with ❤️ for Maestro ML Platform**
**Version**: 1.0.0 | **Date**: 2025-10-04
