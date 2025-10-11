import { check } from 'k6';

// Environment configuration
export const config = {
  // Base URLs
  API_BASE_URL: __ENV.API_BASE_URL || 'http://localhost:4000',
  FRONTEND_BASE_URL: __ENV.FRONTEND_BASE_URL || 'http://localhost:3000',

  // Database connection
  DATABASE_URL: __ENV.TEST_DATABASE_URL || 'postgresql://test:test@localhost:5432/sunday_test',

  // Test users
  TEST_USERS: {
    ADMIN: {
      email: 'admin@test.com',
      password: 'password123'
    },
    MANAGER: {
      email: 'manager@test.com',
      password: 'password123'
    },
    MEMBER: {
      email: 'member@test.com',
      password: 'password123'
    }
  },

  // Performance thresholds
  THRESHOLDS: {
    // HTTP request duration should be < 200ms for 95% of requests
    http_req_duration: ['p(95)<200'],

    // HTTP request duration should be < 500ms for 99% of requests
    'http_req_duration{expected_response:true}': ['p(99)<500'],

    // Error rate should be < 1%
    http_req_failed: ['rate<0.01'],

    // Check success rate should be > 99%
    checks: ['rate>0.99'],

    // Iteration duration for complete user journey
    iteration_duration: ['p(95)<2000'],
  },

  // Load test scenarios
  SCENARIOS: {
    LOAD_TEST: {
      executor: 'ramping-vus',
      stages: [
        { duration: '2m', target: 20 },  // Ramp up to 20 users
        { duration: '5m', target: 20 },  // Stay at 20 users
        { duration: '2m', target: 50 },  // Ramp up to 50 users
        { duration: '5m', target: 50 },  // Stay at 50 users
        { duration: '2m', target: 0 },   // Ramp down
      ],
    },

    STRESS_TEST: {
      executor: 'ramping-vus',
      stages: [
        { duration: '2m', target: 100 },  // Ramp up to 100 users
        { duration: '5m', target: 100 },  // Stay at 100 users
        { duration: '2m', target: 200 },  // Ramp up to 200 users
        { duration: '5m', target: 200 },  // Stay at 200 users
        { duration: '2m', target: 300 },  // Ramp up to 300 users
        { duration: '5m', target: 300 },  // Stay at 300 users
        { duration: '2m', target: 0 },    // Ramp down
      ],
    },

    SPIKE_TEST: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 50 },   // Normal load
        { duration: '1m', target: 500 },   // Spike
        { duration: '30s', target: 50 },   // Back to normal
        { duration: '1m', target: 1000 },  // Bigger spike
        { duration: '30s', target: 50 },   // Back to normal
      ],
    },

    ENDURANCE_TEST: {
      executor: 'constant-vus',
      vus: 50,
      duration: '30m',
    },
  },

  // API endpoints for testing
  ENDPOINTS: {
    AUTH: {
      LOGIN: '/api/auth/login',
      LOGOUT: '/api/auth/logout',
      REFRESH: '/api/auth/refresh',
      ME: '/api/auth/me',
    },
    ORGANIZATIONS: {
      LIST: '/api/organizations',
      CREATE: '/api/organizations',
      GET: '/api/organizations/{id}',
      UPDATE: '/api/organizations/{id}',
      DELETE: '/api/organizations/{id}',
    },
    WORKSPACES: {
      LIST: '/api/organizations/{orgId}/workspaces',
      CREATE: '/api/organizations/{orgId}/workspaces',
      GET: '/api/workspaces/{id}',
      UPDATE: '/api/workspaces/{id}',
    },
    BOARDS: {
      LIST: '/api/workspaces/{workspaceId}/boards',
      CREATE: '/api/workspaces/{workspaceId}/boards',
      GET: '/api/boards/{id}',
      UPDATE: '/api/boards/{id}',
    },
    ITEMS: {
      LIST: '/api/boards/{boardId}/items',
      CREATE: '/api/boards/{boardId}/items',
      GET: '/api/items/{id}',
      UPDATE: '/api/items/{id}',
      DELETE: '/api/items/{id}',
    },
    ANALYTICS: {
      BOARD: '/api/boards/{id}/analytics',
      ORGANIZATION: '/api/organizations/{id}/analytics',
    },
  },
};

// Common headers
export const commonHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'User-Agent': 'k6-performance-test/1.0',
};

