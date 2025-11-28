import { request, APIRequestContext } from '@playwright/test';

export class ApiHelper {
  private static apiContext: APIRequestContext;

  /**
   * Get API request context
   */
  static async getApiContext(baseURL?: string): Promise<APIRequestContext> {
    if (!this.apiContext) {
      this.apiContext = await request.newContext({
        baseURL: baseURL || process.env.E2E_API_URL || 'http://localhost:4000',
        extraHTTPHeaders: {
          'Content-Type': 'application/json',
        },
      });
    }
    return this.apiContext;
  }

  /**
   * Wait for API to be ready
   */
  static async waitForAPI(apiURL: string, timeoutMs = 30000): Promise<void> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      try {
        const context = await this.getApiContext(apiURL);
        const response = await context.get('/health');

        if (response.ok()) {
          console.log('✅ API is ready');
          return;
        }
      } catch (error) {
        console.log('⏳ Waiting for API...');
      }

      await new Promise(resolve => setTimeout(resolve, 1000));
    }

    throw new Error('API not ready within timeout');
  }

  /**
   * Perform health check
   */
  static async healthCheck(apiURL: string): Promise<void> {
    const context = await this.getApiContext(apiURL);

    try {
      const response = await context.get('/health');

      if (!response.ok()) {
        throw new Error(`Health check failed: ${response.status()}`);
      }

      const health = await response.json();
      console.log('🏥 Health check passed:', health);

    } catch (error) {
      console.error('❌ Health check failed:', error);
      throw error;
    }
  }

  /**
   * Authenticate user and get tokens
   */
  static async authenticateUser(email: string, password: string): Promise<{
    user: any;
    tokens: {
      accessToken: string;
      refreshToken: string;
      expiresIn: number;
    };
  }> {
    const context = await this.getApiContext();

    const response = await context.post('/api/auth/login', {
      data: {
        email,
        password,
      },
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Authentication failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Create authenticated API context
   */
  static async createAuthenticatedContext(accessToken: string, baseURL?: string): Promise<APIRequestContext> {
    return await request.newContext({
      baseURL: baseURL || process.env.E2E_API_URL || 'http://localhost:4000',
      extraHTTPHeaders: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
    });
  }

  /**
   * Get user profile
   */
  static async getUserProfile(accessToken: string): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.get('/api/auth/me');

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Get profile failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Create organization
   */
  static async createOrganization(accessToken: string, orgData: {
    name: string;
    slug: string;
    description?: string;
  }): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.post('/api/organizations', {
      data: orgData,
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Create organization failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Get user organizations
   */
  static async getUserOrganizations(accessToken: string): Promise<any[]> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.get('/api/organizations');

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Get organizations failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data.data; // Paginated response
  }

  /**
   * Create workspace
   */
  static async createWorkspace(accessToken: string, organizationId: string, workspaceData: {
    name: string;
    description?: string;
  }): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.post(`/api/organizations/${organizationId}/workspaces`, {
      data: workspaceData,
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Create workspace failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Create board
   */
  static async createBoard(accessToken: string, workspaceId: string, boardData: {
    name: string;
    description?: string;
    template?: string;
  }): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.post(`/api/workspaces/${workspaceId}/boards`, {
      data: boardData,
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Create board failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Create item
   */
  static async createItem(accessToken: string, boardId: string, itemData: {
    name: string;
    description?: string;
    assigneeId?: string;
    status?: string;
  }): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.post(`/api/boards/${boardId}/items`, {
      data: itemData,
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Create item failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Update item
   */
  static async updateItem(accessToken: string, itemId: string, updates: {
    name?: string;
    description?: string;
    status?: string;
    assigneeId?: string;
  }): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.patch(`/api/items/${itemId}`, {
      data: updates,
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Update item failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Delete item
   */
  static async deleteItem(accessToken: string, itemId: string): Promise<void> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.delete(`/api/items/${itemId}`);

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Delete item failed: ${error.message}`);
    }
  }

  /**
   * Invite user to organization
   */
  static async inviteUser(accessToken: string, organizationId: string, inviteData: {
    email: string;
    role: string;
  }): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.post(`/api/organizations/${organizationId}/invitations`, {
      data: inviteData,
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Invite user failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Get board analytics
   */
  static async getBoardAnalytics(accessToken: string, boardId: string): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.get(`/api/boards/${boardId}/analytics`);

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Get board analytics failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Search across organization
   */
  static async searchContent(accessToken: string, organizationId: string, query: string): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);

    const response = await context.get(`/api/organizations/${organizationId}/search`, {
      params: { q: query },
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`Search failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Upload file attachment
   */
  static async uploadFile(accessToken: string, itemId: string, filePath: string): Promise<any> {
    const context = await this.createAuthenticatedContext(accessToken);
    const fs = require('fs');

    const response = await context.post(`/api/items/${itemId}/attachments`, {
      multipart: {
        file: fs.createReadStream(filePath),
      },
    });

    if (!response.ok()) {
      const error = await response.json();
      throw new Error(`File upload failed: ${error.message}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * Get real-time events (WebSocket simulation)
   */
  static async simulateRealtimeEvent(eventType: string, data: any): Promise<void> {
    // This would integrate with WebSocket testing
    console.log(`Simulating real-time event: ${eventType}`, data);
  }

  /**
   * Clean up API context
   */
  static async cleanup(): Promise<void> {
    if (this.apiContext) {
      await this.apiContext.dispose();
    }
  }

  /**
   * Bulk operations for test setup
   */
  static async bulkCreateItems(accessToken: string, boardId: string, items: Array<{
    name: string;
    description?: string;
    status?: string;
  }>): Promise<any[]> {
    const results = [];

    for (const item of items) {
      const created = await this.createItem(accessToken, boardId, item);
      results.push(created);
    }

    return results;
  }

  /**
   * Wait for async operation to complete
   */
  static async waitForOperation(
    checkFn: () => Promise<boolean>,
    timeoutMs = 10000,
    intervalMs = 500
  ): Promise<void> {
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      if (await checkFn()) {
        return;
      }
      await new Promise(resolve => setTimeout(resolve, intervalMs));
    }

    throw new Error('Operation did not complete within timeout');
  }

  /**
   * Performance timing helper
   */
  static async measureApiCall<T>(
    operation: () => Promise<T>
  ): Promise<{ result: T; duration: number }> {
    const start = Date.now();
    const result = await operation();
    const duration = Date.now() - start;

    return { result, duration };
  }
}