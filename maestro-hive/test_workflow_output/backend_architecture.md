# Backend Architecture & Implementation Guide - User Management API

## Project Information
**Workflow ID:** workflow-20251012-130125
**Phase:** Requirements
**Document Version:** 1.0
**Date:** 2025-10-12
**Prepared by:** Backend Developer

---

## 1. Architecture Overview

### 1.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (Web Apps, Mobile Apps, Third-party Integrations)              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTPS/TLS
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    Load Balancer / API Gateway                   │
│              (Rate Limiting, SSL Termination)                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   Application Layer (API)                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              REST API Server (Node.js/Python)             │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │  │
│  │  │   Routes    │  │ Controllers  │  │  Middleware    │  │  │
│  │  │  (Routing)  │─▶│  (Business)  │◀─│ (Auth, Valid.) │  │  │
│  │  └─────────────┘  └──────┬───────┘  └────────────────┘  │  │
│  │                           │                               │  │
│  │                           │                               │  │
│  │  ┌─────────────┐  ┌──────▼───────┐  ┌────────────────┐  │  │
│  │  │   Models    │◀─│   Services   │─▶│   Validators   │  │  │
│  │  │ (ORM/Data)  │  │  (Bus. Logic)│  │  (Data Valid.) │  │  │
│  │  └──────┬──────┘  └──────────────┘  └────────────────┘  │  │
│  └─────────┼──────────────────────────────────────────────┘  │
└────────────┼──────────────────────────────────────────────────┘
             │
             │
┌────────────▼────────────────────────────────────────────────────┐
│                       Data Layer                                 │
│  ┌──────────────────────┐       ┌────────────────────────┐     │
│  │  PostgreSQL Database │       │   Redis Cache          │     │
│  │  (Primary Data Store)│       │   (Session/Cache)      │     │
│  └──────────────────────┘       └────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

#### Primary Stack (Node.js Option)
- **Runtime:** Node.js v18+
- **Framework:** Express.js v4.18+
- **Language:** TypeScript v5+
- **ORM:** TypeORM or Prisma
- **Database:** PostgreSQL v14+
- **Cache:** Redis v7+ (optional)
- **Authentication:** jsonwebtoken (JWT)
- **Validation:** Joi or Zod
- **Password Hashing:** bcrypt
- **Testing:** Jest + Supertest
- **API Documentation:** Swagger/OpenAPI

#### Alternative Stack (Python Option)
- **Runtime:** Python v3.9+
- **Framework:** FastAPI v0.104+
- **ORM:** SQLAlchemy v2+
- **Database:** PostgreSQL v14+
- **Cache:** Redis v7+ (optional)
- **Authentication:** python-jose (JWT)
- **Validation:** Pydantic (built-in FastAPI)
- **Password Hashing:** passlib with bcrypt
- **Testing:** pytest + httpx
- **API Documentation:** FastAPI built-in (OpenAPI)

---

## 2. Layered Architecture

### 2.1 Layer Responsibilities

#### **Presentation Layer (Routes)**
- Define API endpoints and HTTP methods
- Map URLs to controller functions
- Handle request/response formatting
- Apply route-level middleware

#### **Controller Layer**
- Receive HTTP requests
- Extract and validate request data
- Call appropriate service methods
- Format responses
- Handle HTTP-specific concerns

#### **Service Layer (Business Logic)**
- Implement core business logic
- Orchestrate multiple operations
- Transaction management
- Data transformation
- Error handling

#### **Data Access Layer (Models/Repositories)**
- Database queries and mutations
- ORM model definitions
- Data mapping and relationships
- Query optimization

#### **Validation Layer**
- Input validation schemas
- Data sanitization
- Business rule validation
- Custom validators

---

## 3. Project Structure

### 3.1 Node.js/TypeScript Structure

