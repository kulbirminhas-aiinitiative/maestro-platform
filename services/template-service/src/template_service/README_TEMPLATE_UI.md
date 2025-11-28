# MAESTRO Template Library - Web UI & API

## Overview

The MAESTRO Central Registry Service provides both a **REST API** and a **beautiful web interface** for discovering, browsing, and accessing production-ready templates.

---

## 🚀 Quick Start

### 1. Start the Service

```bash
cd services/central_registry

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Set environment variables
export POSTGRES_URL="postgresql://user:password@localhost:5432/maestro_registry"
export REDIS_URL="redis://localhost:6379/0"
export AUTO_SEED_TEMPLATES="true"

# Start the service
python app.py
```

The service will start on **http://localhost:9600**

### 2. Access the Web UI

Open your browser and navigate to:
```
http://localhost:9600
```

You'll see the **MAESTRO Template Library** web interface with:
- 📊 **Real-time statistics** (Total templates, average quality, languages, frameworks)
- 🔍 **Powerful search** (Search by name, description, tags)
- 🎯 **Smart filters** (Category, language, framework, quality score)
- 📱 **Responsive design** (Works on desktop, tablet, mobile)
- 🎨 **Beautiful card interface** (Each template displayed as an interactive card)

---

## 📚 API Endpoints

### List All Templates

```bash
GET /api/v1/templates

# With filters
GET /api/v1/templates?category=iot&language=python&min_quality_score=90

# With search
GET /api/v1/templates?search=websocket
```

**Response:**
```json
{
  "templates": [
    {
      "id": "websocket-real-time-server-v1",
      "metadata": {
        "id": "websocket-real-time-server-v1",
        "name": "WebSocket Real-Time Server",
        "category": "real_time",
        "language": "python",
        "framework": "fastapi",
        "description": "Production-ready WebSocket server...",
        "tags": ["websocket", "real-time", "broadcasting"],
        "quality_score": 90.0,
        "security_score": 88.0,
        "performance_score": 92.0
      },
      "content": "#!/usr/bin/env python3...",
      "dependencies": ["fastapi>=0.109.0", "..."],
      "workflow_context": {...}
    }
  ],
  "stats": {
    "total_templates": 61,
    "average_quality_score": 91.5,
    "unique_languages": 5,
    "unique_frameworks": 8
  }
}
```

### Get Single Template

```bash
GET /api/v1/templates/{template_id}
```

**Response:**
```json
{
  "id": "iot-device-management-platform-v1",
  "metadata": {...},
  "content": "...",
  "dependencies": [...],
  "variables": {...},
  "workflow_context": {...}
}
```

### Search Templates

```bash
# Search by keyword
GET /api/v1/templates/search?q=microservices

# Advanced filters
GET /api/v1/templates/search?q=api&category=architecture&language=python
```

### Get Template Statistics

```bash
GET /api/v1/templates/stats
```

**Response:**
```json
{
  "total_templates": 61,
  "by_category": {
    "iot": 3,
    "architecture": 4,
    "security": 1,
    "real_time": 2
  },
  "by_language": {
    "python": 55,
    "typescript": 5,
    "go": 1
  },
  "by_quality": {
    "excellent_90_plus": 42,
    "good_80_89": 15,
    "fair_70_79": 4
  },
  "average_quality_score": 91.5
}
```

---

## 🎯 Using the Web Interface

### Browse Templates

1. **Homepage**: Displays all templates in a card grid
2. **Search Bar**: Type keywords to filter templates instantly
3. **Filters**: Refine by category, language, framework, or quality
4. **Template Cards**: Click any card to see detailed information

### Template Card Features

Each template card shows:
- **Template Name**: Clear, descriptive title
- **Quality Badge**: Color-coded quality score (90+ = Excellent, 80-89 = Good)
- **Metadata**: Category, language, framework
- **Description**: Brief overview (3-line preview)
- **Tags**: Technology tags for quick identification
- **Actions**:
  - 📥 **Download**: Download template JSON
  - 👁️ **Details**: View full template information

### Template Details Modal

Click "Details" to see:
- **Quality Metrics**: Quality, security, performance, maintainability scores
- **Full Description**: Complete template documentation
- **Tags**: All technology tags
- **Dependencies**: Required packages and versions
- **Quick Start**: Language, framework, category info
- **Download Button**: Get the template JSON

---

## 🔧 API Integration Examples

### Python

