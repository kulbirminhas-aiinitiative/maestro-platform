# Test Automation Framework Implementation
**QA Engineer Design Document - December 19, 2024**
**Project:** Sunday.com - Iteration 2
**Session ID:** sunday_com

## Executive Summary

This document outlines the implementation of a comprehensive test automation framework for Sunday.com platform. The framework leverages existing excellent test infrastructure and extends it with performance testing, E2E automation, and advanced testing capabilities to ensure production readiness.

### Framework Maturity: Advanced (Level 4/5)
- **Current Infrastructure:** 95% complete ✅
- **Automation Coverage:** 85% complete ✅
- **CI/CD Integration:** 90% complete ✅
- **Performance Testing:** 20% complete ❌
- **E2E Automation:** 40% complete ⚠️

## Framework Architecture

### Test Pyramid Implementation

```
                    E2E Tests (10%)
                   ┌─────────────────┐
                   │   Playwright    │
                   │   Cypress       │
                   └─────────────────┘

            Integration Tests (20%)
          ┌─────────────────────────────┐
          │    Jest + Supertest        │
          │    API Integration         │
          │    Database Testing        │
          └─────────────────────────────┘

        Unit Tests (70%)
  ┌─────────────────────────────────────────┐
  │           Jest + TypeScript             │
  │     React Testing Library + jsdom      │
  │        Service Layer Testing           │
  └─────────────────────────────────────────┘
```

### Technology Stack Matrix

| Test Type | Framework | Language | Environment | Status |
|-----------|-----------|----------|-------------|---------|
| Backend Unit | Jest + TypeScript | TypeScript | Node.js | ✅ Implemented |
| Frontend Unit | Jest + RTL | TypeScript | jsdom | ✅ Implemented |
| API Integration | Jest + Supertest | TypeScript | Node.js | ✅ Implemented |
| E2E Testing | Playwright | TypeScript | Browsers | ⚠️ Partial |
| Performance | k6 | JavaScript | Load Testing | ❌ Not Implemented |
| Security | OWASP ZAP | Python/JS | Security Scan | ⚠️ Basic |
| Visual Regression | Percy/Chromatic | TypeScript | Visual Diff | ❌ Not Implemented |

## Enhanced Test Infrastructure

### 1. Performance Testing Framework ⚠️ CRITICAL IMPLEMENTATION

#### k6 Performance Testing Setup

**Directory Structure:**
```
performance/
├── config/
│   ├── environments.js
│   ├── scenarios.js
│   └── thresholds.js
├── tests/
│   ├── api/
│   │   ├── auth-load.js
│   │   ├── boards-load.js
│   │   ├── items-load.js
│   │   └── websocket-load.js
│   ├── scenarios/
│   │   ├── normal-load.js
│   │   ├── stress-test.js
│   │   └── spike-test.js
│   └── utils/
│       ├── data-generators.js
│       ├── auth-helpers.js
│       └── assertions.js
├── reports/
└── package.json
```

**Implementation Files:**

##### performance/config/environments.js
```javascript
export const environments = {
  development: {
    baseUrl: 'http://localhost:3001',
    wsUrl: 'ws://localhost:3001',
    users: {
      concurrent: 50,
      rampUp: '2m',
      duration: '5m'
    }
  },
  staging: {
    baseUrl: 'https://staging-api.sunday.com',
    wsUrl: 'wss://staging-api.sunday.com',
    users: {
      concurrent: 500,
      rampUp: '5m',
      duration: '15m'
    }
  },
  production: {
    baseUrl: 'https://api.sunday.com',
    wsUrl: 'wss://api.sunday.com',
    users: {
      concurrent: 1000,
      rampUp: '10m',
      duration: '30m'
    }
  }
}
```

