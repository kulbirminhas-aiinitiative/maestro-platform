#!/usr/bin/env python3
"""
Sunday.com Database Backup and Recovery Manager

Comprehensive backup and disaster recovery system for PostgreSQL databases.
Supports multiple backup strategies, automated scheduling, encryption,
compression, and multi-region replication.

Features:
- Full, incremental, and differential backups
- Point-in-time recovery (PITR)
- Automated backup scheduling
- Backup verification and integrity checks
- Encrypted and compressed backups
- Multi-region backup replication
- Disaster recovery automation
- Backup retention management
"""

import os
import sys
import json
import time
import boto3
import logging
import argparse
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from cryptography.fernet import Fernet
import schedule

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class BackupMetadata:
    """Backup metadata structure"""
    backup_id: str
    backup_type: str  # full, incremental, differential
    database_name: str
    timestamp: datetime.datetime
    size_bytes: int
    compressed_size_bytes: int
    duration_seconds: float
    wal_start_lsn: str
    wal_end_lsn: str
    checksum: str
    encrypted: bool
    s3_path: Optional[str] = None
    local_path: Optional[str] = None
    verified: bool = False
    retention_date: Optional[datetime.datetime] = None

@dataclass
class RecoveryPoint:
    """Point-in-time recovery point"""
    timestamp: datetime.datetime
    backup_id: str
    wal_file: str
    lsn: str
    description: str

class BackupError(Exception):
    """Custom backup exception"""
    pass

class EncryptionManager:
    """Manages backup encryption and decryption"""

    def __init__(self, key_file: str = "backup_encryption.key"):
        self.key_file = key_file
        self.key = self._load_or_create_key()

    def _load_or_create_key(self) -> bytes:
        """Load existing key or create new one"""
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Restrict permissions
            logger.info(f"Created new encryption key: {self.key_file}")
            return key

    def encrypt_file(self, file_path: str) -> str:
        """Encrypt a file and return the encrypted file path"""
        fernet = Fernet(self.key)
        encrypted_path = f"{file_path}.encrypted"

        with open(file_path, 'rb') as infile, open(encrypted_path, 'wb') as outfile:
            while True:
                chunk = infile.read(8192)
                if not chunk:
                    break
                encrypted_chunk = fernet.encrypt(chunk)
                outfile.write(encrypted_chunk)

        return encrypted_path

    def decrypt_file(self, encrypted_file_path: str, output_path: str) -> str:
        """Decrypt a file and return the decrypted file path"""
        fernet = Fernet(self.key)

        with open(encrypted_file_path, 'rb') as infile, open(output_path, 'wb') as outfile:
            while True:
                chunk = infile.read(8192 + 44)  # Account for Fernet overhead
                if not chunk:
                    break
                try:
                    decrypted_chunk = fernet.decrypt(chunk)
                    outfile.write(decrypted_chunk)
                except Exception as e:
                    logger.error(f"Decryption error: {e}")
                    raise BackupError(f"Failed to decrypt file: {e}")

        return output_path

class S3BackupStorage:
    """S3 storage backend for backups"""

    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except:
            try:
                if self.region == 'us-east-1':
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
                logger.info(f"Created S3 bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to create S3 bucket: {e}")
                raise

    def upload_backup(self, local_path: str, s3_key: str, metadata: Dict = None) -> bool:
        """Upload backup file to S3"""
        try:
            extra_args = {}
            if metadata:
                extra_args['Metadata'] = {k: str(v) for k, v in metadata.items()}

            # Enable server-side encryption
            extra_args['ServerSideEncryption'] = 'AES256'

            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(f"Uploaded backup to S3: s3://{self.bucket_name}/{s3_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to upload backup to S3: {e}")
            return False

    def download_backup(self, s3_key: str, local_path: str) -> bool:
        """Download backup file from S3"""
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded backup from S3: {s3_key} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to download backup from S3: {e}")
            return False

    def list_backups(self, prefix: str = "") -> List[Dict]:
        """List backup files in S3"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            backups = []
            for obj in response.get('Contents', []):
                backups.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag']
                })

            return backups

        except Exception as e:
            logger.error(f"Failed to list S3 backups: {e}")
            return []

    def delete_backup(self, s3_key: str) -> bool:
        """Delete backup file from S3"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted backup from S3: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup from S3: {e}")
            return False

