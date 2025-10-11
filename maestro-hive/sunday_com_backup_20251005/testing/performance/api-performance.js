import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
export const errorRate = new Rate('errors');
export const responseTime = new Trend('response_time');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '3m', target: 200 },  // Ramp up to 200 users
    { duration: '5m', target: 200 },  // Stay at 200 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    errors: ['rate<0.1'],           // Error rate should be less than 10%
    response_time: ['p(95)<200'],   // 95% of requests should be below 200ms
    http_req_duration: ['p(95)<500'], // 95% of requests should complete within 500ms
  },
};

// Test configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000/api';
const USERS = [
  { email: 'test1@example.com', password: 'TestPassword123!' },
  { email: 'test2@example.com', password: 'TestPassword123!' },
  { email: 'test3@example.com', password: 'TestPassword123!' },
];

// Test data
let authToken = '';
let workspaceId = '';
let boardId = '';

export function setup() {
  // Setup test data
  console.log('Setting up performance test...');

  // Create test user and get auth token
  const loginResponse = http.post(`${BASE_URL}/auth/login`, JSON.stringify({
    email: USERS[0].email,
    password: USERS[0].password,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginResponse.status === 200) {
    const loginData = JSON.parse(loginResponse.body);
    authToken = loginData.token;
  }

  return { authToken };
}

export default function (data) {
  const token = data.authToken || '';
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  // Test scenario: API Performance Testing
  const scenario = Math.random();

  if (scenario < 0.3) {
    // 30% - Authentication tests
    testAuthentication();
  } else if (scenario < 0.6) {
    // 30% - Board operations
    testBoardOperations(headers);
  } else if (scenario < 0.9) {
    // 30% - Item operations
    testItemOperations(headers);
  } else {
    // 10% - File operations
    testFileOperations(headers);
  }

  sleep(1); // Think time between requests
}

function testAuthentication() {
  const user = USERS[Math.floor(Math.random() * USERS.length)];

  const response = http.post(`${BASE_URL}/auth/login`, JSON.stringify(user), {
    headers: { 'Content-Type': 'application/json' },
  });

  const success = check(response, {
    'login status is 200': (r) => r.status === 200,
    'login response time < 200ms': (r) => r.timings.duration < 200,
    'login returns token': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.token !== undefined;
      } catch {
        return false;
      }
    },
  });

  errorRate.add(!success);
  responseTime.add(response.timings.duration);
}

function testBoardOperations(headers) {
  // Get boards list
  const boardsResponse = http.get(`${BASE_URL}/boards`, { headers });

  const success = check(boardsResponse, {
    'boards list status is 200': (r) => r.status === 200,
    'boards response time < 200ms': (r) => r.timings.duration < 200,
    'boards returns array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body);
      } catch {
        return false;
      }
    },
  });

  if (success && boardsResponse.status === 200) {
    const boards = JSON.parse(boardsResponse.body);

    if (boards.length > 0) {
      // Get board details
      const boardId = boards[0].id;
      const boardResponse = http.get(`${BASE_URL}/boards/${boardId}`, { headers });

      check(boardResponse, {
        'board details status is 200': (r) => r.status === 200,
        'board details response time < 200ms': (r) => r.timings.duration < 200,
      });

      responseTime.add(boardResponse.timings.duration);
    }
  }

  errorRate.add(!success);
  responseTime.add(boardsResponse.timings.duration);
}

function testItemOperations(headers) {
  // Create item test data
  const itemData = {
    name: `Performance Test Item ${Math.random()}`,
    description: 'Generated for performance testing',
    status: 'todo',
    priority: 'medium',
  };

  // Create item
  const createResponse = http.post(`${BASE_URL}/items`, JSON.stringify(itemData), { headers });

  const createSuccess = check(createResponse, {
    'item creation status is 200 or 201': (r) => r.status >= 200 && r.status < 300,
    'item creation response time < 300ms': (r) => r.timings.duration < 300,
  });

  if (createSuccess && createResponse.status < 300) {
    try {
      const createdItem = JSON.parse(createResponse.body);
      const itemId = createdItem.id;

      // Update item
      const updateData = { status: 'in_progress' };
      const updateResponse = http.put(`${BASE_URL}/items/${itemId}`, JSON.stringify(updateData), { headers });

      check(updateResponse, {
        'item update status is 200': (r) => r.status === 200,
        'item update response time < 200ms': (r) => r.timings.duration < 200,
      });

      responseTime.add(updateResponse.timings.duration);

      // Get item
      const getResponse = http.get(`${BASE_URL}/items/${itemId}`, { headers });

      check(getResponse, {
        'item get status is 200': (r) => r.status === 200,
        'item get response time < 100ms': (r) => r.timings.duration < 100,
      });

      responseTime.add(getResponse.timings.duration);
    } catch (e) {
      console.error('Error parsing item response:', e);
    }
  }

  errorRate.add(!createSuccess);
  responseTime.add(createResponse.timings.duration);
}

function testFileOperations(headers) {
  // Simulate file upload (without actual file for performance testing)
  const fileData = {
    filename: `test-file-${Math.random()}.txt`,
    size: Math.floor(Math.random() * 1000000), // Random size up to 1MB
    mimeType: 'text/plain',
  };

  const response = http.post(`${BASE_URL}/files/upload`, JSON.stringify(fileData), { headers });

  const success = check(response, {
    'file upload status is acceptable': (r) => r.status >= 200 && r.status < 400,
    'file upload response time < 1000ms': (r) => r.timings.duration < 1000,
  });

  errorRate.add(!success);
  responseTime.add(response.timings.duration);
}

export function teardown(data) {
  console.log('Performance test completed');
  console.log(`Auth token used: ${data.authToken ? 'Yes' : 'No'}`);
}

// Additional test scenarios for specific performance concerns
export function handleSummary(data) {
  return {
    'performance-summary.json': JSON.stringify(data, null, 2),
    'performance-report.html': generateHTMLReport(data),
  };
}

function generateHTMLReport(data) {
  const metrics = data.metrics;

  return `
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sunday.com API Performance Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .metric { margin: 10px 0; padding: 10px; border: 1px solid #ddd; }
            .pass { background-color: #d4edda; }
            .fail { background-color: #f8d7da; }
            .summary { font-size: 1.2em; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>Sunday.com API Performance Test Report</h1>

        <div class="summary">
            <h2>Summary</h2>
            <p>Test Duration: ${data.state.testRunDuration}ms</p>
            <p>Total Requests: ${metrics.http_reqs.count}</p>
            <p>Failed Requests: ${metrics.http_req_failed.count}</p>
            <p>Average Response Time: ${metrics.http_req_duration.avg.toFixed(2)}ms</p>
        </div>

        <div class="metric ${metrics.http_req_duration.p95 < 200 ? 'pass' : 'fail'}">
            <h3>Response Time (95th percentile)</h3>
            <p>Target: < 200ms</p>
            <p>Actual: ${metrics.http_req_duration.p95.toFixed(2)}ms</p>
        </div>

        <div class="metric ${(metrics.http_req_failed.rate * 100) < 10 ? 'pass' : 'fail'}">
            <h3>Error Rate</h3>
            <p>Target: < 10%</p>
            <p>Actual: ${(metrics.http_req_failed.rate * 100).toFixed(2)}%</p>
        </div>

        <div class="metric">
            <h3>Detailed Metrics</h3>
            <pre>${JSON.stringify(metrics, null, 2)}</pre>
        </div>
    </body>
    </html>
  `;
}