/**
 * Load Testing Script for Sunday.com
 *
 * This script simulates normal expected load on the system
 * Tests typical user workflows under normal operating conditions
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter, Trend } from 'k6/metrics';
import {
  config,
  authenticate,
  getAuthHeaders,
  checkApiResponse,
  randomTaskName,
  randomStatus,
  replaceUrlParams,
  weightedChoice,
  recordCustomMetric,
} from '../config/test-config.js';

// Custom metrics
const userWorkflowRate = new Rate('user_workflow_success');
const apiCallsCounter = new Counter('api_calls_total');
const taskCreationTime = new Trend('task_creation_duration');
const boardLoadTime = new Trend('board_load_duration');

// Test configuration
export const options = {
  scenarios: {
    load_test: config.SCENARIOS.LOAD_TEST,
  },
  thresholds: {
    ...config.THRESHOLDS,
    'user_workflow_success': ['rate>0.95'],
    'task_creation_duration': ['p(95)<500'],
    'board_load_duration': ['p(95)<300'],
  },
};

// Shared test data
let testOrganizations = [];
let testWorkspaces = [];
let testBoards = [];

export function setup() {
  console.log('🚀 Setting up load test environment...');

  // Authenticate as admin to create test data
  const adminAuth = authenticate(http, config.TEST_USERS.ADMIN);

  // Create test organizations if they don't exist
  const orgsResponse = http.get(
    `${config.API_BASE_URL}${config.ENDPOINTS.ORGANIZATIONS.LIST}`,
    { headers: getAuthHeaders(adminAuth.accessToken) }
  );

  if (orgsResponse.status === 200) {
    const existingOrgs = JSON.parse(orgsResponse.body).data.data;
    testOrganizations = existingOrgs.slice(0, 3); // Use first 3 organizations

    if (testOrganizations.length > 0) {
      // Get workspaces for first organization
      const workspacesResponse = http.get(
        `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.WORKSPACES.LIST, {
          orgId: testOrganizations[0].id
        })}`,
        { headers: getAuthHeaders(adminAuth.accessToken) }
      );

      if (workspacesResponse.status === 200) {
        testWorkspaces = JSON.parse(workspacesResponse.body).data.data;

        if (testWorkspaces.length > 0) {
          // Get boards for first workspace
          const boardsResponse = http.get(
            `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.BOARDS.LIST, {
              workspaceId: testWorkspaces[0].id
            })}`,
            { headers: getAuthHeaders(adminAuth.accessToken) }
          );

          if (boardsResponse.status === 200) {
            testBoards = JSON.parse(boardsResponse.body).data.data;
          }
        }
      }
    }
  }

  console.log(`✅ Setup complete: ${testOrganizations.length} orgs, ${testWorkspaces.length} workspaces, ${testBoards.length} boards`);

  return {
    organizations: testOrganizations,
    workspaces: testWorkspaces,
    boards: testBoards,
  };
}

/**
 * Main test function - simulates a typical user session
 */
export default function (data) {
  // Choose user type based on realistic distribution
  const userType = weightedChoice([
    { value: 'MEMBER', weight: 60 },    // 60% members
    { value: 'MANAGER', weight: 30 },   // 30% managers
    { value: 'ADMIN', weight: 10 },     // 10% admins
  ]);

  const testUser = config.TEST_USERS[userType];

  // Authenticate user
  const authResult = authenticate(http, testUser);
  apiCallsCounter.add(1);

  if (!authResult) {
    userWorkflowRate.add(false);
    return;
  }

  const authHeaders = getAuthHeaders(authResult.accessToken);

  // Simulate user workflow based on user type
  let workflowSuccess = false;

  try {
    if (userType === 'ADMIN') {
      workflowSuccess = adminWorkflow(authHeaders, data);
    } else if (userType === 'MANAGER') {
      workflowSuccess = managerWorkflow(authHeaders, data);
    } else {
      workflowSuccess = memberWorkflow(authHeaders, data);
    }
  } catch (error) {
    console.error(`Workflow failed for ${userType}:`, error);
    workflowSuccess = false;
  }

  userWorkflowRate.add(workflowSuccess);

  // Random think time between actions
  sleep(1, 3);
}

/**
 * Admin user workflow - organization and workspace management
 */