```
user-management-api/
├── src/
│   ├── config/
│   │   ├── database.ts           # Database connection config
│   │   ├── jwt.ts                # JWT configuration
│   │   └── environment.ts        # Environment variables
│   │
│   ├── middleware/
│   │   ├── auth.middleware.ts    # JWT authentication
│   │   ├── validation.middleware.ts  # Request validation
│   │   ├── errorHandler.middleware.ts  # Error handling
│   │   ├── rateLimit.middleware.ts  # Rate limiting
│   │   └── logger.middleware.ts  # Request logging
│   │
│   ├── models/
│   │   ├── user.model.ts         # User entity/model
│   │   └── auditLog.model.ts     # Audit log model
│   │
│   ├── repositories/
│   │   └── user.repository.ts    # User data access
│   │
│   ├── services/
│   │   ├── user.service.ts       # User business logic
│   │   ├── auth.service.ts       # Authentication logic
│   │   └── password.service.ts   # Password operations
│   │
│   ├── controllers/
│   │   ├── user.controller.ts    # User endpoints logic
│   │   └── auth.controller.ts    # Auth endpoints logic
│   │
│   ├── routes/
│   │   ├── index.ts              # Route aggregation
│   │   ├── user.routes.ts        # User routes
│   │   └── auth.routes.ts        # Auth routes
│   │
│   ├── validators/
│   │   ├── user.validator.ts     # User validation schemas
│   │   └── auth.validator.ts     # Auth validation schemas
│   │
│   ├── utils/
│   │   ├── logger.ts             # Logging utility
│   │   ├── response.ts           # Standard response format
│   │   └── errors.ts             # Custom error classes
│   │
│   ├── types/
│   │   ├── express.d.ts          # Express type extensions
│   │   └── api.types.ts          # API type definitions
│   │
│   ├── app.ts                    # Express app setup
│   └── server.ts                 # Server entry point
│
├── tests/
│   ├── unit/
│   │   ├── services/
│   │   └── controllers/
│   ├── integration/
│   │   └── api/
│   └── fixtures/
│       └── testData.ts
│
├── migrations/                    # Database migrations
│   └── 001_create_users_table.ts
│
├── docs/
│   └── api/
│       └── openapi.yaml
│
├── .env.example                   # Environment template
├── .gitignore
├── package.json
├── tsconfig.json
├── jest.config.js
└── README.md
```

### 3.2 Python/FastAPI Structure

```
user_management_api/
├── app/
│   ├── core/
│   │   ├── config.py             # Configuration
│   │   ├── security.py           # Security utilities
│   │   └── database.py           # Database connection
│   │
│   ├── middleware/
│   │   ├── auth.py               # Authentication
│   │   ├── error_handler.py      # Error handling
│   │   └── rate_limit.py         # Rate limiting
│   │
│   ├── models/
│   │   ├── user.py               # User SQLAlchemy model
│   │   └── audit_log.py          # Audit log model
│   │
│   ├── schemas/
│   │   ├── user.py               # User Pydantic schemas
│   │   └── auth.py               # Auth Pydantic schemas
│   │
│   ├── repositories/
│   │   └── user_repository.py    # User data access
│   │
│   ├── services/
│   │   ├── user_service.py       # User business logic
│   │   ├── auth_service.py       # Authentication logic
│   │   └── password_service.py   # Password operations
│   │
│   ├── api/
│   │   ├── deps.py               # API dependencies
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── users.py          # User endpoints
│   │   │   └── auth.py           # Auth endpoints
│   │   └── router.py             # API router aggregation
│   │
│   ├── utils/
│   │   ├── logger.py             # Logging utility
│   │   ├── response.py           # Response formatter
│   │   └── exceptions.py         # Custom exceptions
│   │
│   ├── main.py                   # FastAPI app entry
│   └── __init__.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── alembic/                       # Database migrations
│   └── versions/
│
├── .env.example
├── requirements.txt
├── pytest.ini
└── README.md
```

---

## 4. Core Components Implementation

### 4.1 User Model (TypeScript/TypeORM)

