/**
 * Performance Load Tests - Sunday.com
 * Using k6 for comprehensive load testing
 *
 * Run with: k6 run load-tests.js
 *
 * Test scenarios:
 * 1. API endpoint performance
 * 2. WebSocket connection handling
 * 3. Concurrent user simulation
 * 4. Database stress testing
 */

import http from 'k6/http';
import ws from 'k6/ws';
import { check, sleep, group } from 'k6';
import { Counter, Rate, Trend, Gauge } from 'k6/metrics';

// Custom metrics
const apiResponseTime = new Trend('api_response_time');
const websocketConnectionTime = new Trend('websocket_connection_time');
const errorRate = new Rate('error_rate');
const activeUsers = new Gauge('active_users');

// Test configuration
export const options = {
  stages: [
    // Gradual ramp-up
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Ramp up to 200 users
    { duration: '5m', target: 200 },  // Stay at 200 users
    { duration: '2m', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    // API performance requirements
    'http_req_duration': ['p(95)<200'],        // 95% of requests under 200ms
    'http_req_duration{group:::API}': ['p(90)<150'], // API calls under 150ms

    // Error rate thresholds
    'error_rate': ['rate<0.05'],               // Less than 5% errors
    'http_req_failed': ['rate<0.02'],          // Less than 2% HTTP failures

    // WebSocket performance
    'websocket_connection_time': ['p(95)<500'], // WebSocket connection under 500ms

    // Custom metrics
    'api_response_time': ['p(95)<200'],
  },
};

// Test data
const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const WS_URL = __ENV.WS_URL || 'ws://localhost:3000';

// Test users (in real scenario, these would be pre-created)
const testUsers = [
  { email: 'load-test-user-1@example.com', password: 'TestPassword123!' },
  { email: 'load-test-user-2@example.com', password: 'TestPassword123!' },
  { email: 'load-test-user-3@example.com', password: 'TestPassword123!' },
  // Add more users as needed
];

// Authentication helper
function authenticate(userIndex) {
  const user = testUsers[userIndex % testUsers.length];

  const loginResponse = http.post(`${BASE_URL}/api/auth/login`, JSON.stringify({
    email: user.email,
    password: user.password
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(loginResponse, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => JSON.parse(r.body).tokens.accessToken !== undefined,
  });

  if (loginResponse.status === 200) {
    return JSON.parse(loginResponse.body).tokens.accessToken;
  }

  errorRate.add(1);
  return null;
}

// Main test function
export default function () {
  activeUsers.add(1);

  const userIndex = Math.floor(Math.random() * testUsers.length);
  const authToken = authenticate(userIndex);

  if (!authToken) {
    sleep(1);
    return;
  }

  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${authToken}`,
  };

  // Test different user behaviors
  const scenarios = [
    'heavy_api_user',     // 40% - Heavy API usage
    'board_manager',      // 30% - Board management focus
    'collaborative_user', // 20% - Real-time collaboration
    'casual_user'         // 10% - Light usage
  ];

  const scenario = scenarios[Math.floor(Math.random() * 100) < 40 ? 0 :
                           Math.floor(Math.random() * 100) < 70 ? 1 :
                           Math.floor(Math.random() * 100) < 90 ? 2 : 3];

  switch (scenario) {
    case 'heavy_api_user':
      heavyApiUserScenario(authHeaders);
      break;
    case 'board_manager':
      boardManagerScenario(authHeaders);
      break;
    case 'collaborative_user':
      collaborativeUserScenario(authHeaders);
      break;
    case 'casual_user':
      casualUserScenario(authHeaders);
      break;
  }

  sleep(Math.random() * 3 + 1); // Random sleep 1-4 seconds
}

// Scenario 1: Heavy API User (40% of users)
function heavyApiUserScenario(headers) {
  group('Heavy API User Workflow', () => {
    // Fetch user workspaces
    group('Get Workspaces', () => {
      const start = Date.now();
      const response = http.get(`${BASE_URL}/api/workspaces`, { headers });
      const duration = Date.now() - start;

      apiResponseTime.add(duration);

      check(response, {
        'workspaces loaded': (r) => r.status === 200,
        'response time < 200ms': (r) => duration < 200,
      });

      if (response.status !== 200) {
        errorRate.add(1);
        return;
      }
    });

    // Fetch boards for each workspace
    group('Get Boards', () => {
      for (let i = 0; i < 3; i++) { // Simulate checking 3 boards
        const start = Date.now();
        const response = http.get(`${BASE_URL}/api/boards?limit=10&offset=${i * 10}`, { headers });
        const duration = Date.now() - start;

        apiResponseTime.add(duration);

        check(response, {
          'boards loaded': (r) => r.status === 200,
          'response time < 150ms': (r) => duration < 150,
        });

        if (response.status !== 200) {
          errorRate.add(1);
        }

        sleep(0.1);
      }
    });

    // Fetch items for boards
    group('Get Items', () => {
      for (let i = 0; i < 5; i++) { // Simulate checking 5 sets of items
        const start = Date.now();
        const response = http.get(`${BASE_URL}/api/items?limit=20&offset=${i * 20}`, { headers });
        const duration = Date.now() - start;

        apiResponseTime.add(duration);

        check(response, {
          'items loaded': (r) => r.status === 200,
          'response time < 100ms': (r) => duration < 100,
        });

        sleep(0.05);
      }
    });
  });
}

// Scenario 2: Board Manager (30% of users)
function boardManagerScenario(headers) {
  group('Board Manager Workflow', () => {
    let boardId;

    // Create new board
    group('Create Board', () => {
      const boardData = {
        name: `Load Test Board ${Date.now()}`,
        description: 'Created during load testing',
        type: 'kanban',
        workspaceId: 'workspace-1' // Assume workspace exists
      };

      const start = Date.now();
      const response = http.post(`${BASE_URL}/api/boards`, JSON.stringify(boardData), { headers });
      const duration = Date.now() - start;

      apiResponseTime.add(duration);

      check(response, {
        'board created': (r) => r.status === 201,
        'creation time < 300ms': (r) => duration < 300,
      });

      if (response.status === 201) {
        boardId = JSON.parse(response.body).id;
      } else {
        errorRate.add(1);
        return;
      }
    });

    // Create multiple items on board
    group('Create Items', () => {
      for (let i = 0; i < 10; i++) {
        const itemData = {
          name: `Load Test Item ${i}`,
          description: `Item created during load test`,
          status: ['todo', 'in_progress', 'done'][i % 3],
          priority: ['low', 'medium', 'high'][i % 3],
          boardId: boardId
        };

        const start = Date.now();
        const response = http.post(`${BASE_URL}/api/items`, JSON.stringify(itemData), { headers });
        const duration = Date.now() - start;

        apiResponseTime.add(duration);

        check(response, {
          'item created': (r) => r.status === 201,
          'creation time < 200ms': (r) => duration < 200,
        });

        if (response.status !== 201) {
          errorRate.add(1);
        }

        sleep(0.1);
      }
    });

    // Update board settings
    group('Update Board', () => {
      const updateData = {
        name: `Updated Load Test Board ${Date.now()}`,
        description: 'Updated during load testing'
      };

      const start = Date.now();
      const response = http.put(`${BASE_URL}/api/boards/${boardId}`, JSON.stringify(updateData), { headers });
      const duration = Date.now() - start;

      apiResponseTime.add(duration);

      check(response, {
        'board updated': (r) => r.status === 200,
        'update time < 200ms': (r) => duration < 200,
      });
    });
  });
}

// Scenario 3: Collaborative User (20% of users)
function collaborativeUserScenario(headers) {
  group('Collaborative User Workflow', () => {
    // Test WebSocket connection
    group('WebSocket Connection', () => {
      const start = Date.now();

      const response = ws.connect(`${WS_URL}/ws`, {
        headers: {
          'Authorization': headers.Authorization
        }
      }, function (socket) {
        socket.on('open', () => {
          const connectionTime = Date.now() - start;
          websocketConnectionTime.add(connectionTime);

          // Send presence update
          socket.send(JSON.stringify({
            type: 'presence',
            data: { status: 'active', boardId: 'board-1' }
          }));

          // Simulate real-time collaboration
          for (let i = 0; i < 5; i++) {
            socket.send(JSON.stringify({
              type: 'item_update',
              data: {
                itemId: `item-${i}`,
                status: 'in_progress',
                timestamp: Date.now()
              }
            }));

            sleep(0.5);
          }
        });

        socket.on('message', (data) => {
          const message = JSON.parse(data);
          check(message, {
            'valid message format': (m) => m.type !== undefined,
            'has timestamp': (m) => m.timestamp !== undefined,
          });
        });

        socket.on('error', (e) => {
          console.log('WebSocket error:', e.error());
          errorRate.add(1);
        });

        // Keep connection open for 10 seconds
        sleep(10);
      });

      check(response, {
        'websocket connected': (r) => r && r.url != '',
      });
    });

    // Also perform some API calls while connected
    group('Concurrent API Calls', () => {
      const responses = http.batch([
        ['GET', `${BASE_URL}/api/boards/board-1`, null, { headers }],
        ['GET', `${BASE_URL}/api/items?boardId=board-1`, null, { headers }],
        ['GET', `${BASE_URL}/api/comments?itemId=item-1`, null, { headers }],
      ]);

      responses.forEach((response, index) => {
        check(response, {
          [`batch request ${index} successful`]: (r) => r.status === 200,
        });
      });
    });
  });
}

// Scenario 4: Casual User (10% of users)
function casualUserScenario(headers) {
  group('Casual User Workflow', () => {
    // Light browsing
    group('Browse Dashboard', () => {
      const response = http.get(`${BASE_URL}/api/dashboard/stats`, { headers });

      check(response, {
        'dashboard loaded': (r) => r.status === 200,
      });

      sleep(2); // Casual users read content
    });

    // Check a few items
    group('Check Items', () => {
      const response = http.get(`${BASE_URL}/api/items?limit=5`, { headers });

      check(response, {
        'items loaded': (r) => r.status === 200,
      });

      sleep(1);
    });

    // Light interaction
    group('Light Interaction', () => {
      // View single item details
      const response = http.get(`${BASE_URL}/api/items/item-1`, { headers });

      check(response, {
        'item details loaded': (r) => r.status === 200,
      });

      sleep(3); // Read item details
    });
  });
}

// Stress testing stages
export function handleSummary(data) {
  return {
    'load-test-summary.json': JSON.stringify(data, null, 2),
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
  };
}

// Spike test scenario (separate test)
export const spikeTestOptions = {
  stages: [
    { duration: '1m', target: 10 },   // Normal load
    { duration: '30s', target: 500 }, // Spike to 500 users
    { duration: '1m', target: 500 },  // Stay at spike
    { duration: '30s', target: 10 },  // Drop back to normal
    { duration: '1m', target: 10 },   // Recover
  ],
};

// Volume test scenario (separate test)
export const volumeTestOptions = {
  stages: [
    { duration: '5m', target: 100 },
    { duration: '30m', target: 100 }, // Extended duration
    { duration: '5m', target: 0 },
  ],
};

function textSummary(data, options) {
  // Simple text summary implementation
  return `
Load Test Summary:
==================
Total Requests: ${data.metrics.http_reqs.count}
Failed Requests: ${data.metrics.http_req_failed.count}
Request Rate: ${data.metrics.http_reqs.rate.toFixed(2)}/s
Average Response Time: ${data.metrics.http_req_duration.avg.toFixed(2)}ms
95th Percentile: ${data.metrics.http_req_duration['p(95)'].toFixed(2)}ms
WebSocket Connections: ${data.metrics.ws_connecting ? data.metrics.ws_connecting.count : 'N/A'}
Error Rate: ${(data.metrics.error_rate ? data.metrics.error_rate.rate * 100 : 0).toFixed(2)}%
`;
}