# Getting Started with Sunday.com Development

## 🎯 Overview

This tutorial will guide you through setting up Sunday.com locally, understanding the codebase structure, and making your first contribution. By the end, you'll have a fully functional development environment and understand how to build features for the platform.

## 📋 Prerequisites

Before starting, ensure you have:

- **Node.js 18+** and **npm 8+**
- **PostgreSQL 14+**
- **Redis 6+**
- **Git** for version control
- **VS Code** (recommended) with TypeScript extension
- **Docker** (optional but recommended)

## 🚀 Quick Setup with Docker

The fastest way to get started is using Docker Compose:

```bash
# Clone the repository
git clone https://github.com/sunday-com/sunday.git
cd sunday

# Start all services
docker-compose up -d

# Wait for services to start (about 2-3 minutes)
docker-compose logs -f

# Open your browser
open http://localhost:3001
```

## 🛠️ Manual Setup

### 1. Clone and Setup Backend

```bash
# Clone the repository
git clone https://github.com/sunday-com/sunday.git
cd sunday/backend

# Install dependencies
npm install

# Setup environment
cp .env.example .env
```

Edit `.env` with your database credentials:
```bash
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/sunday_dev"
REDIS_URL="redis://localhost:6379"

# JWT Secrets
JWT_SECRET="your-super-secret-jwt-key"
JWT_REFRESH_SECRET="your-refresh-secret-key"

# Other settings
NODE_ENV="development"
PORT=3000
```

### 2. Database Setup

```bash
# Generate Prisma client
npx prisma generate

# Run database migrations
npx prisma migrate dev --name init

# Seed the database with sample data
npm run seed
```

### 3. Start Backend Server

```bash
# Development mode with hot reload
npm run dev

# Or production mode
npm run build
npm start
```

The API will be available at `http://localhost:3000`

### 4. Setup Frontend

Open a new terminal:

```bash
cd sunday/frontend

# Install dependencies
npm install

# Setup environment
cp .env.example .env.local
```

Edit `.env.local`:
```bash
VITE_API_URL=http://localhost:3000
VITE_APP_URL=http://localhost:3001
VITE_WS_URL=ws://localhost:3000
```

### 5. Start Frontend Server

```bash
# Development mode
npm run dev

# The app will be available at http://localhost:3001
```

## 🧪 Verify Installation

### Test Backend

```bash
# Test API health
curl http://localhost:3000/health

# Expected response:
# {"status":"ok","timestamp":"2024-12-01T10:00:00.000Z"}

# Test authentication endpoint
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Password123!",
    "firstName": "Test",
    "lastName": "User"
  }'
```

### Test Frontend

1. Open `http://localhost:3001` in your browser
2. You should see the Sunday.com login page
3. Register a new account or login with seeded data:
   - Email: `admin@sunday.com`
   - Password: `password123`

## 🏗️ Understanding the Architecture

### Backend Structure

```
backend/
├── src/
│   ├── config/          # Configuration files
│   │   ├── database.ts  # Database connection
│   │   ├── redis.ts     # Redis configuration
│   │   └── logger.ts    # Logging setup
│   ├── middleware/      # Express middleware
│   │   ├── auth.ts      # Authentication
│   │   ├── validation.ts # Request validation
│   │   └── error.ts     # Error handling
│   ├── routes/          # API routes
│   │   ├── auth.routes.ts
│   │   ├── organization.routes.ts
│   │   └── index.ts
│   ├── services/        # Business logic
│   │   ├── auth.service.ts
│   │   ├── organization.service.ts
│   │   └── ...
│   ├── types/           # TypeScript types
│   └── server.ts        # Main server file
├── prisma/             # Database schema
├── docs/               # API documentation
└── __tests__/          # Test files
```

### Frontend Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   │   ├── ui/        # Base components
│   │   └── layout/    # Layout components
│   ├── pages/         # Route components
│   ├── hooks/         # Custom React hooks
│   ├── lib/           # Utilities and API client
│   ├── store/         # State management
│   ├── styles/        # Global styles
│   └── types/         # TypeScript types
├── public/            # Static assets
└── __tests__/         # Test files
```

## 🔧 Development Workflow

### 1. Creating a New Feature

Let's create a simple "Labels" feature for work items:

#### Backend Implementation

**Step 1: Database Schema**

Update `prisma/schema.prisma`:
```prisma
model Label {
  id          String   @id @default(cuid())
  name        String
  color       String
  description String?

  organizationId String
  organization   Organization @relation(fields: [organizationId], references: [id])

  items ItemLabel[]

  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("labels")
}