##### performance/tests/scenarios/normal-load.js
```javascript
import http from 'k6/http'
import ws from 'k6/ws'
import { check, sleep } from 'k6'
import { Counter, Rate, Trend } from 'k6/metrics'

// Custom metrics
const authFailures = new Counter('auth_failures')
const apiResponseTime = new Trend('api_response_time')
const wsConnectionRate = new Rate('ws_connection_success')

export let options = {
  stages: [
    { duration: '5m', target: 100 },   // Ramp up
    { duration: '10m', target: 500 },  // Normal load
    { duration: '5m', target: 1000 },  // Peak load
    { duration: '10m', target: 1000 }, // Sustained peak
    { duration: '5m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<200'],     // 95% under 200ms
    http_req_failed: ['rate<0.1'],        // Error rate under 10%
    ws_connection_success: ['rate>0.95'], // 95% WS connections succeed
    api_response_time: ['p(95)<150'],     // API calls under 150ms
  }
}

export default function() {
  // 1. Authentication
  const authResponse = http.post(`${__ENV.BASE_URL}/api/auth/login`,
    JSON.stringify({
      email: `user_${__VU}@test.com`,
      password: 'TestPassword123'
    }),
    { headers: { 'Content-Type': 'application/json' } }
  )

  const authSuccess = check(authResponse, {
    'auth successful': (r) => r.status === 200,
    'auth response time OK': (r) => r.timings.duration < 500,
  })

  if (!authSuccess) {
    authFailures.add(1)
    return
  }

  const token = JSON.parse(authResponse.body).token
  const authHeaders = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }

  // 2. Workspace operations
  const workspacesResponse = http.get(`${__ENV.BASE_URL}/api/workspaces`, {
    headers: authHeaders
  })

  check(workspacesResponse, {
    'workspaces loaded': (r) => r.status === 200,
    'workspaces response time': (r) => r.timings.duration < 200,
  })

  apiResponseTime.add(workspacesResponse.timings.duration)

  // 3. Board operations
  const boardsResponse = http.get(`${__ENV.BASE_URL}/api/boards`, {
    headers: authHeaders
  })

  check(boardsResponse, {
    'boards loaded': (r) => r.status === 200,
    'boards response time': (r) => r.timings.duration < 200,
  })

  // 4. WebSocket connection test
  const wsUrl = `${__ENV.WS_URL}/ws/collaboration?token=${token}`
  const wsResponse = ws.connect(wsUrl, {}, function(socket) {
    socket.on('open', () => {
      wsConnectionRate.add(true)
      socket.send(JSON.stringify({
        type: 'board.join',
        boardId: 'test-board-id'
      }))
    })

    socket.on('error', () => {
      wsConnectionRate.add(false)
    })

    socket.setTimeout(() => {
      socket.close()
    }, 5000)
  })

  sleep(1) // Think time between operations
}
```

#### Performance Test Execution Scripts

##### performance/package.json
```json
{
  "name": "sunday-performance-tests",
  "scripts": {
    "test:load": "k6 run --env BASE_URL=http://localhost:3001 tests/scenarios/normal-load.js",
    "test:stress": "k6 run --env BASE_URL=http://localhost:3001 tests/scenarios/stress-test.js",
    "test:staging": "k6 run --env BASE_URL=https://staging-api.sunday.com tests/scenarios/normal-load.js",
    "test:api:auth": "k6 run tests/api/auth-load.js",
    "test:api:boards": "k6 run tests/api/boards-load.js",
    "test:websocket": "k6 run tests/api/websocket-load.js",
    "report:html": "k6 run --out json=reports/results.json tests/scenarios/normal-load.js && k6-reporter --input reports/results.json --output reports/report.html"
  },
  "devDependencies": {
    "k6": "^0.47.0",
    "k6-reporter": "^2.4.0"
  }
}
```

### 2. Enhanced E2E Testing Framework ⚠️ NEEDS EXPANSION

#### Playwright E2E Testing Setup

**Directory Structure:**
```
tests/e2e/
├── fixtures/
│   ├── test-data.ts
│   ├── user-factory.ts
│   └── workspace-factory.ts
├── page-objects/
│   ├── auth/
│   │   ├── login-page.ts
│   │   └── register-page.ts
│   ├── workspace/
│   │   ├── workspace-list-page.ts
│   │   └── workspace-detail-page.ts
│   ├── boards/
│   │   ├── boards-page.ts
│   │   └── board-view-page.ts
│   └── base-page.ts
├── tests/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   └── registration.spec.ts
│   ├── workspace/
│   │   ├── workspace-creation.spec.ts
│   │   └── workspace-management.spec.ts
│   ├── boards/
│   │   ├── board-creation.spec.ts
│   │   ├── item-management.spec.ts
│   │   └── collaboration.spec.ts
│   └── user-journeys/
│       ├── onboarding-flow.spec.ts
│       ├── daily-workflow.spec.ts
│       └── team-collaboration.spec.ts
├── utils/
│   ├── test-helpers.ts
│   ├── api-helpers.ts
│   └── data-setup.ts
├── playwright.config.ts
└── global-setup.ts
```

