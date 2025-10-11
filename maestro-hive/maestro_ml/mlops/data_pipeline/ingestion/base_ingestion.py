"""
Base Data Ingestion Framework
Provides common functionality for ingesting data from various sources
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
import logging
from dataclasses import dataclass
from enum import Enum


class DataSourceType(Enum):
    """Supported data source types"""
    DATABASE = "database"
    API = "api"
    S3 = "s3"
    STREAM = "stream"
    FILE = "file"


class IngestionStatus(Enum):
    """Ingestion job status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class IngestionMetrics:
    """Metrics for an ingestion job"""
    records_read: int = 0
    records_written: int = 0
    records_failed: int = 0
    bytes_processed: int = 0
    duration_seconds: float = 0.0
    error_rate: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "records_read": self.records_read,
            "records_written": self.records_written,
            "records_failed": self.records_failed,
            "bytes_processed": self.bytes_processed,
            "duration_seconds": self.duration_seconds,
            "error_rate": self.error_rate
        }


@dataclass
class IngestionConfig:
    """Configuration for data ingestion"""
    source_type: DataSourceType
    source_config: Dict[str, Any]
    target_path: str
    batch_size: int = 1000
    max_retries: int = 3
    timeout_seconds: int = 300
    validation_enabled: bool = True
    deduplication_enabled: bool = True
    schema_enforcement: bool = True