model ItemLabel {
  id String @id @default(cuid())

  itemId String
  item   Item   @relation(fields: [itemId], references: [id])

  labelId String
  label   Label  @relation(fields: [labelId], references: [id])

  @@unique([itemId, labelId])
  @@map("item_labels")
}
```

**Step 2: Run Migration**
```bash
npx prisma migrate dev --name add-labels
```

**Step 3: Create Service**

Create `src/services/label.service.ts`:
```typescript
import { PrismaClient } from '@prisma/client';
import { CreateLabelDto, UpdateLabelDto } from '../types/label.types';

export class LabelService {
  constructor(private prisma: PrismaClient) {}

  async createLabel(organizationId: string, data: CreateLabelDto) {
    return this.prisma.label.create({
      data: {
        ...data,
        organizationId,
      },
    });
  }

  async getLabels(organizationId: string) {
    return this.prisma.label.findMany({
      where: { organizationId },
      include: {
        _count: {
          select: { items: true },
        },
      },
      orderBy: { name: 'asc' },
    });
  }

  async updateLabel(id: string, data: UpdateLabelDto) {
    return this.prisma.label.update({
      where: { id },
      data,
    });
  }

  async deleteLabel(id: string) {
    return this.prisma.label.delete({
      where: { id },
    });
  }

  async addLabelToItem(itemId: string, labelId: string) {
    return this.prisma.itemLabel.create({
      data: { itemId, labelId },
    });
  }

  async removeLabelFromItem(itemId: string, labelId: string) {
    return this.prisma.itemLabel.delete({
      where: {
        itemId_labelId: { itemId, labelId },
      },
    });
  }
}
```

**Step 4: Create Routes**

Create `src/routes/label.routes.ts`:
```typescript
import { Router } from 'express';
import { LabelService } from '../services/label.service';
import { auth, requirePermission } from '../middleware/auth';
import { validate } from '../middleware/validation';
import { createLabelSchema, updateLabelSchema } from '../schemas/label.schemas';

const router = Router();
const labelService = new LabelService();

// GET /organizations/:orgId/labels
router.get(
  '/organizations/:orgId/labels',
  auth,
  requirePermission('label:read'),
  async (req, res, next) => {
    try {
      const labels = await labelService.getLabels(req.params.orgId);
      res.json({ data: labels });
    } catch (error) {
      next(error);
    }
  }
);

// POST /organizations/:orgId/labels
router.post(
  '/organizations/:orgId/labels',
  auth,
  requirePermission('label:write'),
  validate(createLabelSchema),
  async (req, res, next) => {
    try {
      const label = await labelService.createLabel(req.params.orgId, req.body);
      res.status(201).json({ data: label });
    } catch (error) {
      next(error);
    }
  }
);

// PUT /labels/:id
router.put(
  '/labels/:id',
  auth,
  requirePermission('label:write'),
  validate(updateLabelSchema),
  async (req, res, next) => {
    try {
      const label = await labelService.updateLabel(req.params.id, req.body);
      res.json({ data: label });
    } catch (error) {
      next(error);
    }
  }
);

// DELETE /labels/:id
router.delete(
  '/labels/:id',
  auth,
  requirePermission('label:write'),
  async (req, res, next) => {
    try {
      await labelService.deleteLabel(req.params.id);
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  }
);

export default router;
```

#### Frontend Implementation

**Step 1: Create Types**

Add to `src/types/index.ts`:
```typescript
export interface Label {
  id: string;
  name: string;
  color: string;
  description?: string;
  organizationId: string;
  _count?: {
    items: number;
  };
  createdAt: string;
  updatedAt: string;
}

export interface CreateLabelData {
  name: string;
  color: string;
  description?: string;
}
```

**Step 2: Create API Client**

Add to `src/lib/api.ts`:
```typescript
// Label operations
export const labelApi = {
  async getLabels(organizationId: string): Promise<Label[]> {
    const response = await apiClient.get(`/organizations/${organizationId}/labels`);
    return response.data.data;
  },

  async createLabel(organizationId: string, data: CreateLabelData): Promise<Label> {
    const response = await apiClient.post(`/organizations/${organizationId}/labels`, data);
    return response.data.data;
  },

  async updateLabel(id: string, data: Partial<CreateLabelData>): Promise<Label> {
    const response = await apiClient.put(`/labels/${id}`, data);
    return response.data.data;
  },

  async deleteLabel(id: string): Promise<void> {
    await apiClient.delete(`/labels/${id}`);
  },
};
```

**Step 3: Create Components**

Create `src/components/labels/LabelManager.tsx`:
```tsx
import React, { useState, useEffect } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card } from '../ui/Card';
import { labelApi } from '../../lib/api';
import { Label, CreateLabelData } from '../../types';

