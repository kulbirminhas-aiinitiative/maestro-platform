# ML Model Cards Generator

**Status**: ✅ Complete
**Quick Win**: #3
**Google Model Cards Standard**: [arxiv.org/abs/1810.03993](https://arxiv.org/abs/1810.03993)

Auto-generate ML model documentation following Google's Model Cards standard, with automatic extraction from MLflow metadata and PDF generation via MAESTRO PDF Service.

---

## 🎯 Features

- ✅ Auto-extract model metadata from MLflow
- ✅ Google Model Cards standard compliance
- ✅ Multiple export formats (Markdown, JSON, PDF)
- ✅ Manual override system for human annotations
- ✅ CLI tool for easy generation
- ✅ Integration with MAESTRO PDF Generator Service
- ✅ Type-safe with Pydantic schemas
- ✅ Batch generation support

---

## 📦 Installation

```bash
# Install dependencies
pip install mlflow pydantic click aiohttp

# Or from project root
pip install -r requirements.txt
```

---

## 🚀 Quick Start

### 1. CLI Usage (Recommended)

```bash
# List available models
python cli.py list

# Generate Markdown model card
python cli.py generate fraud-detector 3

# Generate PDF model card (requires PDF service)
python cli.py generate fraud-detector 3 --format pdf

# Generate all formats
python cli.py generate fraud-detector 3 --format all

# Generate with manual overrides
python cli.py generate fraud-detector 3 --override overrides.json
```

### 2. Programmatic Usage

```python
from card_generator import ModelCardGenerator

# Initialize generator
generator = ModelCardGenerator(mlflow_uri="http://localhost:5000")

# Generate from MLflow
card = generator.generate_from_mlflow(
    model_name="fraud-detector",
    version="3"
)

# Save as Markdown
generator.save_markdown(card, "fraud-detector-v3.md")

# Save as JSON
generator.save_json(card, "fraud-detector-v3.json")

# Save as PDF (requires PDF service)
generator.save_pdf(card, "fraud-detector-v3.pdf")
```

---

## 📋 Model Card Sections

Following Google's Model Card standard, each card includes:

### 1. Model Details
- Name, version, type
- Framework and algorithm
- Owners and license
- References and citations

**Auto-extracted from**: MLflow model registry and run metadata

### 2. Intended Use
- Primary use cases
- Intended users
- Out-of-scope applications

**Requires**: Manual annotation via overrides

### 3. Performance Metrics
- Model performance metrics
- Decision thresholds
- Uncertainty quantification

**Auto-extracted from**: MLflow run metrics

### 4. Training Data
- Dataset information
- Sample counts
- Preprocessing steps
- Feature lists

**Auto-extracted from**: MLflow run parameters and tags

### 5. Evaluation Data
- Test dataset details
- Evaluation methodology

**Requires**: Manual annotation via overrides

### 6. Ethical Considerations
- Sensitive data usage
- Risks and potential harms
- Mitigation strategies
- Use cases to avoid

**Requires**: Manual annotation via overrides

### 7. Caveats and Recommendations
- Known limitations
- Recommendations for use
- Ideal deployment conditions

**Requires**: Manual annotation via overrides

---

## 🎨 Output Formats

### Markdown (.md)
Human-readable documentation, GitHub-compatible

```bash
python cli.py generate fraud-detector 3 --format md
```

### JSON (.json)
Structured data for APIs and databases

```bash
python cli.py generate fraud-detector 3 --format json
```

### PDF (.pdf)
Professional documentation for compliance and reporting

```bash
python cli.py generate fraud-detector 3 --format pdf
```

**Note**: PDF generation requires the MAESTRO PDF Generator Service to be running:

```bash
cd ~/projects/utilities/services/pdf_generator
python app.py
```

---

## ✏️ Manual Overrides

For sections requiring human input (ethical considerations, intended use, etc.):

### Option 1: Create Override JSON File

```json
{
  "intended_use": {
    "primary_uses": ["Fraud detection in payment processing"],
    "primary_users": ["Fraud analysts", "Risk team"],
    "out_of_scope": ["Credit scoring", "Employment decisions"]
  },
  "ethical_considerations": {
    "risks_and_harms": [
      "May exhibit bias against certain demographics",
      "False positives could delay legitimate transactions"
    ],
    "mitigations": [
      "Regular bias audits conducted monthly",
      "Human review required for high-value transactions"
    ]
  }
}
```

Then use with:

```bash
python cli.py generate fraud-detector 3 --override overrides.json
```

### Option 2: Use CLI Override Helper

```bash
# Add intended use
python cli.py override fraud-detector 3 \
  --key intended_use.primary_uses \
  --value '["Fraud detection", "Risk assessment"]'

# Add ethical considerations
python cli.py override fraud-detector 3 \
  --key ethical_considerations.risks_and_harms \
  --value '["Potential demographic bias"]'

# Generate with overrides
python cli.py generate fraud-detector 3 \
  --override fraud-detector-v3-overrides.json
```

---

## 📂 File Structure

```
governance/model-cards/
├── __init__.py
├── model_card_schema.py      # Pydantic schemas (Google standard)
├── card_generator.py          # Core generation logic
├── cli.py                     # Command-line interface
├── example_usage.py           # Programmatic examples
├── README.md                  # This file
├── templates/                 # HTML templates (for future use)
└── generated/                 # Generated model cards
    ├── fraud-detector-v3.md
    ├── fraud-detector-v3.json
    └── fraud-detector-v3.pdf
```

---

## 🔌 Integration with PDF Service

The model card generator integrates with the existing MAESTRO PDF Generator Service (`~/projects/utilities/services/pdf_generator/`).

**Enhanced PDF service with**:
- New `MODEL_CARD` template type
- Specialized rendering for ML model documentation
- Performance metrics tables
- Compliance-ready formatting

**API endpoint**: `POST /api/v1/generate/pdf`

**Template type**: `model_card`

---

## 🧪 Example: Complete Workflow

```bash
# 1. List available models
python cli.py list

# Output:
# Found 3 model(s):
# 📦 fraud-detector
#    v3 [Production]
#    v2 [Staging]
#    v1 [None]

# 2. Create overrides for ethical considerations
python cli.py override fraud-detector 3 \
  --key intended_use.primary_uses \
  --value '["Real-time fraud detection", "Risk assessment"]'

python cli.py override fraud-detector 3 \
  --key ethical_considerations.risks_and_harms \
  --value '["May have demographic bias", "False positives impact customers"]'

# 3. Generate all formats with overrides
python cli.py generate fraud-detector 3 \
  --format all \
  --override fraud-detector-v3-overrides.json \
  --output ./docs/model-cards/

# Output:
# ✅ Markdown saved to ./docs/model-cards/fraud-detector-v3.md
# ✅ JSON saved to ./docs/model-cards/fraud-detector-v3.json
# ✅ PDF saved to ./docs/model-cards/fraud-detector-v3.pdf
# 🎉 Model card generated successfully!

# 4. Validate generated card
python cli.py validate ./docs/model-cards/fraud-detector-v3.json

# Output:
# ✅ Model card is valid!
# Model: fraud-detector v3
# Type: classification
# Metrics: 4 metrics
# Dataset: fraud_transactions_2024
```

---

## 🔧 Configuration

### Environment Variables

```bash
# MLflow configuration
export MLFLOW_TRACKING_URI=http://localhost:5000

# PDF service configuration
export PDF_SERVICE_URL=http://localhost:9550
```

### MLflow Tags for Better Extraction

Tag your MLflow runs for richer model cards:

```python
import mlflow

mlflow.set_tags({
    "model_type": "classification",
    "framework": "pytorch",
    "algorithm": "XGBoost",
    "owner": "data-science-team@company.com",
    "license": "Apache 2.0",
    "dataset_name": "fraud_transactions_2024",
    "dataset_version": "v2.1",
    "features": '["amount", "merchant_id", "user_age", "transaction_time"]'
})
```

---

## 📊 CLI Commands Reference

### `generate`
Generate model card from MLflow

```bash
python cli.py generate MODEL_NAME VERSION [OPTIONS]

Options:
  -f, --format [pdf|md|json|all]  Output format (default: md)
  -o, --output PATH               Output directory
  -r, --override PATH             JSON file with manual overrides
```

### `list`
List available models in MLflow registry

```bash
python cli.py list [OPTIONS]

Options:
  -f, --filter TEXT  Filter models by name pattern
```

### `validate`
Validate a model card JSON file

```bash
python cli.py validate CARD_FILE
```

### `override`
Create override file for manual annotations

```bash
python cli.py override MODEL_NAME VERSION --key KEY --value VALUE

Options:
  -k, --key TEXT    Key to override (e.g., intended_use.primary_uses)
  -v, --value TEXT  JSON value to set
```

---

## 🎯 Use Cases

1. **Compliance & Governance**: Generate model cards for regulatory compliance (GDPR, AI Act)
2. **Model Registry**: Auto-document all production models
3. **Team Communication**: Share model details with stakeholders
4. **Audit Trail**: Track model evolution and decisions
5. **Responsible AI**: Document ethical considerations and limitations

---

## 🚀 Advanced Usage

### Batch Generation for All Production Models

```python
from pathlib import Path
import mlflow
from mlflow.tracking import MlflowClient
from card_generator import ModelCardGenerator

mlflow.set_tracking_uri("http://localhost:5000")
client = MlflowClient()
generator = ModelCardGenerator()

# Get all production models
models = client.search_registered_models()

for model in models:
    versions = client.get_latest_versions(model.name, stages=["Production"])

    for version in versions:
        card = generator.generate_from_mlflow(model.name, version.version)
        output_path = Path(f"./cards/{model.name}-v{version.version}.pdf")
        generator.save_pdf(card, output_path)
        print(f"✅ Generated {output_path}")
```

### Custom Template Integration

```python
# Future: Custom Jinja2 templates for HTML rendering
generator = ModelCardGenerator(templates_dir="./custom_templates")
```

---

## 🐛 Troubleshooting

### Issue: "Model not found in MLflow"

```bash
# Check MLflow is accessible
curl http://localhost:5000/api/2.0/mlflow/registered-models/search

# List models
python cli.py list
```

### Issue: "PDF generation failed"

```bash
# Check PDF service is running
curl http://localhost:9550/health

# Start PDF service
cd ~/projects/utilities/services/pdf_generator
python app.py

# Check logs
tail -f ~/projects/utilities/logs/pdf_generator.log
```

### Issue: "Missing required fields"

```bash
# Validate your override JSON
python cli.py validate fraud-detector-v3.json

# Check schema
python -c "from model_card_schema import ModelCard; print(ModelCard.model_json_schema())"
```

---

## 📚 References

- [Google Model Cards Paper](https://arxiv.org/abs/1810.03993)
- [MLflow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [Hugging Face Model Cards](https://huggingface.co/docs/hub/model-cards)
- [MAESTRO PDF Generator Service](~/projects/utilities/services/pdf_generator/)

---

## ✅ Quick Win #3 Status

**Progress**: 100% Complete ✅

- [x] Create model card schema (Pydantic)
- [x] Implement auto-extraction from MLflow
- [x] Markdown rendering
- [x] JSON export
- [x] PDF generation integration
- [x] CLI tool with 4 commands
- [x] Manual override system
- [x] Batch generation support
- [x] Documentation and examples

**Completion Date**: 2025-10-04
**Estimated Effort**: 1 week ✅
**Actual Effort**: 1 week

---

**Built with ❤️ for Maestro ML Platform**
**Follows Google's Model Cards for Model Reporting standard**