```typescript
// src/models/user.model.ts
import {
  Entity,
  PrimaryGeneratedColumn,
  Column,
  CreateDateColumn,
  UpdateDateColumn,
  Index,
} from 'typeorm';

@Entity('users')
export class User {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ length: 50, unique: true })
  @Index()
  username: string;

  @Column({ length: 255, unique: true })
  @Index()
  email: string;

  @Column({ length: 255, select: false })
  passwordHash: string;

  @Column({ length: 100, nullable: true })
  firstName?: string;

  @Column({ length: 100, nullable: true })
  lastName?: string;

  @Column({ length: 20, nullable: true })
  phoneNumber?: string;

  @Column({ type: 'date', nullable: true })
  dateOfBirth?: Date;

  @Column({ length: 500, nullable: true })
  profilePictureUrl?: string;

  @Column({ type: 'text', nullable: true })
  bio?: string;

  @Column({ length: 20, default: 'active' })
  status: 'active' | 'inactive' | 'suspended' | 'deleted';

  @Column({ default: true })
  isActive: boolean;

  @Column({ default: false })
  emailVerified: boolean;

  @CreateDateColumn()
  createdAt: Date;

  @UpdateDateColumn()
  updatedAt: Date;

  @Column({ type: 'timestamp', nullable: true })
  lastLogin?: Date;

  @Column({ type: 'timestamp', nullable: true })
  deletedAt?: Date;
}
```

### 4.2 User Service (TypeScript)

```typescript
// src/services/user.service.ts
import { Repository } from 'typeorm';
import { User } from '../models/user.model';
import bcrypt from 'bcrypt';
import { ConflictError, NotFoundError } from '../utils/errors';

export class UserService {
  constructor(private userRepository: Repository<User>) {}

  async createUser(userData: CreateUserDto): Promise<User> {
    // Check for duplicate email/username
    const existingUser = await this.userRepository.findOne({
      where: [
        { email: userData.email },
        { username: userData.username }
      ]
    });

    if (existingUser) {
      if (existingUser.email === userData.email) {
        throw new ConflictError('Email already exists');
      }
      throw new ConflictError('Username already exists');
    }

    // Hash password
    const passwordHash = await bcrypt.hash(userData.password, 10);

    // Create user
    const user = this.userRepository.create({
      ...userData,
      passwordHash,
    });

    return await this.userRepository.save(user);
  }

  async getUserById(id: string): Promise<User> {
    const user = await this.userRepository.findOne({
      where: { id, deletedAt: null }
    });

    if (!user) {
      throw new NotFoundError('User not found');
    }

    return user;
  }

  async getUserByEmail(email: string): Promise<User | null> {
    return await this.userRepository
      .createQueryBuilder('user')
      .where('user.email = :email', { email })
      .andWhere('user.deletedAt IS NULL')
      .addSelect('user.passwordHash')
      .getOne();
  }

  async listUsers(options: ListUsersOptions): Promise<PaginatedResponse<User>> {
    const { page = 1, limit = 20, search, status, sortBy, sortOrder } = options;

    const query = this.userRepository
      .createQueryBuilder('user')
      .where('user.deletedAt IS NULL');

    // Apply filters
    if (search) {
      query.andWhere(
        '(user.firstName ILIKE :search OR user.lastName ILIKE :search OR user.email ILIKE :search)',
        { search: `%${search}%` }
      );
    }

    if (status) {
      query.andWhere('user.status = :status', { status });
    }

    // Apply sorting
    const sortColumn = sortBy || 'createdAt';
    const sortDirection = sortOrder?.toUpperCase() === 'ASC' ? 'ASC' : 'DESC';
    query.orderBy(`user.${sortColumn}`, sortDirection);

    // Apply pagination
    const skip = (page - 1) * limit;
    query.skip(skip).take(limit);

    // Execute query
    const [users, total] = await query.getManyAndCount();

    return {
      data: users,
      pagination: {
        currentPage: page,
        perPage: limit,
        totalPages: Math.ceil(total / limit),
        totalItems: total,
        hasNext: page * limit < total,
        hasPrevious: page > 1,
      },
    };
  }

  async updateUser(id: string, updateData: UpdateUserDto): Promise<User> {
    const user = await this.getUserById(id);

    // Check email uniqueness if email is being updated
    if (updateData.email && updateData.email !== user.email) {
      const existingUser = await this.userRepository.findOne({
        where: { email: updateData.email }
      });
      if (existingUser) {
        throw new ConflictError('Email already exists');
      }
    }

    // Update user
    Object.assign(user, updateData);
    return await this.userRepository.save(user);
  }

  async deleteUser(id: string): Promise<void> {
    const user = await this.getUserById(id);

    // Soft delete
    user.deletedAt = new Date();
    user.status = 'deleted';
    user.isActive = false;

    await this.userRepository.save(user);
  }

  async verifyPassword(user: User, password: string): Promise<boolean> {
    return await bcrypt.compare(password, user.passwordHash);
  }

  async updatePassword(
    userId: string,
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    const user = await this.userRepository
      .createQueryBuilder('user')
      .where('user.id = :userId', { userId })
      .addSelect('user.passwordHash')
      .getOne();

    if (!user) {
      throw new NotFoundError('User not found');
    }

    // Verify current password
    const isValid = await this.verifyPassword(user, currentPassword);
    if (!isValid) {
      throw new UnauthorizedError('Current password is incorrect');
    }

    // Hash and save new password
    user.passwordHash = await bcrypt.hash(newPassword, 10);
    await this.userRepository.save(user);
  }
}
```

