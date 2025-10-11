# Maestro ML - Model Registry UI

Modern web interface for the Maestro ML Platform model registry, built with React, TypeScript, and Material-UI.

## Overview

This is **Quick Win #1** from the Path A roadmap - a user-friendly web interface that wraps the MLflow model registry with Maestro branding and enhanced features.

### Features

- 📊 **Model Registry Browser**: View and search all registered models
- 🔬 **Experiments Dashboard**: Track ML experiments (coming soon)
- 💾 **Dataset Catalog**: Browse training datasets (coming soon)
- 🚀 **Deployment Monitor**: Track model deployments (coming soon)
- 🔍 **Search & Filter**: Quickly find models by name or tags
- 📱 **Mobile Responsive**: Works on all device sizes
- 🎨 **Maestro Branding**: Professional UI with Maestro color scheme

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Material-UI v5** - Component library
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Axios** - HTTP client for MLflow API
- **Zustand** - State management (if needed)

## Prerequisites

- Node.js 18+ and npm
- MLflow tracking server running (default: http://localhost:5000)
- Maestro ML Platform deployed

## Getting Started

### 1. Install Dependencies

```bash
cd ui/model-registry
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
VITE_MLFLOW_URL=http://localhost:5000
VITE_API_BASE_URL=http://localhost:8000
VITE_ENV=development
```

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### 4. Access MLflow (for backend)

Make sure MLflow is accessible. You can use port-forwarding:

```bash
kubectl port-forward -n ml-platform svc/mlflow-tracking 5000:5000
```

Or use the NodePort service:

```bash
# Apply the ingress configuration
kubectl apply -f ../../infrastructure/kubernetes/mlflow-ui-ingress.yaml

# Access via NodePort at http://<node-ip>:30500
```

## Development

### Project Structure

```
ui/model-registry/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── Layout.tsx       # Main layout with navigation
│   ├── pages/               # Page components
│   │   ├── ModelsPage.tsx   # Model registry view
│   │   ├── ExperimentsPage.tsx
│   │   ├── DatasetsPage.tsx
│   │   └── DeploymentsPage.tsx
│   ├── api/                 # API clients
│   │   └── mlflow.ts        # MLflow API integration
│   ├── types/               # TypeScript type definitions
│   ├── store/               # State management
│   ├── utils/               # Utility functions
│   ├── App.tsx              # Root component
│   ├── main.tsx             # Entry point
│   └── index.css            # Global styles
├── public/                  # Static assets
├── package.json             # Dependencies
├── tsconfig.json            # TypeScript configuration
├── vite.config.ts           # Vite configuration
└── README.md                # This file
```

### Available Scripts

```bash
npm run dev        # Start development server
npm run build      # Build for production
npm run preview    # Preview production build
npm run lint       # Run ESLint
npm run type-check # Run TypeScript compiler
```

### API Integration

The UI connects to MLflow via the `/api` endpoint, which is proxied in development:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
    }
  }
}
```

## Building for Production

### 1. Build the Application

```bash
npm run build
```

This creates an optimized bundle in the `dist/` directory.

### 2. Deploy to Kubernetes

We'll add deployment configuration in the next iteration. For now, you can serve the built files using nginx.

### 3. Docker Image (Coming Soon)

A Dockerfile will be added to containerize the UI for Kubernetes deployment.

## Quick Win Checklist

- [x] React application scaffolding
- [x] Material-UI setup with Maestro theme
- [x] Responsive layout with navigation
- [x] Model registry page with search
- [x] MLflow API integration
- [x] Mock data for development
- [ ] OAuth 2.0 authentication (next task)
- [ ] Advanced search filters
- [ ] Model detail pages
- [ ] Deployment to Kubernetes

## Next Steps

From the Quick Wins roadmap:

1. ✅ **Expose MLflow UI** - Completed
2. ✅ **Create React wrapper** - This application (in progress)
3. ⏳ **Add OAuth 2.0 authentication** - Next
4. ⏳ **Apply Maestro branding** - In progress
5. ⏳ **Implement search functionality** - Basic version done
6. ⏳ **Make mobile-responsive** - Done with Material-UI

## Deployment

### Option 1: Local Development

```bash
npm run dev
```

### Option 2: Production Build + Serve

```bash
npm run build
npx serve dist -p 3000
```

### Option 3: Docker (Coming Soon)

```bash
docker build -t maestro-ml-ui:latest .
docker run -p 3000:80 maestro-ml-ui:latest
```

### Option 4: Kubernetes (Coming Soon)

Deployment manifests will be added in the infrastructure directory.

## Troubleshooting

### Issue: Cannot connect to MLflow

**Solution**: Make sure MLflow is accessible:

```bash
# Port-forward MLflow service
kubectl port-forward -n ml-platform svc/mlflow-tracking 5000:5000

# Or check if MLflow is running
curl http://localhost:5000/api/2.0/mlflow/experiments/list
```

### Issue: CORS errors

**Solution**: The Vite proxy should handle this in development. For production, configure MLflow with appropriate CORS headers or use a reverse proxy.

### Issue: Mock data displayed instead of real models

**Solution**: This is expected when MLflow API is not accessible. The app falls back to mock data for development. Ensure `VITE_MLFLOW_URL` is set correctly.

## Contributing

This is part of the Maestro ML Platform. See the main project README for contribution guidelines.

## Timeline

- **Week 1**: Basic UI setup and model registry (current)
- **Week 2**: Authentication, branding, and polish
- **Week 3**: Experiments and datasets pages
- **Week 4**: Deployments page and production deployment

## Status

✅ **Week 1 - In Progress**

- [x] Project scaffolding
- [x] Layout and navigation
- [x] Model registry page
- [x] MLflow API integration
- [x] Search functionality
- [x] Mobile responsiveness
- [ ] Authentication layer
- [ ] Full Maestro branding

## License

Part of the Maestro ML Platform