class BaseDataIngestion(ABC):
    """Base class for all data ingestion implementations"""

    def __init__(self, config: IngestionConfig, logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.metrics = IngestionMetrics()
        self.status = IngestionStatus.PENDING

    @abstractmethod
    def extract(self) -> pd.DataFrame:
        """Extract data from source"""
        pass

    @abstractmethod
    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate extracted data"""
        pass

    @abstractmethod
    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform data to required format"""
        pass

    @abstractmethod
    def load(self, data: pd.DataFrame) -> bool:
        """Load data to target destination"""
        pass

    def deduplicate(self, data: pd.DataFrame, keys: List[str]) -> pd.DataFrame:
        """Remove duplicate records based on keys"""
        if not self.config.deduplication_enabled:
            return data

        initial_count = len(data)
        data = data.drop_duplicates(subset=keys, keep='last')
        removed_count = initial_count - len(data)

        if removed_count > 0:
            self.logger.info(f"Removed {removed_count} duplicate records")

        return data

    def run(self) -> IngestionMetrics:
        """Execute the complete ingestion pipeline"""
        start_time = datetime.now()
        self.status = IngestionStatus.RUNNING

        try:
            # Extract
            self.logger.info(f"Extracting data from {self.config.source_type.value}")
            data = self.extract()
            self.metrics.records_read = len(data)

            # Validate
            if self.config.validation_enabled:
                self.logger.info("Validating data")
                data = self.validate(data)

            # Transform
            self.logger.info("Transforming data")
            data = self.transform(data)

            # Load
            self.logger.info(f"Loading data to {self.config.target_path}")
            success = self.load(data)

            if success:
                self.metrics.records_written = len(data)
                self.status = IngestionStatus.SUCCESS
            else:
                self.status = IngestionStatus.FAILED

        except Exception as e:
            self.logger.error(f"Ingestion failed: {e}", exc_info=True)
            self.status = IngestionStatus.FAILED
            self.metrics.records_failed = self.metrics.records_read - self.metrics.records_written

        finally:
            # Calculate metrics
            end_time = datetime.now()
            self.metrics.duration_seconds = (end_time - start_time).total_seconds()

            if self.metrics.records_read > 0:
                self.metrics.error_rate = self.metrics.records_failed / self.metrics.records_read

            self._log_metrics()

        return self.metrics

    def _log_metrics(self):
        """Log ingestion metrics"""
        self.logger.info(f"Ingestion Status: {self.status.value}")
        self.logger.info(f"Records Read: {self.metrics.records_read}")
        self.logger.info(f"Records Written: {self.metrics.records_written}")
        self.logger.info(f"Records Failed: {self.metrics.records_failed}")
        self.logger.info(f"Duration: {self.metrics.duration_seconds:.2f}s")
        self.logger.info(f"Error Rate: {self.metrics.error_rate:.2%}")


class DatabaseIngestion(BaseDataIngestion):
    """Ingest data from databases"""

    def extract(self) -> pd.DataFrame:
        """Extract data from database"""
        import sqlalchemy

        engine = sqlalchemy.create_engine(self.config.source_config['connection_string'])
        query = self.config.source_config.get('query', f"SELECT * FROM {self.config.source_config['table']}")

        self.logger.info(f"Executing query: {query[:100]}...")
        data = pd.read_sql(query, engine)

        return data

    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate database data"""
        # Check for required columns
        required_columns = self.config.source_config.get('required_columns', [])
        missing_columns = set(required_columns) - set(data.columns)

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Remove rows with null values in critical columns
        critical_columns = self.config.source_config.get('critical_columns', [])
        if critical_columns:
            initial_count = len(data)
            data = data.dropna(subset=critical_columns)
            removed_count = initial_count - len(data)
            if removed_count > 0:
                self.logger.warning(f"Removed {removed_count} rows with null values in critical columns")

        return data

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform database data"""
        # Apply column mappings if specified
        column_mapping = self.config.source_config.get('column_mapping', {})
        if column_mapping:
            data = data.rename(columns=column_mapping)

        # Add ingestion metadata
        data['ingestion_timestamp'] = datetime.now()
        data['source'] = self.config.source_type.value

        return data

    def load(self, data: pd.DataFrame) -> bool:
        """Load data to target"""
        try:
            # Save to parquet
            data.to_parquet(self.config.target_path, index=False)
            self.logger.info(f"Saved {len(data)} records to {self.config.target_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")
            return False


class S3Ingestion(BaseDataIngestion):
    """Ingest data from S3"""

    def extract(self) -> pd.DataFrame:
        """Extract data from S3"""
        import boto3
        from io import BytesIO

        s3_client = boto3.client(
            's3',
            endpoint_url=self.config.source_config.get('endpoint_url'),
            aws_access_key_id=self.config.source_config.get('access_key'),
            aws_secret_access_key=self.config.source_config.get('secret_key')
        )

        bucket = self.config.source_config['bucket']
        key = self.config.source_config['key']

        self.logger.info(f"Downloading s3://{bucket}/{key}")

        obj = s3_client.get_object(Bucket=bucket, Key=key)

        # Determine file format
        if key.endswith('.parquet'):
            data = pd.read_parquet(BytesIO(obj['Body'].read()))
        elif key.endswith('.csv'):
            data = pd.read_csv(BytesIO(obj['Body'].read()))
        elif key.endswith('.json'):
            data = pd.read_json(BytesIO(obj['Body'].read()))
        else:
            raise ValueError(f"Unsupported file format: {key}")

        self.metrics.bytes_processed = obj['ContentLength']
        return data

    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate S3 data"""
        # Basic validation
        if data.empty:
            raise ValueError("Empty dataset")

        return data

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform S3 data"""
        data['ingestion_timestamp'] = datetime.now()
        data['source'] = 's3'
        data['source_bucket'] = self.config.source_config['bucket']
        data['source_key'] = self.config.source_config['key']

        return data

    def load(self, data: pd.DataFrame) -> bool:
        """Load data to target"""
        try:
            data.to_parquet(self.config.target_path, index=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")
            return False


class APIIngestion(BaseDataIngestion):
    """Ingest data from REST APIs"""

    def extract(self) -> pd.DataFrame:
        """Extract data from API"""
        import requests

        url = self.config.source_config['url']
        headers = self.config.source_config.get('headers', {})
        params = self.config.source_config.get('params', {})

        self.logger.info(f"Fetching data from {url}")

        response = requests.get(url, headers=headers, params=params, timeout=self.config.timeout_seconds)
        response.raise_for_status()

        # Parse response
        data_key = self.config.source_config.get('data_key', 'data')
        json_data = response.json()

        if data_key:
            records = json_data.get(data_key, json_data)
        else:
            records = json_data

        data = pd.DataFrame(records)
        return data

    def validate(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate API data"""
        if data.empty:
            raise ValueError("API returned no data")

        return data

    def transform(self, data: pd.DataFrame) -> pd.DataFrame:
        """Transform API data"""
        data['ingestion_timestamp'] = datetime.now()
        data['source'] = 'api'
        data['source_url'] = self.config.source_config['url']

        return data

    def load(self, data: pd.DataFrame) -> bool:
        """Load data to target"""
        try:
            data.to_parquet(self.config.target_path, index=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save data: {e}")
            return False