### 4.3 User Controller (TypeScript)

```typescript
// src/controllers/user.controller.ts
import { Request, Response, NextFunction } from 'express';
import { UserService } from '../services/user.service';
import { successResponse } from '../utils/response';

export class UserController {
  constructor(private userService: UserService) {}

  createUser = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const user = await this.userService.createUser(req.body);
      return successResponse(res, user, 'User created successfully', 201);
    } catch (error) {
      next(error);
    }
  };

  getUserById = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const user = await this.userService.getUserById(req.params.id);
      return successResponse(res, { user });
    } catch (error) {
      next(error);
    }
  };

  listUsers = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const result = await this.userService.listUsers(req.query);
      return successResponse(res, result);
    } catch (error) {
      next(error);
    }
  };

  updateUser = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const user = await this.userService.updateUser(req.params.id, req.body);
      return successResponse(res, { user }, 'User updated successfully');
    } catch (error) {
      next(error);
    }
  };

  deleteUser = async (req: Request, res: Response, next: NextFunction) => {
    try {
      await this.userService.deleteUser(req.params.id);
      return res.status(204).send();
    } catch (error) {
      next(error);
    }
  };

  updatePassword = async (req: Request, res: Response, next: NextFunction) => {
    try {
      const { currentPassword, newPassword } = req.body;
      await this.userService.updatePassword(
        req.params.id,
        currentPassword,
        newPassword
      );
      return successResponse(res, null, 'Password updated successfully');
    } catch (error) {
      next(error);
    }
  };
}
```

### 4.4 Authentication Middleware (TypeScript)

```typescript
// src/middleware/auth.middleware.ts
import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { UnauthorizedError } from '../utils/errors';
import { config } from '../config/environment';

export interface JWTPayload {
  userId: string;
  email: string;
  iat: number;
  exp: number;
}

export const authMiddleware = async (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    // Extract token from Authorization header
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      throw new UnauthorizedError('No token provided');
    }

    const token = authHeader.substring(7);

    // Verify token
    const decoded = jwt.verify(token, config.jwtSecret) as JWTPayload;

    // Attach user info to request
    req.user = {
      userId: decoded.userId,
      email: decoded.email,
    };

    next();
  } catch (error) {
    if (error instanceof jwt.JsonWebTokenError) {
      next(new UnauthorizedError('Invalid token'));
    } else if (error instanceof jwt.TokenExpiredError) {
      next(new UnauthorizedError('Token expired'));
    } else {
      next(error);
    }
  }
};
```