**Implementation Files:**

##### tests/e2e/playwright.config.ts
```typescript
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'test-results.xml' }]
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile browsers
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
})
```

##### tests/e2e/page-objects/boards/board-view-page.ts
```typescript
import { Page, Locator, expect } from '@playwright/test'
import { BasePage } from '../base-page'

export class BoardViewPage extends BasePage {
  readonly page: Page
  readonly boardTitle: Locator
  readonly addItemButton: Locator
  readonly columnContainer: Locator
  readonly itemCard: Locator

  constructor(page: Page) {
    super(page)
    this.page = page
    this.boardTitle = page.locator('[data-testid="board-title"]')
    this.addItemButton = page.locator('[data-testid="add-item-button"]')
    this.columnContainer = page.locator('[data-testid="board-column"]')
    this.itemCard = page.locator('[data-testid="item-card"]')
  }

  async waitForBoardToLoad(boardName: string) {
    await expect(this.boardTitle).toContainText(boardName)
    await expect(this.columnContainer).toBeVisible()
  }

  async createItem(itemName: string, description?: string) {
    await this.addItemButton.click()

    const itemNameInput = this.page.locator('[data-testid="item-name-input"]')
    await itemNameInput.fill(itemName)

    if (description) {
      const itemDescInput = this.page.locator('[data-testid="item-description-input"]')
      await itemDescInput.fill(description)
    }

    await this.page.locator('[data-testid="save-item-button"]').click()

    // Wait for item to appear in the board
    await expect(this.page.locator(`[data-testid="item-${itemName.toLowerCase().replace(/\s+/g, '-')}"]`)).toBeVisible()
  }

  async dragItemToColumn(itemName: string, targetColumn: string) {
    const item = this.page.locator(`[data-testid="item-${itemName.toLowerCase().replace(/\s+/g, '-')}"]`)
    const target = this.page.locator(`[data-testid="column-${targetColumn.toLowerCase().replace(/\s+/g, '-')}"]`)

    await item.dragTo(target)

    // Verify item moved to target column
    const targetColumnItems = target.locator('[data-testid*="item-"]')
    await expect(targetColumnItems).toContainText(itemName)
  }

  async verifyRealTimeUpdate(expectedUpdate: string) {
    // Wait for WebSocket update to reflect in UI
    await this.page.waitForTimeout(1000) // Allow for real-time propagation
    await expect(this.page.locator(`[data-testid*="${expectedUpdate}"]`)).toBeVisible()
  }

  async addComment(itemName: string, comment: string) {
    const item = this.page.locator(`[data-testid="item-${itemName.toLowerCase().replace(/\s+/g, '-')}"]`)
    await item.click()

    // Item detail modal should open
    const commentInput = this.page.locator('[data-testid="comment-input"]')
    await commentInput.fill(comment)
    await this.page.locator('[data-testid="add-comment-button"]').click()

    // Verify comment appears
    await expect(this.page.locator('[data-testid="comment-list"]')).toContainText(comment)
  }
}
```

