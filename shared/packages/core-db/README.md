# MAESTRO Core DB

Enterprise database management and migrations for MAESTRO ecosystem services.

## Features

- SQLAlchemy 2.0 async/sync support
- Automatic Alembic migrations setup
- Connection pooling and management
- Multi-database support (PostgreSQL, MySQL, SQLite)
- Health checks and monitoring
- Transaction management
- Query performance tracking

## Installation

```bash
poetry add maestro-core-db
```

## Usage

```python
from maestro_core_db import DatabaseManager, Base

# Initialize database
db_manager = DatabaseManager(
    database_url="postgresql+asyncpg://user:pass@localhost/dbname",
    enable_migrations=True
)

# Define models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True)

# Get async session
async with db_manager.get_session() as session:
    result = await session.execute(select(User))
    users = result.scalars().all()
```

## Migrations

Alembic is automatically initialized when `enable_migrations=True`:

```bash
# Create migration
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## License

MIT