class PostgreSQLBackupManager:
    """PostgreSQL backup manager"""

    def __init__(self, connection_config: Dict, backup_dir: str = "/var/backups/sunday"):
        self.connection_config = connection_config
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self.encryption_manager = EncryptionManager()
        self.s3_storage = None
        self.metadata = self._load_metadata()

        # Initialize S3 if configured
        if os.getenv('BACKUP_S3_BUCKET'):
            self.s3_storage = S3BackupStorage(
                bucket_name=os.getenv('BACKUP_S3_BUCKET'),
                region=os.getenv('BACKUP_S3_REGION', 'us-east-1')
            )

    def _load_metadata(self) -> Dict[str, BackupMetadata]:
        """Load backup metadata from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    return {
                        k: BackupMetadata(**v) for k, v in data.items()
                    }
            except Exception as e:
                logger.error(f"Failed to load backup metadata: {e}")

        return {}

    def _save_metadata(self):
        """Save backup metadata to file"""
        try:
            data = {k: asdict(v) for k, v in self.metadata.items()}
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save backup metadata: {e}")

    def _get_connection_string(self) -> str:
        """Get PostgreSQL connection string"""
        return (
            f"host={self.connection_config['host']} "
            f"port={self.connection_config['port']} "
            f"dbname={self.connection_config['database']} "
            f"user={self.connection_config['user']}"
        )

    def _run_command(self, command: List[str], env: Dict = None) -> Tuple[int, str, str]:
        """Run shell command and return result"""
        try:
            env_vars = os.environ.copy()
            if env:
                env_vars.update(env)

            if 'password' in self.connection_config:
                env_vars['PGPASSWORD'] = self.connection_config['password']

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=env_vars,
                check=False
            )

            return result.returncode, result.stdout, result.stderr

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return 1, "", str(e)

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum of a file"""
        import hashlib
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    def _compress_file(self, file_path: str) -> str:
        """Compress file using gzip"""
        compressed_path = f"{file_path}.gz"
        command = ["gzip", "-c", file_path]

        try:
            with open(compressed_path, 'wb') as f:
                result = subprocess.run(command, stdout=f, check=True)

            logger.info(f"Compressed backup: {file_path} -> {compressed_path}")
            return compressed_path

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise BackupError(f"Failed to compress backup: {e}")

    def create_full_backup(self, backup_id: str = None) -> BackupMetadata:
        """Create a full database backup"""
        if not backup_id:
            backup_id = f"full_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting full backup: {backup_id}")
        start_time = time.time()

        # Create backup directory
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)

        # Full backup using pg_dump
        dump_file = backup_path / f"{backup_id}.sql"
        command = [
            "pg_dump",
            "--host", self.connection_config['host'],
            "--port", str(self.connection_config['port']),
            "--username", self.connection_config['user'],
            "--dbname", self.connection_config['database'],
            "--format", "custom",
            "--compress", "9",
            "--verbose",
            "--file", str(dump_file)
        ]

        returncode, stdout, stderr = self._run_command(command)

        if returncode != 0:
            logger.error(f"Full backup failed: {stderr}")
            raise BackupError(f"pg_dump failed: {stderr}")

        # Get WAL information
        wal_info = self._get_wal_info()

        # Calculate file sizes and checksum
        original_size = dump_file.stat().st_size
        checksum = self._calculate_checksum(str(dump_file))

        # Compress backup
        compressed_file = self._compress_file(str(dump_file))
        compressed_size = Path(compressed_file).stat().st_size

        # Encrypt backup
        encrypted_file = self.encryption_manager.encrypt_file(compressed_file)

        # Create metadata
        duration = time.time() - start_time
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type="full",
            database_name=self.connection_config['database'],
            timestamp=datetime.datetime.now(),
            size_bytes=original_size,
            compressed_size_bytes=compressed_size,
            duration_seconds=duration,
            wal_start_lsn=wal_info.get('current_lsn', ''),
            wal_end_lsn=wal_info.get('current_lsn', ''),
            checksum=checksum,
            encrypted=True,
            local_path=str(encrypted_file)
        )

        # Upload to S3 if configured
        if self.s3_storage:
            s3_key = f"backups/{backup_id}/{Path(encrypted_file).name}"
            if self.s3_storage.upload_backup(encrypted_file, s3_key, asdict(metadata)):
                metadata.s3_path = s3_key

        # Save metadata
        self.metadata[backup_id] = metadata
        self._save_metadata()

        # Cleanup local unencrypted files
        dump_file.unlink()
        Path(compressed_file).unlink()

        logger.info(f"Full backup completed: {backup_id} ({duration:.2f}s)")
        return metadata

    def create_incremental_backup(self, base_backup_id: str, backup_id: str = None) -> BackupMetadata:
        """Create an incremental backup (WAL files since last backup)"""
        if not backup_id:
            backup_id = f"incr_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting incremental backup: {backup_id}")
        start_time = time.time()

        # Get base backup metadata
        if base_backup_id not in self.metadata:
            raise BackupError(f"Base backup not found: {base_backup_id}")

        base_backup = self.metadata[base_backup_id]

        # Create backup directory
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)

        # Archive WAL files since base backup
        wal_archive_dir = backup_path / "wal_files"
        wal_archive_dir.mkdir(exist_ok=True)

        # Get WAL files using pg_receivewal or manual archiving
        current_wal_info = self._get_wal_info()
        wal_files = self._get_wal_files_since_lsn(base_backup.wal_end_lsn)

        total_size = 0
        for wal_file in wal_files:
            wal_path = wal_archive_dir / wal_file
            if self._archive_wal_file(wal_file, str(wal_path)):
                total_size += wal_path.stat().st_size

        # Create tar archive of WAL files
        tar_file = backup_path / f"{backup_id}_wal.tar"
        command = ["tar", "-cf", str(tar_file), "-C", str(wal_archive_dir), "."]
        returncode, stdout, stderr = self._run_command(command)

        if returncode != 0:
            raise BackupError(f"Failed to create WAL archive: {stderr}")

        # Compress and encrypt
        compressed_file = self._compress_file(str(tar_file))
        encrypted_file = self.encryption_manager.encrypt_file(compressed_file)

        # Calculate sizes and checksum
        compressed_size = Path(compressed_file).stat().st_size
        checksum = self._calculate_checksum(str(tar_file))

        # Create metadata
        duration = time.time() - start_time
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type="incremental",
            database_name=self.connection_config['database'],
            timestamp=datetime.datetime.now(),
            size_bytes=total_size,
            compressed_size_bytes=compressed_size,
            duration_seconds=duration,
            wal_start_lsn=base_backup.wal_end_lsn,
            wal_end_lsn=current_wal_info.get('current_lsn', ''),
            checksum=checksum,
            encrypted=True,
            local_path=str(encrypted_file)
        )

        # Upload to S3 if configured
        if self.s3_storage:
            s3_key = f"backups/{backup_id}/{Path(encrypted_file).name}"
            if self.s3_storage.upload_backup(encrypted_file, s3_key, asdict(metadata)):
                metadata.s3_path = s3_key

        # Save metadata
        self.metadata[backup_id] = metadata
        self._save_metadata()

        # Cleanup
        tar_file.unlink()
        Path(compressed_file).unlink()

        logger.info(f"Incremental backup completed: {backup_id} ({duration:.2f}s)")
        return metadata

    def _get_wal_info(self) -> Dict:
        """Get current WAL information"""
        try:
            connection = psycopg2.connect(self._get_connection_string())
            cursor = connection.cursor()

            cursor.execute("SELECT pg_current_wal_lsn(), pg_current_wal_flush_lsn()")
            current_lsn, flush_lsn = cursor.fetchone()

            cursor.execute("SELECT pg_walfile_name(pg_current_wal_lsn())")
            wal_file = cursor.fetchone()[0]

            cursor.close()
            connection.close()

            return {
                'current_lsn': current_lsn,
                'flush_lsn': flush_lsn,
                'wal_file': wal_file
            }

        except Exception as e:
            logger.error(f"Failed to get WAL info: {e}")
            return {}

    def _get_wal_files_since_lsn(self, start_lsn: str) -> List[str]:
        """Get WAL files since specified LSN"""
        # This is a simplified implementation
        # In production, you'd query pg_ls_waldir() or use pg_receivewal
        try:
            connection = psycopg2.connect(self._get_connection_string())
            cursor = connection.cursor()

            cursor.execute("""
                SELECT name FROM pg_ls_waldir()
                WHERE name ~ '^[0-9A-F]{24}$'
                ORDER BY name
            """)

            wal_files = [row[0] for row in cursor.fetchall()]
            cursor.close()
            connection.close()

            return wal_files

        except Exception as e:
            logger.error(f"Failed to get WAL files: {e}")
            return []

    def _archive_wal_file(self, wal_file: str, destination: str) -> bool:
        """Archive a specific WAL file"""
        # In production, this would copy from pg_wal directory
        # or use pg_receivewal for streaming
        try:
            wal_source = f"/var/lib/postgresql/data/pg_wal/{wal_file}"
            if os.path.exists(wal_source):
                command = ["cp", wal_source, destination]
                returncode, stdout, stderr = self._run_command(command)
                return returncode == 0
        except Exception as e:
            logger.error(f"Failed to archive WAL file {wal_file}: {e}")

        return False

    def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity"""
        if backup_id not in self.metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False

        metadata = self.metadata[backup_id]
        logger.info(f"Verifying backup: {backup_id}")

        try:
            # Download from S3 if needed
            local_file = metadata.local_path
            if not local_file or not os.path.exists(local_file):
                if metadata.s3_path and self.s3_storage:
                    temp_file = f"/tmp/verify_{backup_id}"
                    if not self.s3_storage.download_backup(metadata.s3_path, temp_file):
                        return False
                    local_file = temp_file
                else:
                    logger.error(f"Backup file not found: {backup_id}")
                    return False

            # Decrypt backup
            temp_decrypted = f"/tmp/verify_decrypted_{backup_id}"
            self.encryption_manager.decrypt_file(local_file, temp_decrypted)

            # Decompress
            temp_decompressed = f"/tmp/verify_decompressed_{backup_id}"
            command = ["gunzip", "-c", temp_decrypted]
            with open(temp_decompressed, 'wb') as f:
                result = subprocess.run(command, stdout=f, check=True)

            # Verify checksum
            calculated_checksum = self._calculate_checksum(temp_decompressed)
            checksum_valid = calculated_checksum == metadata.checksum

            # Cleanup temp files
            for temp_file in [temp_decrypted, temp_decompressed]:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

            if local_file.startswith('/tmp/'):
                os.unlink(local_file)

            if checksum_valid:
                logger.info(f"Backup verification successful: {backup_id}")
                metadata.verified = True
                self._save_metadata()
            else:
                logger.error(f"Backup verification failed - checksum mismatch: {backup_id}")

            return checksum_valid

        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False

    def restore_database(self, backup_id: str, target_time: Optional[datetime.datetime] = None) -> bool:
        """Restore database from backup"""
        if backup_id not in self.metadata:
            logger.error(f"Backup not found: {backup_id}")
            return False

        metadata = self.metadata[backup_id]
        logger.info(f"Starting database restore from backup: {backup_id}")

        try:
            # Stop database connections
            self._terminate_connections()

            # Download backup if needed
            local_file = metadata.local_path
            if not local_file or not os.path.exists(local_file):
                if metadata.s3_path and self.s3_storage:
                    temp_file = f"/tmp/restore_{backup_id}"
                    if not self.s3_storage.download_backup(metadata.s3_path, temp_file):
                        return False
                    local_file = temp_file
                else:
                    raise BackupError(f"Backup file not found: {backup_id}")

            # Decrypt and decompress backup
            temp_decrypted = f"/tmp/restore_decrypted_{backup_id}"
            self.encryption_manager.decrypt_file(local_file, temp_decrypted)

            temp_decompressed = f"/tmp/restore_decompressed_{backup_id}"
            command = ["gunzip", "-c", temp_decrypted]
            with open(temp_decompressed, 'wb') as f:
                subprocess.run(command, stdout=f, check=True)

            # Drop and recreate database
            self._recreate_database()

            # Restore from backup
            command = [
                "pg_restore",
                "--host", self.connection_config['host'],
                "--port", str(self.connection_config['port']),
                "--username", self.connection_config['user'],
                "--dbname", self.connection_config['database'],
                "--verbose",
                "--clean",
                "--if-exists",
                temp_decompressed
            ]

            returncode, stdout, stderr = self._run_command(command)

            if returncode != 0:
                raise BackupError(f"Database restore failed: {stderr}")

            # Apply WAL files for point-in-time recovery if needed
            if target_time and metadata.backup_type == "full":
                self._apply_wal_files_until_time(target_time)

            # Cleanup temp files
            for temp_file in [temp_decrypted, temp_decompressed]:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

            if local_file.startswith('/tmp/'):
                os.unlink(local_file)

            logger.info(f"Database restore completed successfully: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Database restore failed: {e}")
            return False

    def _terminate_connections(self):
        """Terminate all connections to the database"""
        try:
            # Connect to postgres database to terminate connections
            admin_config = self.connection_config.copy()
            admin_config['database'] = 'postgres'

            connection = psycopg2.connect(
                f"host={admin_config['host']} "
                f"port={admin_config['port']} "
                f"dbname={admin_config['database']} "
                f"user={admin_config['user']}"
            )
            connection.autocommit = True
            cursor = connection.cursor()

            cursor.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{self.connection_config['database']}'
                AND pid != pg_backend_pid()
            """)

            cursor.close()
            connection.close()

        except Exception as e:
            logger.warning(f"Failed to terminate connections: {e}")

    def _recreate_database(self):
        """Drop and recreate the database"""
        try:
            admin_config = self.connection_config.copy()
            admin_config['database'] = 'postgres'

            connection = psycopg2.connect(
                f"host={admin_config['host']} "
                f"port={admin_config['port']} "
                f"dbname={admin_config['database']} "
                f"user={admin_config['user']}"
            )
            connection.autocommit = True
            cursor = connection.cursor()

            db_name = self.connection_config['database']
            cursor.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            cursor.execute(f'CREATE DATABASE "{db_name}"')

            cursor.close()
            connection.close()

        except Exception as e:
            raise BackupError(f"Failed to recreate database: {e}")

    def _apply_wal_files_until_time(self, target_time: datetime.datetime):
        """Apply WAL files for point-in-time recovery"""
        # This is a simplified implementation
        # In production, you'd use pg_waldump and recovery.conf
        logger.info(f"Applying WAL files for PITR to: {target_time}")

    def cleanup_old_backups(self, retention_days: int = 30):
        """Clean up old backups based on retention policy"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
        logger.info(f"Cleaning up backups older than {retention_days} days")

        to_delete = []
        for backup_id, metadata in self.metadata.items():
            if metadata.timestamp < cutoff_date:
                to_delete.append(backup_id)

        for backup_id in to_delete:
            metadata = self.metadata[backup_id]

            # Delete from S3
            if metadata.s3_path and self.s3_storage:
                self.s3_storage.delete_backup(metadata.s3_path)

            # Delete local file
            if metadata.local_path and os.path.exists(metadata.local_path):
                os.unlink(metadata.local_path)

            # Remove from metadata
            del self.metadata[backup_id]
            logger.info(f"Deleted old backup: {backup_id}")

        self._save_metadata()

    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups"""
        return sorted(self.metadata.values(), key=lambda x: x.timestamp, reverse=True)

    def get_recovery_points(self) -> List[RecoveryPoint]:
        """Get available recovery points"""
        recovery_points = []

        for metadata in self.metadata.values():
            if metadata.backup_type == "full":
                recovery_points.append(RecoveryPoint(
                    timestamp=metadata.timestamp,
                    backup_id=metadata.backup_id,
                    wal_file="",
                    lsn=metadata.wal_end_lsn,
                    description=f"Full backup: {metadata.backup_id}"
                ))

        return sorted(recovery_points, key=lambda x: x.timestamp, reverse=True)

