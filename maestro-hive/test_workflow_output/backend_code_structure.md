# Backend Code Structure

## Project Directory Structure

```
user-management-api/
├── src/
│   ├── config/                      # Configuration files
│   │   ├── database.js              # Database configuration
│   │   ├── server.js                # Server configuration
│   │   ├── jwt.js                   # JWT configuration
│   │   └── constants.js             # Application constants
│   │
│   ├── controllers/                 # Request handlers
│   │   ├── userController.js        # User CRUD operations
│   │   ├── authController.js        # Authentication operations
│   │   └── healthController.js      # Health check endpoints
│   │
│   ├── services/                    # Business logic layer
│   │   ├── userService.js           # User business logic
│   │   ├── authService.js           # Authentication logic
│   │   ├── auditService.js          # Audit logging
│   │   └── emailService.js          # Email notifications
│   │
│   ├── repositories/                # Data access layer
│   │   ├── userRepository.js        # User data operations
│   │   ├── auditRepository.js       # Audit log operations
│   │   └── tokenRepository.js       # Token operations
│   │
│   ├── models/                      # Database models
│   │   ├── User.js                  # User model
│   │   ├── UserProfile.js           # User profile model
│   │   ├── Role.js                  # Role model
│   │   ├── UserRole.js              # User-role association
│   │   ├── AuditLog.js              # Audit log model
│   │   ├── PasswordResetToken.js    # Password reset model
│   │   └── EmailVerificationToken.js # Email verification model
│   │
│   ├── middleware/                  # Express middleware
│   │   ├── authentication.js        # JWT authentication
│   │   ├── authorization.js         # Permission checks
│   │   ├── validation.js            # Request validation
│   │   ├── errorHandler.js          # Global error handler
│   │   ├── logger.js                # Request logging
│   │   ├── rateLimiter.js           # Rate limiting
│   │   └── cors.js                  # CORS configuration
│   │
│   ├── routes/                      # Route definitions
│   │   ├── index.js                 # Route aggregator
│   │   ├── v1/                      # API version 1
│   │   │   ├── userRoutes.js        # User routes
│   │   │   ├── authRoutes.js        # Auth routes
│   │   │   └── healthRoutes.js      # Health routes
│   │   └── v2/                      # API version 2 (future)
│   │
│   ├── validators/                  # Input validation schemas
│   │   ├── userValidator.js         # User validation schemas
│   │   └── authValidator.js         # Auth validation schemas
│   │
│   ├── utils/                       # Utility functions
│   │   ├── passwordHasher.js        # Password hashing
│   │   ├── tokenGenerator.js        # JWT token generation
│   │   ├── errorTypes.js            # Custom error classes
│   │   ├── responseFormatter.js     # Response formatting
│   │   └── queryBuilder.js          # Query helper utilities
│   │
│   ├── database/                    # Database management
│   │   ├── connection.js            # Database connection
│   │   ├── migrations/              # Database migrations
│   │   │   ├── 001_create_users.sql
│   │   │   ├── 002_create_roles.sql
│   │   │   └── 003_create_audit_log.sql
│   │   └── seeds/                   # Seed data
│   │       └── 001_default_roles.sql
│   │
│   ├── types/                       # TypeScript definitions (if using TS)
│   │   ├── user.d.ts                # User types
│   │   ├── api.d.ts                 # API types
│   │   └── common.d.ts              # Common types
│   │
│   ├── app.js                       # Express app setup
│   └── server.js                    # Server entry point
│
├── tests/                           # Test files
│   ├── unit/                        # Unit tests
│   │   ├── services/
│   │   │   └── userService.test.js
│   │   ├── repositories/
│   │   │   └── userRepository.test.js
│   │   └── utils/
│   │       └── passwordHasher.test.js
│   │
│   ├── integration/                 # Integration tests
│   │   ├── userApi.test.js
│   │   └── authApi.test.js
│   │
│   ├── e2e/                         # End-to-end tests
│   │   └── userFlow.test.js
│   │
│   ├── fixtures/                    # Test fixtures
│   │   └── users.json
│   │
│   └── helpers/                     # Test helpers
│       ├── testDatabase.js
│       └── testServer.js
│
├── docs/                            # Documentation
│   ├── api/                         # API documentation
│   │   └── openapi.yaml             # OpenAPI specification
│   ├── architecture/                # Architecture docs
│   │   └── system-design.md
│   └── deployment/                  # Deployment guides
│       └── production-setup.md
│
├── scripts/                         # Utility scripts
│   ├── migrate.js                   # Run migrations
│   ├── seed.js                      # Seed database
│   └── cleanupTokens.js             # Cleanup expired tokens
│
├── .env.example                     # Environment variables template
├── .gitignore                       # Git ignore rules
├── .dockerignore                    # Docker ignore rules
├── Dockerfile                       # Docker configuration
├── docker-compose.yml               # Docker Compose setup
├── package.json                     # NPM dependencies
├── package-lock.json                # NPM lock file
├── jest.config.js                   # Jest configuration
├── .eslintrc.js                     # ESLint configuration
├── .prettierrc                      # Prettier configuration
└── README.md                        # Project documentation
```