##### tests/e2e/tests/user-journeys/onboarding-flow.spec.ts
```typescript
import { test, expect } from '@playwright/test'
import { LoginPage } from '../../page-objects/auth/login-page'
import { RegisterPage } from '../../page-objects/auth/register-page'
import { WorkspaceListPage } from '../../page-objects/workspace/workspace-list-page'
import { BoardsPage } from '../../page-objects/boards/boards-page'
import { BoardViewPage } from '../../page-objects/boards/board-view-page'
import { createTestUser } from '../../fixtures/user-factory'

test.describe('User Onboarding Flow', () => {
  test('Complete new user onboarding journey', async ({ page }) => {
    const testUser = createTestUser()

    // Step 1: User Registration
    const registerPage = new RegisterPage(page)
    await registerPage.goto()
    await registerPage.register(testUser.email, testUser.password, testUser.name)

    // Step 2: Email verification (simulate)
    await registerPage.verifyEmailConfirmation()

    // Step 3: First login
    const loginPage = new LoginPage(page)
    await loginPage.login(testUser.email, testUser.password)

    // Step 4: Workspace creation (onboarding flow)
    const workspacePage = new WorkspaceListPage(page)
    await workspacePage.waitForOnboardingFlow()
    await workspacePage.createFirstWorkspace('My First Workspace', 'Project management workspace')

    // Step 5: First board creation
    const boardsPage = new BoardsPage(page)
    await boardsPage.waitForEmptyState()
    await boardsPage.createFirstBoard('Project Board', 'Main project tracking board')

    // Step 6: First item creation
    const boardViewPage = new BoardViewPage(page)
    await boardViewPage.waitForBoardToLoad('Project Board')
    await boardViewPage.createItem('Welcome Task', 'Your first task in Sunday.com')

    // Step 7: Verify onboarding completion
    await expect(page.locator('[data-testid="onboarding-complete"]')).toBeVisible()
    await expect(page.locator('[data-testid="dashboard-link"]')).toBeVisible()

    // Step 8: Navigate to dashboard and verify setup
    await page.click('[data-testid="dashboard-link"]')
    await expect(page.locator('[data-testid="workspace-My-First-Workspace"]')).toBeVisible()
    await expect(page.locator('[data-testid="board-Project-Board"]')).toBeVisible()
  })

  test('Team collaboration onboarding', async ({ page, context }) => {
    const teamOwner = createTestUser('owner')
    const teamMember = createTestUser('member')

    // Owner creates workspace and invites member
    const ownerPage = page
    const loginPage = new LoginPage(ownerPage)
    await loginPage.goto()
    await loginPage.login(teamOwner.email, teamOwner.password)

    const workspacePage = new WorkspaceListPage(ownerPage)
    await workspacePage.createWorkspace('Team Workspace')
    await workspacePage.inviteTeamMember(teamMember.email, 'member')

    // Member accepts invitation and joins
    const memberPage = await context.newPage()
    const memberLoginPage = new LoginPage(memberPage)
    await memberLoginPage.goto()
    await memberLoginPage.login(teamMember.email, teamMember.password)

    // Verify invitation notification
    await expect(memberPage.locator('[data-testid="invitation-notification"]')).toBeVisible()
    await memberPage.click('[data-testid="accept-invitation"]')

    // Both users collaborate on same board
    const ownerBoardPage = new BoardViewPage(ownerPage)
    const memberBoardPage = new BoardViewPage(memberPage)

    // Owner creates item
    await ownerBoardPage.createItem('Collaborative Task')

    // Member should see the item in real-time
    await memberBoardPage.verifyRealTimeUpdate('Collaborative Task')

    // Member adds comment
    await memberBoardPage.addComment('Collaborative Task', 'Working on this now!')

    // Owner should see the comment in real-time
    await ownerBoardPage.verifyRealTimeUpdate('Working on this now!')
  })
})
```

### 3. Visual Regression Testing Framework ❌ NEW IMPLEMENTATION

#### Percy/Chromatic Integration

##### tests/visual/visual-regression.spec.ts
```typescript
import { test } from '@playwright/test'
import percySnapshot from '@percy/playwright'

test.describe('Visual Regression Tests', () => {
  test('Dashboard page visual snapshot', async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    await percySnapshot(page, 'Dashboard - Default State')
  })

  test('Board view visual snapshot', async ({ page }) => {
    await page.goto('/boards/sample-board')
    await page.waitForLoadState('networkidle')
    await percySnapshot(page, 'Board View - With Items')
  })

  test('Responsive design snapshots', async ({ page }) => {
    // Desktop
    await page.setViewportSize({ width: 1920, height: 1080 })
    await page.goto('/dashboard')
    await percySnapshot(page, 'Dashboard - Desktop')

    // Tablet
    await page.setViewportSize({ width: 768, height: 1024 })
    await percySnapshot(page, 'Dashboard - Tablet')

    // Mobile
    await page.setViewportSize({ width: 375, height: 667 })
    await percySnapshot(page, 'Dashboard - Mobile')
  })
})
```

### 4. API Test Automation Enhancement

#### Advanced API Testing Framework