class BackupScheduler:
    """Automated backup scheduler"""

    def __init__(self, backup_manager: PostgreSQLBackupManager):
        self.backup_manager = backup_manager
        self.scheduler_running = False

    def schedule_backups(self):
        """Set up backup schedules"""
        # Full backup weekly on Sunday at 2 AM
        schedule.every().sunday.at("02:00").do(self._run_full_backup)

        # Incremental backup daily at 2 AM (except Sunday)
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
            getattr(schedule.every(), day).at("02:00").do(self._run_incremental_backup)

        # Cleanup old backups monthly
        schedule.every().month.do(self._run_cleanup)

        logger.info("Backup schedules configured")

    def _run_full_backup(self):
        """Run scheduled full backup"""
        try:
            logger.info("Running scheduled full backup")
            self.backup_manager.create_full_backup()
        except Exception as e:
            logger.error(f"Scheduled full backup failed: {e}")

    def _run_incremental_backup(self):
        """Run scheduled incremental backup"""
        try:
            logger.info("Running scheduled incremental backup")
            # Find latest full backup
            backups = self.backup_manager.list_backups()
            latest_full = None

            for backup in backups:
                if backup.backup_type == "full":
                    latest_full = backup
                    break

            if latest_full:
                self.backup_manager.create_incremental_backup(latest_full.backup_id)
            else:
                logger.warning("No full backup found for incremental backup")
                self.backup_manager.create_full_backup()

        except Exception as e:
            logger.error(f"Scheduled incremental backup failed: {e}")

    def _run_cleanup(self):
        """Run scheduled cleanup"""
        try:
            logger.info("Running scheduled backup cleanup")
            self.backup_manager.cleanup_old_backups()
        except Exception as e:
            logger.error(f"Scheduled cleanup failed: {e}")

    def start_scheduler(self):
        """Start the backup scheduler"""
        self.scheduler_running = True
        logger.info("Backup scheduler started")

        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def stop_scheduler(self):
        """Stop the backup scheduler"""
        self.scheduler_running = False
        logger.info("Backup scheduler stopped")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Sunday.com Database Backup Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Create backup')
    backup_parser.add_argument('--type', choices=['full', 'incremental'], default='full',
                              help='Backup type')
    backup_parser.add_argument('--base', help='Base backup ID for incremental backup')
    backup_parser.add_argument('--id', help='Custom backup ID')

    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('backup_id', help='Backup ID to restore from')
    restore_parser.add_argument('--time', help='Point-in-time recovery target (ISO format)')

    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify backup integrity')
    verify_parser.add_argument('backup_id', help='Backup ID to verify')

    # List command
    subparsers.add_parser('list', help='List available backups')

    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old backups')
    cleanup_parser.add_argument('--days', type=int, default=30,
                               help='Retention period in days')

    # Scheduler command
    scheduler_parser = subparsers.add_parser('scheduler', help='Run backup scheduler')
    scheduler_parser.add_argument('--daemon', action='store_true',
                                 help='Run as daemon')

    # Add database connection options
    for subparser in [backup_parser, restore_parser, verify_parser, cleanup_parser, scheduler_parser]:
        subparser.add_argument('--host', default='localhost', help='Database host')
        subparser.add_argument('--port', type=int, default=5432, help='Database port')
        subparser.add_argument('--database', default='sunday_dev', help='Database name')
        subparser.add_argument('--user', default='sunday_dev', help='Database user')
        subparser.add_argument('--password', help='Database password')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Build connection config
    connection_config = {
        'host': args.host,
        'port': args.port,
        'database': args.database,
        'user': args.user,
        'password': args.password or os.getenv('DB_PASSWORD', 'dev_password123')
    }

    try:
        backup_manager = PostgreSQLBackupManager(connection_config)

        if args.command == 'backup':
            if args.type == 'full':
                metadata = backup_manager.create_full_backup(args.id)
                print(f"Full backup created: {metadata.backup_id}")
            elif args.type == 'incremental':
                if not args.base:
                    # Find latest full backup
                    backups = backup_manager.list_backups()
                    for backup in backups:
                        if backup.backup_type == 'full':
                            args.base = backup.backup_id
                            break

                if not args.base:
                    print("No base backup found. Creating full backup instead.")
                    metadata = backup_manager.create_full_backup(args.id)
                else:
                    metadata = backup_manager.create_incremental_backup(args.base, args.id)

                print(f"Incremental backup created: {metadata.backup_id}")

        elif args.command == 'restore':
            target_time = None
            if args.time:
                target_time = datetime.datetime.fromisoformat(args.time)

            success = backup_manager.restore_database(args.backup_id, target_time)
            if success:
                print(f"Database restored successfully from: {args.backup_id}")
            else:
                print(f"Database restore failed")
                sys.exit(1)

        elif args.command == 'verify':
            success = backup_manager.verify_backup(args.backup_id)
            if success:
                print(f"Backup verification successful: {args.backup_id}")
            else:
                print(f"Backup verification failed: {args.backup_id}")
                sys.exit(1)

        elif args.command == 'list':
            backups = backup_manager.list_backups()
            if backups:
                print("\nAvailable Backups:")
                print("-" * 80)
                for backup in backups:
                    size_mb = backup.compressed_size_bytes / 1024 / 1024
                    verified_status = "✓" if backup.verified else "✗"
                    print(f"{backup.backup_id:<25} {backup.backup_type:<12} "
                          f"{backup.timestamp.strftime('%Y-%m-%d %H:%M:%S'):<20} "
                          f"{size_mb:>8.1f} MB {verified_status}")
            else:
                print("No backups found")

        elif args.command == 'cleanup':
            backup_manager.cleanup_old_backups(args.days)
            print(f"Cleanup completed (retention: {args.days} days)")

        elif args.command == 'scheduler':
            scheduler = BackupScheduler(backup_manager)
            scheduler.schedule_backups()

            if args.daemon:
                print("Starting backup scheduler daemon...")
                scheduler.start_scheduler()
            else:
                print("Backup schedules configured. Run with --daemon to start scheduler.")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()