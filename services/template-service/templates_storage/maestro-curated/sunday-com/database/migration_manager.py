#!/usr/bin/env python3
"""
Sunday.com Database Migration Manager

A comprehensive migration system for managing database schema changes
with versioning, rollback capabilities, and deployment automation.

Usage:
    python migration_manager.py migrate [--target=VERSION]
    python migration_manager.py rollback [--target=VERSION]
    python migration_manager.py status
    python migration_manager.py create [MIGRATION_NAME]
    python migration_manager.py validate
"""

import os
import sys
import re
import hashlib
import logging
import argparse
import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migrations.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class MigrationError(Exception):
    """Custom exception for migration errors"""
    pass

class DatabaseConfig:
    """Database configuration management"""

    def __init__(self, config_file: str = "database_config.yaml"):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load database configuration from file or environment"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)

        # Fallback to environment variables
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'sunday_dev'),
            'user': os.getenv('DB_USER', 'sunday_dev'),
            'password': os.getenv('DB_PASSWORD', 'dev_password123'),
            'sslmode': os.getenv('DB_SSLMODE', 'prefer')
        }

    def get_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return (f"host={self.config['host']} "
                f"port={self.config['port']} "
                f"dbname={self.config['database']} "
                f"user={self.config['user']} "
                f"password={self.config['password']} "
                f"sslmode={self.config['sslmode']}")

class Migration:
    """Represents a single database migration"""

    def __init__(self, version: str, name: str, file_path: Path):
        self.version = version
        self.name = name
        self.file_path = file_path
        self.content = self._read_content()
        self.checksum = self._calculate_checksum()

    def _read_content(self) -> str:
        """Read migration file content"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise MigrationError(f"Error reading migration file {self.file_path}: {e}")

    def _calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of migration content"""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def has_up_script(self) -> bool:
        """Check if migration has up script"""
        return 'BEGIN;' in self.content and 'COMMIT;' in self.content

    def has_down_script(self) -> bool:
        """Check if migration has down script"""
        return '-- DOWN MIGRATION' in self.content.upper()

    def get_up_script(self) -> str:
        """Extract up migration script"""
        return self.content

    def get_down_script(self) -> Optional[str]:
        """Extract down migration script if available"""
        lines = self.content.split('\n')
        down_start = None

        for i, line in enumerate(lines):
            if '-- DOWN MIGRATION' in line.upper():
                down_start = i + 1
                break

        if down_start:
            return '\n'.join(lines[down_start:])
        return None

