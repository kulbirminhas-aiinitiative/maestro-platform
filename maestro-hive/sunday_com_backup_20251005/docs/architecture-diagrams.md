# Sunday.com Architecture Diagrams

## 🏗️ Overview

This document provides visual representations of Sunday.com's architecture, from high-level system overview to detailed component interactions. These diagrams help developers, architects, and stakeholders understand how the platform is designed and how different components work together.

## 📋 Table of Contents

1. [System Architecture Overview](#system-architecture-overview)
2. [Microservices Architecture](#microservices-architecture)
3. [Data Architecture](#data-architecture)
4. [Security Architecture](#security-architecture)
5. [Deployment Architecture](#deployment-architecture)
6. [Real-time Collaboration](#real-time-collaboration)
7. [API Architecture](#api-architecture)
8. [User Journey Flows](#user-journey-flows)

---

## 🌐 System Architecture Overview

### High-Level System Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Application<br/>React + TypeScript]
        MOBILE[Mobile Apps<br/>React Native]
        API_CLIENTS[Third-party Clients<br/>API Integrations]
    end

    subgraph "Edge Layer"
        CDN[CloudFront CDN<br/>Global Content Delivery]
        WAF[Web Application Firewall<br/>DDoS Protection]
        LB[Application Load Balancer<br/>Traffic Distribution]
    end

    subgraph "API Gateway Layer"
        GATEWAY[API Gateway<br/>Kong/AWS ALB]
        RATE_LIMIT[Rate Limiting<br/>Throttling]
        AUTH_PROXY[Auth Proxy<br/>JWT Validation]
    end

    subgraph "Application Layer"
        AUTH_SVC[Authentication Service]
        USER_SVC[User Service]
        ORG_SVC[Organization Service]
        PROJECT_SVC[Project Service]
        BOARD_SVC[Board Service]
        ITEM_SVC[Item Service]
        NOTIFICATION_SVC[Notification Service]
        AI_SVC[AI/ML Service]
        INTEGRATION_SVC[Integration Service]
        FILE_SVC[File Service]
        ANALYTICS_SVC[Analytics Service]
        REALTIME_SVC[Real-time Service]
    end

    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>Primary Database)]
        REDIS[(Redis<br/>Cache & Sessions)]
        CLICKHOUSE[(ClickHouse<br/>Analytics)]
        ELASTICSEARCH[(Elasticsearch<br/>Search)]
        S3[(Amazon S3<br/>File Storage)]
        VECTOR_DB[(Vector Database<br/>AI Embeddings)]
    end

    subgraph "Message Layer"
        KAFKA[Apache Kafka<br/>Event Streaming]
        SQS[Amazon SQS<br/>Message Queue]
        SNS[Amazon SNS<br/>Notifications]
    end

    subgraph "External Services"
        EMAIL[SendGrid<br/>Email Service]
        SMS[Twilio<br/>SMS Service]
        MONITORING[Datadog<br/>Monitoring]
        AI_API[OpenAI<br/>AI Services]
        INTEGRATIONS[Third-party APIs<br/>Slack, Teams, etc.]
    end

    %% Client connections
    WEB --> CDN
    MOBILE --> CDN
    API_CLIENTS --> GATEWAY

    %% Edge to Gateway
    CDN --> WAF
    WAF --> LB
    LB --> GATEWAY

    %% Gateway to Auth
    GATEWAY --> RATE_LIMIT
    RATE_LIMIT --> AUTH_PROXY

    %% Auth to Services
    AUTH_PROXY --> AUTH_SVC
    AUTH_PROXY --> USER_SVC
    AUTH_PROXY --> ORG_SVC
    AUTH_PROXY --> PROJECT_SVC
    AUTH_PROXY --> BOARD_SVC
    AUTH_PROXY --> ITEM_SVC
    AUTH_PROXY --> NOTIFICATION_SVC
    AUTH_PROXY --> AI_SVC
    AUTH_PROXY --> INTEGRATION_SVC
    AUTH_PROXY --> FILE_SVC
    AUTH_PROXY --> ANALYTICS_SVC
    AUTH_PROXY --> REALTIME_SVC

    %% Services to Data
    AUTH_SVC --> POSTGRES
    AUTH_SVC --> REDIS
    USER_SVC --> POSTGRES
    USER_SVC --> REDIS
    ORG_SVC --> POSTGRES
    PROJECT_SVC --> POSTGRES
    BOARD_SVC --> POSTGRES
    ITEM_SVC --> POSTGRES
    ITEM_SVC --> ELASTICSEARCH
    NOTIFICATION_SVC --> REDIS
    AI_SVC --> VECTOR_DB
    FILE_SVC --> S3
    ANALYTICS_SVC --> CLICKHOUSE
    REALTIME_SVC --> REDIS

    %% Event streaming
    ITEM_SVC --> KAFKA
    BOARD_SVC --> KAFKA
    KAFKA --> ANALYTICS_SVC
    KAFKA --> NOTIFICATION_SVC
    KAFKA --> REALTIME_SVC

    %% External integrations
    NOTIFICATION_SVC --> EMAIL
    NOTIFICATION_SVC --> SMS
    AI_SVC --> AI_API
    INTEGRATION_SVC --> INTEGRATIONS
    ANALYTICS_SVC --> MONITORING

    %% Queue processing
    NOTIFICATION_SVC --> SQS
    SQS --> SNS

    classDef client fill:#e1f5fe
    classDef edge fill:#f3e5f5
    classDef gateway fill:#e8f5e8
    classDef service fill:#fff3e0
    classDef data fill:#fce4ec
    classDef message fill:#f1f8e9
    classDef external fill:#f5f5f5

    class WEB,MOBILE,API_CLIENTS client
    class CDN,WAF,LB edge
    class GATEWAY,RATE_LIMIT,AUTH_PROXY gateway
    class AUTH_SVC,USER_SVC,ORG_SVC,PROJECT_SVC,BOARD_SVC,ITEM_SVC,NOTIFICATION_SVC,AI_SVC,INTEGRATION_SVC,FILE_SVC,ANALYTICS_SVC,REALTIME_SVC service
    class POSTGRES,REDIS,CLICKHOUSE,ELASTICSEARCH,S3,VECTOR_DB data
    class KAFKA,SQS,SNS message
    class EMAIL,SMS,MONITORING,AI_API,INTEGRATIONS external
```

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|----------------|------------|
| **Web Application** | User interface, client-side logic | React 18, TypeScript, Vite |
| **Mobile Apps** | Native mobile experience | React Native, TypeScript |
| **API Gateway** | Request routing, authentication, rate limiting | Kong/AWS ALB |
| **Authentication Service** | User auth, JWT tokens, SSO | Node.js, Passport.js |
| **User Service** | User management, profiles | Node.js, Prisma |
| **Organization Service** | Multi-tenancy, workspace management | Node.js, Prisma |
| **Project Service** | Project lifecycle, permissions | Node.js, Prisma |
| **Board Service** | Board management, customization | Node.js, Prisma |
| **Item Service** | Work items, tasks, relationships | Node.js, Prisma |
| **Real-time Service** | Live collaboration, WebSocket | Node.js, Socket.IO |
| **AI Service** | ML models, intelligent features | Python, TensorFlow |
| **Analytics Service** | Metrics, reporting, dashboards | Node.js, ClickHouse |

---

## 🔧 Microservices Architecture

### Service Decomposition

```mermaid
graph TB
    subgraph "Core Domain Services"
        AUTH[Authentication Service<br/>- User auth<br/>- JWT tokens<br/>- SSO integration]
        USER[User Service<br/>- Profile management<br/>- User preferences<br/>- Settings]
        ORG[Organization Service<br/>- Multi-tenancy<br/>- Billing<br/>- Admin functions]
        WORKSPACE[Workspace Service<br/>- Team management<br/>- Permissions<br/>- Collaboration]
        BOARD[Board Service<br/>- Board configuration<br/>- Column management<br/>- Views]
        ITEM[Item Service<br/>- Work items<br/>- Dependencies<br/>- Assignments]
    end

    subgraph "Supporting Services"
        NOTIFICATION[Notification Service<br/>- Email/SMS<br/>- Push notifications<br/>- Preferences]
        FILE[File Service<br/>- Upload/download<br/>- Processing<br/>- CDN integration]
        SEARCH[Search Service<br/>- Full-text search<br/>- Indexing<br/>- Faceted search]
        ANALYTICS[Analytics Service<br/>- Metrics collection<br/>- Reporting<br/>- Dashboards]
        AUTOMATION[Automation Service<br/>- Workflow rules<br/>- Triggers<br/>- Actions]
    end

    subgraph "Intelligence Services"
        AI_ML[AI/ML Service<br/>- Smart suggestions<br/>- Predictive analytics<br/>- NLP processing]
        RECOMMENDATION[Recommendation Service<br/>- Content recommendations<br/>- User matching<br/>- Template suggestions]
    end

    subgraph "Integration Services"
        INTEGRATION[Integration Service<br/>- Third-party APIs<br/>- Webhook management<br/>- Data sync]
        IMPORT_EXPORT[Import/Export Service<br/>- Data migration<br/>- Bulk operations<br/>- Format conversion]
    end

    subgraph "Infrastructure Services"
        REALTIME[Real-time Service<br/>- WebSocket management<br/>- Live updates<br/>- Presence tracking]
        AUDIT[Audit Service<br/>- Activity logging<br/>- Compliance<br/>- Security events]
        CONFIG[Configuration Service<br/>- Feature flags<br/>- A/B testing<br/>- Environment config]
    end

    %% Core dependencies
    USER --> AUTH
    ORG --> USER
    WORKSPACE --> ORG
    BOARD --> WORKSPACE
    ITEM --> BOARD

    %% Supporting service dependencies
    NOTIFICATION --> USER
    FILE --> AUTH
    SEARCH --> ITEM
    ANALYTICS --> ITEM
    AUTOMATION --> ITEM

    %% Intelligence dependencies
    AI_ML --> ITEM
    RECOMMENDATION --> USER
    RECOMMENDATION --> ITEM

    %% Integration dependencies
    INTEGRATION --> AUTH
    IMPORT_EXPORT --> ORG

    %% Infrastructure dependencies
    REALTIME --> AUTH
    AUDIT --> AUTH
    CONFIG --> AUTH

    classDef core fill:#e3f2fd
    classDef supporting fill:#e8f5e8
    classDef intelligence fill:#fff3e0
    classDef integration fill:#f3e5f5
    classDef infrastructure fill:#fce4ec

    class AUTH,USER,ORG,WORKSPACE,BOARD,ITEM core
    class NOTIFICATION,FILE,SEARCH,ANALYTICS,AUTOMATION supporting
    class AI_ML,RECOMMENDATION intelligence
    class INTEGRATION,IMPORT_EXPORT integration
    class REALTIME,AUDIT,CONFIG infrastructure
```

### Service Communication Patterns

```mermaid
sequenceDiagram
    participant C as Client
    participant G as API Gateway
    participant A as Auth Service
    participant B as Board Service
    participant I as Item Service
    participant R as Real-time Service
    participant N as Notification Service
    participant DB as Database

    Note over C,DB: Create New Item Flow

    C->>G: POST /boards/123/items
    G->>A: Validate JWT token
    A-->>G: Token valid + user info
    G->>B: Check board permissions
    B->>DB: Query board & permissions
    DB-->>B: Board data + user role
    B-->>G: Permission granted
    G->>I: Create item request
    I->>DB: Insert new item
    DB-->>I: Item created
    I->>R: Emit real-time event
    I->>N: Queue notification
    I-->>G: Item response
    G-->>C: 201 Created

    Note over R,N: Async Processing
    R->>C: WebSocket: item-created
    N->>DB: Get notification preferences
    N->>External: Send email/push notification
```

---

## 💾 Data Architecture

### Database Schema Overview

```mermaid
erDiagram
    Organization ||--o{ User : has
    Organization ||--o{ Workspace : contains
    Organization ||--o{ Subscription : has

    User ||--o{ OrganizationMember : member_of
    User ||--o{ WorkspaceMember : member_of
    User ||--o{ BoardMember : member_of
    User ||--o{ ItemAssignment : assigned_to
    User ||--o{ Comment : creates
    User ||--o{ ActivityLog : generates

    Workspace ||--o{ Board : contains
    Workspace ||--o{ WorkspaceMember : has

    Board ||--o{ BoardColumn : has
    Board ||--o{ Item : contains
    Board ||--o{ BoardMember : has
    Board ||--o{ Automation : has

    Item ||--o{ ItemAssignment : has
    Item ||--o{ Comment : has
    Item ||--o{ Attachment : has
    Item ||--o{ TimeEntry : has
    Item ||--o{ ItemDependency : depends_on
    Item ||--o{ ItemLabel : tagged_with

    Organization {
        uuid id
        string name
        string slug
        string domain
        jsonb settings
        timestamp created_at
        timestamp updated_at
    }

    User {
        uuid id
        string email
        string first_name
        string last_name
        string avatar_url
        jsonb preferences
        timestamp last_login
        timestamp created_at
    }

    Workspace {
        uuid id
        uuid organization_id
        string name
        text description
        string color
        boolean is_private
        jsonb settings
        timestamp created_at
    }

    Board {
        uuid id
        uuid workspace_id
        string name
        text description
        jsonb settings
        jsonb view_settings
        boolean is_private
        timestamp created_at
    }

    Item {
        uuid id
        uuid board_id
        uuid parent_id
        string name
        text description
        jsonb data
        decimal position
        timestamp created_at
        timestamp updated_at
    }

    Comment {
        uuid id
        uuid item_id
        uuid user_id
        text content
        string content_type
        jsonb mentions
        boolean is_edited
        timestamp created_at
    }
```

### Data Flow Architecture

```mermaid
graph TB
    subgraph "Application Layer"
        API[REST/GraphQL APIs]
        WEBSOCKET[WebSocket Handlers]
        WORKERS[Background Workers]
    end

    subgraph "Caching Layer"
        REDIS_CACHE[Redis Cache<br/>- Session data<br/>- API responses<br/>- Real-time data]
        MEMORY_CACHE[In-Memory Cache<br/>- Static data<br/>- Configuration<br/>- User preferences]
    end

    subgraph "Primary Storage"
        POSTGRES[PostgreSQL<br/>- Transactional data<br/>- User accounts<br/>- Business logic]

        subgraph "Postgres Partitions"
            ORG_SHARD[Organization Shards]
            TIME_PARTITION[Time-based Partitions]
            AUDIT_PARTITION[Audit Log Partitions]
        end
    end

    subgraph "Specialized Storage"
        ELASTICSEARCH[Elasticsearch<br/>- Full-text search<br/>- Log aggregation<br/>- Analytics queries]
        CLICKHOUSE[ClickHouse<br/>- Time-series data<br/>- Analytics events<br/>- Reporting]
        S3[Amazon S3<br/>- File storage<br/>- Backups<br/>- Static assets]
        VECTOR_DB[Vector Database<br/>- AI embeddings<br/>- Semantic search<br/>- ML features]
    end

    subgraph "Event Streaming"
        KAFKA[Apache Kafka<br/>- Event sourcing<br/>- Data streaming<br/>- Service communication]

        subgraph "Kafka Topics"
            USER_EVENTS[user.events]
            ITEM_EVENTS[item.events]
            ANALYTICS_EVENTS[analytics.events]
            NOTIFICATION_EVENTS[notification.events]
        end
    end

    %% Data flow connections
    API --> REDIS_CACHE
    API --> POSTGRES
    WEBSOCKET --> REDIS_CACHE
    WORKERS --> POSTGRES

    REDIS_CACHE -.-> MEMORY_CACHE
    POSTGRES --> ORG_SHARD
    POSTGRES --> TIME_PARTITION
    POSTGRES --> AUDIT_PARTITION

    %% Event streaming
    API --> KAFKA
    WEBSOCKET --> KAFKA
    KAFKA --> USER_EVENTS
    KAFKA --> ITEM_EVENTS
    KAFKA --> ANALYTICS_EVENTS
    KAFKA --> NOTIFICATION_EVENTS

    %% Specialized storage sync
    KAFKA --> ELASTICSEARCH
    KAFKA --> CLICKHOUSE
    POSTGRES --> S3
    API --> S3

    %% AI/ML data flow
    POSTGRES --> VECTOR_DB
    KAFKA --> VECTOR_DB

    classDef application fill:#e3f2fd
    classDef cache fill:#e8f5e8
    classDef primary fill:#fff3e0
    classDef specialized fill:#f3e5f5
    classDef streaming fill:#fce4ec

    class API,WEBSOCKET,WORKERS application
    class REDIS_CACHE,MEMORY_CACHE cache
    class POSTGRES,ORG_SHARD,TIME_PARTITION,AUDIT_PARTITION primary
    class ELASTICSEARCH,CLICKHOUSE,S3,VECTOR_DB specialized
    class KAFKA,USER_EVENTS,ITEM_EVENTS,ANALYTICS_EVENTS,NOTIFICATION_EVENTS streaming
```

---

## 🔐 Security Architecture

### Zero-Trust Security Model

```mermaid
graph TB
    subgraph "External Perimeter"
        INTERNET[Internet Traffic]
        CDN[CloudFront CDN<br/>- Global edge locations<br/>- DDoS protection<br/>- SSL termination]
        WAF[Web Application Firewall<br/>- OWASP protection<br/>- Rate limiting<br/>- Geo-blocking]
    end

    subgraph "Network Security"
        VPC[Virtual Private Cloud<br/>- Isolated network<br/>- Subnet segmentation<br/>- Network ACLs]
        NAT[NAT Gateway<br/>- Outbound internet access<br/>- No inbound access]
        VPN[VPN Gateway<br/>- Secure admin access<br/>- Site-to-site connectivity]
    end

    subgraph "Application Security"
        ALB[Application Load Balancer<br/>- TLS 1.3 termination<br/>- Header validation<br/>- Health checks]

        subgraph "Security Middleware"
            AUTH_MW[Authentication Middleware<br/>- JWT validation<br/>- Token refresh<br/>- Session management]
            AUTHZ_MW[Authorization Middleware<br/>- RBAC enforcement<br/>- Permission checking<br/>- Resource isolation]
            RATE_MW[Rate Limiting<br/>- Per-user limits<br/>- API endpoint limits<br/>- Burst protection]
            VALIDATION_MW[Input Validation<br/>- Schema validation<br/>- SQL injection prevention<br/>- XSS protection]
        end
    end

    subgraph "Data Security"
        ENCRYPTION[Encryption at Rest<br/>- AES-256 encryption<br/>- Key rotation<br/>- Field-level encryption]
        TLS[Encryption in Transit<br/>- TLS 1.3<br/>- Certificate management<br/>- Perfect forward secrecy]
        BACKUP[Secure Backups<br/>- Encrypted backups<br/>- Cross-region replication<br/>- Point-in-time recovery]
    end

    subgraph "Identity & Access"
        SSO[Single Sign-On<br/>- SAML 2.0<br/>- OAuth 2.0<br/>- OpenID Connect]
        MFA[Multi-Factor Authentication<br/>- TOTP<br/>- SMS<br/>- Hardware keys]
        IAM[Identity & Access Management<br/>- User provisioning<br/>- Role management<br/>- Access reviews]
    end

    subgraph "Monitoring & Compliance"
        AUDIT[Audit Logging<br/>- Activity tracking<br/>- Compliance reports<br/>- Forensic analysis]
        SIEM[Security Information Event Management<br/>- Threat detection<br/>- Incident response<br/>- Alert correlation]
        COMPLIANCE[Compliance Framework<br/>- SOC 2 Type II<br/>- GDPR<br/>- HIPAA ready]
    end

    %% Traffic flow
    INTERNET --> CDN
    CDN --> WAF
    WAF --> VPC
    VPC --> ALB
    ALB --> AUTH_MW
    AUTH_MW --> AUTHZ_MW
    AUTHZ_MW --> RATE_MW
    RATE_MW --> VALIDATION_MW

    %% Security controls
    VPC -.-> NAT
    VPC -.-> VPN
    VALIDATION_MW -.-> ENCRYPTION
    VALIDATION_MW -.-> TLS
    ENCRYPTION -.-> BACKUP

    %% Identity integration
    AUTH_MW -.-> SSO
    AUTH_MW -.-> MFA
    AUTHZ_MW -.-> IAM

    %% Monitoring integration
    AUTH_MW -.-> AUDIT
    AUTHZ_MW -.-> AUDIT
    AUDIT -.-> SIEM
    SIEM -.-> COMPLIANCE

    classDef perimeter fill:#ffebee
    classDef network fill:#e8eaf6
    classDef application fill:#e3f2fd
    classDef data fill:#e8f5e8
    classDef identity fill:#fff3e0
    classDef monitoring fill:#f3e5f5

    class INTERNET,CDN,WAF perimeter
    class VPC,NAT,VPN network
    class ALB,AUTH_MW,AUTHZ_MW,RATE_MW,VALIDATION_MW application
    class ENCRYPTION,TLS,BACKUP data
    class SSO,MFA,IAM identity
    class AUDIT,SIEM,COMPLIANCE monitoring
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant G as API Gateway
    participant A as Auth Service
    participant SSO as SSO Provider
    participant DB as Database
    participant C as Cache

    Note over U,C: SSO Authentication Flow

    U->>F: Login attempt
    F->>A: Initiate SSO
    A->>SSO: Redirect to SSO provider
    SSO->>U: Present login form
    U->>SSO: Enter credentials + MFA
    SSO->>A: Return authorization code
    A->>SSO: Exchange code for tokens
    SSO-->>A: Access token + ID token
    A->>DB: Verify/create user account
    A->>A: Generate JWT tokens
    A->>C: Store refresh token
    A-->>F: Return JWT + refresh token
    F->>F: Store tokens securely

    Note over U,C: API Request Flow

    F->>G: API request with JWT
    G->>A: Validate JWT token
    A->>A: Verify signature + expiry
    alt Token valid
        A-->>G: User context
        G->>Service: Forward request
        Service-->>G: Response
        G-->>F: Response
    else Token expired
        A-->>G: Token expired error
        G-->>F: 401 Unauthorized
        F->>A: Refresh token request
        A->>C: Validate refresh token
        A->>A: Generate new JWT
        A-->>F: New JWT token
        F->>G: Retry with new token
    end
```

---

## 🚀 Deployment Architecture

### Multi-Environment Deployment

```mermaid
graph TB
    subgraph "Development Environment"
        DEV_CODE[Developer Workstation<br/>- Local development<br/>- Hot reload<br/>- Debug mode]
        DEV_DB[(Local Databases<br/>- PostgreSQL<br/>- Redis<br/>- Docker containers)]
        DEV_CODE -.-> DEV_DB
    end

    subgraph "CI/CD Pipeline"
        GITHUB[GitHub Repository<br/>- Source code<br/>- Pull requests<br/>- Code reviews]
        ACTIONS[GitHub Actions<br/>- Automated testing<br/>- Security scanning<br/>- Build automation]
        REGISTRY[Container Registry<br/>- Docker images<br/>- Version tagging<br/>- Vulnerability scanning]

        GITHUB --> ACTIONS
        ACTIONS --> REGISTRY
    end

    subgraph "Staging Environment"
        STAGING_K8S[Kubernetes Cluster<br/>- AWS EKS<br/>- Staging workloads<br/>- Integration testing]
        STAGING_DB[(Staging Databases<br/>- RDS instances<br/>- Masked data<br/>- Performance testing)]
        STAGING_CACHE[(Redis Cluster<br/>- ElastiCache<br/>- Session storage)]

        STAGING_K8S --> STAGING_DB
        STAGING_K8S --> STAGING_CACHE
    end

    subgraph "Production Environment"
        subgraph "Multi-Region Setup"
            US_EAST[US-East-1 (Primary)<br/>- Active workloads<br/>- Full traffic]
            US_WEST[US-West-2 (Secondary)<br/>- Standby<br/>- Disaster recovery]
        end

        subgraph "Production Infrastructure"
            PROD_K8S[Kubernetes Clusters<br/>- AWS EKS<br/>- Auto-scaling<br/>- Load balancing]
            PROD_DB[(Production Databases<br/>- RDS Multi-AZ<br/>- Read replicas<br/>- Automated backups)]
            PROD_CACHE[(Redis Clusters<br/>- ElastiCache<br/>- Cross-AZ replication)]
            PROD_STORAGE[(S3 Storage<br/>- Cross-region replication<br/>- Lifecycle policies)]
        end
    end

    subgraph "Monitoring & Observability"
        MONITORING[Monitoring Stack<br/>- Datadog APM<br/>- Prometheus<br/>- Grafana dashboards]
        LOGGING[Centralized Logging<br/>- ELK Stack<br/>- Log aggregation<br/>- Search & analytics]
        ALERTING[Alerting System<br/>- PagerDuty<br/>- Slack notifications<br/>- Email alerts]
    end

    %% Development to CI/CD
    DEV_CODE --> GITHUB

    %% CI/CD to environments
    REGISTRY --> STAGING_K8S
    REGISTRY --> PROD_K8S

    %% Production setup
    PROD_K8S --> PROD_DB
    PROD_K8S --> PROD_CACHE
    PROD_K8S --> PROD_STORAGE
    US_EAST -.-> US_WEST

    %% Monitoring connections
    STAGING_K8S -.-> MONITORING
    PROD_K8S -.-> MONITORING
    MONITORING -.-> LOGGING
    MONITORING -.-> ALERTING

    classDef dev fill:#e8f5e8
    classDef cicd fill:#e3f2fd
    classDef staging fill:#fff3e0
    classDef prod fill:#ffebee
    classDef monitoring fill:#f3e5f5

    class DEV_CODE,DEV_DB dev
    class GITHUB,ACTIONS,REGISTRY cicd
    class STAGING_K8S,STAGING_DB,STAGING_CACHE staging
    class US_EAST,US_WEST,PROD_K8S,PROD_DB,PROD_CACHE,PROD_STORAGE prod
    class MONITORING,LOGGING,ALERTING monitoring
```

### Kubernetes Architecture

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        subgraph "Control Plane"
            API_SERVER[API Server<br/>- REST API<br/>- Authentication<br/>- Authorization]
            SCHEDULER[Scheduler<br/>- Pod placement<br/>- Resource allocation]
            CONTROLLER[Controller Manager<br/>- State reconciliation<br/>- Health monitoring]
            ETCD[(etcd<br/>- Cluster state<br/>- Configuration data)]
        end

        subgraph "Worker Nodes"
            subgraph "Node Pool 1: Application Services"
                APP_NODE1[Node 1<br/>c5.2xlarge<br/>- CPU optimized<br/>- API services]
                APP_NODE2[Node 2<br/>c5.2xlarge<br/>- CPU optimized<br/>- API services]
                APP_NODE3[Node 3<br/>c5.2xlarge<br/>- CPU optimized<br/>- API services]
            end

            subgraph "Node Pool 2: Data Services"
                DATA_NODE1[Node 4<br/>r5.xlarge<br/>- Memory optimized<br/>- Caching, databases]
                DATA_NODE2[Node 5<br/>r5.xlarge<br/>- Memory optimized<br/>- Caching, databases]
            end

            subgraph "Node Pool 3: AI/ML Workloads"
                ML_NODE1[Node 6<br/>p3.2xlarge<br/>- GPU optimized<br/>- ML inference]
                ML_NODE2[Node 7<br/>p3.2xlarge<br/>- GPU optimized<br/>- ML training]
            end
        end

        subgraph "Namespaces"
            PROD_NS[sunday-prod<br/>- Production workloads<br/>- Resource quotas<br/>- Network policies]
            STAGING_NS[sunday-staging<br/>- Staging workloads<br/>- Lower resource limits]
            MONITORING_NS[monitoring<br/>- Prometheus<br/>- Grafana<br/>- Alertmanager]
            INGRESS_NS[ingress-nginx<br/>- Ingress controllers<br/>- SSL termination]
        end

        subgraph "Storage"
            EBS_CSI[EBS CSI Driver<br/>- Persistent volumes<br/>- Dynamic provisioning]
            EFS_CSI[EFS CSI Driver<br/>- Shared storage<br/>- Multi-AZ access]
        end

        subgraph "Networking"
            CNI[Calico CNI<br/>- Pod networking<br/>- Network policies<br/>- Security rules]
            INGRESS[NGINX Ingress<br/>- Load balancing<br/>- SSL termination<br/>- Path routing]
            SERVICE_MESH[Istio Service Mesh<br/>- Traffic management<br/>- Security<br/>- Observability]
        end
    end

    %% Control plane connections
    API_SERVER -.-> SCHEDULER
    API_SERVER -.-> CONTROLLER
    API_SERVER -.-> ETCD

    %% Node connections
    API_SERVER --> APP_NODE1
    API_SERVER --> APP_NODE2
    API_SERVER --> APP_NODE3
    API_SERVER --> DATA_NODE1
    API_SERVER --> DATA_NODE2
    API_SERVER --> ML_NODE1
    API_SERVER --> ML_NODE2

    %% Storage connections
    APP_NODE1 -.-> EBS_CSI
    APP_NODE2 -.-> EBS_CSI
    APP_NODE3 -.-> EBS_CSI
    DATA_NODE1 -.-> EFS_CSI
    DATA_NODE2 -.-> EFS_CSI

    %% Networking
    APP_NODE1 -.-> CNI
    APP_NODE2 -.-> CNI
    APP_NODE3 -.-> CNI
    CNI -.-> INGRESS
    INGRESS -.-> SERVICE_MESH

    classDef control fill:#e3f2fd
    classDef app fill:#e8f5e8
    classDef data fill:#fff3e0
    classDef ml fill:#f3e5f5
    classDef namespace fill:#fce4ec
    classDef storage fill:#e0f2f1
    classDef network fill:#f9fbe7

    class API_SERVER,SCHEDULER,CONTROLLER,ETCD control
    class APP_NODE1,APP_NODE2,APP_NODE3 app
    class DATA_NODE1,DATA_NODE2 data
    class ML_NODE1,ML_NODE2 ml
    class PROD_NS,STAGING_NS,MONITORING_NS,INGRESS_NS namespace
    class EBS_CSI,EFS_CSI storage
    class CNI,INGRESS,SERVICE_MESH network
```

---

## ⚡ Real-time Collaboration

### WebSocket Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB_CLIENT[Web Client<br/>React Components]
        MOBILE_CLIENT[Mobile Client<br/>React Native]
        THIRD_PARTY[Third-party Client<br/>Custom Integration]
    end

    subgraph "Connection Management"
        LB[Load Balancer<br/>- Sticky sessions<br/>- Health checks]

        subgraph "WebSocket Servers"
            WS_SERVER1[WS Server 1<br/>- Socket.IO<br/>- Connection pool]
            WS_SERVER2[WS Server 2<br/>- Socket.IO<br/>- Connection pool]
            WS_SERVER3[WS Server 3<br/>- Socket.IO<br/>- Connection pool]
        end
    end

    subgraph "Event Processing"
        EVENT_HANDLER[Event Handler<br/>- Message routing<br/>- Validation<br/>- Authorization]
        ROOM_MANAGER[Room Manager<br/>- User presence<br/>- Channel management<br/>- Broadcasting]
        CONFLICT_RESOLVER[Conflict Resolver<br/>- Operational transform<br/>- State reconciliation<br/>- Merge strategies]
    end

    subgraph "State Management"
        REDIS_PUBSUB[Redis Pub/Sub<br/>- Message broadcasting<br/>- Cross-server communication]
        REDIS_STATE[Redis State Store<br/>- User presence<br/>- Active sessions<br/>- Temporary data]
        OPERATION_LOG[Operation Log<br/>- Change history<br/>- Conflict resolution<br/>- Replay capability]
    end

    subgraph "Business Logic"
        ITEM_SERVICE[Item Service<br/>- Data persistence<br/>- Business rules<br/>- Validation]
        PERMISSION_SERVICE[Permission Service<br/>- Access control<br/>- Resource isolation<br/>- Audit logging]
        NOTIFICATION_SERVICE[Notification Service<br/>- Push notifications<br/>- Email alerts<br/>- Activity feeds]
    end

    %% Client connections
    WEB_CLIENT --> LB
    MOBILE_CLIENT --> LB
    THIRD_PARTY --> LB

    %% Load balancer distribution
    LB --> WS_SERVER1
    LB --> WS_SERVER2
    LB --> WS_SERVER3

    %% WebSocket server processing
    WS_SERVER1 --> EVENT_HANDLER
    WS_SERVER2 --> EVENT_HANDLER
    WS_SERVER3 --> EVENT_HANDLER

    EVENT_HANDLER --> ROOM_MANAGER
    ROOM_MANAGER --> CONFLICT_RESOLVER

    %% State management
    ROOM_MANAGER --> REDIS_PUBSUB
    CONFLICT_RESOLVER --> REDIS_STATE
    CONFLICT_RESOLVER --> OPERATION_LOG

    %% Cross-server communication
    REDIS_PUBSUB -.-> WS_SERVER1
    REDIS_PUBSUB -.-> WS_SERVER2
    REDIS_PUBSUB -.-> WS_SERVER3

    %% Business logic integration
    EVENT_HANDLER --> ITEM_SERVICE
    EVENT_HANDLER --> PERMISSION_SERVICE
    ROOM_MANAGER --> NOTIFICATION_SERVICE

    classDef client fill:#e3f2fd
    classDef connection fill:#e8f5e8
    classDef processing fill:#fff3e0
    classDef state fill:#f3e5f5
    classDef business fill:#fce4ec

    class WEB_CLIENT,MOBILE_CLIENT,THIRD_PARTY client
    class LB,WS_SERVER1,WS_SERVER2,WS_SERVER3 connection
    class EVENT_HANDLER,ROOM_MANAGER,CONFLICT_RESOLVER processing
    class REDIS_PUBSUB,REDIS_STATE,OPERATION_LOG state
    class ITEM_SERVICE,PERMISSION_SERVICE,NOTIFICATION_SERVICE business
```

### Real-time Event Flow

```mermaid
sequenceDiagram
    participant U1 as User 1 (Web)
    participant U2 as User 2 (Mobile)
    participant WS1 as WebSocket Server 1
    participant WS2 as WebSocket Server 2
    participant RM as Room Manager
    participant CR as Conflict Resolver
    participant RS as Redis State
    participant RP as Redis Pub/Sub
    participant IS as Item Service

    Note over U1,IS: Real-time Collaboration Flow

    U1->>WS1: Connect to board channel
    WS1->>RM: Join room "board:123"
    RM->>RS: Store user presence
    RM->>RP: Broadcast user joined
    RP->>WS2: User joined event
    WS2->>U2: Notify user presence

    Note over U1,IS: User 1 edits item

    U1->>WS1: Update item: "Change title"
    WS1->>RM: Validate permissions
    RM->>CR: Process operation
    CR->>RS: Check for conflicts

    alt No conflicts
        CR->>IS: Persist change
        IS-->>CR: Change saved
        CR->>RP: Broadcast change
        RP->>WS1: Change event
        RP->>WS2: Change event
        WS1->>U1: Confirm update
        WS2->>U2: Live update
    else Conflict detected
        CR->>CR: Resolve using OT
        CR->>IS: Save merged change
        CR->>RP: Broadcast resolved change
        RP->>WS1: Resolved change
        RP->>WS2: Resolved change
        WS1->>U1: Show resolved version
        WS2->>U2: Show resolved version
    end

    Note over U1,IS: User presence updates

    U1->>WS1: Cursor movement
    WS1->>RM: Update cursor position
    RM->>RS: Store cursor data
    RM->>RP: Broadcast cursor update
    RP->>WS2: Cursor event
    WS2->>U2: Show User 1 cursor

    U1->>WS1: Start typing
    WS1->>RM: Typing indicator
    RM->>RP: Broadcast typing
    RP->>WS2: Typing event
    WS2->>U2: Show "User 1 is typing"
```

---

## 📡 API Architecture

### API Layer Design

```mermaid
graph TB
    subgraph "Client Applications"
        WEB_APP[Web Application<br/>React SPA]
        MOBILE_APP[Mobile Application<br/>React Native]
        THIRD_PARTY[Third-party Apps<br/>Integrations]
        CLI_TOOLS[CLI Tools<br/>Developer utilities]
    end

    subgraph "API Gateway Layer"
        EDGE_GATEWAY[Edge Gateway<br/>- Global distribution<br/>- DDoS protection<br/>- Caching]

        subgraph "API Gateway Cluster"
            GATEWAY_1[Gateway Instance 1<br/>Kong API Gateway]
            GATEWAY_2[Gateway Instance 2<br/>Kong API Gateway]
            GATEWAY_3[Gateway Instance 3<br/>Kong API Gateway]
        end

        subgraph "Gateway Features"
            RATE_LIMITING[Rate Limiting<br/>- Per-user limits<br/>- API endpoint limits<br/>- Burst protection]
            AUTH_PLUGIN[Authentication<br/>- JWT validation<br/>- API key validation<br/>- OAuth verification]
            TRANSFORM[Request Transform<br/>- Header manipulation<br/>- Body transformation<br/>- Response formatting]
            ANALYTICS[API Analytics<br/>- Usage metrics<br/>- Performance monitoring<br/>- Error tracking]
        end
    end

    subgraph "API Endpoints"
        REST_API[REST API v1<br/>- CRUD operations<br/>- Resource management<br/>- Standard HTTP methods]
        GRAPHQL_API[GraphQL API<br/>- Flexible queries<br/>- Real-time subscriptions<br/>- Schema introspection]
        WEBHOOK_API[Webhook API<br/>- Event delivery<br/>- Retry logic<br/>- Signature verification]
        BATCH_API[Batch API<br/>- Bulk operations<br/>- Long-running tasks<br/>- Job management]
    end

    subgraph "Business Services"
        AUTH_SERVICE[Authentication Service<br/>- User management<br/>- Token generation<br/>- Permission validation]
        CORE_SERVICES[Core Services<br/>- Organization<br/>- Workspace<br/>- Board management]
        DATA_SERVICES[Data Services<br/>- Item management<br/>- Search<br/>- Analytics]
        INTEGRATION_SERVICES[Integration Services<br/>- Third-party APIs<br/>- Webhook management<br/>- Data sync]
    end

    %% Client connections
    WEB_APP --> EDGE_GATEWAY
    MOBILE_APP --> EDGE_GATEWAY
    THIRD_PARTY --> EDGE_GATEWAY
    CLI_TOOLS --> EDGE_GATEWAY

    %% Gateway distribution
    EDGE_GATEWAY --> GATEWAY_1
    EDGE_GATEWAY --> GATEWAY_2
    EDGE_GATEWAY --> GATEWAY_3

    %% Gateway features
    GATEWAY_1 --> RATE_LIMITING
    GATEWAY_1 --> AUTH_PLUGIN
    GATEWAY_1 --> TRANSFORM
    GATEWAY_1 --> ANALYTICS

    %% API routing
    AUTH_PLUGIN --> REST_API
    AUTH_PLUGIN --> GRAPHQL_API
    AUTH_PLUGIN --> WEBHOOK_API
    AUTH_PLUGIN --> BATCH_API

    %% Service connections
    REST_API --> AUTH_SERVICE
    REST_API --> CORE_SERVICES
    REST_API --> DATA_SERVICES
    GRAPHQL_API --> CORE_SERVICES
    GRAPHQL_API --> DATA_SERVICES
    WEBHOOK_API --> INTEGRATION_SERVICES
    BATCH_API --> DATA_SERVICES

    classDef client fill:#e3f2fd
    classDef gateway fill:#e8f5e8
    classDef features fill:#fff3e0
    classDef api fill:#f3e5f5
    classDef service fill:#fce4ec

    class WEB_APP,MOBILE_APP,THIRD_PARTY,CLI_TOOLS client
    class EDGE_GATEWAY,GATEWAY_1,GATEWAY_2,GATEWAY_3 gateway
    class RATE_LIMITING,AUTH_PLUGIN,TRANSFORM,ANALYTICS features
    class REST_API,GRAPHQL_API,WEBHOOK_API,BATCH_API api
    class AUTH_SERVICE,CORE_SERVICES,DATA_SERVICES,INTEGRATION_SERVICES service
```

---

## 🎯 User Journey Flows

### User Onboarding Flow

```mermaid
flowchart TD
    START[User visits Sunday.com] --> SIGNUP{Sign up method}

    SIGNUP -->|Email| EMAIL_SIGNUP[Email Registration]
    SIGNUP -->|SSO| SSO_SIGNUP[SSO Registration]
    SIGNUP -->|Invitation| INVITE_SIGNUP[Team Invitation]

    EMAIL_SIGNUP --> EMAIL_VERIFY[Email Verification]
    EMAIL_VERIFY --> PROFILE_SETUP[Profile Setup]

    SSO_SIGNUP --> SSO_AUTH[SSO Authentication]
    SSO_AUTH --> PROFILE_SETUP

    INVITE_SIGNUP --> INVITE_ACCEPT[Accept Invitation]
    INVITE_ACCEPT --> PROFILE_SETUP

    PROFILE_SETUP --> ORG_SETUP{Organization exists?}

    ORG_SETUP -->|No| CREATE_ORG[Create Organization]
    ORG_SETUP -->|Yes| JOIN_ORG[Join Organization]

    CREATE_ORG --> WORKSPACE_SETUP[Create First Workspace]
    JOIN_ORG --> WORKSPACE_SETUP

    WORKSPACE_SETUP --> BOARD_SETUP[Create First Board]
    BOARD_SETUP --> TEMPLATE_SELECT[Select Template]
    TEMPLATE_SELECT --> BOARD_CUSTOMIZE[Customize Board]
    BOARD_CUSTOMIZE --> INVITE_TEAM[Invite Team Members]
    INVITE_TEAM --> TUTORIAL[Interactive Tutorial]
    TUTORIAL --> FIRST_ITEM[Create First Item]
    FIRST_ITEM --> ONBOARDING_COMPLETE[Onboarding Complete]

    classDef start fill:#e8f5e8
    classDef process fill:#e3f2fd
    classDef decision fill:#fff3e0
    classDef end fill:#fce4ec

    class START,ONBOARDING_COMPLETE start
    class EMAIL_SIGNUP,SSO_SIGNUP,INVITE_SIGNUP,EMAIL_VERIFY,PROFILE_SETUP,SSO_AUTH,INVITE_ACCEPT,CREATE_ORG,JOIN_ORG,WORKSPACE_SETUP,BOARD_SETUP,TEMPLATE_SELECT,BOARD_CUSTOMIZE,INVITE_TEAM,TUTORIAL,FIRST_ITEM process
    class SIGNUP,ORG_SETUP decision
```

### Item Creation & Collaboration Flow

```mermaid
flowchart TD
    USER_ACTION[User creates new item] --> VALIDATE_PERMS{Has permissions?}

    VALIDATE_PERMS -->|No| ACCESS_DENIED[Access Denied]
    VALIDATE_PERMS -->|Yes| CREATE_ITEM[Create Item in Database]

    CREATE_ITEM --> EMIT_EVENT[Emit Real-time Event]
    EMIT_EVENT --> NOTIFY_USERS[Notify Relevant Users]

    NOTIFY_USERS --> UPDATE_UI[Update UI for All Users]
    UPDATE_UI --> TRIGGER_AUTOMATION{Automation rules?}

    TRIGGER_AUTOMATION -->|Yes| RUN_AUTOMATION[Execute Automation]
    TRIGGER_AUTOMATION -->|No| LOG_ACTIVITY[Log Activity]

    RUN_AUTOMATION --> AUTO_ASSIGN[Auto-assign Users]
    AUTO_ASSIGN --> SEND_NOTIFICATIONS[Send Notifications]
    SEND_NOTIFICATIONS --> LOG_ACTIVITY

    LOG_ACTIVITY --> UPDATE_ANALYTICS[Update Analytics]
    UPDATE_ANALYTICS --> INDEX_SEARCH[Index for Search]
    INDEX_SEARCH --> PROCESS_COMPLETE[Process Complete]

    %% Parallel processes
    EMIT_EVENT --> AI_PROCESSING[AI Processing]
    AI_PROCESSING --> GENERATE_SUGGESTIONS[Generate Suggestions]
    GENERATE_SUGGESTIONS --> UPDATE_ML_MODELS[Update ML Models]

    classDef action fill:#e8f5e8
    classDef process fill:#e3f2fd
    classDef decision fill:#fff3e0
    classDef ai fill:#f3e5f5
    classDef end fill:#fce4ec

    class USER_ACTION action
    class CREATE_ITEM,EMIT_EVENT,NOTIFY_USERS,UPDATE_UI,RUN_AUTOMATION,AUTO_ASSIGN,SEND_NOTIFICATIONS,LOG_ACTIVITY,UPDATE_ANALYTICS,INDEX_SEARCH process
    class VALIDATE_PERMS,TRIGGER_AUTOMATION decision
    class AI_PROCESSING,GENERATE_SUGGESTIONS,UPDATE_ML_MODELS ai
    class ACCESS_DENIED,PROCESS_COMPLETE end
```

---

## 📊 Performance Architecture

### Caching Strategy

```mermaid
graph TB
    subgraph "Client-Side Caching"
        BROWSER_CACHE[Browser Cache<br/>- Static assets<br/>- API responses<br/>- Local storage]
        APP_CACHE[App Cache<br/>- React Query<br/>- Component state<br/>- Offline data]
    end

    subgraph "CDN Layer"
        CLOUDFRONT[CloudFront CDN<br/>- Global edge locations<br/>- Static asset caching<br/>- Dynamic content acceleration]
        EDGE_CACHE[Edge Cache<br/>- API response caching<br/>- Personalized content<br/>- Smart invalidation]
    end

    subgraph "Application Layer"
        API_CACHE[API Response Cache<br/>- Redis cluster<br/>- TTL-based expiry<br/>- Tag-based invalidation]
        SESSION_CACHE[Session Cache<br/>- User sessions<br/>- Authentication state<br/>- Preferences]
        QUERY_CACHE[Query Result Cache<br/>- Database query results<br/>- Computed values<br/>- Expensive operations]
    end

    subgraph "Database Layer"
        PG_CACHE[PostgreSQL Buffer Cache<br/>- Query plan cache<br/>- Index cache<br/>- Connection pooling]
        REDIS_CACHE[Redis Cache<br/>- Hot data<br/>- Computed results<br/>- Temporary storage]
        ES_CACHE[Elasticsearch Cache<br/>- Search results<br/>- Aggregation cache<br/>- Filter cache]
    end

    subgraph "Cache Invalidation"
        EVENT_INVALIDATION[Event-driven Invalidation<br/>- Real-time updates<br/>- Dependency tracking<br/>- Cascade invalidation]
        TTL_INVALIDATION[TTL-based Invalidation<br/>- Time-based expiry<br/>- Stale data handling<br/>- Refresh strategies]
        MANUAL_INVALIDATION[Manual Invalidation<br/>- Admin controls<br/>- Bulk operations<br/>- Emergency clearing]
    end

    %% Cache hierarchy
    BROWSER_CACHE --> CLOUDFRONT
    APP_CACHE --> EDGE_CACHE
    CLOUDFRONT --> API_CACHE
    EDGE_CACHE --> SESSION_CACHE
    API_CACHE --> QUERY_CACHE
    SESSION_CACHE --> REDIS_CACHE
    QUERY_CACHE --> PG_CACHE
    REDIS_CACHE --> ES_CACHE

    %% Invalidation connections
    EVENT_INVALIDATION -.-> API_CACHE
    EVENT_INVALIDATION -.-> QUERY_CACHE
    EVENT_INVALIDATION -.-> REDIS_CACHE
    TTL_INVALIDATION -.-> CLOUDFRONT
    TTL_INVALIDATION -.-> SESSION_CACHE
    MANUAL_INVALIDATION -.-> EDGE_CACHE

    classDef client fill:#e3f2fd
    classDef cdn fill:#e8f5e8
    classDef app fill:#fff3e0
    classDef db fill:#f3e5f5
    classDef invalidation fill:#fce4ec

    class BROWSER_CACHE,APP_CACHE client
    class CLOUDFRONT,EDGE_CACHE cdn
    class API_CACHE,SESSION_CACHE,QUERY_CACHE app
    class PG_CACHE,REDIS_CACHE,ES_CACHE db
    class EVENT_INVALIDATION,TTL_INVALIDATION,MANUAL_INVALIDATION invalidation
```

---

## 🔍 Monitoring & Observability

### Observability Stack

```mermaid
graph TB
    subgraph "Data Collection"
        METRICS[Metrics Collection<br/>- Prometheus exporters<br/>- Custom metrics<br/>- Business metrics]
        LOGS[Log Collection<br/>- Structured logging<br/>- Application logs<br/>- System logs]
        TRACES[Distributed Tracing<br/>- Jaeger tracing<br/>- Request correlation<br/>- Performance profiling]
        EVENTS[Event Collection<br/>- User events<br/>- System events<br/>- Business events]
    end

    subgraph "Data Processing"
        AGGREGATION[Data Aggregation<br/>- Metric rollups<br/>- Log parsing<br/>- Trace analysis]
        ENRICHMENT[Data Enrichment<br/>- Context addition<br/>- Metadata tagging<br/>- Correlation analysis]
        FILTERING[Data Filtering<br/>- Noise reduction<br/>- Pattern detection<br/>- Anomaly detection]
    end

    subgraph "Storage"
        TSDB[Time Series DB<br/>- Prometheus<br/>- InfluxDB<br/>- Metrics storage]
        LOG_STORE[Log Storage<br/>- Elasticsearch<br/>- CloudWatch Logs<br/>- Searchable logs]
        TRACE_STORE[Trace Storage<br/>- Jaeger backend<br/>- Cassandra<br/>- Trace analysis]
    end

    subgraph "Visualization"
        DASHBOARDS[Monitoring Dashboards<br/>- Grafana<br/>- Real-time charts<br/>- Custom views]
        ANALYTICS[Analytics Platform<br/>- Data exploration<br/>- Business intelligence<br/>- Custom reports]
        SEARCH[Log Search & Analysis<br/>- Kibana<br/>- Full-text search<br/>- Log correlation]
    end

    subgraph "Alerting"
        ALERT_RULES[Alert Rules<br/>- Threshold alerts<br/>- Trend analysis<br/>- Composite conditions]
        NOTIFICATION[Notification Routing<br/>- PagerDuty<br/>- Slack integration<br/>- Email alerts]
        ESCALATION[Escalation Policies<br/>- On-call rotation<br/>- Severity levels<br/>- Auto-resolution]
    end

    %% Data flow
    METRICS --> AGGREGATION
    LOGS --> AGGREGATION
    TRACES --> AGGREGATION
    EVENTS --> AGGREGATION

    AGGREGATION --> ENRICHMENT
    ENRICHMENT --> FILTERING

    FILTERING --> TSDB
    FILTERING --> LOG_STORE
    FILTERING --> TRACE_STORE

    TSDB --> DASHBOARDS
    LOG_STORE --> SEARCH
    TRACE_STORE --> ANALYTICS

    DASHBOARDS --> ALERT_RULES
    SEARCH --> ALERT_RULES
    ANALYTICS --> ALERT_RULES

    ALERT_RULES --> NOTIFICATION
    NOTIFICATION --> ESCALATION

    classDef collection fill:#e3f2fd
    classDef processing fill:#e8f5e8
    classDef storage fill:#fff3e0
    classDef visualization fill:#f3e5f5
    classDef alerting fill:#fce4ec

    class METRICS,LOGS,TRACES,EVENTS collection
    class AGGREGATION,ENRICHMENT,FILTERING processing
    class TSDB,LOG_STORE,TRACE_STORE storage
    class DASHBOARDS,ANALYTICS,SEARCH visualization
    class ALERT_RULES,NOTIFICATION,ESCALATION alerting
```

---

## 📝 Conclusion

This architecture documentation provides a comprehensive view of Sunday.com's technical design, from high-level system architecture to detailed component interactions. The diagrams serve as a reference for:

### For Developers
- **Understanding system boundaries** and service interactions
- **Implementing new features** within the existing architecture
- **Debugging issues** by tracing data flow through components
- **Planning integrations** with external systems

### For Architects
- **Reviewing design decisions** and architectural patterns
- **Planning system evolution** and scaling strategies
- **Identifying optimization opportunities** and bottlenecks
- **Ensuring consistency** across different system components

### For Operations Teams
- **Understanding deployment architecture** and infrastructure
- **Planning capacity** and scaling requirements
- **Implementing monitoring** and observability
- **Managing security** and compliance requirements

### For Stakeholders
- **Visualizing system complexity** and technical investment
- **Understanding scalability** and growth capabilities
- **Assessing security** and compliance posture
- **Planning technical roadmap** and resource allocation

These architectural diagrams are living documents that should be updated as the system evolves. They represent the current state and planned architecture for Sunday.com's work management platform.

---

*Document Version: 1.0*
*Created: December 2024*
*Next Review: Q1 2025*