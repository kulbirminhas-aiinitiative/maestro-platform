# Sunday.com Backend API

A comprehensive work management platform backend built with Node.js, TypeScript, and PostgreSQL. This backend provides enterprise-grade APIs for managing projects, teams, and workflows with real-time collaboration, AI-powered features, and comprehensive automation capabilities.

## 🚀 Features

- **RESTful API** with comprehensive endpoints for work management
- **GraphQL API** for flexible data querying (planned)
- **Real-time collaboration** with WebSocket support
- **Enterprise-grade security** with JWT authentication and RBAC
- **Scalable architecture** with Redis caching and event-driven design
- **Comprehensive validation** and error handling
- **Database-first design** with Prisma ORM
- **Type-safe development** with TypeScript
- **Production-ready** with logging, monitoring, and health checks

## 📋 Prerequisites

- Node.js 18+ and npm 8+
- PostgreSQL 14+
- Redis 6+
- TypeScript 5+

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sunday_com/backend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Environment setup**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Database setup**
   ```bash
   # Generate Prisma client
   npm run generate

   # Run database migrations
   npm run migrate
   ```

5. **Start development server**
   ```bash
   npm run dev
   ```

## 📚 API Documentation

### Base URL
```
http://localhost:3000/api/v1
```

### Authentication
All protected endpoints require a Bearer token in the Authorization header:
```
Authorization: Bearer <jwt_token>
```

### Core Endpoints

#### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - User logout
- `GET /auth/me` - Get current user profile
- `PUT /auth/me` - Update user profile
- `POST /auth/change-password` - Change password
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password

#### Organizations
- `GET /organizations` - List user's organizations
- `POST /organizations` - Create organization
- `GET /organizations/:id` - Get organization details
- `PUT /organizations/:id` - Update organization
- `DELETE /organizations/:id` - Delete organization
- `GET /organizations/:id/members` - List members
- `POST /organizations/:id/members` - Invite member
- `PUT /organizations/:id/members/:userId` - Update member role
- `DELETE /organizations/:id/members/:userId` - Remove member
- `GET /organizations/:id/stats` - Get organization statistics

### Response Format

#### Success Response
```json
{
  "data": {
    // Response data
  },
  "meta": {
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "totalPages": 5,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

#### Error Response
```json
{
  "error": {
    "type": "validation_error",
    "message": "Invalid input parameters",
    "details": {
      "field": ["Error message"]
    },
    "requestId": "req_123abc"
  }
}
```

### Status Codes
- `200` - Success
- `201` - Created
- `204` - No Content
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

## 🏗️ Architecture

### Tech Stack
- **Runtime**: Node.js 20 LTS
- **Language**: TypeScript 5.3
- **Framework**: Express.js with Fastify (planned migration)
- **Database**: PostgreSQL 15 with Prisma ORM
- **Cache**: Redis 7
- **Authentication**: JWT with bcrypt
- **Validation**: Joi
- **Real-time**: Socket.IO
- **Testing**: Jest with supertest
- **Logging**: Winston
- **Documentation**: OpenAPI 3.0

### Project Structure
```
src/
├── __tests__/           # Test files
├── config/              # Configuration files
│   ├── database.ts      # Database connection
│   ├── redis.ts         # Redis configuration
│   ├── logger.ts        # Logging setup
│   └── index.ts         # Main config
├── middleware/          # Express middleware
│   ├── auth.ts          # Authentication middleware
│   ├── validation.ts    # Request validation
│   └── error.ts         # Error handling
├── routes/              # API route definitions
│   ├── auth.routes.ts   # Authentication routes
│   ├── organization.routes.ts
│   └── index.ts         # Route aggregation
├── services/            # Business logic services
│   ├── auth.service.ts  # Authentication service
│   ├── organization.service.ts
│   └── ...
├── types/               # TypeScript type definitions
│   └── index.ts
├── utils/               # Utility functions
└── server.ts            # Main server file
```

## 🔒 Security Features

- **JWT Authentication** with access and refresh tokens
- **Role-Based Access Control (RBAC)** with granular permissions
- **Rate Limiting** to prevent abuse
- **Input Validation** with Joi schemas
- **SQL Injection Prevention** with Prisma ORM
- **CORS Protection** with configurable origins
- **Helmet.js** for security headers
- **Password Hashing** with bcrypt
- **Request ID Tracking** for audit trails
- **Secure Headers** and CSP policies

## 📊 Database Schema

### Core Entities
- **Organizations** - Multi-tenant organizations
- **Users** - User accounts and profiles
- **Workspaces** - Project containers within organizations
- **Boards** - Kanban-style work boards
- **Items** - Tasks and work items
- **Comments** - Collaboration and discussions
- **Files** - File attachments and storage
- **Activity Logs** - Audit trail and history

### Key Relationships
```
Organization (1) -> (*) Workspace (1) -> (*) Board (1) -> (*) Item
User (*) <-> (*) Organization (through OrganizationMember)
User (*) <-> (*) Workspace (through WorkspaceMember)
Item (1) -> (*) Comment
Item (*) <-> (*) User (through ItemAssignment)
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test auth.service.test.ts
```

### Test Structure
- **Unit Tests** - Individual service and utility functions
- **Integration Tests** - API endpoint testing
- **E2E Tests** - Complete user flow testing

## 📈 Performance & Monitoring

### Caching Strategy
- **Redis** for application-level caching
- **Query result caching** for expensive database operations
- **User session storage** in Redis
- **Rate limiting counters** in Redis

### Logging
- **Structured logging** with Winston
- **Request/response logging** with Morgan
- **Performance metrics** tracking
- **Error tracking** with detailed context

### Health Checks
- `GET /health` - Basic health check
- Database connectivity check
- Redis connectivity check
- Service dependency status

## 🚀 Deployment

### Environment Variables
Required environment variables (see `.env.example`):
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET` - JWT signing secret
- `JWT_REFRESH_SECRET` - Refresh token secret

### Production Deployment
1. Build the application:
   ```bash
   npm run build
   ```

2. Start the production server:
   ```bash
   npm start
   ```

3. Run database migrations:
   ```bash
   npm run migrate:prod
   ```

## 🔄 Real-time Features

### WebSocket Events
- **Board Updates** - Real-time item changes
- **User Presence** - Show online users and cursors
- **Typing Indicators** - Live typing status
- **Comment Notifications** - Instant comment updates

### Connection Authentication
WebSocket connections require JWT token authentication:
```javascript
const socket = io('ws://localhost:3000', {
  auth: {
    token: 'your-jwt-token'
  }
});
```

## 📝 API Examples

### Register a new user
```bash
curl -X POST http://localhost:3000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "Password123!",
    "firstName": "John",
    "lastName": "Doe"
  }'
```

### Create an organization
```bash
curl -X POST http://localhost:3000/api/v1/organizations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Company",
    "slug": "my-company",
    "domain": "mycompany.com"
  }'
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes and add tests
4. Run tests: `npm test`
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin feature/new-feature`
7. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the API documentation
- Review the test files for usage examples
- Open an issue on GitHub
- Contact the development team

---

Built with ❤️ by the Sunday.com team