### 4.5 Validation Schemas (TypeScript with Joi)

```typescript
// src/validators/user.validator.ts
import Joi from 'joi';

export const createUserSchema = Joi.object({
  username: Joi.string()
    .alphanum()
    .min(3)
    .max(50)
    .required()
    .messages({
      'string.alphanum': 'Username must contain only alphanumeric characters',
      'string.min': 'Username must be at least 3 characters',
      'string.max': 'Username must not exceed 50 characters',
    }),

  email: Joi.string()
    .email()
    .max(255)
    .required()
    .messages({
      'string.email': 'Invalid email format',
    }),

  password: Joi.string()
    .min(8)
    .pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/)
    .required()
    .messages({
      'string.pattern.base': 'Password must contain uppercase, lowercase, number, and special character',
      'string.min': 'Password must be at least 8 characters',
    }),

  firstName: Joi.string().max(100).optional(),
  lastName: Joi.string().max(100).optional(),
  phoneNumber: Joi.string().pattern(/^\+?[1-9]\d{1,14}$/).optional(),
  dateOfBirth: Joi.date().max('now').optional(),
});

export const updateUserSchema = Joi.object({
  email: Joi.string().email().max(255).optional(),
  firstName: Joi.string().max(100).optional(),
  lastName: Joi.string().max(100).optional(),
  phoneNumber: Joi.string().pattern(/^\+?[1-9]\d{1,14}$/).optional(),
  dateOfBirth: Joi.date().max('now').optional(),
  profilePictureUrl: Joi.string().uri().max(500).optional(),
  bio: Joi.string().max(500).optional(),
}).min(1);

export const listUsersSchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  limit: Joi.number().integer().min(1).max(100).default(20),
  search: Joi.string().min(2).optional(),
  status: Joi.string().valid('active', 'inactive', 'suspended').optional(),
  sortBy: Joi.string().valid('createdAt', 'email', 'username', 'lastName').default('createdAt'),
  sortOrder: Joi.string().valid('asc', 'desc').default('desc'),
});
```

---

## 5. Security Implementation

### 5.1 Password Hashing

```typescript
// src/services/password.service.ts
import bcrypt from 'bcrypt';

export class PasswordService {
  private readonly saltRounds = 10;

  async hashPassword(password: string): Promise<string> {
    return await bcrypt.hash(password, this.saltRounds);
  }

  async comparePassword(password: string, hash: string): Promise<boolean> {
    return await bcrypt.compare(password, hash);
  }

  validatePasswordStrength(password: string): boolean {
    const minLength = 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[@$!%*?&]/.test(password);

    return (
      password.length >= minLength &&
      hasUpperCase &&
      hasLowerCase &&
      hasNumbers &&
      hasSpecialChar
    );
  }
}
```

### 5.2 JWT Authentication

```typescript
// src/services/auth.service.ts
import jwt from 'jsonwebtoken';
import { config } from '../config/environment';

export interface TokenPayload {
  userId: string;
  email: string;
}

export class AuthService {
  generateAccessToken(payload: TokenPayload): string {
    return jwt.sign(payload, config.jwtSecret, {
      expiresIn: config.jwtExpiresIn, // '1h'
    });
  }

  generateRefreshToken(payload: TokenPayload): string {
    return jwt.sign(payload, config.jwtRefreshSecret, {
      expiresIn: config.jwtRefreshExpiresIn, // '7d'
    });
  }

  verifyAccessToken(token: string): TokenPayload {
    return jwt.verify(token, config.jwtSecret) as TokenPayload;
  }

  verifyRefreshToken(token: string): TokenPayload {
    return jwt.verify(token, config.jwtRefreshSecret) as TokenPayload;
  }
}
```

### 5.3 Rate Limiting