// Standard checks for API responses
export function checkApiResponse(response, expectedStatus = 200, responseName = 'API response') {
  return check(response, {
    [`${responseName} status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
    [`${responseName} has success field`]: (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.hasOwnProperty('success');
      } catch {
        return false;
      }
    },
    [`${responseName} has data field on success`]: (r) => {
      try {
        const body = JSON.parse(r.body);
        return r.status >= 200 && r.status < 300 ? body.hasOwnProperty('data') : true;
      } catch {
        return false;
      }
    },
    [`${responseName} response time < 1s`]: (r) => r.timings.duration < 1000,
  });
}

// Standard checks for HTML responses
export function checkHtmlResponse(response, expectedTitle = null) {
  const checks = {
    'HTML response status is 200': (r) => r.status === 200,
    'HTML response has content': (r) => r.body && r.body.length > 0,
    'HTML response is HTML': (r) => r.headers['Content-Type'] && r.headers['Content-Type'].includes('text/html'),
    'HTML response time < 2s': (r) => r.timings.duration < 2000,
  };

  if (expectedTitle) {
    checks[`HTML contains expected title: ${expectedTitle}`] = (r) =>
      r.body && r.body.includes(`<title>${expectedTitle}</title>`);
  }

  return check(response, checks);
}

// Authentication helper
export function authenticate(http, user = config.TEST_USERS.ADMIN) {
  const loginResponse = http.post(
    `${config.API_BASE_URL}${config.ENDPOINTS.AUTH.LOGIN}`,
    JSON.stringify({
      email: user.email,
      password: user.password,
    }),
    {
      headers: commonHeaders,
    }
  );

  if (!checkApiResponse(loginResponse, 200, 'Login')) {
    throw new Error(`Authentication failed: ${loginResponse.status} ${loginResponse.body}`);
  }

  const loginData = JSON.parse(loginResponse.body);
  return {
    accessToken: loginData.data.tokens.accessToken,
    refreshToken: loginData.data.tokens.refreshToken,
    user: loginData.data.user,
  };
}

// Authenticated headers helper
export function getAuthHeaders(accessToken) {
  return {
    ...commonHeaders,
    'Authorization': `Bearer ${accessToken}`,
  };
}

// Random data generators
export function randomString(length = 10) {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let result = '';
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

export function randomEmail() {
  return `test-${randomString(8)}@example.com`;
}

export function randomTaskName() {
  const prefixes = ['Implement', 'Fix', 'Update', 'Create', 'Review', 'Test', 'Deploy'];
  const subjects = ['user interface', 'authentication', 'database', 'API endpoint', 'dashboard', 'reports'];

  return `${prefixes[Math.floor(Math.random() * prefixes.length)]} ${subjects[Math.floor(Math.random() * subjects.length)]}`;
}

export function randomStatus() {
  const statuses = ['not_started', 'in_progress', 'review', 'completed'];
  return statuses[Math.floor(Math.random() * statuses.length)];
}

export function randomPriority() {
  const priorities = ['low', 'medium', 'high', 'critical'];
  return priorities[Math.floor(Math.random() * priorities.length)];
}

// Weighted selection helper
export function weightedChoice(choices) {
  const totalWeight = choices.reduce((sum, choice) => sum + choice.weight, 0);
  let random = Math.random() * totalWeight;

  for (const choice of choices) {
    random -= choice.weight;
    if (random <= 0) {
      return choice.value;
    }
  }

  return choices[choices.length - 1].value;
}

// Sleep helper with jitter
export function sleep(min = 1, max = 3) {
  const duration = Math.random() * (max - min) + min;
  return duration;
}

// Performance metrics helpers
export function recordCustomMetric(name, value, tags = {}) {
  // k6 custom metrics would be imported and used here
  console.log(`Custom metric ${name}: ${value}`, tags);
}

export function measureOperation(operation, metricName, tags = {}) {
  const start = Date.now();
  const result = operation();
  const duration = Date.now() - start;

  recordCustomMetric(metricName, duration, tags);
  return result;
}

// URL parameter replacement helper
export function replaceUrlParams(url, params) {
  let result = url;
  for (const [key, value] of Object.entries(params)) {
    result = result.replace(`{${key}}`, value);
  }
  return result;
}

// Test data structures
export const testData = {
  organizations: [
    { name: 'Acme Corporation', slug: 'acme-corp' },
    { name: 'Tech Startup Inc', slug: 'tech-startup' },
    { name: 'Creative Agency', slug: 'creative-agency' },
  ],

  workspaces: [
    { name: 'Product Development' },
    { name: 'Marketing Campaigns' },
    { name: 'Customer Support' },
  ],

  boards: [
    { name: 'Sprint Planning', template: 'scrum' },
    { name: 'Bug Tracking', template: 'bug_tracking' },
    { name: 'Feature Requests', template: 'feature_requests' },
  ],

  items: [
    { name: 'User Authentication System', priority: 'high' },
    { name: 'Dashboard UI Components', priority: 'medium' },
    { name: 'API Documentation', priority: 'low' },
  ],
};

export default config;