class MigrationManager:
    """Main migration manager class"""

    def __init__(self, migrations_dir: str = "migrations"):
        self.migrations_dir = Path(migrations_dir)
        self.db_config = DatabaseConfig()
        self.connection = None
        self.migrations = self._discover_migrations()

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                self.db_config.get_connection_string(),
                cursor_factory=RealDictCursor
            )
            self.connection.autocommit = False
            logger.info("Connected to database successfully")
        except Exception as e:
            raise MigrationError(f"Failed to connect to database: {e}")

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def _discover_migrations(self) -> List[Migration]:
        """Discover all migration files"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory {self.migrations_dir} does not exist")
            return []

        migrations = []
        pattern = re.compile(r'^(\d{3})_(.+)\.sql$')

        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            match = pattern.match(file_path.name)
            if match:
                version = match.group(1)
                name = match.group(2)
                migration = Migration(version, name, file_path)
                migrations.append(migration)
                logger.debug(f"Discovered migration: {version}_{name}")

        return migrations

    def _ensure_migrations_table(self):
        """Ensure schema_migrations table exists"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(20) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            applied_at TIMESTAMPTZ DEFAULT NOW(),
            applied_by VARCHAR(100) DEFAULT current_user,
            checksum VARCHAR(64),
            execution_time_ms INTEGER
        );
        """

        with self.connection.cursor() as cursor:
            cursor.execute(create_table_sql)
            self.connection.commit()

    def get_applied_migrations(self) -> Dict[str, Dict]:
        """Get list of applied migrations from database"""
        self._ensure_migrations_table()

        with self.connection.cursor() as cursor:
            cursor.execute("""
                SELECT version, name, applied_at, applied_by, checksum, execution_time_ms
                FROM schema_migrations
                ORDER BY version
            """)

            applied = {}
            for row in cursor.fetchall():
                applied[row['version']] = dict(row)

            return applied

    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations"""
        applied = self.get_applied_migrations()
        pending = []

        for migration in self.migrations:
            if migration.version not in applied:
                pending.append(migration)
            elif applied[migration.version]['checksum'] != migration.checksum:
                logger.warning(
                    f"Migration {migration.version} checksum mismatch. "
                    f"Applied: {applied[migration.version]['checksum'][:8]}..., "
                    f"Current: {migration.checksum[:8]}..."
                )

        return pending

    def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration"""
        logger.info(f"Applying migration {migration.version}_{migration.name}")

        start_time = datetime.datetime.now()

        try:
            with self.connection.cursor() as cursor:
                # Execute migration script
                cursor.execute(migration.get_up_script())

                # Record migration
                execution_time = (datetime.datetime.now() - start_time).total_seconds() * 1000
                cursor.execute("""
                    INSERT INTO schema_migrations (version, name, checksum, execution_time_ms)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (version) DO UPDATE SET
                        name = EXCLUDED.name,
                        applied_at = NOW(),
                        checksum = EXCLUDED.checksum,
                        execution_time_ms = EXCLUDED.execution_time_ms
                """, (migration.version, migration.name, migration.checksum, int(execution_time)))

                self.connection.commit()
                logger.info(
                    f"Migration {migration.version}_{migration.name} applied successfully "
                    f"in {execution_time:.2f}ms"
                )
                return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to apply migration {migration.version}_{migration.name}: {e}")
            raise MigrationError(f"Migration failed: {e}")

    def rollback_migration(self, migration: Migration) -> bool:
        """Rollback a single migration"""
        down_script = migration.get_down_script()
        if not down_script:
            raise MigrationError(f"Migration {migration.version}_{migration.name} has no down script")

        logger.info(f"Rolling back migration {migration.version}_{migration.name}")

        try:
            with self.connection.cursor() as cursor:
                # Execute rollback script
                cursor.execute(down_script)

                # Remove migration record
                cursor.execute("DELETE FROM schema_migrations WHERE version = %s", (migration.version,))

                self.connection.commit()
                logger.info(f"Migration {migration.version}_{migration.name} rolled back successfully")
                return True

        except Exception as e:
            self.connection.rollback()
            logger.error(f"Failed to rollback migration {migration.version}_{migration.name}: {e}")
            raise MigrationError(f"Rollback failed: {e}")

    def migrate(self, target_version: Optional[str] = None) -> bool:
        """Apply all pending migrations up to target version"""
        pending = self.get_pending_migrations()

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            logger.info("No pending migrations to apply")
            return True

        logger.info(f"Applying {len(pending)} pending migrations")

        for migration in pending:
            if not self.apply_migration(migration):
                return False

        logger.info("All migrations applied successfully")
        return True

    def rollback(self, target_version: Optional[str] = None) -> bool:
        """Rollback migrations to target version"""
        applied = self.get_applied_migrations()

        if not target_version:
            # Rollback last migration
            if not applied:
                logger.info("No migrations to rollback")
                return True
            target_version = max(applied.keys())

        # Find migrations to rollback
        to_rollback = []
        for migration in reversed(self.migrations):
            if migration.version in applied and migration.version > target_version:
                to_rollback.append(migration)

        if not to_rollback:
            logger.info("No migrations to rollback")
            return True

        logger.info(f"Rolling back {len(to_rollback)} migrations")

        for migration in to_rollback:
            if not self.rollback_migration(migration):
                return False

        logger.info("Rollback completed successfully")
        return True

    def status(self) -> Dict:
        """Get migration status"""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        status = {
            'total_migrations': len(self.migrations),
            'applied_count': len(applied),
            'pending_count': len(pending),
            'applied_migrations': list(applied.keys()),
            'pending_migrations': [m.version for m in pending],
            'database': self.db_config.config['database'],
            'last_migration': max(applied.keys()) if applied else None
        }

        return status

    def validate(self) -> bool:
        """Validate migration integrity"""
        logger.info("Validating migration integrity")

        applied = self.get_applied_migrations()
        issues = []

        # Check for missing migration files
        for version in applied:
            migration_file = self.migrations_dir / f"{version}_{applied[version]['name']}.sql"
            if not migration_file.exists():
                issues.append(f"Missing migration file for applied migration: {version}")

        # Check for checksum mismatches
        for migration in self.migrations:
            if migration.version in applied:
                if applied[migration.version]['checksum'] != migration.checksum:
                    issues.append(f"Checksum mismatch for migration {migration.version}")

        # Check for invalid migration syntax
        for migration in self.migrations:
            if not migration.has_up_script():
                issues.append(f"Migration {migration.version} missing valid up script")

        if issues:
            logger.error("Migration validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        logger.info("Migration validation passed")
        return True

    def create_migration(self, name: str) -> str:
        """Create a new migration file template"""
        # Get next version number
        existing_versions = [int(m.version) for m in self.migrations]
        next_version = f"{max(existing_versions, default=0) + 1:03d}"

        # Clean name
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        filename = f"{next_version}_{clean_name}.sql"
        file_path = self.migrations_dir / filename

        # Create migrations directory if it doesn't exist
        self.migrations_dir.mkdir(exist_ok=True)

        # Migration template
        template = f"""-- Migration: {filename}