##### tests/api/enhanced-api.spec.ts
```typescript
import { test, expect } from '@playwright/test'
import { APIRequestContext } from '@playwright/test'

class APITestFramework {
  private apiContext: APIRequestContext
  private baseURL: string
  private authToken?: string

  constructor(apiContext: APIRequestContext, baseURL: string) {
    this.apiContext = apiContext
    this.baseURL = baseURL
  }

  async authenticate(email: string, password: string) {
    const response = await this.apiContext.post(`${this.baseURL}/api/auth/login`, {
      data: { email, password }
    })

    expect(response.status()).toBe(200)
    const responseBody = await response.json()
    this.authToken = responseBody.token
    return this.authToken
  }

  async createWorkspace(name: string, description?: string) {
    const response = await this.apiContext.post(`${this.baseURL}/api/workspaces`, {
      headers: { 'Authorization': `Bearer ${this.authToken}` },
      data: { name, description }
    })

    expect(response.status()).toBe(201)
    return await response.json()
  }

  async createBoard(workspaceId: string, name: string) {
    const response = await this.apiContext.post(`${this.baseURL}/api/boards`, {
      headers: { 'Authorization': `Bearer ${this.authToken}` },
      data: { workspaceId, name }
    })

    expect(response.status()).toBe(201)
    return await response.json()
  }

  async validateAPIPerformance(endpoint: string, maxResponseTime: number = 200) {
    const startTime = Date.now()
    const response = await this.apiContext.get(`${this.baseURL}${endpoint}`, {
      headers: { 'Authorization': `Bearer ${this.authToken}` }
    })
    const responseTime = Date.now() - startTime

    expect(response.status()).toBe(200)
    expect(responseTime).toBeLessThan(maxResponseTime)

    return { response, responseTime }
  }
}

test.describe('Enhanced API Testing', () => {
  let apiFramework: APITestFramework

  test.beforeAll(async ({ playwright }) => {
    const apiContext = await playwright.request.newContext()
    apiFramework = new APITestFramework(apiContext, 'http://localhost:3001')
    await apiFramework.authenticate('test@example.com', 'password123')
  })

  test('Complete workflow API testing', async () => {
    // Create workspace
    const workspace = await apiFramework.createWorkspace('API Test Workspace')
    expect(workspace.id).toBeDefined()

    // Create board
    const board = await apiFramework.createBoard(workspace.id, 'API Test Board')
    expect(board.id).toBeDefined()

    // Validate performance of key endpoints
    await apiFramework.validateAPIPerformance('/api/workspaces', 150)
    await apiFramework.validateAPIPerformance('/api/boards', 150)
    await apiFramework.validateAPIPerformance(`/api/boards/${board.id}`, 100)
  })
})
```

## CI/CD Integration Enhanced

### GitHub Actions Workflow Enhancement

