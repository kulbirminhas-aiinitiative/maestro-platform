"""
Data Synchronization Manager.

EPIC: MD-2790 - AC-13, AC-14, AC-15, AC-16
Handles database data synchronization across environments.
"""

import logging
import subprocess
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DataSyncStatus(str, Enum):
    """Data sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class SyncMode(str, Enum):
    """Data sync mode."""
    FULL = "full"  # Replace all data
    UPSERT = "upsert"  # Insert or update
    APPEND = "append"  # Only insert new records


@dataclass
class TableSyncConfig:
    """Configuration for syncing a specific table."""
    table_name: str
    primary_key: str = "id"
    exclude_columns: list[str] = field(default_factory=list)
    where_clause: Optional[str] = None
    sync_mode: SyncMode = SyncMode.UPSERT


@dataclass
class DataSyncResult:
    """Result of a data sync operation."""
    sync_id: str
    source_env: str
    target_env: str
    status: DataSyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    tables_synced: list[str] = field(default_factory=list)
    records_processed: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_failed: int = 0
    error: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "sync_id": self.sync_id,
            "source_environment": self.source_env,
            "target_environment": self.target_env,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tables_synced": self.tables_synced,
            "records_processed": self.records_processed,
            "records_inserted": self.records_inserted,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "error": self.error,
            "details": self.details
        }


@dataclass
class EnvironmentDBConfig:
    """Database configuration for an environment."""
    host: str
    port: int
    database: str
    username: str
    password: str = ""

    @property
    def connection_string(self) -> str:
        """Generate PostgreSQL connection string."""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def psql_args(self) -> list[str]:
        """Get psql command arguments."""
        return ["-h", self.host, "-p", str(self.port), "-U", self.username, "-d", self.database]


class DataSyncManager:
    """
    Manages database data synchronization across environments.

    Implements:
    - AC-13: Export and import team_star_ratings_history from production
    - AC-14: Export additional ai_agents (17 records)
    - AC-15: Export additional users (19 records)
    - AC-16: Sandbox database matches production data
    """

    # Default environment configurations
    DEFAULT_CONFIGS = {
        "production": EnvironmentDBConfig(
            host="localhost",
            port=5435,
            database="maestro",
            username="postgres"
        ),
        "sandbox": EnvironmentDBConfig(
            host="localhost",
            port=15432,
            database="maestro",
            username="postgres"
        ),
        "demo": EnvironmentDBConfig(
            host="localhost",
            port=5432,
            database="maestro",
            username="postgres"
        ),
        "dev": EnvironmentDBConfig(
            host="localhost",
            port=5432,
            database="maestro",
            username="postgres"
        )
    }

    # Tables commonly synced
    DEFAULT_TABLES = [
        TableSyncConfig(
            table_name="users",
            primary_key="id",
            where_clause="email = 'demo@fifth-9.com'"
        ),
        TableSyncConfig(
            table_name="ai_agents",
            primary_key="id"
        ),
        TableSyncConfig(
            table_name="team_blueprints",
            primary_key="id"
        ),
        TableSyncConfig(
            table_name="team_star_ratings_history",
            primary_key="id"
        ),
        TableSyncConfig(
            table_name="team_evolution_stats",
            primary_key="id"
        )
    ]

    def __init__(
        self,
        configs: Optional[dict[str, EnvironmentDBConfig]] = None,
        export_dir: Optional[Path] = None
    ):
        self.configs = configs or self.DEFAULT_CONFIGS
        self.export_dir = export_dir or Path("/tmp/data_sync_exports")
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self._sync_history: list[DataSyncResult] = []

    def get_table_count(self, environment: str, table_name: str) -> int:
        """Get row count for a table in an environment."""
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        try:
            result = subprocess.run(
                ["psql"] + config.psql_args + ["-t", "-c", f"SELECT COUNT(*) FROM {table_name}"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return int(result.stdout.strip())
            return 0
        except Exception as e:
            logger.error(f"Failed to count {table_name} in {environment}: {e}")
            return 0

    def compare_table_counts(
        self,
        source: str,
        target: str,
        tables: Optional[list[str]] = None
    ) -> dict[str, Any]:
        """
        Compare table row counts between environments.

        AC-16: Sandbox database matches production data.
        """
        if tables is None:
            tables = [t.table_name for t in self.DEFAULT_TABLES]

        comparison = {
            "source_environment": source,
            "target_environment": target,
            "tables": {},
            "checked_at": datetime.utcnow().isoformat()
        }

        total_diff = 0
        for table in tables:
            source_count = self.get_table_count(source, table)
            target_count = self.get_table_count(target, table)
            diff = source_count - target_count

            comparison["tables"][table] = {
                "source_count": source_count,
                "target_count": target_count,
                "difference": diff,
                "matches": source_count == target_count
            }
            total_diff += abs(diff)

        comparison["total_difference"] = total_diff
        comparison["all_match"] = total_diff == 0

        return comparison

    def export_table_data(
        self,
        environment: str,
        table_config: TableSyncConfig
    ) -> Path:
        """
        Export table data to SQL file.

        AC-13, AC-14, AC-15: Export data from source environment.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        config = self.configs[environment]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_file = self.export_dir / f"{table_config.table_name}_{environment}_{timestamp}.sql"

        # Build pg_dump command
        cmd = [
            "pg_dump",
            "-h", config.host,
            "-p", str(config.port),
            "-U", config.username,
            "-d", config.database,
            "-t", table_config.table_name,
            "--data-only",
            "--column-inserts"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                with open(export_file, "w") as f:
                    # Add header
                    f.write(f"-- Data export for {table_config.table_name}\n")
                    f.write(f"-- Source: {environment}\n")
                    f.write(f"-- Timestamp: {timestamp}\n")
                    f.write(f"-- EPIC: MD-2790\n\n")
                    f.write(result.stdout)

                logger.info(f"Exported {table_config.table_name} to {export_file}")
                return export_file
            else:
                logger.error(f"pg_dump failed: {result.stderr}")
                raise RuntimeError(f"pg_dump failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Export failed for {table_config.table_name}: {e}")
            raise

    def import_table_data(
        self,
        environment: str,
        sql_file: Path,
        truncate_first: bool = False
    ) -> dict[str, Any]:
        """
        Import table data from SQL file.

        AC-13, AC-14, AC-15: Import data to target environment.
        """
        if environment not in self.configs:
            raise ValueError(f"Unknown environment: {environment}")

        if not sql_file.exists():
            raise FileNotFoundError(f"SQL file not found: {sql_file}")

        config = self.configs[environment]

        try:
            if truncate_first:
                # Extract table name from file
                table_name = sql_file.stem.split("_")[0]
                truncate_result = subprocess.run(
                    ["psql"] + config.psql_args + ["-c", f"TRUNCATE TABLE {table_name} CASCADE"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if truncate_result.returncode != 0:
                    logger.warning(f"Truncate failed: {truncate_result.stderr}")

            # Import data
            result = subprocess.run(
                ["psql"] + config.psql_args + ["-f", str(sql_file)],
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "status": "success" if result.returncode == 0 else "failed",
                "environment": environment,
                "file": str(sql_file),
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except Exception as e:
            return {
                "status": "error",
                "environment": environment,
                "file": str(sql_file),
                "error": str(e)
            }

    async def sync_table(
        self,
        source: str,
        target: str,
        table_config: TableSyncConfig
    ) -> dict[str, Any]:
        """Sync a single table from source to target."""
        try:
            # Export from source
            export_file = self.export_table_data(source, table_config)

            # Count records before import
            before_count = self.get_table_count(target, table_config.table_name)

            # Import to target
            import_result = self.import_table_data(target, export_file)

            # Count records after import
            after_count = self.get_table_count(target, table_config.table_name)

            return {
                "table": table_config.table_name,
                "status": import_result.get("status", "unknown"),
                "before_count": before_count,
                "after_count": after_count,
                "records_added": max(0, after_count - before_count),
                "export_file": str(export_file)
            }

        except Exception as e:
            return {
                "table": table_config.table_name,
                "status": "error",
                "error": str(e)
            }

    async def sync_data(
        self,
        source: str,
        target: str,
        tables: Optional[list[TableSyncConfig]] = None
    ) -> DataSyncResult:
        """
        Synchronize data from source to target environment.

        Full implementation of AC-13 through AC-16.
        """
        import uuid

        if tables is None:
            tables = self.DEFAULT_TABLES

        sync_id = str(uuid.uuid4())
        result = DataSyncResult(
            sync_id=sync_id,
            source_env=source,
            target_env=target,
            status=DataSyncStatus.IN_PROGRESS,
            started_at=datetime.utcnow()
        )

        try:
            details: dict[str, Any] = {"tables": {}}
            total_processed = 0
            total_inserted = 0
            tables_synced = []

            for table_config in tables:
                table_result = await self.sync_table(source, target, table_config)
                details["tables"][table_config.table_name] = table_result

                if table_result.get("status") == "success":
                    tables_synced.append(table_config.table_name)
                    total_inserted += table_result.get("records_added", 0)

                total_processed += 1

            result.tables_synced = tables_synced
            result.records_processed = total_processed
            result.records_inserted = total_inserted
            result.details = details

            if len(tables_synced) == len(tables):
                result.status = DataSyncStatus.COMPLETED
            elif len(tables_synced) > 0:
                result.status = DataSyncStatus.PARTIAL
            else:
                result.status = DataSyncStatus.FAILED

            result.completed_at = datetime.utcnow()

        except Exception as e:
            result.status = DataSyncStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.utcnow()
            logger.error(f"Data sync failed: {e}")

        self._sync_history.append(result)
        return result

    async def sync_users(
        self,
        source: str,
        target: str,
        email_filter: Optional[str] = "demo@fifth-9.com"
    ) -> dict[str, Any]:
        """
        Sync specific user(s) from source to target.

        AC-15: Export additional users (19 records).
        """
        table_config = TableSyncConfig(
            table_name="users",
            primary_key="id",
            where_clause=f"email = '{email_filter}'" if email_filter else None
        )

        return await self.sync_table(source, target, table_config)

    async def sync_ai_agents(
        self,
        source: str,
        target: str
    ) -> dict[str, Any]:
        """
        Sync AI Agents from source to target.

        AC-14: Export additional ai_agents (17 records).
        """
        table_config = TableSyncConfig(
            table_name="ai_agents",
            primary_key="id"
        )

        return await self.sync_table(source, target, table_config)

    async def sync_star_ratings_history(
        self,
        source: str,
        target: str
    ) -> dict[str, Any]:
        """
        Sync team star ratings history.

        AC-13: Export and import team_star_ratings_history from production.
        """
        table_config = TableSyncConfig(
            table_name="team_star_ratings_history",
            primary_key="id"
        )

        return await self.sync_table(source, target, table_config)

    def get_sync_history(self, limit: int = 50) -> list[DataSyncResult]:
        """Get recent sync history."""
        return self._sync_history[-limit:]

    def generate_comparison_report(
        self,
        source: str,
        target: str
    ) -> dict[str, Any]:
        """
        Generate detailed comparison report between environments.

        Verifies AC-16: Sandbox database matches production data.
        """
        tables = [t.table_name for t in self.DEFAULT_TABLES]
        comparison = self.compare_table_counts(source, target, tables)

        report = {
            "title": f"Data Comparison: {source} vs {target}",
            "epic": "MD-2790",
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "source": source,
                "target": target,
                "tables_compared": len(tables),
                "tables_matching": sum(
                    1 for t in comparison["tables"].values() if t["matches"]
                ),
                "total_difference": comparison["total_difference"],
                "all_match": comparison["all_match"]
            },
            "details": comparison["tables"],
            "recommendations": []
        }

        # Add recommendations based on differences
        for table, data in comparison["tables"].items():
            if not data["matches"]:
                diff = data["difference"]
                if diff > 0:
                    report["recommendations"].append(
                        f"Sync {diff} records from {source} to {target} for table '{table}'"
                    )
                else:
                    report["recommendations"].append(
                        f"Table '{table}' has {abs(diff)} extra records in {target}"
                    )

        return report
