import { API_BASE_URL, TOKEN_STORAGE_KEY } from './constants'
import type { ApiResponse, ApiError } from '@/types'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public details?: Record<string, any>
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiClient {
  private baseURL: string
  private token: string | null = null

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL
    this.token = localStorage.getItem(TOKEN_STORAGE_KEY)
  }

  setToken(token: string | null) {
    this.token = token
    if (token) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
  }

  getToken(): string | null {
    return this.token || localStorage.getItem(TOKEN_STORAGE_KEY)
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const token = this.getToken()

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        const errorData: ApiError = await response.json().catch(() => ({
          error: {
            type: 'unknown_error',
            message: 'An unknown error occurred',
            requestId: response.headers.get('x-request-id') || undefined,
          },
        }))

        throw new ApiError(
          errorData.error.message,
          response.status,
          errorData.error.details
        )
      }

      // Handle 204 No Content responses
      if (response.status === 204) {
        return {} as T
      }

      const data = await response.json()
      return data
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }

      // Network or other errors
      throw new ApiError(
        error instanceof Error ? error.message : 'Network error',
        0
      )
    }
  }

  // HTTP methods
  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T> {
    const url = new URL(endpoint, this.baseURL)
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value))
        }
      })
    }

    return this.request<T>(url.pathname + url.search)
  }

  async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async patch<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'DELETE',
    })
  }

  // File upload
  async upload<T>(endpoint: string, file: File, additionalData?: Record<string, any>): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)

    if (additionalData) {
      Object.entries(additionalData).forEach(([key, value]) => {
        formData.append(key, String(value))
      })
    }

    const token = this.getToken()

    return this.request<T>(endpoint, {
      method: 'POST',
      headers: {
        ...(token && { Authorization: `Bearer ${token}` }),
        // Don't set Content-Type for FormData, let browser set it with boundary
      },
      body: formData,
    })
  }
}

// Create singleton instance
export const apiClient = new ApiClient()

// API endpoints
export const api = {
  // Authentication
  auth: {
    register: (data: any) => apiClient.post('/api/v1/auth/register', data),
    login: (data: any) => apiClient.post('/api/v1/auth/login', data),
    refresh: (data: any) => apiClient.post('/api/v1/auth/refresh', data),
    me: () => apiClient.get('/api/v1/auth/me'),
    updateProfile: (data: any) => apiClient.put('/api/v1/auth/me', data),
  },

  // Organizations
  organizations: {
    list: (params?: any) => apiClient.get('/api/v1/organizations', params),
    create: (data: any) => apiClient.post('/api/v1/organizations', data),
    get: (id: string, params?: any) => apiClient.get(`/api/v1/organizations/${id}`, params),
    update: (id: string, data: any) => apiClient.put(`/api/v1/organizations/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/v1/organizations/${id}`),

    // Members
    listMembers: (id: string, params?: any) =>
      apiClient.get(`/api/v1/organizations/${id}/members`, params),
    inviteMember: (id: string, data: any) =>
      apiClient.post(`/api/v1/organizations/${id}/members`, data),
    updateMember: (orgId: string, memberId: string, data: any) =>
      apiClient.put(`/api/v1/organizations/${orgId}/members/${memberId}`, data),
    removeMember: (orgId: string, memberId: string) =>
      apiClient.delete(`/api/v1/organizations/${orgId}/members/${memberId}`),
  },

  // Workspaces
  workspaces: {
    list: (orgId: string, params?: any) =>
      apiClient.get(`/api/v1/organizations/${orgId}/workspaces`, params),
    create: (orgId: string, data: any) =>
      apiClient.post(`/api/v1/organizations/${orgId}/workspaces`, data),
    get: (id: string, params?: any) => apiClient.get(`/api/v1/workspaces/${id}`, params),
    update: (id: string, data: any) => apiClient.put(`/api/v1/workspaces/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/v1/workspaces/${id}`),
  },

  // Boards
  boards: {
    list: (workspaceId: string, params?: any) =>
      apiClient.get(`/api/v1/workspaces/${workspaceId}/boards`, params),
    create: (workspaceId: string, data: any) =>
      apiClient.post(`/api/v1/workspaces/${workspaceId}/boards`, data),
    get: (id: string, params?: any) => apiClient.get(`/api/v1/boards/${id}`, params),
    update: (id: string, data: any) => apiClient.put(`/api/v1/boards/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/v1/boards/${id}`),
  },

  // Items
  items: {
    list: (boardId: string, params?: any) =>
      apiClient.get(`/api/v1/boards/${boardId}/items`, params),
    create: (boardId: string, data: any) =>
      apiClient.post(`/api/v1/boards/${boardId}/items`, data),
    get: (id: string, params?: any) => apiClient.get(`/api/v1/items/${id}`, params),
    update: (id: string, data: any) => apiClient.put(`/api/v1/items/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/v1/items/${id}`),
    bulkUpdate: (data: any) => apiClient.put('/api/v1/items/bulk', data),
    bulkDelete: (data: any) => apiClient.delete('/api/v1/items/bulk'),
  },

  // Comments
  comments: {
    list: (itemId: string, params?: any) =>
      apiClient.get(`/api/v1/items/${itemId}/comments`, params),
    create: (itemId: string, data: any) =>
      apiClient.post(`/api/v1/items/${itemId}/comments`, data),
    update: (id: string, data: any) => apiClient.put(`/api/v1/comments/${id}`, data),
    delete: (id: string) => apiClient.delete(`/api/v1/comments/${id}`),
  },

  // Files
  files: {
    upload: (file: File, data?: any) => apiClient.upload('/api/v1/files', file, data),
    get: (id: string) => apiClient.get(`/api/v1/files/${id}`),
    delete: (id: string) => apiClient.delete(`/api/v1/files/${id}`),
  },
}

export default api