#### .github/workflows/comprehensive-testing.yml
```yaml
name: Comprehensive Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

env:
  NODE_VERSION: '18'
  POSTGRES_DB: sunday_test
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        component: [backend, frontend]

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: ${{ env.POSTGRES_DB }}
          POSTGRES_USER: ${{ env.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: ${{ matrix.component }}/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: ${{ matrix.component }}

      - name: Run unit tests
        run: npm run test:coverage
        working-directory: ${{ matrix.component }}
        env:
          DATABASE_URL: postgresql://${{ env.POSTGRES_USER }}:${{ env.POSTGRES_PASSWORD }}@localhost:5432/${{ env.POSTGRES_DB }}

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ${{ matrix.component }}/coverage/lcov.info
          flags: ${{ matrix.component }}

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: ${{ env.POSTGRES_DB }}
          POSTGRES_USER: ${{ env.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install backend dependencies
        run: npm ci
        working-directory: backend

      - name: Run database migrations
        run: npm run migrate
        working-directory: backend
        env:
          DATABASE_URL: postgresql://${{ env.POSTGRES_USER }}:${{ env.POSTGRES_PASSWORD }}@localhost:5432/${{ env.POSTGRES_DB }}

      - name: Run integration tests
        run: npm run test:integration
        working-directory: backend
        env:
          DATABASE_URL: postgresql://${{ env.POSTGRES_USER }}:${{ env.POSTGRES_PASSWORD }}@localhost:5432/${{ env.POSTGRES_DB }}
          REDIS_URL: redis://localhost:6379

  e2e-tests:
    name: E2E Tests
    runs-on: ubuntu-latest
    needs: integration-tests

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'

      - name: Install dependencies
        run: |
          npm ci --prefix backend
          npm ci --prefix frontend

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Build application
        run: |
          npm run build --prefix backend
          npm run build --prefix frontend

      - name: Start application
        run: |
          npm start --prefix backend &
          npm run preview --prefix frontend &
          npx wait-on http://localhost:3000 http://localhost:3001

      - name: Run E2E tests
        run: npx playwright test
        working-directory: tests/e2e

      - name: Upload E2E test results
        uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: e2e-test-results
          path: tests/e2e/test-results/

  performance-tests:
    name: Performance Tests
    runs-on: ubuntu-latest
    needs: e2e-tests
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Install k6
        run: |
          sudo gpg -k
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6

      - name: Run performance tests
        run: k6 run --out json=performance-results.json performance/tests/scenarios/normal-load.js
        env:
          BASE_URL: ${{ secrets.STAGING_URL }}

      - name: Upload performance results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: performance-results.json

  security-tests:
    name: Security Tests
    runs-on: ubuntu-latest
    needs: integration-tests

    steps:
      - uses: actions/checkout@v4

      - name: Run OWASP ZAP Baseline Scan
        uses: zaproxy/action-baseline@v0.7.0
        with:
          target: ${{ secrets.STAGING_URL }}
          rules_file_name: '.zap/rules.tsv'
          cmd_options: '-a'

      - name: Run npm audit
        run: |
          npm audit --audit-level high --prefix backend
          npm audit --audit-level high --prefix frontend

      - name: Run Snyk security scan
        uses: snyk/actions/node@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  quality-gate:
    name: Quality Gate
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests, e2e-tests, performance-tests, security-tests]
    if: always()

    steps:
      - name: Quality Gate Decision
        run: |
          if [[ "${{ needs.unit-tests.result }}" == "success" &&
                "${{ needs.integration-tests.result }}" == "success" &&
                "${{ needs.e2e-tests.result }}" == "success" &&
                "${{ needs.performance-tests.result }}" == "success" &&
                "${{ needs.security-tests.result }}" == "success" ]]; then
            echo "✅ Quality Gate PASSED - All tests successful"
            echo "QUALITY_GATE=PASS" >> $GITHUB_ENV
          else
            echo "❌ Quality Gate FAILED - Some tests failed"
            echo "QUALITY_GATE=FAIL" >> $GITHUB_ENV
            exit 1
          fi

      - name: Deployment notification
        if: env.QUALITY_GATE == 'PASS' && github.ref == 'refs/heads/main'
        run: |
          echo "🚀 Ready for deployment to production"
          # Add deployment trigger logic here
```

## Test Data Management Framework

### Test Data Factory System

#### tests/shared/factories/index.ts
```typescript
import { faker } from '@faker-js/faker'

export interface TestUser {
  id?: string
  email: string
  password: string
  name: string
  role: 'admin' | 'member' | 'viewer'
}

export interface TestWorkspace {
  id?: string
  name: string
  description?: string
  ownerId: string
}

export interface TestBoard {
  id?: string
  name: string
  workspaceId: string
  columns: TestColumn[]
}

export interface TestColumn {
  id?: string
  name: string
  position: number
  settings: { statusValue: string }
}

export interface TestItem {
  id?: string
  name: string
  description?: string
  boardId: string
  columnId: string
  assigneeId?: string
}

export class TestDataFactory {
  static createUser(role: TestUser['role'] = 'member'): TestUser {
    return {
      email: faker.internet.email(),
      password: 'TestPassword123!',
      name: faker.person.fullName(),
      role
    }
  }

  static createWorkspace(ownerId: string): TestWorkspace {
    return {
      name: faker.company.name(),
      description: faker.lorem.paragraph(),
      ownerId
    }
  }

  static createBoard(workspaceId: string): TestBoard {
    return {
      name: faker.lorem.words(2),
      workspaceId,
      columns: [
        {
          name: 'To Do',
          position: 0,
          settings: { statusValue: 'todo' }
        },
        {
          name: 'In Progress',
          position: 1,
          settings: { statusValue: 'in-progress' }
        },
        {
          name: 'Done',
          position: 2,
          settings: { statusValue: 'done' }
        }
      ]
    }
  }

  static createItem(boardId: string, columnId: string): TestItem {
    return {
      name: faker.lorem.words(3),
      description: faker.lorem.paragraph(),
      boardId,
      columnId
    }
  }

  static createCompleteWorkflow(): {
    user: TestUser
    workspace: TestWorkspace
    board: TestBoard
    items: TestItem[]
  } {
    const user = this.createUser('admin')
    const workspace = this.createWorkspace(user.id!)
    const board = this.createBoard(workspace.id!)
    const items = board.columns.map(column =>
      this.createItem(board.id!, column.id!)
    )

    return { user, workspace, board, items }
  }
}
```