## Core Components

### 1. Controllers (API Layer)

**Purpose**: Handle HTTP requests and responses

**Example: userController.js**
```javascript
class UserController {
  async createUser(req, res, next) {
    // 1. Extract data from request
    // 2. Call service layer
    // 3. Format and send response
  }

  async getUsers(req, res, next) {
    // Handle list with pagination, filtering, sorting
  }

  async getUserById(req, res, next) {
    // Handle single user retrieval
  }

  async updateUser(req, res, next) {
    // Handle full update
  }

  async patchUser(req, res, next) {
    // Handle partial update
  }

  async deleteUser(req, res, next) {
    // Handle soft delete
  }
}
```

### 2. Services (Business Logic Layer)

**Purpose**: Implement business rules and orchestrate operations

**Example: userService.js**
```javascript
class UserService {
  constructor(userRepository, auditService, emailService) {
    this.userRepository = userRepository;
    this.auditService = auditService;
    this.emailService = emailService;
  }

  async createUser(userData) {
    // 1. Validate business rules
    // 2. Check for duplicates
    // 3. Hash password
    // 4. Create user via repository
    // 5. Log audit event
    // 6. Send welcome email (async)
    // 7. Return sanitized user data
  }

  async updateUser(userId, updateData) {
    // 1. Verify user exists
    // 2. Validate update permissions
    // 3. Apply updates via repository
    // 4. Log changes
    // 5. Return updated user
  }

  async searchUsers(filters, pagination) {
    // Implement search with business logic
  }

  async softDeleteUser(userId) {
    // Implement soft delete logic
  }
}
```

### 3. Repositories (Data Access Layer)

**Purpose**: Interact with database, execute queries

**Example: userRepository.js**
```javascript
class UserRepository {
  async create(userData) {
    // Execute INSERT query
    // Return created user
  }

  async findById(id) {
    // Execute SELECT by ID
    // Return user or null
  }

  async findByEmail(email) {
    // Execute SELECT by email
    // Return user or null
  }

  async findByUsername(username) {
    // Execute SELECT by username
    // Return user or null
  }

  async findAll(filters, pagination) {
    // Execute SELECT with filters
    // Return paginated results
  }

  async update(id, data) {
    // Execute UPDATE
    // Return updated user
  }

  async softDelete(id) {
    // Set deleted_at timestamp
    // Return success status
  }

  async search(searchTerm, pagination) {
    // Full-text search query
    // Return matching users
  }
}
```

### 4. Models (ORM Definitions)

**Purpose**: Define database schema and relationships

**Example: User.js (Sequelize)**
```javascript
module.exports = (sequelize, DataTypes) => {
  const User = sequelize.define('User', {
    id: {
      type: DataTypes.UUID,
      defaultValue: DataTypes.UUIDV4,
      primaryKey: true
    },
    username: {
      type: DataTypes.STRING(50),
      allowNull: false,
      unique: true,
      validate: {
        is: /^[a-zA-Z0-9_-]+$/
      }
    },
    email: {
      type: DataTypes.STRING(255),
      allowNull: false,
      unique: true,
      validate: {
        isEmail: true
      }
    },
    passwordHash: {
      type: DataTypes.STRING(255),
      allowNull: false
    },
    firstName: {
      type: DataTypes.STRING(100),
      allowNull: false
    },
    lastName: {
      type: DataTypes.STRING(100),
      allowNull: false
    },
    status: {
      type: DataTypes.ENUM('active', 'inactive', 'suspended'),
      defaultValue: 'active'
    },
    deletedAt: {
      type: DataTypes.DATE,
      allowNull: true
    }
  }, {
    tableName: 'users',
    timestamps: true,
    paranoid: true,
    underscored: true
  });

  User.associate = (models) => {
    User.hasOne(models.UserProfile, { foreignKey: 'userId' });
    User.belongsToMany(models.Role, { through: models.UserRole });
  };

  return User;
};
```

### 5. Middleware

