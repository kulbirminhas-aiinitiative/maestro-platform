"""
AWS S3 Storage Connector for Maestro ML Platform

Features:
- Upload/download artifacts
- List objects
- Versioning support
- Multipart uploads
- Presigned URLs
- Lifecycle management
"""

import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional, List, Dict, Any, BinaryIO
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class S3Connector:
    """
    AWS S3 storage connector

    Usage:
        connector = S3Connector(
            bucket_name="maestro-ml-artifacts",
            region="us-east-1"
        )

        # Upload file
        connector.upload_file("model.pkl", "models/model_v1.pkl")

        # Download file
        connector.download_file("models/model_v1.pkl", "local_model.pkl")

        # List objects
        objects = connector.list_objects(prefix="models/")
    """

    def __init__(
        self,
        bucket_name: str,
        region: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        create_bucket: bool = False
    ):
        """
        Initialize S3 connector

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            aws_access_key_id: AWS access key (or use environment variable)
            aws_secret_access_key: AWS secret key (or use environment variable)
            endpoint_url: Custom endpoint URL (for S3-compatible services)
            create_bucket: Create bucket if it doesn't exist
        """
        self.bucket_name = bucket_name
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        # Initialize S3 client
        session_kwargs = {}
        if aws_access_key_id:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
        if aws_secret_access_key:
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        if region:
            session_kwargs["region_name"] = region

        self.s3_client = boto3.client("s3", **session_kwargs, endpoint_url=endpoint_url)
        self.s3_resource = boto3.resource("s3", **session_kwargs, endpoint_url=endpoint_url)

        # Create bucket if requested
        if create_bucket:
            self._create_bucket_if_not_exists()

        logger.info(f"S3 connector initialized: {bucket_name} ({self.region})")

    def _create_bucket_if_not_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"Bucket exists: {self.bucket_name}")
        except ClientError:
            # Bucket doesn't exist, create it
            try:
                if self.region == "us-east-1":
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.s3_client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": self.region}
                    )
                logger.info(f"Created bucket: {self.bucket_name}")
            except ClientError as e:
                logger.error(f"Failed to create bucket: {e}")
                raise

    def upload_file(
        self,
        local_path: str,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None,
        storage_class: str = "STANDARD",
        acl: str = "private"
    ) -> bool:
        """
        Upload file to S3

        Args:
            local_path: Local file path
            s3_key: S3 object key
            metadata: Object metadata
            storage_class: Storage class (STANDARD, INTELLIGENT_TIERING, etc.)
            acl: Access control list

        Returns:
            Success boolean
        """
        try:
            extra_args = {
                "StorageClass": storage_class,
                "ACL": acl
            }

            if metadata:
                extra_args["Metadata"] = metadata

            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(f"Uploaded: {local_path} -> s3://{self.bucket_name}/{s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Upload failed: {e}")
            return False

    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload file-like object to S3

        Args:
            file_obj: File-like object
            s3_key: S3 object key
            metadata: Object metadata

        Returns:
            Success boolean
        """
        try:
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(f"Uploaded file object -> s3://{self.bucket_name}/{s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Upload failed: {e}")
            return False

    def download_file(
        self,
        s3_key: str,
        local_path: str,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Download file from S3

        Args:
            s3_key: S3 object key
            local_path: Local destination path
            version_id: Specific version to download

        Returns:
            Success boolean
        """
        try:
            # Create directory if needed
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            extra_args = {}
            if version_id:
                extra_args["VersionId"] = version_id

            self.s3_client.download_file(
                self.bucket_name,
                s3_key,
                local_path,
                ExtraArgs=extra_args
            )

            logger.info(f"Downloaded: s3://{self.bucket_name}/{s3_key} -> {local_path}")
            return True

        except ClientError as e:
            logger.error(f"Download failed: {e}")
            return False

    def download_fileobj(
        self,
        s3_key: str,
        file_obj: BinaryIO,
        version_id: Optional[str] = None
    ) -> bool:
        """
        Download file to file-like object

        Args:
            s3_key: S3 object key
            file_obj: File-like object to write to
            version_id: Specific version to download

        Returns:
            Success boolean
        """
        try:
            extra_args = {}
            if version_id:
                extra_args["VersionId"] = version_id

            self.s3_client.download_fileobj(
                self.bucket_name,
                s3_key,
                file_obj,
                ExtraArgs=extra_args
            )

            logger.info(f"Downloaded: s3://{self.bucket_name}/{s3_key} to file object")
            return True

        except ClientError as e:
            logger.error(f"Download failed: {e}")
            return False

    def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000,
        delimiter: str = ""
    ) -> List[Dict[str, Any]]:
        """
        List objects in bucket

        Args:
            prefix: Object key prefix filter
            max_keys: Maximum number of objects to return
            delimiter: Delimiter for grouping

        Returns:
            List of object metadata dictionaries
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys,
                Delimiter=delimiter
            )

            objects = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    objects.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                        "etag": obj["ETag"]
                    })

            logger.info(f"Listed {len(objects)} objects with prefix: {prefix}")
            return objects

        except ClientError as e:
            logger.error(f"List failed: {e}")
            return []

    def delete_object(self, s3_key: str, version_id: Optional[str] = None) -> bool:
        """
        Delete object from S3

        Args:
            s3_key: S3 object key
            version_id: Specific version to delete

        Returns:
            Success boolean
        """
        try:
            delete_kwargs = {
                "Bucket": self.bucket_name,
                "Key": s3_key
            }

            if version_id:
                delete_kwargs["VersionId"] = version_id

            self.s3_client.delete_object(**delete_kwargs)

            logger.info(f"Deleted: s3://{self.bucket_name}/{s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Delete failed: {e}")
            return False

    def object_exists(self, s3_key: str) -> bool:
        """
        Check if object exists

        Args:
            s3_key: S3 object key

        Returns:
            Exists boolean
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False

    def get_object_metadata(self, s3_key: str) -> Optional[Dict[str, Any]]:
        """
        Get object metadata

        Args:
            s3_key: S3 object key

        Returns:
            Metadata dictionary or None
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return {
                "size": response["ContentLength"],
                "last_modified": response["LastModified"],
                "content_type": response.get("ContentType"),
                "metadata": response.get("Metadata", {}),
                "etag": response["ETag"],
                "version_id": response.get("VersionId")
            }

        except ClientError as e:
            logger.error(f"Get metadata failed: {e}")
            return None

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        method: str = "get_object"
    ) -> Optional[str]:
        """
        Generate presigned URL for temporary access

        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds
            method: S3 method (get_object, put_object)

        Returns:
            Presigned URL or None
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key
                },
                ExpiresIn=expiration
            )

            logger.info(f"Generated presigned URL for: {s3_key}")
            return url

        except ClientError as e:
            logger.error(f"Generate presigned URL failed: {e}")
            return None

    def copy_object(
        self,
        source_key: str,
        destination_key: str,
        source_bucket: Optional[str] = None
    ) -> bool:
        """
        Copy object within or between buckets

        Args:
            source_key: Source object key
            destination_key: Destination object key
            source_bucket: Source bucket (defaults to same bucket)

        Returns:
            Success boolean
        """
        try:
            source_bucket = source_bucket or self.bucket_name
            copy_source = {
                "Bucket": source_bucket,
                "Key": source_key
            }

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=destination_key
            )

            logger.info(f"Copied: {source_key} -> {destination_key}")
            return True

        except ClientError as e:
            logger.error(f"Copy failed: {e}")
            return False

    def enable_versioning(self) -> bool:
        """
        Enable versioning on bucket

        Returns:
            Success boolean
        """
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={"Status": "Enabled"}
            )

            logger.info(f"Enabled versioning on: {self.bucket_name}")
            return True

        except ClientError as e:
            logger.error(f"Enable versioning failed: {e}")
            return False

    def set_lifecycle_policy(
        self,
        transition_days: int = 90,
        expiration_days: int = 365
    ) -> bool:
        """
        Set lifecycle policy for automatic archival and deletion

        Args:
            transition_days: Days until transition to cheaper storage
            expiration_days: Days until deletion

        Returns:
            Success boolean
        """
        try:
            lifecycle_policy = {
                "Rules": [
                    {
                        "Id": "maestro-ml-lifecycle",
                        "Status": "Enabled",
                        "Filter": {"Prefix": ""},
                        "Transitions": [
                            {
                                "Days": transition_days,
                                "StorageClass": "INTELLIGENT_TIERING"
                            }
                        ],
                        "Expiration": {
                            "Days": expiration_days
                        }
                    }
                ]
            }

            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_policy
            )

            logger.info(f"Set lifecycle policy on: {self.bucket_name}")
            return True

        except ClientError as e:
            logger.error(f"Set lifecycle policy failed: {e}")
            return False
