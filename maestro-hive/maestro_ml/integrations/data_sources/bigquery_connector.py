"""
Google BigQuery Data Source Connector for Maestro ML Platform
"""

from google.cloud import bigquery
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPIError
from typing import Optional, List, Dict, Any
import logging
import pandas as pd
import os

logger = logging.getLogger(__name__)


class BigQueryConnector:
    """
    Google BigQuery connector

    Usage:
        connector = BigQueryConnector(
            project_id="my-project",
            credentials_path="/path/to/service-account.json"
        )

        # Execute query
        results = connector.execute_query("SELECT * FROM `project.dataset.table`")

        # Load to DataFrame
        df = connector.query_to_dataframe("SELECT * FROM `project.dataset.table`")

        # Write DataFrame to table
        connector.dataframe_to_table(df, "dataset.table")
    """

    def __init__(
        self,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        location: str = "US"
    ):
        """
        Initialize BigQuery connector

        Args:
            project_id: Google Cloud project ID
            credentials_path: Path to service account JSON
            location: Default location for queries and datasets
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.location = location

        # Initialize credentials
        credentials = None
        if credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            credentials = service_account.Credentials.from_service_account_file(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )

        # Initialize client
        try:
            self.client = bigquery.Client(
                project=self.project_id,
                credentials=credentials,
                location=location
            )

            logger.info(f"BigQuery connector initialized: {self.project_id}")

        except Exception as e:
            logger.error(f"Failed to initialize BigQuery client: {e}")
            raise

    def execute_query(
        self,
        query: str,
        parameters: Optional[List[bigquery.ScalarQueryParameter]] = None,
        use_legacy_sql: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Execute query and return results

        Args:
            query: SQL query
            parameters: Query parameters
            use_legacy_sql: Use legacy SQL syntax

        Returns:
            List of result dictionaries
        """
        try:
            job_config = bigquery.QueryJobConfig(
                use_legacy_sql=use_legacy_sql
            )

            if parameters:
                job_config.query_parameters = parameters

            query_job = self.client.query(query, job_config=job_config)
            results = list(query_job.result())

            # Convert to dictionaries
            results_dict = [dict(row) for row in results]

            logger.debug(f"Query returned {len(results_dict)} rows")
            return results_dict

        except GoogleAPIError as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def query_to_dataframe(
        self,
        query: str,
        parameters: Optional[List[bigquery.ScalarQueryParameter]] = None,
        use_legacy_sql: bool = False
    ) -> pd.DataFrame:
        """
        Execute query and return DataFrame

        Args:
            query: SQL query
            parameters: Query parameters
            use_legacy_sql: Use legacy SQL syntax

        Returns:
            pandas DataFrame
        """
        try:
            job_config = bigquery.QueryJobConfig(
                use_legacy_sql=use_legacy_sql
            )

            if parameters:
                job_config.query_parameters = parameters

            df = self.client.query(query, job_config=job_config).to_dataframe()

            logger.info(f"Loaded {len(df)} rows to DataFrame")
            return df

        except Exception as e:
            logger.error(f"Query to DataFrame failed: {e}")
            raise

    def dataframe_to_table(
        self,
        df: pd.DataFrame,
        table_id: str,
        write_disposition: str = "WRITE_APPEND",
        create_disposition: str = "CREATE_IF_NEEDED",
        schema: Optional[List[bigquery.SchemaField]] = None
    ):
        """
        Write DataFrame to BigQuery table

        Args:
            df: pandas DataFrame
            table_id: Table ID (format: dataset.table or project.dataset.table)
            write_disposition: WRITE_TRUNCATE, WRITE_APPEND, or WRITE_EMPTY
            create_disposition: CREATE_IF_NEEDED or CREATE_NEVER
            schema: Table schema (auto-detected if not provided)
        """
        try:
            # Ensure table_id has project
            if table_id.count('.') == 1:
                table_id = f"{self.project_id}.{table_id}"

            job_config = bigquery.LoadJobConfig(
                write_disposition=write_disposition,
                create_disposition=create_disposition
            )

            if schema:
                job_config.schema = schema

            job = self.client.load_table_from_dataframe(
                df,
                table_id,
                job_config=job_config
            )

            job.result()  # Wait for completion

            logger.info(f"Wrote {len(df)} rows to {table_id}")

        except Exception as e:
            logger.error(f"DataFrame to table failed: {e}")
            raise

    def create_dataset(
        self,
        dataset_id: str,
        location: Optional[str] = None,
        description: Optional[str] = None
    ):
        """
        Create dataset

        Args:
            dataset_id: Dataset ID
            location: Dataset location
            description: Dataset description
        """
        try:
            dataset = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
            dataset.location = location or self.location

            if description:
                dataset.description = description

            dataset = self.client.create_dataset(dataset, exists_ok=True)

            logger.info(f"Created dataset: {dataset_id}")

        except GoogleAPIError as e:
            logger.error(f"Create dataset failed: {e}")
            raise

    def delete_dataset(
        self,
        dataset_id: str,
        delete_contents: bool = False
    ):
        """
        Delete dataset

        Args:
            dataset_id: Dataset ID
            delete_contents: Delete all tables in dataset
        """
        try:
            self.client.delete_dataset(
                f"{self.project_id}.{dataset_id}",
                delete_contents=delete_contents,
                not_found_ok=True
            )

            logger.info(f"Deleted dataset: {dataset_id}")

        except GoogleAPIError as e:
            logger.error(f"Delete dataset failed: {e}")
            raise

    def list_datasets(self) -> List[str]:
        """List datasets in project"""
        try:
            datasets = list(self.client.list_datasets())
            dataset_ids = [dataset.dataset_id for dataset in datasets]

            logger.debug(f"Found {len(dataset_ids)} datasets")
            return dataset_ids

        except GoogleAPIError as e:
            logger.error(f"List datasets failed: {e}")
            raise

    def list_tables(self, dataset_id: str) -> List[str]:
        """List tables in dataset"""
        try:
            tables = list(self.client.list_tables(dataset_id))
            table_ids = [table.table_id for table in tables]

            logger.debug(f"Found {len(table_ids)} tables in {dataset_id}")
            return table_ids

        except GoogleAPIError as e:
            logger.error(f"List tables failed: {e}")
            raise

    def table_exists(self, table_id: str) -> bool:
        """
        Check if table exists

        Args:
            table_id: Table ID (format: dataset.table or project.dataset.table)

        Returns:
            Exists boolean
        """
        try:
            # Ensure table_id has project
            if table_id.count('.') == 1:
                table_id = f"{self.project_id}.{table_id}"

            self.client.get_table(table_id)
            return True

        except Exception:
            return False

    def get_table_schema(self, table_id: str) -> List[Dict[str, str]]:
        """
        Get table schema

        Args:
            table_id: Table ID

        Returns:
            List of column definitions
        """
        try:
            # Ensure table_id has project
            if table_id.count('.') == 1:
                table_id = f"{self.project_id}.{table_id}"

            table = self.client.get_table(table_id)

            schema = [
                {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description or ""
                }
                for field in table.schema
            ]

            return schema

        except GoogleAPIError as e:
            logger.error(f"Get table schema failed: {e}")
            raise

    def get_table_info(self, table_id: str) -> Dict[str, Any]:
        """
        Get table metadata

        Args:
            table_id: Table ID

        Returns:
            Table metadata
        """
        try:
            # Ensure table_id has project
            if table_id.count('.') == 1:
                table_id = f"{self.project_id}.{table_id}"

            table = self.client.get_table(table_id)

            return {
                "table_id": table.table_id,
                "dataset_id": table.dataset_id,
                "project": table.project,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "created": table.created,
                "modified": table.modified,
                "schema": self.get_table_schema(table_id)
            }

        except GoogleAPIError as e:
            logger.error(f"Get table info failed: {e}")
            raise

    def delete_table(self, table_id: str):
        """
        Delete table

        Args:
            table_id: Table ID
        """
        try:
            # Ensure table_id has project
            if table_id.count('.') == 1:
                table_id = f"{self.project_id}.{table_id}"

            self.client.delete_table(table_id, not_found_ok=True)

            logger.info(f"Deleted table: {table_id}")

        except GoogleAPIError as e:
            logger.error(f"Delete table failed: {e}")
            raise

    def run_query_job(
        self,
        query: str,
        destination_table: Optional[str] = None,
        write_disposition: str = "WRITE_TRUNCATE"
    ) -> str:
        """
        Run query job (async)

        Args:
            query: SQL query
            destination_table: Destination table for results
            write_disposition: Write disposition

        Returns:
            Job ID
        """
        try:
            job_config = bigquery.QueryJobConfig()

            if destination_table:
                if destination_table.count('.') == 1:
                    destination_table = f"{self.project_id}.{destination_table}"

                job_config.destination = destination_table
                job_config.write_disposition = write_disposition

            query_job = self.client.query(query, job_config=job_config)

            logger.info(f"Started query job: {query_job.job_id}")
            return query_job.job_id

        except GoogleAPIError as e:
            logger.error(f"Run query job failed: {e}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get job status

        Args:
            job_id: Job ID

        Returns:
            Job status information
        """
        try:
            job = self.client.get_job(job_id)

            return {
                "job_id": job.job_id,
                "state": job.state,
                "created": job.created,
                "started": job.started,
                "ended": job.ended,
                "errors": job.errors
            }

        except GoogleAPIError as e:
            logger.error(f"Get job status failed: {e}")
            raise
