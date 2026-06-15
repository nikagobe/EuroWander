"""
Amazon S3 storage client.

All boto3 calls are synchronous, so they are wrapped in asyncio.to_thread()
to keep the FastAPI event loop non-blocking.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import boto3
from botocore.config import Config as BotoConfig

from app.modules.documents.domain.interfaces import StorageClient

logger = logging.getLogger(__name__)


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

        # On Lambda, AWS_SESSION_TOKEN is set — we must let boto3 use the
        # full credential chain (key + secret + token) automatically.
        # Only pass explicit credentials for local dev (no session token).
        import os
        is_lambda = bool(os.environ.get("AWS_SESSION_TOKEN"))

        kwargs: dict = {
            "region_name": region,
            "config": BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "virtual"},
            ),
        }
        if not is_lambda and access_key_id and secret_access_key:
            # Local dev: use explicit IAM user credentials from .env
            kwargs["aws_access_key_id"] = access_key_id
            kwargs["aws_secret_access_key"] = secret_access_key

        self._client = boto3.client("s3", **kwargs)
        logger.info(
            "[S3] client initialised bucket=%s region=%s lambda=%s explicit_creds=%s",
            bucket_name, region, is_lambda,
            bool(not is_lambda and access_key_id and secret_access_key),
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

