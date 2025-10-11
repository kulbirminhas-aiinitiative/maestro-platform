"""
Azure Blob Storage Connector for Maestro ML Platform

Features:
- Upload/download artifacts
- List blobs
- Container management
- SAS token generation
- Lifecycle management
- Access tiers
"""

import os
from azure.storage.blob import (
    BlobServiceClient,
    BlobClient,
    ContainerClient,
    ContentSettings,
    StandardBlobTier,
    generate_blob_sas,
    BlobSasPermissions
)
from azure.core.exceptions import AzureError, ResourceNotFoundError
from typing import Optional, List, Dict, Any, BinaryIO
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AzureBlobConnector:
    """
    Azure Blob Storage connector

    Usage:
        connector = AzureBlobConnector(
            container_name="maestro-ml-artifacts",
            connection_string="DefaultEndpointsProtocol=https;..."
        )

        # Upload file
        connector.upload_file("model.pkl", "models/model_v1.pkl")

        # Download file
        connector.download_file("models/model_v1.pkl", "local_model.pkl")

        # List blobs
        blobs = connector.list_blobs(prefix="models/")
    """

    def __init__(
        self,
        container_name: str,
        connection_string: Optional[str] = None,
        account_url: Optional[str] = None,
        credential: Optional[str] = None,
        create_container: bool = False
    ):
        """
        Initialize Azure Blob connector

        Args:
            container_name: Container name
            connection_string: Azure Storage connection string
            account_url: Storage account URL
            credential: Account key or SAS token
            create_container: Create container if it doesn't exist
        """
        self.container_name = container_name

        # Initialize blob service client
        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )
        elif account_url:
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
        else:
            # Try to get from environment
            conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if conn_str:
                self.blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            else:
                raise ValueError("No connection string or account URL provided")

        # Get or create container
        self.container_client = self.blob_service_client.get_container_client(container_name)

        if create_container:
            self._create_container_if_not_exists()

        logger.info(f"Azure Blob connector initialized: {container_name}")

    def _create_container_if_not_exists(self):
        """Create container if it doesn't exist"""
        try:
            if not self.container_client.exists():
                self.container_client.create_container()
                logger.info(f"Created container: {self.container_name}")
            else:
                logger.info(f"Container exists: {self.container_name}")
        except AzureError as e:
            logger.error(f"Failed to create container: {e}")
            raise

    def upload_file(
        self,
        local_path: str,
        blob_name: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
        tier: Optional[StandardBlobTier] = None
    ) -> bool:
        """
        Upload file to Azure Blob Storage

        Args:
            local_path: Local file path
            blob_name: Blob name
            metadata: Blob metadata
            content_type: Content type
            tier: Access tier (Hot, Cool, Archive)

        Returns:
            Success boolean
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)

            content_settings = None
            if content_type:
                content_settings = ContentSettings(content_type=content_type)

            with open(local_path, "rb") as data:
                blob_client.upload_blob(
                    data,
                    metadata=metadata,
                    content_settings=content_settings,
                    standard_blob_tier=tier,
                    overwrite=True
                )

            logger.info(f"Uploaded: {local_path} -> {self.container_name}/{blob_name}")
            return True

        except AzureError as e:
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
        Upload string content to blob

        Args:
            content: String content
            blob_name: Blob name
            metadata: Blob metadata
            content_type: Content type

        Returns:
            Success boolean
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)

            content_settings = ContentSettings(content_type=content_type)

            blob_client.upload_blob(
                content,
                metadata=metadata,
                content_settings=content_settings,
                overwrite=True
            )

            logger.info(f"Uploaded string -> {self.container_name}/{blob_name}")
            return True

        except AzureError as e:
            logger.error(f"Upload failed: {e}")
            return False

    def download_file(
        self,
        blob_name: str,
        local_path: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Download blob to file

        Args:
            blob_name: Blob name
            local_path: Local destination path
            version_id: Specific version to download

        Returns:
            Success boolean
        """
        try:
            # Create directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            blob_client = self.container_client.get_blob_client(
                blob_name,
                version_id=version_id
            )

            with open(local_path, "wb") as file:
                download_stream = blob_client.download_blob()
                file.write(download_stream.readall())

            logger.info(f"Downloaded: {self.container_name}/{blob_name} -> {local_path}")
            return True

        except AzureError as e:
            logger.error(f"Download failed: {e}")
            return False

    def download_as_string(
        self,
        blob_name: str,
        encoding: str = "utf-8",
        version_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Download blob as string

        Args:
            blob_name: Blob name
            encoding: Text encoding
            version_id: Specific version to download

        Returns:
            String content or None
        """
        try:
            blob_client = self.container_client.get_blob_client(
                blob_name,
                version_id=version_id
            )

            download_stream = blob_client.download_blob()
            content = download_stream.readall().decode(encoding)

            logger.info(f"Downloaded as string: {self.container_name}/{blob_name}")
            return content

        except AzureError as e:
            logger.error(f"Download failed: {e}")
            return None

    def list_blobs(
        self,
        prefix: str = "",
        max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        List blobs in container

        Args:
            prefix: Blob name prefix filter
            max_results: Maximum number of blobs to return

        Returns:
            List of blob metadata dictionaries
        """
        try:
            blob_list = []

            blobs = self.container_client.list_blobs(
                name_starts_with=prefix,
                results_per_page=max_results
            )

            for blob in blobs:
                blob_list.append({
                    "name": blob.name,
                    "size": blob.size,
                    "created": blob.creation_time,
                    "last_modified": blob.last_modified,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "metadata": blob.metadata,
                    "etag": blob.etag,
                    "tier": blob.blob_tier
                })

            logger.info(f"Listed {len(blob_list)} blobs with prefix: {prefix}")
            return blob_list

        except AzureError as e:
            logger.error(f"List failed: {e}")
            return []

    def delete_blob(
        self,
        blob_name: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Delete blob

        Args:
            blob_name: Blob name
            version_id: Specific version to delete

        Returns:
            Success boolean
        """
        try:
            blob_client = self.container_client.get_blob_client(
                blob_name,
                version_id=version_id
            )

            blob_client.delete_blob()

            logger.info(f"Deleted: {self.container_name}/{blob_name}")
            return True

        except AzureError as e:
            logger.error(f"Delete failed: {e}")
            return False

    def blob_exists(self, blob_name: str) -> bool:
        """
        Check if blob exists

        Args:
            blob_name: Blob name

        Returns:
            Exists boolean
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            return blob_client.exists()
        except AzureError:
            return False

    def get_blob_properties(self, blob_name: str) -> Optional[Dict[str, Any]]:
        """
        Get blob properties

        Args:
            blob_name: Blob name

        Returns:
            Properties dictionary or None
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            properties = blob_client.get_blob_properties()

            return {
                "name": blob_name,
                "size": properties.size,
                "created": properties.creation_time,
                "last_modified": properties.last_modified,
                "content_type": properties.content_settings.content_type,
                "metadata": properties.metadata,
                "etag": properties.etag,
                "version_id": properties.version_id,
                "tier": properties.blob_tier,
                "lease_state": properties.lease.state
            }

        except AzureError as e:
            logger.error(f"Get properties failed: {e}")
            return None

    def generate_sas_url(
        self,
        blob_name: str,
        expiration_hours: int = 1,
        permissions: str = "r"
    ) -> Optional[str]:
        """
        Generate SAS URL for temporary access

        Args:
            blob_name: Blob name
            expiration_hours: URL expiration in hours
            permissions: Permissions (r=read, w=write, d=delete, etc.)

        Returns:
            SAS URL or None
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)

            # Parse permissions
            sas_permissions = BlobSasPermissions(
                read="r" in permissions,
                write="w" in permissions,
                delete="d" in permissions,
                add="a" in permissions,
                create="c" in permissions
            )

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=blob_client.credential.account_key,
                permission=sas_permissions,
                expiry=datetime.utcnow() + timedelta(hours=expiration_hours)
            )

            # Generate full URL
            sas_url = f"{blob_client.url}?{sas_token}"

            logger.info(f"Generated SAS URL for: {blob_name}")
            return sas_url

        except Exception as e:
            logger.error(f"Generate SAS URL failed: {e}")
            return None

    def copy_blob(
        self,
        source_blob_name: str,
        destination_blob_name: str,
        source_container_name: Optional[str] = None
    ) -> bool:
        """
        Copy blob within or between containers

        Args:
            source_blob_name: Source blob name
            destination_blob_name: Destination blob name
            source_container_name: Source container (defaults to same container)

        Returns:
            Success boolean
        """
        try:
            source_container = source_container_name or self.container_name
            source_blob_client = self.blob_service_client.get_blob_client(
                source_container,
                source_blob_name
            )

            destination_blob_client = self.container_client.get_blob_client(
                destination_blob_name
            )

            # Start copy operation
            destination_blob_client.start_copy_from_url(source_blob_client.url)

            logger.info(f"Copied: {source_blob_name} -> {destination_blob_name}")
            return True

        except AzureError as e:
            logger.error(f"Copy failed: {e}")
            return False

    def set_blob_tier(
        self,
        blob_name: str,
        tier: StandardBlobTier
    ) -> bool:
        """
        Set blob access tier

        Args:
            blob_name: Blob name
            tier: Access tier (Hot, Cool, Archive)

        Returns:
            Success boolean
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.set_standard_blob_tier(tier)

            logger.info(f"Set tier for {blob_name}: {tier}")
            return True

        except AzureError as e:
            logger.error(f"Set tier failed: {e}")
            return False

    def set_metadata(
        self,
        blob_name: str,
        metadata: Dict[str, str]
    ) -> bool:
        """
        Set blob metadata

        Args:
            blob_name: Blob name
            metadata: Metadata dictionary

        Returns:
            Success boolean
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.set_blob_metadata(metadata)

            logger.info(f"Set metadata for: {blob_name}")
            return True

        except AzureError as e:
            logger.error(f"Set metadata failed: {e}")
            return False

    def enable_versioning(self) -> bool:
        """
        Enable versioning on storage account

        Note: This requires account-level permissions

        Returns:
            Success boolean
        """
        try:
            # Get blob service properties
            properties = self.blob_service_client.get_service_properties()

            # Enable versioning
            properties['versioning'] = {'enabled': True}

            # Set properties
            self.blob_service_client.set_service_properties(**properties)

            logger.info("Enabled versioning on storage account")
            return True

        except AzureError as e:
            logger.error(f"Enable versioning failed: {e}")
            return False
