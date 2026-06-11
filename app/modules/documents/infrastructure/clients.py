"""
Amazon S3 storage client.

All boto3 calls are synchronous, so they are wrapped in asyncio.to_thread()
to keep the FastAPI event loop non-blocking.
"""

import asyncio
from datetime import datetime, timedelta

import boto3
from botocore.config import Config as BotoConfig

from app.modules.documents.domain.interfaces import StorageClient


class S3StorageClient(StorageClient):
    """Presigned-URL generator and file-deletion client for Amazon S3."""

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region: str = "eu-central-1",
        url_expiration_seconds: int = 3600,
    ) -> None:
        self._bucket = bucket_name
        self._expiration = url_expiration_seconds
        self._client = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
            ),
        )

    async def generate_upload_url(
        self, file_key: str, content_type: str, size_bytes: int
    ) -> tuple[str, datetime]:
        """Generate a presigned PUT URL for direct frontend upload."""
        url = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": file_key,
                "ContentType": content_type,
            },
            ExpiresIn=self._expiration,
        )
        expires_at = datetime.utcnow() + timedelta(seconds=self._expiration)
        return url, expires_at

    async def generate_download_url(self, file_key: str) -> tuple[str, datetime]:
        """Generate a presigned GET URL for direct frontend download."""
        url = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": file_key,
            },
            ExpiresIn=self._expiration,
        )
        expires_at = datetime.utcnow() + timedelta(seconds=self._expiration)
        return url, expires_at

    async def delete_file(self, file_key: str) -> None:
        """Remove an object from the S3 bucket."""
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self._bucket,
            Key=file_key,
        )

