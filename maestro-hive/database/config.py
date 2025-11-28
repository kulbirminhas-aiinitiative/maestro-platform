#!/usr/bin/env python3
"""
Database configuration and connection management.

Provides SQLAlchemy engine, session management, and database utilities.
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging
import os

from database.models import Base

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class DatabaseConfig:
    """Database configuration"""

    def __init__(self):
        # PostgreSQL connection from environment or defaults
        self.host = os.getenv("POSTGRES_HOST", "localhost")
        self.port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.database = os.getenv("POSTGRES_DB", "maestro_workflows")
        self.username = os.getenv("POSTGRES_USER", "maestro")
        self.password = os.getenv("POSTGRES_PASSWORD", "maestro_dev")

        # Connection pool settings
        self.pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle = int(os.getenv("DB_POOL_RECYCLE", "3600"))

        # SQLite fallback for development
        self.use_sqlite = os.getenv("USE_SQLITE", "false").lower() == "true"
        self.sqlite_path = os.getenv("SQLITE_PATH", "maestro_workflows.db")

    @property
    def database_url(self) -> str:
        """Get database connection URL"""
        if self.use_sqlite:
            return f"sqlite:///{self.sqlite_path}"
        else:
            return (
                f"postgresql://{self.username}:{self.password}"
                f"@{self.host}:{self.port}/{self.database}"
            )

    def __repr__(self):
        if self.use_sqlite:
            return f"<DatabaseConfig(sqlite={self.sqlite_path})>"
        else:
            return f"<DatabaseConfig(postgres={self.host}:{self.port}/{self.database})>"


# =============================================================================
# Database Engine
# =============================================================================

class DatabaseEngine:
    """SQLAlchemy engine and session factory"""

    def __init__(self, config: DatabaseConfig = None):
        self.config = config or DatabaseConfig()
        self.engine = None
        self.SessionLocal = None
        self._initialized = False

    def initialize(self):
        """Initialize database engine and session factory"""
        if self._initialized:
            logger.warning("Database already initialized")
            return

        logger.info(f"Initializing database: {self.config}")

        # Create engine
        if self.config.use_sqlite:
            # SQLite configuration
            self.engine = create_engine(
                self.config.database_url,
                connect_args={"check_same_thread": False},
                echo=False
            )
        else:
            # PostgreSQL configuration with connection pooling
            self.engine = create_engine(
                self.config.database_url,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_timeout=self.config.pool_timeout,
                pool_recycle=self.config.pool_recycle,
                echo=False
            )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Add connection event listeners
        self._setup_event_listeners()

        self._initialized = True
        logger.info("Database initialized successfully")

    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners"""

        @event.listens_for(self.engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            logger.debug("Database connection established")

        @event.listens_for(self.engine, "close")
        def receive_close(dbapi_conn, connection_record):
            logger.debug("Database connection closed")

    def create_tables(self):
        """Create all database tables"""
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    def drop_tables(self):
        """Drop all database tables (use with caution!)"""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    def get_session(self) -> Session:
        """Get a new database session"""
        if not self._initialized:
            self.initialize()
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations.

        Usage:
            with db_engine.session_scope() as session:
                workflow = session.query(WorkflowDefinition).first()
                # ... work with workflow
                # Automatically commits on success, rolls back on error
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            with self.session_scope() as session:
                session.execute(text("SELECT 1"))
            logger.info("Database health check: OK")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def dispose(self):
        """Dispose of the database engine"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database engine disposed")


# =============================================================================
# Global Database Instance
# =============================================================================

# Global database engine instance
db_engine = DatabaseEngine()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database session.

    Usage in FastAPI:
        @app.get("/api/workflows")
        async def list_workflows(db: Session = Depends(get_db)):
            workflows = db.query(WorkflowDefinition).all()
            return workflows
    """
    session = db_engine.get_session()
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# Initialization
# =============================================================================

def initialize_database(create_tables: bool = True):
    """
    Initialize database engine and optionally create tables.

    Args:
        create_tables: Whether to create tables if they don't exist
    """
    db_engine.initialize()

    if create_tables:
        db_engine.create_tables()

    # Health check
    if not db_engine.health_check():
        raise RuntimeError("Database health check failed")

    logger.info("Database ready for use")


def reset_database():
    """
    Reset database by dropping and recreating all tables.

    WARNING: This will delete all data!
    """
    logger.warning("Resetting database - all data will be lost!")
    db_engine.drop_tables()
    db_engine.create_tables()
    logger.info("Database reset complete")


# =============================================================================
# CLI Utilities
# =============================================================================

if __name__ == "__main__":
    import sys

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "init":
            initialize_database(create_tables=True)
        elif command == "reset":
            response = input("Are you sure you want to reset the database? (yes/no): ")
            if response.lower() == "yes":
                reset_database()
            else:
                print("Reset cancelled")
        elif command == "health":
            config = DatabaseConfig()
            engine = DatabaseEngine(config)
            engine.initialize()
            if engine.health_check():
                print("✅ Database is healthy")
            else:
                print("❌ Database health check failed")
        else:
            print(f"Unknown command: {command}")
            print("Available commands: init, reset, health")
    else:
        print("Usage: python database/config.py [init|reset|health]")
        print("  init   - Initialize database and create tables")
        print("  reset  - Drop and recreate all tables (WARNING: deletes data)")
        print("  health - Check database connectivity")
