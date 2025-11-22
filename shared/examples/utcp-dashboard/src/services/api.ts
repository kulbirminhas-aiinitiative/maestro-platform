import axios from 'axios';
import type {
  UTCPService,
  ServiceHealth,
  UTCPTool,
  OrchestrationLog,
  ServiceStats,
  DashboardMetrics,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:9000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for auth
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('utcp_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export const registryApi = {
  // Services
  async listServices(): Promise<UTCPService[]> {
    const response = await api.get('/registry/services');
    return response.data.services || [];
  },

  async getService(name: string): Promise<UTCPService> {
    const response = await api.get(`/registry/services/${name}`);
    return response.data;
  },

  async registerService(service: Partial<UTCPService>): Promise<UTCPService> {
    const response = await api.post('/registry/services', service);
    return response.data;
  },

  async unregisterService(name: string): Promise<void> {
    await api.delete(`/registry/services/${name}`);
  },

  // Health
  async checkHealth(serviceName?: string): Promise<ServiceHealth> {
    const url = serviceName
      ? `/registry/health/${serviceName}`
      : '/registry/health';
    const response = await api.get(url);
    return response.data;
  },

  // Tools
  async listTools(params?: {
    service?: string;
    tags?: string[];
  }): Promise<UTCPTool[]> {
    const response = await api.get('/registry/tools', { params });
    return response.data.tools || [];
  },

  async getTool(toolName: string): Promise<UTCPTool> {
    const response = await api.get(`/registry/tools/${toolName}`);
    return response.data;
  },

  // Tool calls
  async callTool(
    toolName: string,
    toolInput: Record<string, any>,
    context?: Record<string, any>
  ): Promise<any> {
    const response = await api.post('/registry/call-tool', {
      tool_name: toolName,
      tool_input: toolInput,
      context,
    });
    return response.data;
  },

  // Orchestration
  async orchestrate(requirement: string): Promise<OrchestrationLog> {
    const response = await api.post('/orchestrate', { requirement });
    return response.data;
  },

  async getOrchestrationLogs(limit: number = 50): Promise<OrchestrationLog[]> {
    const response = await api.get('/orchestration/logs', {
      params: { limit },
    });
    return response.data.logs || [];
  },

  // Metrics
  async getMetrics(): Promise<DashboardMetrics> {
    const response = await api.get('/registry/metrics');
    return response.data;
  },

  async getServiceStats(serviceName?: string): Promise<ServiceStats[]> {
    const url = serviceName
      ? `/registry/stats/${serviceName}`
      : '/registry/stats';
    const response = await api.get(url);
    return response.data.stats || [];
  },

  // Discovery
  async discoverServices(urls: string[]): Promise<UTCPService[]> {
    const response = await api.post('/registry/discover', { urls });
    return response.data.discovered || [];
  },
};

export default api;