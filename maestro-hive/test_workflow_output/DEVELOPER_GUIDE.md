# Developer Guide

## User Management REST API - Design Phase
### Version: 1.0.0

---

## Table of Contents
1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Project Structure](#project-structure)
4. [Development Workflow](#development-workflow)
5. [API Implementation Guide](#api-implementation-guide)
6. [Database Integration](#database-integration)
7. [Authentication & Authorization](#authentication--authorization)
8. [Testing Strategy](#testing-strategy)
9. [Code Style & Standards](#code-style--standards)
10. [Common Patterns](#common-patterns)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

This guide provides developers with comprehensive information for implementing the User Management REST API based on the design specifications.

### Prerequisites

**Required Knowledge:**
- RESTful API design principles
- Database fundamentals (SQL, transactions)
- Authentication & authorization concepts
- Asynchronous programming
- Git version control

**Required Skills:**
- Backend programming (Python/Node.js)
- Database design (PostgreSQL)
- API testing
- Docker basics

**Development Environment:**
- OS: Linux, macOS, or Windows with WSL2
- IDE: VS Code, PyCharm, or similar
- Git: Version 2.30+
- Docker: Version 20.10+
- PostgreSQL client: psql or pgAdmin

---

## Getting Started

### Environment Setup

#### 1. Install Dependencies

**For Python/FastAPI:**
```bash
# Python 3.11+
python3 --version

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy psycopg2-binary \
    pydantic python-jose passlib bcrypt redis python-multipart
```

**For Node.js/Express:**
```bash
# Node.js 18+
node --version

# Initialize project
npm init -y

# Install dependencies
npm install express pg redis bcrypt jsonwebtoken \
    joi express-validator helmet cors
```

#### 2. Database Setup

```bash
# Start PostgreSQL with Docker
docker run -d \
  --name user-api-db \
  -e POSTGRES_DB=user_management \
  -e POSTGRES_USER=api_user \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  postgres:14

# Start Redis with Docker
docker run -d \
  --name user-api-cache \
  -p 6379:6379 \
  redis:7
```

#### 3. Environment Configuration

Create `.env` file:
```env
# Application
APP_NAME=User Management API
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
PORT=8000

# Database
DATABASE_URL=postgresql://api_user:secure_password@localhost:5432/user_management
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_CACHE_TTL=300

# JWT
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=10080

# Security
BCRYPT_ROUNDS=12
RATE_LIMIT_PER_MINUTE=60

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=json
```

#### 4. Initialize Database Schema

```bash
# Apply migrations (see DATABASE_SCHEMA.md)
psql -U api_user -d user_management -f migrations/001_create_users_table.sql
psql -U api_user -d user_management -f migrations/002_create_user_sessions_table.sql
psql -U api_user -d user_management -f migrations/003_create_audit_logs_table.sql
psql -U api_user -d user_management -f migrations/004_create_indexes.sql
```

---

## Project Structure

### Recommended Directory Structure

**For Python/FastAPI:**
```
user-management-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Application entry point
│   ├── config.py               # Configuration management
│   ├── dependencies.py         # Dependency injection
│   │
│   ├── api/                    # API layer
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── users.py        # User endpoints
│   │   │   ├── auth.py         # Auth endpoints
│   │   │   └── health.py       # Health check endpoints
│   │   └── dependencies.py     # Route dependencies
│   │
│   ├── middleware/             # Middleware
│   │   ├── __init__.py
│   │   ├── authentication.py
│   │   ├── logging.py
│   │   └── rate_limiting.py
│   │
│   ├── schemas/                # Pydantic schemas (DTOs)
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── auth.py
│   │   └── common.py
│   │
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   ├── auth_service.py
│   │   └── audit_service.py
│   │
│   ├── repositories/           # Data access
│   │   ├── __init__.py
│   │   ├── user_repository.py
│   │   ├── session_repository.py
│   │   └── audit_repository.py
│   │
│   ├── models/                 # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── session.py
│   │   └── audit_log.py
│   │
│   ├── core/                   # Core utilities
│   │   ├── __init__.py
│   │   ├── security.py         # Password hashing, JWT
│   │   ├── cache.py            # Redis client
│   │   ├── database.py         # Database connection
│   │   └── exceptions.py       # Custom exceptions
│   │
│   └── utils/                  # Helper functions
│       ├── __init__.py
│       ├── validators.py
│       └── formatters.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/
│   │   ├── test_user_service.py
│   │   └── test_auth_service.py
│   ├── integration/
│   │   ├── test_user_api.py
│   │   └── test_auth_api.py
│   └── e2e/
│       └── test_user_flow.py
│
├── migrations/                  # Database migrations
│   ├── 001_create_users_table.sql
│   ├── 002_create_user_sessions_table.sql
│   └── ...
│
├── docs/                        # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── DATABASE_SCHEMA.md
│   └── SYSTEM_ARCHITECTURE.md
│
├── scripts/                     # Utility scripts
│   ├── seed_data.py
│   └── run_migrations.py
│
├── .env.example                # Example environment variables
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
└── README.md
```

---

## Development Workflow

### 1. Feature Development Process

```
1. Create feature branch
   git checkout -b feature/user-crud-endpoints

2. Implement changes
   ├── Write tests first (TDD approach)
   ├── Implement feature
   └── Update documentation

3. Run tests
   pytest tests/ -v --cov=app

4. Commit changes
   git add .
   git commit -m "feat: implement user CRUD endpoints"

5. Push and create pull request
   git push origin feature/user-crud-endpoints
```

### 2. Code Review Checklist

Before submitting PR:
- [ ] All tests pass
- [ ] Code coverage > 80%
- [ ] No linting errors
- [ ] Documentation updated
- [ ] API documentation generated
- [ ] Environment variables documented
- [ ] Migration scripts included (if schema changes)
- [ ] Security review completed

---

## API Implementation Guide

### Creating a New Endpoint

#### Step 1: Define Schema (DTO)

**File:** `app/schemas/user.py`

```python
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    username: str = Field(..., min_length=3, max_length=50,
                          regex=r'^[a-zA-Z0-9_]+$')
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = Field(None, regex=r'^\+?[0-9\-\(\) ]{7,20}$')
    role: str = Field(default="user")

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password complexity"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*' for c in v):
            raise ValueError('Password must contain special character')
        return v

class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    username: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # For SQLAlchemy models
```

#### Step 2: Create Service

**File:** `app/services/user_service.py`

```python
from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User
from app.core.security import get_password_hash
from app.core.exceptions import DuplicateUserError, UserNotFoundError

class UserService:
    """Business logic for user operations"""

    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)
        self.audit_repo = AuditRepository(db)
        self.db = db

    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user

        Args:
            user_data: User creation data

        Returns:
            Created user object

        Raises:
            DuplicateUserError: If username or email already exists
        """
        # Check for duplicates
        if await self.user_repo.exists_by_email(user_data.email):
            raise DuplicateUserError("Email already registered")

        if await self.user_repo.exists_by_username(user_data.username):
            raise DuplicateUserError("Username already taken")

        # Hash password
        password_hash = get_password_hash(user_data.password)

        # Create user
        user = await self.user_repo.create({
            **user_data.dict(exclude={'password'}),
            'password_hash': password_hash
        })

        # Log audit entry
        await self.audit_repo.create({
            'user_id': user.id,
            'action': 'CREATE',
            'entity_type': 'user',
            'entity_id': user.id,
            'new_values': user_data.dict(exclude={'password'})
        })

        return user

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID with caching"""
        # Try cache first
        cached = await self.cache.get(f"user:{user_id}")
        if cached:
            return User.parse_raw(cached)

        # Query database
        user = await self.user_repo.find_by_id(user_id)

        # Update cache
        if user:
            await self.cache.set(
                f"user:{user_id}",
                user.json(),
                ex=300  # 5 minutes TTL
            )

        return user

    async def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate
    ) -> User:
        """Update user information"""
        # Get existing user
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User {user_id} not found")

        # Store old values for audit
        old_values = user.dict()

        # Update user
        updated_user = await self.user_repo.update(
            user_id,
            user_data.dict(exclude_unset=True)
        )

        # Invalidate cache
        await self.cache.delete(f"user:{user_id}")

        # Log audit entry
        await self.audit_repo.create({
            'user_id': user_id,
            'action': 'UPDATE',
            'entity_type': 'user',
            'entity_id': user_id,
            'old_values': old_values,
            'new_values': user_data.dict(exclude_unset=True)
        })

        return updated_user
```

#### Step 3: Create Repository

**File:** `app/repositories/user_repository.py`

```python
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session
from app.models.user import User

class UserRepository:
    """Data access layer for users"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, user_data: dict) -> User:
        """Create new user record"""
        user = User(**user_data)
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find user by ID"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """Check if email exists"""
        user = await self.find_by_email(email)
        return user is not None

    async def find_all(
        self,
        skip: int = 0,
        limit: int = 20,
        filters: dict = None
    ) -> Tuple[List[User], int]:
        """Find all users with pagination"""
        query = select(User).where(User.deleted_at.is_(None))

        # Apply filters
        if filters:
            if filters.get('is_active') is not None:
                query = query.where(User.is_active == filters['is_active'])
            if filters.get('role'):
                query = query.where(User.role == filters['role'])

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Apply pagination
        query = query.offset(skip).limit(limit)

        # Execute query
        result = await self.db.execute(query)
        users = result.scalars().all()

        return users, total

    async def update(self, user_id: UUID, user_data: dict) -> User:
        """Update user record"""
        user = await self.find_by_id(user_id)
        if not user:
            return None

        for key, value in user_data.items():
            setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete(self, user_id: UUID, soft: bool = True) -> bool:
        """Delete user (soft or hard)"""
        user = await self.find_by_id(user_id)
        if not user:
            return False

        if soft:
            user.deleted_at = datetime.utcnow()
            user.is_active = False
            await self.db.commit()
        else:
            await self.db.delete(user)
            await self.db.commit()

        return True
```

#### Step 4: Create Controller/Route

**File:** `app/api/routes/users.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from uuid import UUID
from sqlalchemy.orm import Session

from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService
from app.core.dependencies import get_db, get_current_user
from app.core.exceptions import DuplicateUserError, UserNotFoundError

router = APIRouter(prefix="/users", tags=["users"])

@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="Creates a new user with the provided information"
)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new user"""
    service = UserService(db)

    try:
        user = await service.create_user(user_data)
        return user
    except DuplicateUserError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )

@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieves a specific user by their unique identifier"
)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user by ID"""
    service = UserService(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found"
        )

    return user

@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List all users",
    description="Retrieves a paginated list of all users"
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool = Query(None),
    role: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all users with pagination"""
    service = UserService(db)

    skip = (page - 1) * page_size
    filters = {}
    if is_active is not None:
        filters['is_active'] = is_active
    if role:
        filters['role'] = role

    users, total = await service.list_users(
        skip=skip,
        limit=page_size,
        filters=filters
    )

    return {
        "data": users,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": (total + page_size - 1) // page_size
        }
    }
```

---

## Database Integration

### Connection Management

**File:** `app/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,  # Verify connections before using
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()

async def get_db():
    """Dependency for database sessions"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Model Definition

**File:** `app/models/user.py`

```python
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.core.database import Base

class User(Base):
    """User database model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(String(20), nullable=False, default="user")
    is_active = Column(Boolean, nullable=False, default=True)
    email_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.username}>"
```

---

## Authentication & Authorization

### JWT Token Generation

**File:** `app/core/security.py`

```python
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt
```

### Authentication Middleware

**File:** `app/middleware/authentication.py`

```python
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import settings
from app.core.dependencies import get_db
from app.repositories.user_repository import UserRepository

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Extract and validate current user from JWT token"""
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    user_repo = UserRepository(db)
    user = await user_repo.find_by_id(user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    return user
```

---

## Testing Strategy

### Unit Test Example

**File:** `tests/unit/test_user_service.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.user_service import UserService
from app.schemas.user import UserCreate
from app.core.exceptions import DuplicateUserError

@pytest.mark.asyncio
async def test_create_user_success(mock_db):
    """Test successful user creation"""
    # Arrange
    service = UserService(mock_db)
    user_data = UserCreate(
        username="testuser",
        email="test@example.com",
        password="SecurePass123!",
        first_name="Test",
        last_name="User"
    )

    service.user_repo.exists_by_email = AsyncMock(return_value=False)
    service.user_repo.exists_by_username = AsyncMock(return_value=False)
    service.user_repo.create = AsyncMock(return_value=Mock(id="user-id"))

    # Act
    user = await service.create_user(user_data)

    # Assert
    assert user.id == "user-id"
    service.user_repo.create.assert_called_once()

@pytest.mark.asyncio
async def test_create_user_duplicate_email(mock_db):
    """Test user creation with duplicate email"""
    # Arrange
    service = UserService(mock_db)
    user_data = UserCreate(
        username="testuser",
        email="existing@example.com",
        password="SecurePass123!",
        first_name="Test",
        last_name="User"
    )

    service.user_repo.exists_by_email = AsyncMock(return_value=True)

    # Act & Assert
    with pytest.raises(DuplicateUserError):
        await service.create_user(user_data)
```

### Integration Test Example

**File:** `tests/integration/test_user_api.py`

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_user_endpoint():
    """Test POST /users endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "SecurePass123!",
                "first_name": "Test",
                "last_name": "User"
            },
            headers={"Authorization": f"Bearer {test_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "password" not in data
```

---

## Code Style & Standards

### Python (PEP 8)

```python
# Good
def create_user(user_data: UserCreate) -> User:
    """Create a new user with validation"""
    pass

# Bad
def createUser(userData):
    pass
```

### Naming Conventions

- **Classes:** PascalCase (`UserService`, `UserRepository`)
- **Functions:** snake_case (`create_user`, `get_user_by_id`)
- **Constants:** UPPER_SNAKE_CASE (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Private:** _leading_underscore (`_internal_function`)

### Documentation

```python
def create_user(user_data: UserCreate) -> User:
    """
    Create a new user in the system.

    Args:
        user_data: User creation data including username, email, and password

    Returns:
        Created user object with generated ID

    Raises:
        DuplicateUserError: If username or email already exists
        ValidationError: If user data is invalid

    Example:
        >>> user_data = UserCreate(username="john", email="john@example.com", ...)
        >>> user = await service.create_user(user_data)
        >>> print(user.id)
        '550e8400-e29b-41d4-a716-446655440000'
    """
    pass
```

---

## Common Patterns

### Error Handling Pattern

```python
# Custom exceptions
class APIException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

# Error handler
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.__class__.__name__,
                "message": exc.detail,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request.state.request_id
            }
        }
    )
```

### Repository Pattern

```python
class BaseRepository:
    """Base repository with common CRUD operations"""

    def __init__(self, db: Session, model):
        self.db = db
        self.model = model

    async def create(self, data: dict):
        obj = self.model(**data)
        self.db.add(obj)
        await self.db.commit()
        return obj

    async def find_by_id(self, id):
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
```

---

## Troubleshooting

### Common Issues

**Issue: Database connection errors**
```
Solution: Check DATABASE_URL, ensure PostgreSQL is running
Debug: docker ps | grep postgres
```

**Issue: JWT token validation fails**
```
Solution: Verify JWT_SECRET matches between token creation and validation
Debug: Print decoded token payload
```

**Issue: Import errors**
```
Solution: Ensure PYTHONPATH includes project root
Debug: python -c "import sys; print(sys.path)"
```

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-12
**Phase:** Design
**Status:** Draft