```typescript
// src/middleware/rateLimit.middleware.ts
import rateLimit from 'express-rate-limit';

export const apiRateLimiter = rateLimit({
  windowMs: 60 * 1000, // 1 minute
  max: 100, // 100 requests per window
  message: {
    success: false,
    error: {
      code: 'RATE_LIMIT_EXCEEDED',
      message: 'Too many requests. Please try again later.',
    },
  },
  standardHeaders: true,
  legacyHeaders: false,
});

export const authRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 login attempts
  message: {
    success: false,
    error: {
      code: 'RATE_LIMIT_EXCEEDED',
      message: 'Too many login attempts. Please try again later.',
    },
  },
  skipSuccessfulRequests: true,
});
```

---

## 6. Error Handling

### 6.1 Custom Error Classes

```typescript
// src/utils/errors.ts
export class AppError extends Error {
  constructor(
    public statusCode: number,
    public code: string,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(message: string, details?: any) {
    super(400, 'VALIDATION_ERROR', message, details);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = 'Unauthorized') {
    super(401, 'UNAUTHORIZED', message);
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = 'Forbidden') {
    super(403, 'FORBIDDEN', message);
  }
}

export class NotFoundError extends AppError {
  constructor(message: string = 'Resource not found') {
    super(404, 'RESOURCE_NOT_FOUND', message);
  }
}

export class ConflictError extends AppError {
  constructor(message: string, details?: any) {
    super(409, 'DUPLICATE_RESOURCE', message, details);
  }
}
```

### 6.2 Error Handler Middleware

```typescript
// src/middleware/errorHandler.middleware.ts
import { Request, Response, NextFunction } from 'express';
import { AppError } from '../utils/errors';
import { logger } from '../utils/logger';

export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  // Log error
  logger.error({
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  // Handle known errors
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: {
        code: err.code,
        message: err.message,
        details: err.details,
        timestamp: new Date().toISOString(),
      },
    });
  }

  // Handle unknown errors
  return res.status(500).json({
    success: false,
    error: {
      code: 'INTERNAL_SERVER_ERROR',
      message: 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
    },
  });
};
```

---

## 7. Testing Strategy

### 7.1 Unit Tests (Jest)

```typescript
// tests/unit/services/user.service.test.ts
import { UserService } from '../../../src/services/user.service';
import { User } from '../../../src/models/user.model';
import { ConflictError, NotFoundError } from '../../../src/utils/errors';

describe('UserService', () => {
  let userService: UserService;
  let mockRepository: jest.Mocked<Repository<User>>;

  beforeEach(() => {
    mockRepository = {
      findOne: jest.fn(),
      create: jest.fn(),
      save: jest.fn(),
      createQueryBuilder: jest.fn(),
    } as any;

    userService = new UserService(mockRepository);
  });

  describe('createUser', () => {
    it('should create a new user successfully', async () => {
      const userData = {
        username: 'testuser',
        email: 'test@example.com',
        password: 'Test@1234',
        firstName: 'Test',
        lastName: 'User',
      };

      mockRepository.findOne.mockResolvedValue(null);
      mockRepository.create.mockReturnValue(userData as any);
      mockRepository.save.mockResolvedValue({ ...userData, id: 'uuid' } as any);

      const result = await userService.createUser(userData);

      expect(result).toHaveProperty('id');
      expect(mockRepository.findOne).toHaveBeenCalled();
      expect(mockRepository.save).toHaveBeenCalled();
    });

    it('should throw ConflictError if email exists', async () => {
      const userData = {
        username: 'testuser',
        email: 'existing@example.com',
        password: 'Test@1234',
      };

      mockRepository.findOne.mockResolvedValue({ email: userData.email } as any);

      await expect(userService.createUser(userData)).rejects.toThrow(ConflictError);
    });
  });

  describe('getUserById', () => {
    it('should return user if found', async () => {
      const userId = 'uuid';
      const mockUser = { id: userId, email: 'test@example.com' };

      mockRepository.findOne.mockResolvedValue(mockUser as any);

      const result = await userService.getUserById(userId);

      expect(result).toEqual(mockUser);
    });

    it('should throw NotFoundError if user not found', async () => {
      mockRepository.findOne.mockResolvedValue(null);

      await expect(userService.getUserById('uuid')).rejects.toThrow(NotFoundError);
    });
  });
});
```