interface LabelManagerProps {
  organizationId: string;
}

export function LabelManager({ organizationId }: LabelManagerProps) {
  const [labels, setLabels] = useState<Label[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [newLabel, setNewLabel] = useState<CreateLabelData>({
    name: '',
    color: '#3B82F6',
    description: '',
  });

  useEffect(() => {
    loadLabels();
  }, [organizationId]);

  const loadLabels = async () => {
    try {
      const data = await labelApi.getLabels(organizationId);
      setLabels(data);
    } catch (error) {
      console.error('Failed to load labels:', error);
    }
  };

  const handleCreateLabel = async () => {
    try {
      const label = await labelApi.createLabel(organizationId, newLabel);
      setLabels([...labels, label]);
      setNewLabel({ name: '', color: '#3B82F6', description: '' });
      setIsCreating(false);
    } catch (error) {
      console.error('Failed to create label:', error);
    }
  };

  const handleDeleteLabel = async (id: string) => {
    try {
      await labelApi.deleteLabel(id);
      setLabels(labels.filter(label => label.id !== id));
    } catch (error) {
      console.error('Failed to delete label:', error);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Labels</h2>
        <Button onClick={() => setIsCreating(true)}>
          Create Label
        </Button>
      </div>

      {isCreating && (
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Create New Label</h3>
          <div className="space-y-4">
            <Input
              label="Name"
              value={newLabel.name}
              onChange={(e) => setNewLabel({ ...newLabel, name: e.target.value })}
              placeholder="Enter label name"
            />
            <div>
              <label className="block text-sm font-medium mb-2">Color</label>
              <input
                type="color"
                value={newLabel.color}
                onChange={(e) => setNewLabel({ ...newLabel, color: e.target.value })}
                className="w-16 h-8 rounded border"
              />
            </div>
            <Input
              label="Description (optional)"
              value={newLabel.description}
              onChange={(e) => setNewLabel({ ...newLabel, description: e.target.value })}
              placeholder="Enter description"
            />
            <div className="flex gap-2">
              <Button onClick={handleCreateLabel}>Create</Button>
              <Button variant="outline" onClick={() => setIsCreating(false)}>
                Cancel
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {labels.map((label) => (
          <Card key={label.id} className="p-4">
            <div className="flex items-center gap-3 mb-2">
              <div
                className="w-4 h-4 rounded"
                style={{ backgroundColor: label.color }}
              />
              <h3 className="font-semibold">{label.name}</h3>
            </div>
            {label.description && (
              <p className="text-sm text-gray-600 mb-2">{label.description}</p>
            )}
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">
                {label._count?.items || 0} items
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDeleteLabel(label.id)}
              >
                Delete
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
```

### 2. Testing Your Feature

**Backend Tests**

Create `src/__tests__/label.service.test.ts`:
```typescript
import { LabelService } from '../services/label.service';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();
const labelService = new LabelService(prisma);

describe('LabelService', () => {
  beforeEach(async () => {
    // Clean up test data
    await prisma.itemLabel.deleteMany();
    await prisma.label.deleteMany();
  });

  it('should create a label', async () => {
    const labelData = {
      name: 'Bug',
      color: '#FF0000',
      description: 'Issues that need fixing',
    };

    const label = await labelService.createLabel('org_123', labelData);

    expect(label.name).toBe(labelData.name);
    expect(label.color).toBe(labelData.color);
    expect(label.organizationId).toBe('org_123');
  });

  it('should get labels for organization', async () => {
    // Create test labels
    await labelService.createLabel('org_123', { name: 'Bug', color: '#FF0000' });
    await labelService.createLabel('org_123', { name: 'Feature', color: '#00FF00' });

    const labels = await labelService.getLabels('org_123');

    expect(labels).toHaveLength(2);
    expect(labels[0].name).toBe('Bug');
    expect(labels[1].name).toBe('Feature');
  });
});
```

**Frontend Tests**

Create `src/components/labels/__tests__/LabelManager.test.tsx`:
```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LabelManager } from '../LabelManager';
import { labelApi } from '../../../lib/api';

// Mock the API
jest.mock('../../../lib/api');
const mockedLabelApi = labelApi as jest.Mocked<typeof labelApi>;

describe('LabelManager', () => {
  beforeEach(() => {
    mockedLabelApi.getLabels.mockResolvedValue([
      {
        id: '1',
        name: 'Bug',
        color: '#FF0000',
        organizationId: 'org_123',
        createdAt: '2024-01-01T00:00:00Z',
        updatedAt: '2024-01-01T00:00:00Z',
      },
    ]);
  });

  it('should render labels', async () => {
    render(<LabelManager organizationId="org_123" />);

    await waitFor(() => {
      expect(screen.getByText('Bug')).toBeInTheDocument();
    });
  });

  it('should create a new label', async () => {
    mockedLabelApi.createLabel.mockResolvedValue({
      id: '2',
      name: 'Feature',
      color: '#00FF00',
      organizationId: 'org_123',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    });

    render(<LabelManager organizationId="org_123" />);

    // Click create button
    fireEvent.click(screen.getByText('Create Label'));

    // Fill form
    fireEvent.change(screen.getByPlaceholderText('Enter label name'), {
      target: { value: 'Feature' },
    });

    // Submit
    fireEvent.click(screen.getByText('Create'));

    await waitFor(() => {
      expect(mockedLabelApi.createLabel).toHaveBeenCalledWith('org_123', {
        name: 'Feature',
        color: '#3B82F6',
        description: '',
      });
    });
  });
});
```

**Run Tests**
```bash
# Backend tests
cd backend
npm test

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 🔍 Debugging Tips

### Backend Debugging

**Enable Debug Logging**
```typescript
// In your service methods
import { logger } from '../config/logger';

export class LabelService {
  async createLabel(organizationId: string, data: CreateLabelData) {
    logger.debug('Creating label', { organizationId, data });

    const label = await this.prisma.label.create({
      data: { ...data, organizationId },
    });

    logger.info('Label created', { labelId: label.id });
    return label;
  }
}
```

**Database Query Debugging**
```bash
# Enable Prisma query logging
export DEBUG="prisma:query"
npm run dev
```

### Frontend Debugging

**React Developer Tools**
- Install React DevTools browser extension
- Use the Components and Profiler tabs
- Inspect state and props

**Network Debugging**
```typescript
// Add request/response interceptors
import axios from 'axios';

axios.interceptors.request.use(request => {
  console.log('Starting Request:', request);
  return request;
});

axios.interceptors.response.use(
  response => {
    console.log('Response:', response);
    return response;
  },
  error => {
    console.error('Response Error:', error);
    return Promise.reject(error);
  }
);
```

## 🚀 Next Steps

### Advanced Topics

1. **Real-time Features**
   - Learn WebSocket implementation
   - Add real-time label updates
   - Handle optimistic updates

2. **Performance Optimization**
   - Implement caching strategies
   - Add database indexes
   - Optimize API queries

3. **Security**
   - Add input validation
   - Implement rate limiting
   - Add audit logging

4. **Testing**
   - Write comprehensive test suites
   - Add integration tests
   - Set up E2E testing

### Contribution Guidelines

1. **Fork the repository** and create a feature branch
2. **Follow code standards** (ESLint, Prettier)
3. **Write tests** for new features
4. **Update documentation** as needed
5. **Submit a pull request** with a clear description

### Resources

- **API Documentation**: `docs/api-documentation.md`
- **Architecture Guide**: `architecture_document.md`
- **Code Style Guide**: `.eslintrc.js`
- **Database Schema**: `prisma/schema.prisma`

## 💬 Getting Help

- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Ask questions and share ideas
- **Discord**: Join our developer community
- **Email**: dev-support@sunday.com

---

Congratulations! You now have a fully functional Sunday.com development environment and understand how to build features. Start contributing and help us build the future of work management! 🎉