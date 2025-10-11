"""
Google Cloud Storage (GCS) Connector for Maestro ML Platform

Features:
- Upload/download artifacts
- List objects
- Versioning support
- Signed URLs
- Lifecycle management
- IAM integration
"""

import os
from google.cloud import storage
from google.oauth2 import service_account
from google.api_core.exceptions import GoogleAPIError, NotFound
from typing import Optional, List, Dict, Any, BinaryIO
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class GCSConnector:
    """
    Google Cloud Storage connector

    Usage:
        connector = GCSConnector(
            bucket_name="maestro-ml-artifacts",
            project_id="my-project",
            credentials_path="/path/to/service-account.json"
        )

        # Upload file
        connector.upload_file("model.pkl", "models/model_v1.pkl")

        # Download file
        connector.download_file("models/model_v1.pkl", "local_model.pkl")

        # List objects
        objects = connector.list_blobs(prefix="models/")
    """

    def __init__(
        self,
        bucket_name: str,
        project_id: Optional[str] = None,
        credentials_path: Optional[str] = None,
        create_bucket: bool = False,
        location: str = "US"
    ):
        """
        Initialize GCS connector

        Args:
            bucket_name: GCS bucket name
            project_id: Google Cloud project ID
            credentials_path: Path to service account JSON file
            create_bucket: Create bucket if it doesn't exist
            location: Bucket location (US, EU, ASIA, etc.)
        """
        self.bucket_name = bucket_name
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

        # Initialize storage client
        self.client = storage.Client(
            project=self.project_id,
            credentials=credentials
        )

        # Get or create bucket
        try:
            self.bucket = self.client.bucket(bucket_name)
            if not self.bucket.exists():
                if create_bucket:
                    self._create_bucket()
                else:
                    raise ValueError(f"Bucket does not exist: {bucket_name}")
        except Exception as e:
            if create_bucket:
                self._create_bucket()
            else:
                raise

        logger.info(f"GCS connector initialized: {bucket_name}")

    def _create_bucket(self):
        """Create bucket if it doesn't exist"""
        try:
            self.bucket = self.client.create_bucket(
                self.bucket_name,
                location=self.location
            )
            logger.info(f"Created bucket: {self.bucket_name}")
        except GoogleAPIError as e:
            logger.error(f"Failed to create bucket: {e}")
            raise

    def upload_file(
        self,
        local_path: str,
        blob_name: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> bool:
        """
        Upload file to GCS

        Args:
            local_path: Local file path
            blob_name: GCS blob name
            metadata: Blob metadata
            content_type: Content type

        Returns:
            Success boolean
        """
        try:
            blob = self.bucket.blob(blob_name)

            # Set metadata
            if metadata:
                blob.metadata = metadata

            # Upload file
            blob.upload_from_filename(
                local_path,
                content_type=content_type
            )

            logger.info(f"Uploaded: {local_path} -> gs://{self.bucket_name}/{blob_name}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Upload failed: {e}")
            return False

    def upload_from_string(
        self,
        content: str,
        blob_name: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: str = "text/plain"
    ) -> bool:
        """
        Upload string content to GCS

        Args:
            content: String content
            blob_name: GCS blob name
            metadata: Blob metadata
            content_type: Content type

        Returns:
            Success boolean
        """
        try:
            blob = self.bucket.blob(blob_name)

            if metadata:
                blob.metadata = metadata

            blob.upload_from_string(
                content,
                content_type=content_type
            )

            logger.info(f"Uploaded string -> gs://{self.bucket_name}/{blob_name}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Upload failed: {e}")
            return False

    def download_file(
        self,
        blob_name: str,
        local_path: str,
        generation: Optional[int] = None
    ) -> bool:
        """
        Download file from GCS

        Args:
            blob_name: GCS blob name
            local_path: Local destination path
            generation: Specific generation to download

        Returns:
            Success boolean
        """
        try:
            # Create directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            blob = self.bucket.blob(blob_name, generation=generation)
            blob.download_to_filename(local_path)

            logger.info(f"Downloaded: gs://{self.bucket_name}/{blob_name} -> {local_path}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Download failed: {e}")
            return False

    def download_as_string(
        self,
        blob_name: str,
        generation: Optional[int] = None
    ) -> Optional[str]:
        """
        Download blob as string

        Args:
            blob_name: GCS blob name
            generation: Specific generation to download

        Returns:
            String content or None
        """
        try:
            blob = self.bucket.blob(blob_name, generation=generation)
            content = blob.download_as_text()

            logger.info(f"Downloaded as string: gs://{self.bucket_name}/{blob_name}")
            return content

        except GoogleAPIError as e:
            logger.error(f"Download failed: {e}")
            return None

    def list_blobs(
        self,
        prefix: str = "",
        max_results: Optional[int] = None,
        delimiter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List blobs in bucket

        Args:
            prefix: Blob name prefix filter
            max_results: Maximum number of blobs to return
            delimiter: Delimiter for grouping

        Returns:
            List of blob metadata dictionaries
        """
        try:
            blobs = self.client.list_blobs(
                self.bucket_name,
                prefix=prefix,
                max_results=max_results,
                delimiter=delimiter
            )

            blob_list = []
            for blob in blobs:
                blob_list.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.time_created,
                    "updated": blob.updated,
                    "content_type": blob.content_type,
                    "generation": blob.generation,
                    "metadata": blob.metadata
                })

            logger.info(f"Listed {len(blob_list)} blobs with prefix: {prefix}")
            return blob_list

        except GoogleAPIError as e:
            logger.error(f"List failed: {e}")
            return []

    def delete_blob(
        self,
        blob_name: str,
        generation: Optional[int] = None
    ) -> bool:
        """
        Delete blob from GCS

        Args:
            blob_name: GCS blob name
            generation: Specific generation to delete

        Returns:
            Success boolean
        """
        try:
            blob = self.bucket.blob(blob_name, generation=generation)
            blob.delete()

            logger.info(f"Deleted: gs://{self.bucket_name}/{blob_name}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Delete failed: {e}")
            return False

    def blob_exists(self, blob_name: str) -> bool:
        """
        Check if blob exists

        Args:
            blob_name: GCS blob name

        Returns:
            Exists boolean
        """
        try:
            blob = self.bucket.blob(blob_name)
            return blob.exists()
        except GoogleAPIError:
            return False

    def get_blob_metadata(self, blob_name: str) -> Optional[Dict[str, Any]]:
        """
        Get blob metadata

        Args:
            blob_name: GCS blob name

        Returns:
            Metadata dictionary or None
        """
        try:
            blob = self.bucket.blob(blob_name)

            if not blob.exists():
                return None

            blob.reload()

            return {
                "name": blob.name,
                "size": blob.size,
                "created": blob.time_created,
                "updated": blob.updated,
                "content_type": blob.content_type,
                "generation": blob.generation,
                "metadata": blob.metadata,
                "md5_hash": blob.md5_hash,
                "crc32c": blob.crc32c
            }

        except GoogleAPIError as e:
            logger.error(f"Get metadata failed: {e}")
            return None

    def generate_signed_url(
        self,
        blob_name: str,
        expiration: int = 3600,
        method: str = "GET"
    ) -> Optional[str]:
        """
        Generate signed URL for temporary access

        Args:
            blob_name: GCS blob name
            expiration: URL expiration in seconds
            method: HTTP method (GET, PUT, DELETE)

        Returns:
            Signed URL or None
        """
        try:
            blob = self.bucket.blob(blob_name)

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method=method
            )

            logger.info(f"Generated signed URL for: {blob_name}")
            return url

        except GoogleAPIError as e:
            logger.error(f"Generate signed URL failed: {e}")
            return None

    def copy_blob(
        self,
        source_blob_name: str,
        destination_blob_name: str,
        source_bucket_name: Optional[str] = None
    ) -> bool:
        """
        Copy blob within or between buckets

        Args:
            source_blob_name: Source blob name
            destination_blob_name: Destination blob name
            source_bucket_name: Source bucket (defaults to same bucket)

        Returns:
            Success boolean
        """
        try:
            source_bucket = (
                self.client.bucket(source_bucket_name)
                if source_bucket_name
                else self.bucket
            )

            source_blob = source_bucket.blob(source_blob_name)
            destination_blob = self.bucket.blob(destination_blob_name)

            # Copy blob
            self.bucket.copy_blob(source_blob, self.bucket, destination_blob_name)

            logger.info(f"Copied: {source_blob_name} -> {destination_blob_name}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Copy failed: {e}")
            return False

    def enable_versioning(self) -> bool:
        """
        Enable versioning on bucket

        Returns:
            Success boolean
        """
        try:
            self.bucket.versioning_enabled = True
            self.bucket.patch()

            logger.info(f"Enabled versioning on: {self.bucket_name}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Enable versioning failed: {e}")
            return False

    def set_lifecycle_policy(
        self,
        transition_days: int = 90,
        deletion_days: int = 365
    ) -> bool:
        """
        Set lifecycle policy for automatic archival and deletion

        Args:
            transition_days: Days until transition to cheaper storage
            deletion_days: Days until deletion

        Returns:
            Success boolean
        """
        try:
            rules = [
                storage.bucket.LifecycleRuleDelete(age=deletion_days),
                storage.bucket.LifecycleRuleSetStorageClass(
                    storage_class="NEARLINE",
                    age=transition_days
                )
            ]

            self.bucket.lifecycle_rules = rules
            self.bucket.patch()

            logger.info(f"Set lifecycle policy on: {self.bucket_name}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Set lifecycle policy failed: {e}")
            return False

    def make_public(self, blob_name: str) -> bool:
        """
        Make blob publicly accessible

        Args:
            blob_name: GCS blob name

        Returns:
            Success boolean
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.make_public()

            logger.info(f"Made public: {blob_name}")
            logger.info(f"Public URL: {blob.public_url}")
            return True

        except GoogleAPIError as e:
            logger.error(f"Make public failed: {e}")
            return False

    def get_public_url(self, blob_name: str) -> str:
        """
        Get public URL for blob (blob must be public)

        Args:
            blob_name: GCS blob name

        Returns:
            Public URL
        """
        blob = self.bucket.blob(blob_name)
        return blob.public_url