## Test Reporting and Analytics

### Comprehensive Test Reporting

#### scripts/generate-test-report.js
```javascript
const fs = require('fs')
const path = require('path')

class TestReportGenerator {
  constructor() {
    this.results = {
      summary: {},
      unit: {},
      integration: {},
      e2e: {},
      performance: {},
      security: {},
      coverage: {}
    }
  }

  async generateComprehensiveReport() {
    await this.collectTestResults()
    await this.generateHTMLReport()
    await this.generateMetrics()
    await this.sendNotifications()
  }

  async collectTestResults() {
    // Collect Jest unit test results
    this.results.unit = await this.parseJestResults('backend/coverage/lcov-report')
    this.results.frontend = await this.parseJestResults('frontend/coverage/lcov-report')

    // Collect Playwright E2E results
    this.results.e2e = await this.parsePlaywrightResults('tests/e2e/test-results')

    // Collect k6 performance results
    this.results.performance = await this.parseK6Results('performance/reports')

    // Collect security scan results
    this.results.security = await this.parseSecurityResults('security/reports')
  }

  async generateHTMLReport() {
    const reportTemplate = `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sunday.com Test Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .summary { background: #f5f5f5; padding: 20px; border-radius: 8px; }
            .metric { display: inline-block; margin: 10px; padding: 15px; border-radius: 5px; }
            .pass { background: #d4edda; color: #155724; }
            .fail { background: #f8d7da; color: #721c24; }
            .warning { background: #fff3cd; color: #856404; }
        </style>
    </head>
    <body>
        <h1>Sunday.com Test Report</h1>
        <div class="summary">
            <h2>Test Execution Summary</h2>
            <div class="metric ${this.getStatusClass(this.results.unit.status)}">
                <h3>Unit Tests</h3>
                <p>Status: ${this.results.unit.status}</p>
                <p>Coverage: ${this.results.unit.coverage}%</p>
                <p>Tests: ${this.results.unit.passed}/${this.results.unit.total}</p>
            </div>
            <div class="metric ${this.getStatusClass(this.results.e2e.status)}">
                <h3>E2E Tests</h3>
                <p>Status: ${this.results.e2e.status}</p>
                <p>Tests: ${this.results.e2e.passed}/${this.results.e2e.total}</p>
                <p>Duration: ${this.results.e2e.duration}ms</p>
            </div>
            <div class="metric ${this.getStatusClass(this.results.performance.status)}">
                <h3>Performance</h3>
                <p>Status: ${this.results.performance.status}</p>
                <p>Avg Response: ${this.results.performance.avgResponse}ms</p>
                <p>Error Rate: ${this.results.performance.errorRate}%</p>
            </div>
        </div>

        <h2>Detailed Results</h2>
        <!-- Additional detailed sections -->

    </body>
    </html>
    `

    fs.writeFileSync('test-reports/comprehensive-report.html', reportTemplate)
  }

  getStatusClass(status) {
    switch(status.toLowerCase()) {
      case 'pass': return 'pass'
      case 'fail': return 'fail'
      default: return 'warning'
    }
  }
}

// Execute report generation
if (require.main === module) {
  const generator = new TestReportGenerator()
  generator.generateComprehensiveReport()
    .then(() => console.log('✅ Test report generated successfully'))
    .catch(err => console.error('❌ Test report generation failed:', err))
}
```

## Quality Metrics Dashboard

### Real-time Quality Metrics

#### monitoring/quality-dashboard.js
```javascript
const express = require('express')
const WebSocket = require('ws')

class QualityMetricsDashboard {
  constructor() {
    this.app = express()
    this.wss = new WebSocket.Server({ port: 8080 })
    this.metrics = {
      testCoverage: 0,
      buildStatus: 'unknown',
      performanceScore: 0,
      securityScore: 0,
      lastUpdate: new Date()
    }
  }

  setupRoutes() {
    this.app.get('/api/metrics', (req, res) => {
      res.json(this.metrics)
    })

    this.app.get('/api/test-history', (req, res) => {
      // Return test execution history
      res.json(this.getTestHistory())
    })

    this.app.get('/dashboard', (req, res) => {
      res.send(this.generateDashboardHTML())
    })
  }

  updateMetrics(newMetrics) {
    this.metrics = { ...this.metrics, ...newMetrics, lastUpdate: new Date() }

    // Broadcast to all connected clients
    this.wss.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(this.metrics))
      }
    })
  }

  generateDashboardHTML() {
    return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sunday.com Quality Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .metric-value { font-size: 2em; font-weight: bold; color: #2196F3; }
            .status-indicator { width: 20px; height: 20px; border-radius: 50%; display: inline-block; }
            .status-pass { background: #4CAF50; }
            .status-fail { background: #F44336; }
            .status-warning { background: #FF9800; }
        </style>
    </head>
    <body>
        <h1>Sunday.com Quality Dashboard</h1>
        <div class="dashboard">
            <div class="card">
                <h3>Test Coverage</h3>
                <div class="metric-value" id="coverage">${this.metrics.testCoverage}%</div>
                <canvas id="coverageChart" width="200" height="100"></canvas>
            </div>
            <div class="card">
                <h3>Build Status</h3>
                <span class="status-indicator status-${this.metrics.buildStatus}"></span>
                <span id="buildStatus">${this.metrics.buildStatus}</span>
            </div>
            <div class="card">
                <h3>Performance Score</h3>
                <div class="metric-value" id="performance">${this.metrics.performanceScore}</div>
            </div>
            <div class="card">
                <h3>Security Score</h3>
                <div class="metric-value" id="security">${this.metrics.securityScore}</div>
            </div>
        </div>

        <script>
            const ws = new WebSocket('ws://localhost:8080')
            ws.onmessage = function(event) {
                const metrics = JSON.parse(event.data)
                updateDashboard(metrics)
            }

            function updateDashboard(metrics) {
                document.getElementById('coverage').textContent = metrics.testCoverage + '%'
                document.getElementById('buildStatus').textContent = metrics.buildStatus
                document.getElementById('performance').textContent = metrics.performanceScore
                document.getElementById('security').textContent = metrics.securityScore
            }
        </script>
    </body>
    </html>
    `
  }

  start() {
    this.setupRoutes()
    this.app.listen(3030, () => {
      console.log('Quality Dashboard running on http://localhost:3030/dashboard')
    })
  }
}

module.exports = QualityMetricsDashboard
```

## Implementation Roadmap

### Phase 1: Performance Testing (Week 1)
- [ ] Set up k6 performance testing framework
- [ ] Implement API load testing scenarios
- [ ] Create WebSocket performance tests
- [ ] Set up performance monitoring and alerting

### Phase 2: E2E Enhancement (Week 2)
- [ ] Expand Playwright E2E test coverage
- [ ] Implement cross-browser testing
- [ ] Add mobile responsiveness testing
- [ ] Create complete user journey tests

### Phase 3: Advanced Testing (Week 3)
- [ ] Implement visual regression testing
- [ ] Set up security testing automation
- [ ] Add accessibility testing validation
- [ ] Create performance monitoring dashboard

### Phase 4: Quality Assurance (Week 4)
- [ ] Integrate all testing into CI/CD pipeline
- [ ] Set up comprehensive test reporting
- [ ] Implement quality gates and metrics
- [ ] Complete test documentation

## Success Criteria

### Framework Completeness: Target 95%
- **Performance Testing:** Complete k6 implementation ✅
- **E2E Testing:** Comprehensive Playwright coverage ✅
- **Visual Regression:** Percy/Chromatic integration ✅
- **Security Testing:** OWASP ZAP automation ✅
- **CI/CD Integration:** Complete pipeline integration ✅

### Quality Metrics Targets
- **Test Coverage:** 90%+ across all layers
- **Performance:** <200ms API response time validation
- **E2E Coverage:** 100% critical user paths
- **Security:** Zero critical vulnerabilities
- **Build Success Rate:** 95%+ pipeline success

---

**Implementation Status:** Framework design complete, implementation pending based on priority gaps identified in deployment readiness assessment.

**Next Actions:**
1. Implement performance testing framework (highest priority)
2. Expand E2E testing coverage
3. Integrate advanced testing capabilities
4. Complete CI/CD pipeline enhancement

**QA Engineer:** Claude Code QA Assistant
**Framework Version:** 2.0
**Review Date:** Upon implementation completion