function adminWorkflow(authHeaders, data) {
  // 1. Check organization dashboard
  const orgResponse = http.get(
    `${config.API_BASE_URL}${config.ENDPOINTS.ORGANIZATIONS.LIST}`,
    { headers: authHeaders }
  );
  apiCallsCounter.add(1);

  if (!checkApiResponse(orgResponse, 200, 'Get organizations')) {
    return false;
  }

  sleep(0.5, 1.5);

  // 2. View organization analytics (if organization exists)
  if (data.organizations.length > 0) {
    const analyticsResponse = http.get(
      `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.ANALYTICS.ORGANIZATION, {
        id: data.organizations[0].id
      })}`,
      { headers: authHeaders }
    );
    apiCallsCounter.add(1);

    if (!checkApiResponse(analyticsResponse, 200, 'Get organization analytics')) {
      return false;
    }

    sleep(1, 2);
  }

  // 3. Manage workspace (20% chance to create new workspace)
  if (Math.random() < 0.2 && data.organizations.length > 0) {
    const createWorkspaceResponse = http.post(
      `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.WORKSPACES.CREATE, {
        orgId: data.organizations[0].id
      })}`,
      JSON.stringify({
        name: `Test Workspace ${Date.now()}`,
        description: 'Created during load testing',
      }),
      { headers: authHeaders }
    );
    apiCallsCounter.add(1);

    checkApiResponse(createWorkspaceResponse, 201, 'Create workspace');
  }

  return true;
}

/**
 * Manager user workflow - board and task management
 */
function managerWorkflow(authHeaders, data) {
  // 1. View boards
  if (data.workspaces.length === 0) {
    return false;
  }

  const start = Date.now();
  const boardsResponse = http.get(
    `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.BOARDS.LIST, {
      workspaceId: data.workspaces[0].id
    })}`,
    { headers: authHeaders }
  );
  boardLoadTime.add(Date.now() - start);
  apiCallsCounter.add(1);

  if (!checkApiResponse(boardsResponse, 200, 'Get boards')) {
    return false;
  }

  sleep(1, 2);

  // 2. View specific board with items
  if (data.boards.length > 0) {
    const boardResponse = http.get(
      `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.BOARDS.GET, {
        id: data.boards[0].id
      })}`,
      { headers: authHeaders }
    );
    apiCallsCounter.add(1);

    if (!checkApiResponse(boardResponse, 200, 'Get board details')) {
      return false;
    }

    sleep(1, 2);

    // 3. View board analytics
    const analyticsResponse = http.get(
      `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.ANALYTICS.BOARD, {
        id: data.boards[0].id
      })}`,
      { headers: authHeaders }
    );
    apiCallsCounter.add(1);

    checkApiResponse(analyticsResponse, 200, 'Get board analytics');

    sleep(0.5, 1);

    // 4. Create new task (30% chance)
    if (Math.random() < 0.3) {
      const taskStart = Date.now();
      const createTaskResponse = http.post(
        `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.ITEMS.CREATE, {
          boardId: data.boards[0].id
        })}`,
        JSON.stringify({
          name: randomTaskName(),
          description: 'Created during load testing',
          status: randomStatus(),
          fieldValues: {
            priority: 'medium',
          },
        }),
        { headers: authHeaders }
      );
      taskCreationTime.add(Date.now() - taskStart);
      apiCallsCounter.add(1);

      checkApiResponse(createTaskResponse, 201, 'Create task');
    }
  }

  return true;
}

/**
 * Member user workflow - task updates and collaboration
 */
function memberWorkflow(authHeaders, data) {
  // 1. View assigned tasks
  const assignedTasksResponse = http.get(
    `${config.API_BASE_URL}/api/users/me/tasks`,
    { headers: authHeaders }
  );
  apiCallsCounter.add(1);

  if (!checkApiResponse(assignedTasksResponse, 200, 'Get assigned tasks')) {
    return false;
  }

  sleep(1, 2);

  // 2. View specific board
  if (data.boards.length > 0) {
    const boardResponse = http.get(
      `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.ITEMS.LIST, {
        boardId: data.boards[0].id
      })}`,
      { headers: authHeaders }
    );
    apiCallsCounter.add(1);

    if (!checkApiResponse(boardResponse, 200, 'Get board items')) {
      return false;
    }

    const items = JSON.parse(boardResponse.body).data.data;

    sleep(1, 2);

    // 3. Update task status (50% chance if items exist)
    if (items.length > 0 && Math.random() < 0.5) {
      const randomItem = items[Math.floor(Math.random() * items.length)];

      const updateResponse = http.patch(
        `${config.API_BASE_URL}${replaceUrlParams(config.ENDPOINTS.ITEMS.UPDATE, {
          id: randomItem.id
        })}`,
        JSON.stringify({
          status: randomStatus(),
        }),
        { headers: authHeaders }
      );
      apiCallsCounter.add(1);

      checkApiResponse(updateResponse, 200, 'Update task');

      sleep(0.5, 1);

      // 4. Add comment to task (25% chance)
      if (Math.random() < 0.25) {
        const commentResponse = http.post(
          `${config.API_BASE_URL}/api/items/${randomItem.id}/comments`,
          JSON.stringify({
            content: 'Updated during load testing',
          }),
          { headers: authHeaders }
        );
        apiCallsCounter.add(1);

        checkApiResponse(commentResponse, 201, 'Add comment');
      }
    }
  }

  return true;
}

export function teardown(data) {
  console.log('🧹 Load test completed');
  console.log(`📊 Test data used: ${data.organizations.length} orgs, ${data.workspaces.length} workspaces, ${data.boards.length} boards`);
}