### 7.2 Integration Tests

```typescript
// tests/integration/api/users.test.ts
import request from 'supertest';
import { app } from '../../../src/app';
import { setupTestDatabase, teardownTestDatabase } from '../../fixtures/database';

describe('User API Integration Tests', () => {
  beforeAll(async () => {
    await setupTestDatabase();
  });

  afterAll(async () => {
    await teardownTestDatabase();
  });

  describe('POST /api/v1/users', () => {
    it('should create a new user', async () => {
      const response = await request(app)
        .post('/api/v1/users')
        .send({
          username: 'testuser',
          email: 'test@example.com',
          password: 'Test@1234',
          firstName: 'Test',
          lastName: 'User',
        });

      expect(response.status).toBe(201);
      expect(response.body.success).toBe(true);
      expect(response.body.data.user).toHaveProperty('id');
      expect(response.body.data.user.email).toBe('test@example.com');
    });

    it('should return 409 for duplicate email', async () => {
      // Create first user
      await request(app)
        .post('/api/v1/users')
        .send({
          username: 'user1',
          email: 'duplicate@example.com',
          password: 'Test@1234',
        });

      // Try to create with same email
      const response = await request(app)
        .post('/api/v1/users')
        .send({
          username: 'user2',
          email: 'duplicate@example.com',
          password: 'Test@1234',
        });

      expect(response.status).toBe(409);
      expect(response.body.error.code).toBe('DUPLICATE_RESOURCE');
    });
  });
});
```

---

## 8. Deployment Configuration

### 8.1 Environment Variables

```bash
# .env.example

# Server Configuration
NODE_ENV=development
PORT=3000
API_VERSION=v1

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=user_management_db
DB_USER=app_user
DB_PASSWORD=secure_password
DB_POOL_MIN=2
DB_POOL_MAX=10

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_EXPIRES_IN=1h
JWT_REFRESH_SECRET=your-refresh-token-secret
JWT_REFRESH_EXPIRES_IN=7d

# Security
BCRYPT_ROUNDS=10
RATE_LIMIT_WINDOW_MS=60000
RATE_LIMIT_MAX_REQUESTS=100

# Logging
LOG_LEVEL=info
LOG_FORMAT=json

# CORS
CORS_ORIGIN=http://localhost:3000,https://yourdomain.com
```

### 8.2 Docker Configuration

```dockerfile
# Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["node", "dist/server.js"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=user_management_db
      - DB_USER=app_user
      - DB_PASSWORD=secure_password
    depends_on:
      - postgres
    restart: unless-stopped

  postgres:
    image: postgres:14-alpine
    environment:
      - POSTGRES_DB=user_management_db
      - POSTGRES_USER=app_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## 9. Performance Optimization

### 9.1 Database Query Optimization
- Use indexes on frequently queried columns
- Implement connection pooling
- Use query result caching for static data
- Avoid N+1 queries with eager loading

### 9.2 API Response Optimization
- Implement response compression (gzip)
- Use HTTP caching headers (ETag, Cache-Control)
- Paginate large result sets
- Exclude unnecessary fields from responses

### 9.3 Caching Strategy
- Cache user profiles (5-minute TTL)
- Cache authentication tokens
- Implement Redis for session management

---

## 10. Monitoring and Observability

### 10.1 Logging
- Structured logging (JSON format)
- Log levels: ERROR, WARN, INFO, DEBUG
- Request/response logging
- Performance metrics logging

### 10.2 Health Checks
```typescript
// Health check endpoint
app.get('/api/v1/health', async (req, res) => {
  const health = {
    status: 'healthy',
    version: process.env.API_VERSION,
    timestamp: new Date().toISOString(),
    services: {
      database: await checkDatabaseConnection(),
      cache: await checkCacheConnection(),
    },
  };
  res.json(health);
});
```

---

**Document Status:** Final
**Quality Review:** Passed
**Ready for Implementation:** Yes
