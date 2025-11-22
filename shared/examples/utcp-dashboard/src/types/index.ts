export interface UTCPService {
  name: string;
  base_url: string;
  manual_url: string;
  manual?: UTCPManual;
  last_health_check?: string;
  is_healthy: boolean;
  metadata: Record<string, any>;
  tags: string[];
}

export interface UTCPManual {
  manual_version: string;
  utcp_version: string;
  metadata: ServiceMetadata;
  variables?: Record<string, string>;
  tools: UTCPTool[];
  manual_call_templates: CallTemplate[];
}

export interface ServiceMetadata {
  name: string;
  description: string;
  version: string;
  provider?: string;
  base_url: string;
  protocols: string[];
  authentication?: {
    type: string;
    description: string;
  };
  generated_at?: string;
}

export interface UTCPTool {
  name: string;
  description: string;
  input_schema: JSONSchema;
  metadata?: ToolMetadata;
  service?: {
    name: string;
    base_url: string;
    tags: string[];
  };
}

export interface ToolMetadata {
  path: string;
  method: string;
  tags: string[];
  operationId: string;
  responses?: Record<string, any>;
}

export interface JSONSchema {
  type: string;
  properties?: Record<string, any>;
  required?: string[];
}

export interface CallTemplate {
  name: string;
  description?: string;
  call_template_type: string;
  url: string;
  http_method?: string;
  headers?: Record<string, string>;
  body_template?: string;
  timeout?: number;
}

export interface ServiceHealth {
  [serviceName: string]: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  input: Record<string, any>;
  timestamp: string;
  duration?: number;
  success?: boolean;
  error?: string;
}

export interface OrchestrationLog {
  id: string;
  timestamp: string;
  user_requirement: string;
  tool_calls: ToolCall[];
  success: boolean;
  response: string;
  tokens_used: {
    input: number;
    output: number;
    total: number;
  };
  model: string;
}

export interface ServiceStats {
  name: string;
  total_calls: number;
  success_rate: number;
  avg_latency: number;
  last_call?: string;
  error_count: number;
}

export interface DashboardMetrics {
  total_services: number;
  healthy_services: number;
  total_tools: number;
  total_calls_today: number;
  avg_latency: number;
  success_rate: number;
}