# Sunday.com - API Governance Framework

## Executive Summary

This document establishes a comprehensive API governance framework for Sunday.com, ensuring consistent, secure, and high-quality API development practices across all services. The framework covers API design standards, lifecycle management, security policies, versioning strategies, and quality assurance processes to support enterprise-scale API management.

## Table of Contents

1. [API Governance Overview](#api-governance-overview)
2. [API Design Standards](#api-design-standards)
3. [API Lifecycle Management](#api-lifecycle-management)
4. [Security & Authentication Framework](#security--authentication-framework)
5. [Versioning & Evolution Strategy](#versioning--evolution-strategy)
6. [Quality Assurance & Testing](#quality-assurance--testing)
7. [Documentation & Developer Experience](#documentation--developer-experience)
8. [Monitoring & Analytics](#monitoring--analytics)
9. [Compliance & Risk Management](#compliance--risk-management)
10. [Implementation & Enforcement](#implementation--enforcement)

---

## API Governance Overview

### Governance Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Governance Framework                     │
├─────────────────────────────────────────────────────────────────┤
│  Strategic Layer                                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │   API Strategy   │   Business Goals   │   Technology Vision │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Policy Layer                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Design Standards │ Security Policies │ Quality Guidelines  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Process Layer                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Lifecycle Mgmt │ Change Control │ Review Process │ Approval │ │
│  └─────────────────────────────────────────────────────────────┘ │
│  Implementation Layer                                          │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │   Tools & Automation   │   Enforcement   │   Monitoring     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Governance Stakeholders

| Role | Responsibilities | Authority Level |
|------|------------------|-----------------|
| **API Architect** | API strategy, standards definition | Strategic decisions |
| **Platform Team** | Governance enforcement, tooling | Policy implementation |
| **Product Teams** | API development, compliance | Tactical implementation |
| **Security Team** | Security policies, audit | Security decisions |
| **DevOps Team** | Deployment, monitoring | Operational decisions |

### Governance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Compliance Score** | >95% | Automated compliance checks |
| **Design Review Cycle Time** | <2 days | Review to approval time |
| **Breaking Change Rate** | <1% per release | Version compatibility analysis |
| **Security Vulnerability Response** | <24 hours | Time to patch |
| **Documentation Coverage** | 100% | API documentation completeness |

---

## API Design Standards

### 1. RESTful API Design Principles

#### Resource-Oriented Design

```yaml
# API Resource Design Standards
openapi: 3.0.3
info:
  title: Sunday.com API Design Standards
  version: 1.0.0
  description: Standard API design patterns for Sunday.com

paths:
  # Collection Resources (Plural Nouns)
  /api/v1/workspaces:
    get:
      summary: List workspaces
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: sort
          in: query
          schema:
            type: string
            enum: [name, created_at, updated_at]
            default: created_at
        - name: order
          in: query
          schema:
            type: string
            enum: [asc, desc]
            default: desc
        - name: filter[status]
          in: query
          schema:
            type: string
            enum: [active, archived]
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Workspace'
                  pagination:
                    $ref: '#/components/schemas/PaginationMeta'
                  links:
                    $ref: '#/components/schemas/PaginationLinks'
    post:
      summary: Create workspace
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateWorkspaceRequest'
      responses:
        '201':
          description: Created
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    $ref: '#/components/schemas/Workspace'

  # Individual Resources
  /api/v1/workspaces/{workspaceId}:
    parameters:
      - name: workspaceId
        in: path
        required: true
        schema:
          type: string
          format: uuid
          example: "123e4567-e89b-12d3-a456-426614174000"
    get:
      summary: Get workspace by ID
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    $ref: '#/components/schemas/Workspace'
        '404':
          $ref: '#/components/responses/NotFound'
    put:
      summary: Update workspace
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/UpdateWorkspaceRequest'
      responses:
        '200':
          description: Updated
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    $ref: '#/components/schemas/Workspace'
    delete:
      summary: Delete workspace
      responses:
        '204':
          description: Deleted successfully

  # Sub-resources
  /api/v1/workspaces/{workspaceId}/boards:
    parameters:
      - name: workspaceId
        in: path
        required: true
        schema:
          type: string
          format: uuid
    get:
      summary: List boards in workspace
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                type: object
                properties:
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Board'

components:
  schemas:
    Workspace:
      type: object
      required:
        - id
        - name
        - organizationId
        - createdAt
        - updatedAt
      properties:
        id:
          type: string
          format: uuid
          readOnly: true
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        organizationId:
          type: string
          format: uuid
          readOnly: true
        color:
          type: string
          pattern: "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
          default: "#6B7280"
        isPrivate:
          type: boolean
          default: false
        settings:
          type: object
          additionalProperties: true
        createdAt:
          type: string
          format: date-time
          readOnly: true
        updatedAt:
          type: string
          format: date-time
          readOnly: true

    CreateWorkspaceRequest:
      type: object
      required:
        - name
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        color:
          type: string
          pattern: "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
        isPrivate:
          type: boolean
        settings:
          type: object
          additionalProperties: true

    UpdateWorkspaceRequest:
      type: object
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
        description:
          type: string
          maxLength: 1000
        color:
          type: string
          pattern: "^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"
        isPrivate:
          type: boolean
        settings:
          type: object
          additionalProperties: true

    PaginationMeta:
      type: object
      properties:
        currentPage:
          type: integer
          minimum: 1
        totalPages:
          type: integer
          minimum: 0
        totalItems:
          type: integer
          minimum: 0
        itemsPerPage:
          type: integer
          minimum: 1

    PaginationLinks:
      type: object
      properties:
        first:
          type: string
          format: uri
        prev:
          type: string
          format: uri
          nullable: true
        next:
          type: string
          format: uri
          nullable: true
        last:
          type: string
          format: uri

    Error:
      type: object
      required:
        - error
      properties:
        error:
          type: object
          required:
            - code
            - message
          properties:
            code:
              type: string
              enum:
                - VALIDATION_ERROR
                - RESOURCE_NOT_FOUND
                - UNAUTHORIZED
                - FORBIDDEN
                - INTERNAL_ERROR
                - RATE_LIMIT_EXCEEDED
            message:
              type: string
            details:
              type: array
              items:
                type: object
                properties:
                  field:
                    type: string
                  message:
                    type: string
                  code:
                    type: string
            requestId:
              type: string
              format: uuid
            timestamp:
              type: string
              format: date-time

  responses:
    BadRequest:
      description: Bad Request
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Unauthorized:
      description: Unauthorized
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    Forbidden:
      description: Forbidden
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    UnprocessableEntity:
      description: Validation Error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'
    InternalServerError:
      description: Internal Server Error
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/Error'

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

security:
  - BearerAuth: []
```

#### HTTP Status Code Standards

```typescript
// Standard HTTP Status Code Usage
class APIStatusCodes {
  static readonly SUCCESS = {
    OK: 200,                    // GET requests, successful updates
    CREATED: 201,               // POST requests, resource creation
    NO_CONTENT: 204,            // DELETE requests, successful updates with no response body
  };

  static readonly CLIENT_ERROR = {
    BAD_REQUEST: 400,           // Invalid request syntax, malformed request
    UNAUTHORIZED: 401,          // Authentication required
    FORBIDDEN: 403,             // Authorization failed
    NOT_FOUND: 404,             // Resource not found
    METHOD_NOT_ALLOWED: 405,    // HTTP method not supported
    CONFLICT: 409,              // Resource conflict (duplicate, version conflict)
    UNPROCESSABLE_ENTITY: 422,  // Validation errors
    TOO_MANY_REQUESTS: 429,     // Rate limiting
  };

  static readonly SERVER_ERROR = {
    INTERNAL_SERVER_ERROR: 500, // Unexpected server error
    NOT_IMPLEMENTED: 501,       // Feature not implemented
    BAD_GATEWAY: 502,           // Upstream service error
    SERVICE_UNAVAILABLE: 503,   // Service temporarily unavailable
    GATEWAY_TIMEOUT: 504,       // Upstream service timeout
  };
}

// Error Response Builder
class APIErrorResponse {
  static badRequest(message: string, details?: ValidationError[]): ErrorResponse {
    return {
      error: {
        code: 'VALIDATION_ERROR',
        message,
        details: details?.map(d => ({
          field: d.field,
          message: d.message,
          code: d.code,
        })),
        requestId: this.getRequestId(),
        timestamp: new Date().toISOString(),
      },
    };
  }

  static notFound(resource: string, id: string): ErrorResponse {
    return {
      error: {
        code: 'RESOURCE_NOT_FOUND',
        message: `${resource} with ID ${id} not found`,
        requestId: this.getRequestId(),
        timestamp: new Date().toISOString(),
      },
    };
  }

  static unauthorized(message: string = 'Authentication required'): ErrorResponse {
    return {
      error: {
        code: 'UNAUTHORIZED',
        message,
        requestId: this.getRequestId(),
        timestamp: new Date().toISOString(),
      },
    };
  }

  static forbidden(message: string = 'Access denied'): ErrorResponse {
    return {
      error: {
        code: 'FORBIDDEN',
        message,
        requestId: this.getRequestId(),
        timestamp: new Date().toISOString(),
      },
    };
  }

  static conflict(message: string): ErrorResponse {
    return {
      error: {
        code: 'CONFLICT',
        message,
        requestId: this.getRequestId(),
        timestamp: new Date().toISOString(),
      },
    };
  }

  static internalError(message: string = 'Internal server error'): ErrorResponse {
    return {
      error: {
        code: 'INTERNAL_ERROR',
        message,
        requestId: this.getRequestId(),
        timestamp: new Date().toISOString(),
      },
    };
  }

  private static getRequestId(): string {
    return AsyncLocalStorage.getStore()?.requestId || randomUUID();
  }
}
```

### 2. GraphQL API Design Standards

```typescript
// GraphQL Schema Design Standards
import { gql } from 'apollo-server-express';

// Type Definitions with Standardized Patterns
const typeDefs = gql`
  # Scalars
  scalar DateTime
  scalar UUID
  scalar JSON

  # Enums (Always uppercase)
  enum WorkspaceStatus {
    ACTIVE
    ARCHIVED
    DELETED
  }

  enum SortOrder {
    ASC
    DESC
  }

  # Input Types (Suffix with Input)
  input CreateWorkspaceInput {
    name: String!
    description: String
    color: String
    isPrivate: Boolean = false
    settings: JSON
  }

  input UpdateWorkspaceInput {
    name: String
    description: String
    color: String
    isPrivate: Boolean
    settings: JSON
  }

  input WorkspaceFilterInput {
    status: [WorkspaceStatus!]
    search: String
    organizationId: UUID
  }

  input WorkspaceSortInput {
    field: WorkspaceSortField!
    order: SortOrder! = DESC
  }

  enum WorkspaceSortField {
    NAME
    CREATED_AT
    UPDATED_AT
  }

  # Connection Types (For pagination)
  type WorkspaceEdge {
    node: Workspace!
    cursor: String!
  }

  type WorkspaceConnection {
    edges: [WorkspaceEdge!]!
    nodes: [Workspace!]!
    pageInfo: PageInfo!
    totalCount: Int!
  }

  type PageInfo {
    hasNextPage: Boolean!
    hasPreviousPage: Boolean!
    startCursor: String
    endCursor: String
  }

  # Main Types
  type Workspace {
    id: UUID!
    name: String!
    description: String
    organizationId: UUID!
    color: String!
    isPrivate: Boolean!
    status: WorkspaceStatus!
    settings: JSON

    # Computed fields
    memberCount: Int!
    boardCount: Int!

    # Relationships
    organization: Organization!
    members(
      first: Int
      after: String
      filter: WorkspaceMemberFilterInput
    ): WorkspaceMemberConnection!
    boards(
      first: Int
      after: String
      filter: BoardFilterInput
      sort: BoardSortInput
    ): BoardConnection!

    # Metadata
    createdAt: DateTime!
    updatedAt: DateTime!
    createdBy: User!
  }

  # Mutations follow Command pattern
  type Mutation {
    # Workspace mutations
    createWorkspace(input: CreateWorkspaceInput!): CreateWorkspacePayload!
    updateWorkspace(id: UUID!, input: UpdateWorkspaceInput!): UpdateWorkspacePayload!
    deleteWorkspace(id: UUID!): DeleteWorkspacePayload!
    archiveWorkspace(id: UUID!): ArchiveWorkspacePayload!
  }

  # Mutation Payloads (Include success, errors, and result)
  type CreateWorkspacePayload {
    success: Boolean!
    workspace: Workspace
    errors: [UserError!]!
  }

  type UpdateWorkspacePayload {
    success: Boolean!
    workspace: Workspace
    errors: [UserError!]!
  }

  type DeleteWorkspacePayload {
    success: Boolean!
    deletedWorkspaceId: UUID
    errors: [UserError!]!
  }

  type UserError {
    field: String
    message: String!
    code: String!
  }

  # Queries with consistent patterns
  type Query {
    # Single resource
    workspace(id: UUID!): Workspace

    # Collection with connection pattern
    workspaces(
      first: Int
      after: String
      filter: WorkspaceFilterInput
      sort: WorkspaceSortInput
    ): WorkspaceConnection!

    # Search
    searchWorkspaces(
      query: String!
      first: Int = 20
      after: String
    ): WorkspaceConnection!
  }

  # Subscriptions for real-time updates
  type Subscription {
    workspaceUpdated(workspaceId: UUID!): Workspace!
    workspaceDeleted(workspaceId: UUID!): UUID!
  }
`;

// Resolver Implementation with Error Handling
const resolvers = {
  Query: {
    workspace: async (
      parent: any,
      { id }: { id: string },
      context: GraphQLContext
    ): Promise<Workspace | null> => {
      try {
        // Authorization check
        await context.authService.requirePermission('workspace:read', id);

        const workspace = await context.workspaceService.findById(id);
        if (!workspace) {
          return null;
        }

        return workspace;
      } catch (error) {
        context.logger.error('Error fetching workspace', { workspaceId: id, error });
        throw error;
      }
    },

    workspaces: async (
      parent: any,
      args: WorkspacesQueryArgs,
      context: GraphQLContext
    ): Promise<WorkspaceConnection> => {
      try {
        // Authorization - filter by accessible workspaces
        const accessibleWorkspaceIds = await context.authService.getAccessibleWorkspaces(
          context.user.id
        );

        const result = await context.workspaceService.findMany({
          ...args,
          workspaceIds: accessibleWorkspaceIds,
        });

        return {
          edges: result.items.map(workspace => ({
            node: workspace,
            cursor: encodeCursor(workspace.id),
          })),
          nodes: result.items,
          pageInfo: {
            hasNextPage: result.hasNextPage,
            hasPreviousPage: result.hasPreviousPage,
            startCursor: result.items.length > 0 ? encodeCursor(result.items[0].id) : null,
            endCursor: result.items.length > 0 ?
              encodeCursor(result.items[result.items.length - 1].id) : null,
          },
          totalCount: result.totalCount,
        };
      } catch (error) {
        context.logger.error('Error fetching workspaces', { args, error });
        throw error;
      }
    },
  },

  Mutation: {
    createWorkspace: async (
      parent: any,
      { input }: { input: CreateWorkspaceInput },
      context: GraphQLContext
    ): Promise<CreateWorkspacePayload> => {
      try {
        // Authorization check
        await context.authService.requirePermission('workspace:create');

        // Validation
        const validationErrors = await context.validator.validate(input, CreateWorkspaceSchema);
        if (validationErrors.length > 0) {
          return {
            success: false,
            workspace: null,
            errors: validationErrors.map(error => ({
              field: error.field,
              message: error.message,
              code: error.code,
            })),
          };
        }

        const workspace = await context.workspaceService.create({
          ...input,
          organizationId: context.user.organizationId,
          createdBy: context.user.id,
        });

        // Publish event for real-time updates
        context.pubsub.publish('WORKSPACE_CREATED', {
          workspaceCreated: workspace,
          organizationId: workspace.organizationId,
        });

        return {
          success: true,
          workspace,
          errors: [],
        };
      } catch (error) {
        context.logger.error('Error creating workspace', { input, error });

        return {
          success: false,
          workspace: null,
          errors: [{
            field: null,
            message: 'Failed to create workspace',
            code: 'INTERNAL_ERROR',
          }],
        };
      }
    },
  },

  Subscription: {
    workspaceUpdated: {
      subscribe: withFilter(
        (parent: any, args: any, context: GraphQLContext) => {
          return context.pubsub.asyncIterator(['WORKSPACE_UPDATED']);
        },
        (payload: any, variables: any, context: GraphQLContext) => {
          // Only send updates for workspaces the user has access to
          return context.authService.hasWorkspaceAccess(
            context.user.id,
            variables.workspaceId
          );
        }
      ),
    },
  },

  // Field resolvers
  Workspace: {
    organization: async (
      workspace: Workspace,
      args: any,
      context: GraphQLContext
    ): Promise<Organization> => {
      return context.loaders.organizationLoader.load(workspace.organizationId);
    },

    members: async (
      workspace: Workspace,
      args: WorkspaceMembersArgs,
      context: GraphQLContext
    ): Promise<WorkspaceMemberConnection> => {
      return context.workspaceMemberService.findByWorkspace(workspace.id, args);
    },

    memberCount: async (
      workspace: Workspace,
      args: any,
      context: GraphQLContext
    ): Promise<number> => {
      return context.loaders.workspaceMemberCountLoader.load(workspace.id);
    },
  },
};
```

### 3. API Design Validation Framework

```typescript
// Automated API Design Validation
class APIDesignValidator {
  private rules: ValidationRule[] = [
    new RESTfulNamingRule(),
    new HTTPStatusRule(),
    new SecurityRule(),
    new PaginationRule(),
    new ErrorHandlingRule(),
    new VersioningRule(),
  ];

  async validateOpenAPISpec(spec: OpenAPISpec): Promise<ValidationResult> {
    const issues: ValidationIssue[] = [];

    for (const rule of this.rules) {
      const ruleIssues = await rule.validate(spec);
      issues.push(...ruleIssues);
    }

    return {
      valid: issues.filter(i => i.severity === 'error').length === 0,
      issues,
      score: this.calculateScore(issues),
    };
  }

  private calculateScore(issues: ValidationIssue[]): number {
    const weights = { error: 10, warning: 5, info: 1 };
    const totalDeductions = issues.reduce(
      (sum, issue) => sum + weights[issue.severity],
      0
    );
    return Math.max(0, 100 - totalDeductions);
  }
}

// RESTful Naming Validation
class RESTfulNamingRule implements ValidationRule {
  async validate(spec: OpenAPISpec): Promise<ValidationIssue[]> {
    const issues: ValidationIssue[] = [];

    for (const [path, pathItem] of Object.entries(spec.paths)) {
      // Check resource naming (should be plural nouns)
      const resourceSegments = path.split('/').filter(s => s && !s.startsWith('{'));

      for (const segment of resourceSegments) {
        if (segment !== 'api' && !this.isPluralNoun(segment)) {
          issues.push({
            severity: 'warning',
            code: 'NON_PLURAL_RESOURCE',
            message: `Resource '${segment}' should be a plural noun`,
            path,
          });
        }
      }

      // Check for verbs in URLs
      if (this.containsVerbs(path)) {
        issues.push({
          severity: 'error',
          code: 'VERB_IN_URL',
          message: `URL should not contain verbs: ${path}`,
          path,
        });
      }

      // Check HTTP methods usage
      for (const [method, operation] of Object.entries(pathItem)) {
        if (!this.isValidMethodForPath(method, path)) {
          issues.push({
            severity: 'error',
            code: 'INVALID_HTTP_METHOD',
            message: `${method.toUpperCase()} not appropriate for ${path}`,
            path,
            method,
          });
        }
      }
    }

    return issues;
  }

  private isPluralNoun(word: string): boolean {
    // Simple check - in real implementation, use NLP library
    return word.endsWith('s') || word.endsWith('ies') || word.endsWith('ves');
  }

  private containsVerbs(path: string): boolean {
    const commonVerbs = ['create', 'update', 'delete', 'get', 'list', 'add', 'remove'];
    return commonVerbs.some(verb => path.toLowerCase().includes(verb));
  }

  private isValidMethodForPath(method: string, path: string): boolean {
    const isCollection = !path.includes('{');
    const isResource = path.includes('{');

    switch (method.toLowerCase()) {
      case 'get':
        return true; // GET valid for both collections and resources
      case 'post':
        return isCollection; // POST only for collections
      case 'put':
      case 'patch':
        return isResource; // PUT/PATCH only for specific resources
      case 'delete':
        return isResource; // DELETE only for specific resources
      default:
        return false;
    }
  }
}

// Security Validation Rule
class SecurityRule implements ValidationRule {
  async validate(spec: OpenAPISpec): Promise<ValidationIssue[]> {
    const issues: ValidationIssue[] = [];

    // Check for security schemes
    if (!spec.components?.securitySchemes) {
      issues.push({
        severity: 'error',
        code: 'MISSING_SECURITY_SCHEMES',
        message: 'API specification must define security schemes',
      });
    }

    // Check that all paths have security
    for (const [path, pathItem] of Object.entries(spec.paths)) {
      for (const [method, operation] of Object.entries(pathItem)) {
        if (!operation.security && !spec.security) {
          issues.push({
            severity: 'error',
            code: 'MISSING_SECURITY',
            message: `${method.toUpperCase()} ${path} must specify security requirements`,
            path,
            method,
          });
        }
      }
    }

    // Check for sensitive data in URLs
    for (const [path] of Object.entries(spec.paths)) {
      if (this.containsSensitiveData(path)) {
        issues.push({
          severity: 'warning',
          code: 'SENSITIVE_DATA_IN_URL',
          message: `Path may contain sensitive data: ${path}`,
          path,
        });
      }
    }

    return issues;
  }

  private containsSensitiveData(path: string): boolean {
    const sensitivePatterns = [/password/i, /secret/i, /token/i, /key/i];
    return sensitivePatterns.some(pattern => pattern.test(path));
  }
}

// Error Handling Validation Rule
class ErrorHandlingRule implements ValidationRule {
  async validate(spec: OpenAPISpec): Promise<ValidationIssue[]> {
    const issues: ValidationIssue[] = [];

    for (const [path, pathItem] of Object.entries(spec.paths)) {
      for (const [method, operation] of Object.entries(pathItem)) {
        const responses = operation.responses || {};

        // Check for 4xx and 5xx error responses
        if (!this.hasErrorResponses(responses)) {
          issues.push({
            severity: 'warning',
            code: 'MISSING_ERROR_RESPONSES',
            message: `${method.toUpperCase()} ${path} should define error responses`,
            path,
            method,
          });
        }

        // Check error response format consistency
        for (const [statusCode, response] of Object.entries(responses)) {
          if (statusCode.startsWith('4') || statusCode.startsWith('5')) {
            if (!this.hasStandardErrorFormat(response)) {
              issues.push({
                severity: 'error',
                code: 'NON_STANDARD_ERROR_FORMAT',
                message: `Error response ${statusCode} should follow standard format`,
                path,
                method,
                statusCode,
              });
            }
          }
        }
      }
    }

    return issues;
  }

  private hasErrorResponses(responses: any): boolean {
    const statusCodes = Object.keys(responses);
    return statusCodes.some(code => code.startsWith('4') || code.startsWith('5'));
  }

  private hasStandardErrorFormat(response: any): boolean {
    // Check if response content matches standard error schema
    const content = response.content?.['application/json'];
    if (!content?.schema) return false;

    const schema = content.schema;
    return (
      schema.properties?.error &&
      schema.properties?.error.properties?.code &&
      schema.properties?.error.properties?.message
    );
  }
}
```

---

## API Lifecycle Management

### 1. API Development Lifecycle

```typescript
// API Lifecycle State Machine
enum APILifecycleState {
  DESIGN = 'design',
  DEVELOPMENT = 'development',
  TESTING = 'testing',
  STAGING = 'staging',
  PRODUCTION = 'production',
  DEPRECATED = 'deprecated',
  RETIRED = 'retired'
}

interface APILifecycleTransition {
  from: APILifecycleState;
  to: APILifecycleState;
  requiredApprovals: string[];
  automatedChecks: string[];
  documentation: string[];
}

class APILifecycleManager {
  private transitions: Map<string, APILifecycleTransition[]> = new Map();

  constructor() {
    this.initializeTransitions();
  }

  private initializeTransitions(): void {
    this.transitions.set(APILifecycleState.DESIGN, [
      {
        from: APILifecycleState.DESIGN,
        to: APILifecycleState.DEVELOPMENT,
        requiredApprovals: ['api-architect', 'tech-lead'],
        automatedChecks: ['design-validation', 'security-review'],
        documentation: ['api-specification', 'design-rationale'],
      },
    ]);

    this.transitions.set(APILifecycleState.DEVELOPMENT, [
      {
        from: APILifecycleState.DEVELOPMENT,
        to: APILifecycleState.TESTING,
        requiredApprovals: ['tech-lead'],
        automatedChecks: ['unit-tests', 'integration-tests', 'code-quality'],
        documentation: ['implementation-guide', 'test-plan'],
      },
    ]);

    this.transitions.set(APILifecycleState.TESTING, [
      {
        from: APILifecycleState.TESTING,
        to: APILifecycleState.STAGING,
        requiredApprovals: ['qa-lead'],
        automatedChecks: ['performance-tests', 'security-tests', 'compatibility-tests'],
        documentation: ['test-results', 'performance-report'],
      },
    ]);

    this.transitions.set(APILifecycleState.STAGING, [
      {
        from: APILifecycleState.STAGING,
        to: APILifecycleState.PRODUCTION,
        requiredApprovals: ['product-owner', 'platform-team'],
        automatedChecks: ['smoke-tests', 'monitoring-setup', 'documentation-complete'],
        documentation: ['deployment-guide', 'monitoring-runbook', 'user-documentation'],
      },
    ]);

    this.transitions.set(APILifecycleState.PRODUCTION, [
      {
        from: APILifecycleState.PRODUCTION,
        to: APILifecycleState.DEPRECATED,
        requiredApprovals: ['api-architect', 'product-owner'],
        automatedChecks: ['migration-plan', 'backward-compatibility'],
        documentation: ['deprecation-notice', 'migration-guide'],
      },
    ]);

    this.transitions.set(APILifecycleState.DEPRECATED, [
      {
        from: APILifecycleState.DEPRECATED,
        to: APILifecycleState.RETIRED,
        requiredApprovals: ['api-architect', 'platform-team'],
        automatedChecks: ['usage-analysis', 'migration-completion'],
        documentation: ['retirement-notice', 'final-report'],
      },
    ]);
  }

  async requestTransition(
    apiId: string,
    targetState: APILifecycleState,
    requestedBy: string
  ): Promise<TransitionRequest> {
    const api = await this.getAPI(apiId);
    const availableTransitions = this.transitions.get(api.currentState) || [];

    const transition = availableTransitions.find(t => t.to === targetState);
    if (!transition) {
      throw new Error(`Invalid transition from ${api.currentState} to ${targetState}`);
    }

    const transitionRequest: TransitionRequest = {
      id: randomUUID(),
      apiId,
      from: api.currentState,
      to: targetState,
      requestedBy,
      requestedAt: new Date(),
      status: 'pending',
      requiredApprovals: transition.requiredApprovals,
      pendingApprovals: [...transition.requiredApprovals],
      automatedChecks: transition.automatedChecks,
      pendingChecks: [...transition.automatedChecks],
      documentation: transition.documentation,
      pendingDocumentation: [...transition.documentation],
    };

    await this.saveTransitionRequest(transitionRequest);
    await this.startAutomatedChecks(transitionRequest);

    return transitionRequest;
  }

  async approveTransition(
    requestId: string,
    approver: string,
    role: string
  ): Promise<void> {
    const request = await this.getTransitionRequest(requestId);

    if (!request.pendingApprovals.includes(role)) {
      throw new Error(`Approval not required from role: ${role}`);
    }

    request.pendingApprovals = request.pendingApprovals.filter(r => r !== role);
    request.approvals.push({
      role,
      approver,
      approvedAt: new Date(),
    });

    await this.saveTransitionRequest(request);
    await this.checkTransitionCompletion(request);
  }

  private async startAutomatedChecks(request: TransitionRequest): Promise<void> {
    for (const check of request.automatedChecks) {
      try {
        await this.runAutomatedCheck(check, request.apiId);

        request.pendingChecks = request.pendingChecks.filter(c => c !== check);
        request.completedChecks.push({
          check,
          status: 'passed',
          completedAt: new Date(),
        });
      } catch (error) {
        request.completedChecks.push({
          check,
          status: 'failed',
          error: error.message,
          completedAt: new Date(),
        });
      }
    }

    await this.saveTransitionRequest(request);
  }

  private async checkTransitionCompletion(request: TransitionRequest): Promise<void> {
    const allApproved = request.pendingApprovals.length === 0;
    const allChecksPassed = request.pendingChecks.length === 0 &&
      request.completedChecks.every(c => c.status === 'passed');
    const allDocumentationComplete = request.pendingDocumentation.length === 0;

    if (allApproved && allChecksPassed && allDocumentationComplete) {
      await this.executeTransition(request);
    }
  }

  private async executeTransition(request: TransitionRequest): Promise<void> {
    const api = await this.getAPI(request.apiId);

    api.currentState = request.to;
    api.stateHistory.push({
      state: request.to,
      transitionedAt: new Date(),
      transitionedBy: request.requestedBy,
      requestId: request.id,
    });

    await this.saveAPI(api);

    request.status = 'completed';
    request.completedAt = new Date();
    await this.saveTransitionRequest(request);

    // Trigger post-transition actions
    await this.executePostTransitionActions(api, request);
  }
}
```

### 2. Change Management Process

```typescript
// API Change Management
class APIChangeManager {
  async proposeChange(change: APIChangeProposal): Promise<ChangeRequest> {
    // Analyze impact
    const impact = await this.analyzeChangeImpact(change);

    // Determine approval requirements based on impact
    const approvalRequirements = this.determineApprovalRequirements(impact);

    const changeRequest: ChangeRequest = {
      id: randomUUID(),
      apiId: change.apiId,
      title: change.title,
      description: change.description,
      type: change.type,
      proposedBy: change.proposedBy,
      proposedAt: new Date(),
      status: 'under_review',
      impact,
      approvalRequirements,
      pendingApprovals: [...approvalRequirements.required],
      changes: change.changes,
    };

    await this.saveChangeRequest(changeRequest);
    await this.notifyStakeholders(changeRequest);

    return changeRequest;
  }

  private async analyzeChangeImpact(change: APIChangeProposal): Promise<ChangeImpact> {
    const currentSpec = await this.getAPISpecification(change.apiId);
    const proposedSpec = this.applyChanges(currentSpec, change.changes);

    const analyzer = new APICompatibilityAnalyzer();
    const compatibility = await analyzer.analyze(currentSpec, proposedSpec);

    return {
      breaking: compatibility.breakingChanges.length > 0,
      breakingChanges: compatibility.breakingChanges,
      nonBreakingChanges: compatibility.nonBreakingChanges,
      affectedEndpoints: compatibility.affectedEndpoints,
      estimatedMigrationEffort: this.estimateMigrationEffort(compatibility),
      riskLevel: this.calculateRiskLevel(compatibility),
    };
  }

  private determineApprovalRequirements(impact: ChangeImpact): ApprovalRequirements {
    const requirements: ApprovalRequirements = {
      required: ['api-owner'],
      optional: [],
      documentation: ['change-log'],
    };

    if (impact.breaking) {
      requirements.required.push('api-architect', 'product-owner');
      requirements.documentation.push('migration-guide', 'deprecation-timeline');
    }

    if (impact.riskLevel === 'high') {
      requirements.required.push('security-team', 'platform-team');
    }

    if (impact.affectedEndpoints.length > 5) {
      requirements.required.push('tech-lead');
    }

    return requirements;
  }

  private calculateRiskLevel(compatibility: CompatibilityAnalysis): RiskLevel {
    if (compatibility.breakingChanges.length > 0) {
      return 'high';
    }

    if (compatibility.affectedEndpoints.length > 10) {
      return 'medium';
    }

    return 'low';
  }
}

// API Compatibility Analyzer
class APICompatibilityAnalyzer {
  async analyze(
    currentSpec: OpenAPISpec,
    proposedSpec: OpenAPISpec
  ): Promise<CompatibilityAnalysis> {
    const breakingChanges: BreakingChange[] = [];
    const nonBreakingChanges: NonBreakingChange[] = [];
    const affectedEndpoints: string[] = [];

    // Analyze path changes
    await this.analyzePaths(currentSpec, proposedSpec, breakingChanges, nonBreakingChanges);

    // Analyze schema changes
    await this.analyzeSchemas(currentSpec, proposedSpec, breakingChanges, nonBreakingChanges);

    // Analyze parameter changes
    await this.analyzeParameters(currentSpec, proposedSpec, breakingChanges, nonBreakingChanges);

    return {
      breakingChanges,
      nonBreakingChanges,
      affectedEndpoints: [...new Set(affectedEndpoints)],
      summary: {
        totalChanges: breakingChanges.length + nonBreakingChanges.length,
        breakingChangesCount: breakingChanges.length,
        nonBreakingChangesCount: nonBreakingChanges.length,
      },
    };
  }

  private async analyzePaths(
    currentSpec: OpenAPISpec,
    proposedSpec: OpenAPISpec,
    breakingChanges: BreakingChange[],
    nonBreakingChanges: NonBreakingChange[]
  ): Promise<void> {
    const currentPaths = Object.keys(currentSpec.paths || {});
    const proposedPaths = Object.keys(proposedSpec.paths || {});

    // Removed paths are breaking changes
    for (const path of currentPaths) {
      if (!proposedPaths.includes(path)) {
        breakingChanges.push({
          type: 'path_removed',
          path,
          description: `Path ${path} has been removed`,
          severity: 'high',
        });
      }
    }

    // Added paths are non-breaking changes
    for (const path of proposedPaths) {
      if (!currentPaths.includes(path)) {
        nonBreakingChanges.push({
          type: 'path_added',
          path,
          description: `Path ${path} has been added`,
        });
      }
    }

    // Analyze method changes
    for (const path of currentPaths.filter(p => proposedPaths.includes(p))) {
      await this.analyzePathMethods(
        path,
        currentSpec.paths[path],
        proposedSpec.paths[path],
        breakingChanges,
        nonBreakingChanges
      );
    }
  }

  private async analyzePathMethods(
    path: string,
    currentPath: any,
    proposedPath: any,
    breakingChanges: BreakingChange[],
    nonBreakingChanges: NonBreakingChange[]
  ): Promise<void> {
    const currentMethods = Object.keys(currentPath);
    const proposedMethods = Object.keys(proposedPath);

    // Removed methods are breaking changes
    for (const method of currentMethods) {
      if (!proposedMethods.includes(method)) {
        breakingChanges.push({
          type: 'method_removed',
          path,
          method,
          description: `Method ${method.toUpperCase()} has been removed from ${path}`,
          severity: 'high',
        });
      }
    }

    // Added methods are non-breaking changes
    for (const method of proposedMethods) {
      if (!currentMethods.includes(method)) {
        nonBreakingChanges.push({
          type: 'method_added',
          path,
          method,
          description: `Method ${method.toUpperCase()} has been added to ${path}`,
        });
      }
    }
  }

  private async analyzeSchemas(
    currentSpec: OpenAPISpec,
    proposedSpec: OpenAPISpec,
    breakingChanges: BreakingChange[],
    nonBreakingChanges: NonBreakingChange[]
  ): Promise<void> {
    const currentSchemas = currentSpec.components?.schemas || {};
    const proposedSchemas = proposedSpec.components?.schemas || {};

    for (const [schemaName, currentSchema] of Object.entries(currentSchemas)) {
      const proposedSchema = proposedSchemas[schemaName];

      if (!proposedSchema) {
        breakingChanges.push({
          type: 'schema_removed',
          schema: schemaName,
          description: `Schema ${schemaName} has been removed`,
          severity: 'high',
        });
        continue;
      }

      // Analyze schema property changes
      await this.analyzeSchemaProperties(
        schemaName,
        currentSchema,
        proposedSchema,
        breakingChanges,
        nonBreakingChanges
      );
    }
  }

  private async analyzeSchemaProperties(
    schemaName: string,
    currentSchema: any,
    proposedSchema: any,
    breakingChanges: BreakingChange[],
    nonBreakingChanges: NonBreakingChange[]
  ): Promise<void> {
    const currentProps = currentSchema.properties || {};
    const proposedProps = proposedSchema.properties || {};

    const currentRequired = currentSchema.required || [];
    const proposedRequired = proposedSchema.required || [];

    // Removed properties are breaking changes
    for (const prop of Object.keys(currentProps)) {
      if (!proposedProps[prop]) {
        breakingChanges.push({
          type: 'property_removed',
          schema: schemaName,
          property: prop,
          description: `Property ${prop} removed from schema ${schemaName}`,
          severity: 'medium',
        });
      }
    }

    // New required properties are breaking changes
    for (const prop of proposedRequired) {
      if (!currentRequired.includes(prop)) {
        breakingChanges.push({
          type: 'property_required',
          schema: schemaName,
          property: prop,
          description: `Property ${prop} is now required in schema ${schemaName}`,
          severity: 'high',
        });
      }
    }

    // Added optional properties are non-breaking changes
    for (const prop of Object.keys(proposedProps)) {
      if (!currentProps[prop] && !proposedRequired.includes(prop)) {
        nonBreakingChanges.push({
          type: 'property_added',
          schema: schemaName,
          property: prop,
          description: `Optional property ${prop} added to schema ${schemaName}`,
        });
      }
    }
  }
}
```

This comprehensive API governance framework provides enterprise-grade standards and processes for managing APIs throughout their lifecycle, ensuring consistency, security, and quality across all API development efforts.

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*
*Approval Required: CTO, API Architect, Platform Engineering Lead*