**Purpose**: Process requests before reaching controllers

**Example: authentication.js**
```javascript
const jwt = require('jsonwebtoken');

const authenticate = async (req, res, next) => {
  try {
    const token = extractToken(req);
    if (!token) {
      throw new UnauthorizedError('No token provided');
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    req.user = decoded;
    next();
  } catch (error) {
    next(error);
  }
};

const authorize = (roles) => {
  return (req, res, next) => {
    if (!req.user) {
      return next(new UnauthorizedError('Not authenticated'));
    }

    if (!roles.includes(req.user.role)) {
      return next(new ForbiddenError('Insufficient permissions'));
    }

    next();
  };
};
```

### 6. Validators

**Purpose**: Define and enforce input validation schemas

**Example: userValidator.js (using Joi)**
```javascript
const Joi = require('joi');

const createUserSchema = Joi.object({
  username: Joi.string()
    .alphanum()
    .min(3)
    .max(50)
    .required(),
  email: Joi.string()
    .email()
    .required(),
  password: Joi.string()
    .min(8)
    .pattern(/^(?=.*[A-Za-z])(?=.*\d)/)
    .required(),
  firstName: Joi.string()
    .min(1)
    .max(100)
    .required(),
  lastName: Joi.string()
    .min(1)
    .max(100)
    .required(),
  status: Joi.string()
    .valid('active', 'inactive')
    .default('active')
});

const updateUserSchema = Joi.object({
  email: Joi.string().email(),
  firstName: Joi.string().min(1).max(100),
  lastName: Joi.string().min(1).max(100),
  status: Joi.string().valid('active', 'inactive', 'suspended')
}).min(1);
```

### 7. Routes

**Purpose**: Map HTTP endpoints to controller methods

**Example: userRoutes.js**
```javascript
const express = require('express');
const router = express.Router();
const userController = require('../../controllers/userController');
const { authenticate, authorize } = require('../../middleware/authentication');
const { validate } = require('../../middleware/validation');
const { createUserSchema, updateUserSchema } = require('../../validators/userValidator');

// Public routes
router.post('/',
  validate(createUserSchema),
  userController.createUser
);

// Protected routes
router.get('/',
  authenticate,
  authorize(['admin', 'moderator']),
  userController.getUsers
);

router.get('/:id',
  authenticate,
  userController.getUserById
);

router.put('/:id',
  authenticate,
  validate(updateUserSchema),
  userController.updateUser
);

router.patch('/:id',
  authenticate,
  validate(updateUserSchema),
  userController.patchUser
);

router.delete('/:id',
  authenticate,
  authorize(['admin']),
  userController.deleteUser
);

module.exports = router;
```

## Error Handling

### Custom Error Classes

```javascript
// utils/errorTypes.js
class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

class ValidationError extends AppError {
  constructor(message, details = []) {
    super(message, 400);
    this.code = 'VALIDATION_ERROR';
    this.details = details;
  }
}

class NotFoundError extends AppError {
  constructor(message = 'Resource not found') {
    super(message, 404);
    this.code = 'NOT_FOUND';
  }
}

class ConflictError extends AppError {
  constructor(message = 'Resource conflict') {
    super(message, 409);
    this.code = 'CONFLICT';
  }
}

class UnauthorizedError extends AppError {
  constructor(message = 'Unauthorized') {
    super(message, 401);
    this.code = 'UNAUTHORIZED';
  }
}

class ForbiddenError extends AppError {
  constructor(message = 'Forbidden') {
    super(message, 403);
    this.code = 'FORBIDDEN';
  }
}
```

### Global Error Handler

```javascript
// middleware/errorHandler.js
const errorHandler = (err, req, res, next) => {
  let error = { ...err };
  error.message = err.message;

  // Log error
  logger.error('Error:', {
    message: err.message,
    stack: err.stack,
    url: req.url,
    method: req.method
  });

  // Mongoose/Sequelize validation error
  if (err.name === 'ValidationError') {
    error = new ValidationError('Validation failed', formatValidationErrors(err));
  }

  // Database unique constraint error
  if (err.code === '23505') {
    error = new ConflictError('Resource already exists');
  }

  // JWT errors
  if (err.name === 'JsonWebTokenError') {
    error = new UnauthorizedError('Invalid token');
  }

  // Send response
  res.status(error.statusCode || 500).json({
    success: false,
    error: {
      code: error.code || 'INTERNAL_ERROR',
      message: error.message || 'Internal server error',
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
      ...(error.details && { details: error.details })
    }
  });
};
```

## Configuration Management