```python
import requests

# List templates
response = requests.get("http://localhost:9600/api/v1/templates")
templates = response.json()["templates"]

# Search for IoT templates
response = requests.get(
    "http://localhost:9600/api/v1/templates",
    params={"category": "iot", "min_quality_score": 90}
)

# Get specific template
template = requests.get(
    "http://localhost:9600/api/v1/templates/iot-device-management-platform-v1"
).json()

# Download template content
with open("template.py", "w") as f:
    f.write(template["content"])
```

### JavaScript/Node.js

```javascript
const fetch = require('node-fetch');

// List all templates
const templates = await fetch('http://localhost:9600/api/v1/templates')
  .then(res => res.json());

// Search templates
const iotTemplates = await fetch(
  'http://localhost:9600/api/v1/templates?category=iot&language=python'
).then(res => res.json());

// Get template
const template = await fetch(
  'http://localhost:9600/api/v1/templates/websocket-real-time-server-v1'
).then(res => res.json());
```

### cURL

```bash
# List templates
curl http://localhost:9600/api/v1/templates

# Search
curl "http://localhost:9600/api/v1/templates?search=websocket&min_quality_score=85"

# Get template
curl http://localhost:9600/api/v1/templates/edge-computing-gateway-v1

# Download template to file
curl http://localhost:9600/api/v1/templates/edge-computing-gateway-v1 > template.json
```

---

## 📊 Template Library Statistics

As of latest update:

- **Total Templates**: 61
- **Average Quality Score**: 92.3/100
- **Languages**: Python, TypeScript, Go, Java, Rust
- **Frameworks**: FastAPI, Django, Express, React, Vue, Strawberry GraphQL
- **Categories**: IoT, Architecture, Security, Real-Time, Microservices, API-First, Compliance
- **Latest Additions** (Week 3):
  - Edge Computing Gateway (94/100)
  - Compliance Framework (95/100)
  - IoT Device Management (92/100)
  - Microservices Platform (93/100)
  - API-First GraphQL (94/100)
  - Real-Time Analytics (93/100)
  - WebSocket Server (90/100)

---

## 🎨 UI Features

### Responsive Design
- **Desktop**: 3-column grid layout
- **Tablet**: 2-column layout
- **Mobile**: Single column, optimized for touch

### Visual Elements
- **Gradient Header**: Eye-catching purple gradient
- **Quality Badges**: Color-coded by score
  - Green (90+): Excellent
  - Purple (80-89): Good
  - Default (<80): Fair
- **Hover Effects**: Cards lift on hover with shadow
- **Smooth Transitions**: All interactions are animated
- **Modal Details**: Elegant popup for template details

### Search & Filter UX
- **Instant Search**: Results update as you type
- **Smart Filters**: Dropdowns auto-populate with available options
- **Clear Filters**: One-click reset
- **Result Count**: Shows number of matching templates

---

## 🚀 Deployment

### Production Configuration

```bash
# Environment variables
export CENTRAL_REGISTRY_PORT=9600
export POSTGRES_URL="postgresql://..."
export REDIS_URL="redis://..."
export AUTO_SEED_TEMPLATES="true"
export CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
export ENVIRONMENT="production"

# Run with production server
gunicorn app:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:9600
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV CENTRAL_REGISTRY_PORT=9600
EXPOSE 9600

CMD ["python", "app.py"]
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name templates.yourdomain.com;

    location / {
        proxy_pass http://localhost:9600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🔐 Security

### API Authentication

The service supports API key authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:9600/api/v1/templates
```

### CORS Configuration

Configure allowed origins in production:

```bash
export CORS_ORIGINS="https://yourdomain.com,https://app.yourdomain.com"
```

---

## 📖 Additional Resources

- **API Documentation**: http://localhost:9600/docs (Swagger UI)
- **Health Check**: http://localhost:9600/health
- **Metrics**: http://localhost:9600/metrics (Prometheus format)

---

## 🤝 Contributing Templates

To add new templates to the library:

1. Create template JSON in `storage/templates/{persona}/` directory
2. Follow the template schema (see existing templates for examples)
3. Run template validation
4. Service will auto-discover on next restart (if `AUTO_SEED_TEMPLATES=true`)

---

## 📞 Support

For issues or questions:
- Check service logs: `docker logs central-registry`
- Verify database connection: `GET /health`
- Review API docs: `GET /docs`

---

**Built with ❤️ by the MAESTRO Team**