-- Description: {name}
-- Version: {next_version}
-- Created: {datetime.datetime.now().strftime('%Y-%m-%d')}

BEGIN;

-- ============================================================================
-- UP MIGRATION
-- ============================================================================

-- Add your migration SQL here
-- Example:
-- CREATE TABLE example_table (
--     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--     name VARCHAR(255) NOT NULL,
--     created_at TIMESTAMPTZ DEFAULT NOW()
-- );

-- Record migration
INSERT INTO schema_migrations (version, name, checksum)
VALUES ('{next_version}', '{clean_name}', 'checksum_placeholder');

COMMIT;

-- ============================================================================
-- DOWN MIGRATION
-- ============================================================================

-- BEGIN;
--
-- -- Add your rollback SQL here
-- -- Example:
-- -- DROP TABLE IF EXISTS example_table;
--
-- -- Remove migration record
-- DELETE FROM schema_migrations WHERE version = '{next_version}';
--
-- COMMIT;
"""

        with open(file_path, 'w') as f:
            f.write(template)

        logger.info(f"Created migration file: {file_path}")
        return str(file_path)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Sunday.com Database Migration Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Migrate command
    migrate_parser = subparsers.add_parser('migrate', help='Apply pending migrations')
    migrate_parser.add_argument('--target', help='Target migration version')

    # Rollback command
    rollback_parser = subparsers.add_parser('rollback', help='Rollback migrations')
    rollback_parser.add_argument('--target', help='Target migration version to rollback to')

    # Status command
    subparsers.add_parser('status', help='Show migration status')

    # Create command
    create_parser = subparsers.add_parser('create', help='Create new migration')
    create_parser.add_argument('name', help='Migration name')

    # Validate command
    subparsers.add_parser('validate', help='Validate migration integrity')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        with MigrationManager() as manager:
            if args.command == 'migrate':
                success = manager.migrate(args.target)
                sys.exit(0 if success else 1)

            elif args.command == 'rollback':
                success = manager.rollback(args.target)
                sys.exit(0 if success else 1)

            elif args.command == 'status':
                status = manager.status()
                print(f"Database: {status['database']}")
                print(f"Total migrations: {status['total_migrations']}")
                print(f"Applied: {status['applied_count']}")
                print(f"Pending: {status['pending_count']}")
                print(f"Last migration: {status['last_migration'] or 'None'}")

                if status['pending_migrations']:
                    print(f"Pending migrations: {', '.join(status['pending_migrations'])}")

            elif args.command == 'validate':
                success = manager.validate()
                sys.exit(0 if success else 1)

            elif args.command == 'create':
                manager = MigrationManager()  # Don't need DB connection for create
                file_path = manager.create_migration(args.name)
                print(f"Created migration: {file_path}")

    except MigrationError as e:
        logger.error(f"Migration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()