### config/database.js
```javascript
module.exports = {
  development: {
    host: process.env.DB_HOST || 'localhost',
    port: process.env.DB_PORT || 5432,
    database: process.env.DB_NAME || 'user_management_dev',
    username: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD,
    dialect: 'postgres',
    logging: console.log,
    pool: {
      max: 5,
      min: 0,
      acquire: 30000,
      idle: 10000
    }
  },
  production: {
    host: process.env.DB_HOST,
    port: process.env.DB_PORT,
    database: process.env.DB_NAME,
    username: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    dialect: 'postgres',
    logging: false,
    pool: {
      max: 20,
      min: 5,
      acquire: 60000,
      idle: 10000
    },
    dialectOptions: {
      ssl: {
        require: true,
        rejectUnauthorized: false
      }
    }
  }
};
```

## Dependency Injection

### Service Container Pattern
```javascript
// services/container.js
class Container {
  constructor() {
    this.services = {};
  }

  register(name, service) {
    this.services[name] = service;
  }

  get(name) {
    if (!this.services[name]) {
      throw new Error(`Service ${name} not found`);
    }
    return this.services[name];
  }
}

// Initialize services
const container = new Container();

const userRepository = new UserRepository(db);
const auditService = new AuditService(auditRepository);
const userService = new UserService(userRepository, auditService);
const userController = new UserController(userService);

container.register('userRepository', userRepository);
container.register('userService', userService);
container.register('userController', userController);

module.exports = container;
```

## Testing Structure

### Unit Test Example
```javascript
// tests/unit/services/userService.test.js
const UserService = require('../../../src/services/userService');

describe('UserService', () => {
  let userService;
  let mockUserRepository;
  let mockAuditService;

  beforeEach(() => {
    mockUserRepository = {
      create: jest.fn(),
      findByEmail: jest.fn()
    };
    mockAuditService = {
      log: jest.fn()
    };
    userService = new UserService(mockUserRepository, mockAuditService);
  });

  describe('createUser', () => {
    it('should create user with hashed password', async () => {
      const userData = {
        username: 'testuser',
        email: 'test@example.com',
        password: 'Password123!',
        firstName: 'Test',
        lastName: 'User'
      };

      mockUserRepository.findByEmail.mockResolvedValue(null);
      mockUserRepository.create.mockResolvedValue({ id: '123', ...userData });

      const result = await userService.createUser(userData);

      expect(result).toBeDefined();
      expect(result.password).toBeUndefined();
      expect(mockUserRepository.create).toHaveBeenCalled();
    });

    it('should throw error for duplicate email', async () => {
      mockUserRepository.findByEmail.mockResolvedValue({ id: '123' });

      await expect(userService.createUser({ email: 'test@example.com' }))
        .rejects.toThrow('Email already exists');
    });
  });
});
```

### Integration Test Example
```javascript
// tests/integration/userApi.test.js
const request = require('supertest');
const app = require('../../src/app');
const { setupTestDatabase, cleanupTestDatabase } = require('../helpers/testDatabase');

describe('User API', () => {
  beforeAll(async () => {
    await setupTestDatabase();
  });

  afterAll(async () => {
    await cleanupTestDatabase();
  });

  describe('POST /api/v1/users', () => {
    it('should create a new user', async () => {
      const response = await request(app)
        .post('/api/v1/users')
        .send({
          username: 'testuser',
          email: 'test@example.com',
          password: 'Password123!',
          firstName: 'Test',
          lastName: 'User'
        })
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data.email).toBe('test@example.com');
    });
  });
});
```

## Best Practices

### Code Organization
1. **Single Responsibility** - Each class/function does one thing well
2. **Dependency Injection** - Pass dependencies rather than creating them
3. **Interface Segregation** - Keep interfaces small and focused
4. **DRY Principle** - Don't repeat yourself
5. **SOLID Principles** - Follow object-oriented design principles

### Error Handling
1. Use custom error classes
2. Always catch and handle errors
3. Provide meaningful error messages
4. Log errors with context
5. Never expose internal errors to clients

### Security
1. Validate all input
2. Sanitize output
3. Use parameterized queries
4. Hash passwords with bcrypt
5. Implement rate limiting

### Performance
1. Use connection pooling
2. Implement caching where appropriate
3. Optimize database queries
4. Use pagination for lists
5. Implement proper indexing

### Testing
1. Write tests for all business logic
2. Maintain high test coverage (>80%)
3. Use test fixtures for consistency
4. Mock external dependencies
5. Test error conditions

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-12
**Author**: Backend Developer
**Status**: Design Phase Complete
