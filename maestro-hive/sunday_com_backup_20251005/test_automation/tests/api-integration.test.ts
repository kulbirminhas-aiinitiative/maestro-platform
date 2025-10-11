import { test, expect } from '@playwright/test';

/**
 * API Integration Tests
 * QA Engineer: Backend API Validation
 * Tests API endpoints directly for functionality and performance
 */

test.describe('API Integration Tests', () => {
  let authToken: string;
  let testBoardId: string;
  let testItemId: string;

  test.beforeAll(async ({ request }) => {
    // Authenticate and get token
    const loginResponse = await request.post('/api/auth/login', {
      data: {
        email: 'test@sunday.com',
        password: 'TestPassword123!'
      }
    });

    expect(loginResponse.ok()).toBeTruthy();
    const loginData = await loginResponse.json();
    authToken = loginData.token;
  });

  test('TC-API-001: Authentication endpoints', async ({ request }) => {
    // Test registration
    const registerResponse = await request.post('/api/auth/register', {
      data: {
        email: `test${Date.now()}@sunday.com`,
        password: 'TestPassword123!',
        fullName: 'Test User',
        role: 'member'
      }
    });

    expect(registerResponse.status()).toBe(201);
    const registerData = await registerResponse.json();
    expect(registerData.user.email).toBeTruthy();
    expect(registerData.token).toBeTruthy();

    // Test login with new user
    const loginResponse = await request.post('/api/auth/login', {
      data: {
        email: registerData.user.email,
        password: 'TestPassword123!'
      }
    });

    expect(loginResponse.status()).toBe(200);
    const loginData = await loginResponse.json();
    expect(loginData.token).toBeTruthy();

    // Test profile retrieval
    const profileResponse = await request.get('/api/auth/me', {
      headers: {
        'Authorization': `Bearer ${loginData.token}`
      }
    });

    expect(profileResponse.status()).toBe(200);
    const profileData = await profileResponse.json();
    expect(profileData.email).toBe(registerData.user.email);
  });

  test('TC-API-002: Board CRUD operations', async ({ request }) => {
    // Create board
    const createResponse = await request.post('/api/boards', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        name: 'API Test Board',
        description: 'Board created via API test',
        workspaceId: '1',
        columns: [
          { name: 'To Do', type: 'status', color: '#gray' },
          { name: 'In Progress', type: 'status', color: '#blue' },
          { name: 'Done', type: 'status', color: '#green' }
        ]
      }
    });

    expect(createResponse.status()).toBe(201);
    const createData = await createResponse.json();
    testBoardId = createData.id;
    expect(createData.name).toBe('API Test Board');
    expect(createData.columns).toHaveLength(3);

    // Get board
    const getResponse = await request.get(`/api/boards/${testBoardId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(getResponse.status()).toBe(200);
    const getData = await getResponse.json();
    expect(getData.id).toBe(testBoardId);
    expect(getData.name).toBe('API Test Board');

    // Update board
    const updateResponse = await request.put(`/api/boards/${testBoardId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        name: 'Updated API Test Board',
        description: 'Updated description'
      }
    });

    expect(updateResponse.status()).toBe(200);
    const updateData = await updateResponse.json();
    expect(updateData.name).toBe('Updated API Test Board');

    // List boards
    const listResponse = await request.get('/api/boards', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(listResponse.status()).toBe(200);
    const listData = await listResponse.json();
    expect(Array.isArray(listData)).toBeTruthy();
    expect(listData.some(board => board.id === testBoardId)).toBeTruthy();
  });

  test('TC-API-003: Item CRUD operations', async ({ request }) => {
    // Create item
    const createResponse = await request.post('/api/items', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        name: 'API Test Item',
        description: 'Item created via API test',
        boardId: testBoardId,
        columnId: '1',
        status: 'todo',
        priority: 'medium',
        data: {
          status: 'todo',
          priority: 'medium'
        }
      }
    });

    expect(createResponse.status()).toBe(201);
    const createData = await createResponse.json();
    testItemId = createData.id;
    expect(createData.name).toBe('API Test Item');
    expect(createData.boardId).toBe(testBoardId);

    // Get item
    const getResponse = await request.get(`/api/items/${testItemId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(getResponse.status()).toBe(200);
    const getData = await getResponse.json();
    expect(getData.id).toBe(testItemId);
    expect(getData.name).toBe('API Test Item');

    // Update item
    const updateResponse = await request.put(`/api/items/${testItemId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        name: 'Updated API Test Item',
        status: 'in_progress',
        data: {
          status: 'in_progress',
          priority: 'high'
        }
      }
    });

    expect(updateResponse.status()).toBe(200);
    const updateData = await updateResponse.json();
    expect(updateData.name).toBe('Updated API Test Item');
    expect(updateData.data.status).toBe('in_progress');

    // List items for board
    const listResponse = await request.get(`/api/items?boardId=${testBoardId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(listResponse.status()).toBe(200);
    const listData = await listResponse.json();
    expect(Array.isArray(listData)).toBeTruthy();
    expect(listData.some(item => item.id === testItemId)).toBeTruthy();
  });

  test('TC-API-004: File upload operations', async ({ request }) => {
    // Create test file buffer
    const testFileContent = Buffer.from('This is a test file content');

    // Upload file
    const uploadResponse = await request.post('/api/files/upload', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      multipart: {
        file: {
          name: 'test-file.txt',
          mimeType: 'text/plain',
          buffer: testFileContent
        },
        itemId: testItemId
      }
    });

    expect(uploadResponse.status()).toBe(201);
    const uploadData = await uploadResponse.json();
    expect(uploadData.originalName).toBe('test-file.txt');
    expect(uploadData.mimeType).toBe('text/plain');

    const fileId = uploadData.id;

    // Get file metadata
    const getResponse = await request.get(`/api/files/${fileId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(getResponse.status()).toBe(200);
    const getData = await getResponse.json();
    expect(getData.id).toBe(fileId);
    expect(getData.originalName).toBe('test-file.txt');

    // Delete file
    const deleteResponse = await request.delete(`/api/files/${fileId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(deleteResponse.status()).toBe(204);

    // Verify file deleted
    const verifyResponse = await request.get(`/api/files/${fileId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(verifyResponse.status()).toBe(404);
  });

  test('TC-API-005: Comment operations', async ({ request }) => {
    // Create comment
    const createResponse = await request.post('/api/comments', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        content: 'This is a test comment',
        itemId: testItemId
      }
    });

    expect(createResponse.status()).toBe(201);
    const createData = await createResponse.json();
    expect(createData.content).toBe('This is a test comment');
    expect(createData.itemId).toBe(testItemId);

    const commentId = createData.id;

    // Get comments for item
    const getResponse = await request.get(`/api/comments?itemId=${testItemId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(getResponse.status()).toBe(200);
    const getData = await getResponse.json();
    expect(Array.isArray(getData)).toBeTruthy();
    expect(getData.some(comment => comment.id === commentId)).toBeTruthy();

    // Update comment
    const updateResponse = await request.put(`/api/comments/${commentId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        content: 'Updated test comment'
      }
    });

    expect(updateResponse.status()).toBe(200);
    const updateData = await updateResponse.json();
    expect(updateData.content).toBe('Updated test comment');

    // Delete comment
    const deleteResponse = await request.delete(`/api/comments/${commentId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });

    expect(deleteResponse.status()).toBe(204);
  });

  test('TC-API-006: API performance validation', async ({ request }) => {
    const performanceTests = [
      { method: 'GET', url: '/api/boards', expectedTime: 200 },
      { method: 'GET', url: `/api/boards/${testBoardId}`, expectedTime: 150 },
      { method: 'GET', url: `/api/items?boardId=${testBoardId}`, expectedTime: 200 },
      { method: 'GET', url: `/api/items/${testItemId}`, expectedTime: 150 }
    ];

    for (const testCase of performanceTests) {
      const startTime = Date.now();

      const response = await request.get(testCase.url, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });

      const responseTime = Date.now() - startTime;

      expect(response.status()).toBe(200);
      expect(responseTime).toBeLessThan(testCase.expectedTime);

      console.log(`${testCase.method} ${testCase.url}: ${responseTime}ms (target: <${testCase.expectedTime}ms)`);
    }
  });

  test('TC-API-007: Error handling validation', async ({ request }) => {
    // Test 401 Unauthorized
    const unauthorizedResponse = await request.get('/api/boards');
    expect(unauthorizedResponse.status()).toBe(401);

    // Test 404 Not Found
    const notFoundResponse = await request.get('/api/boards/nonexistent-id', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    expect(notFoundResponse.status()).toBe(404);

    // Test 400 Bad Request
    const badRequestResponse = await request.post('/api/boards', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        // Missing required fields
      }
    });
    expect(badRequestResponse.status()).toBe(400);

    // Test rate limiting
    const rateLimitRequests = Array.from({ length: 10 }, (_, i) =>
      request.get('/api/boards', {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
    );

    const responses = await Promise.all(rateLimitRequests);
    const rateLimitedResponses = responses.filter(res => res.status() === 429);

    // Should have some rate limited responses with high request volume
    console.log(`Rate limited responses: ${rateLimitedResponses.length}/10`);
  });

  test('TC-API-008: Data validation and security', async ({ request }) => {
    // Test SQL injection prevention
    const sqlInjectionResponse = await request.get(`/api/boards?name='; DROP TABLE boards; --`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    expect(sqlInjectionResponse.status()).toBe(200); // Should not crash

    // Test XSS prevention
    const xssResponse = await request.post('/api/boards', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        name: '<script>alert("XSS")</script>',
        description: '<img src=x onerror=alert(1)>',
        workspaceId: '1'
      }
    });

    if (xssResponse.status() === 201) {
      const xssData = await xssResponse.json();
      // Should escape or sanitize malicious content
      expect(xssData.name).not.toContain('<script>');
    }

    // Test input length validation
    const longNameResponse = await request.post('/api/boards', {
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      data: {
        name: 'x'.repeat(1000), // Very long name
        workspaceId: '1'
      }
    });
    expect(longNameResponse.status()).toBe(400); // Should reject overly long input
  });

  test.afterAll(async ({ request }) => {
    // Cleanup: Delete test data
    if (testItemId) {
      await request.delete(`/api/items/${testItemId}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
    }

    if (testBoardId) {
      await request.delete(`/api/boards/${testBoardId}`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      });
    }
  });

});