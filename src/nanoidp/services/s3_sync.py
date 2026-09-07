"""
S3 Configuration Synchronization Service for NanoIDP.
Synchronizes YAML configurations and certificates between local filesystem and an S3 bucket.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class S3ConfigSync:
    """Handles bidirectional configuration sync with Amazon S3."""

    def __init__(self, config_dir: Path, bucket_name: Optional[str] = None, prefix: Optional[str] = None):
        self.config_dir = config_dir
        self.bucket_name = bucket_name or os.getenv("NANOIDP_S3_CONFIG_BUCKET", os.getenv("S3_CONFIG_BUCKET"))
        self.prefix = prefix if prefix is not None else os.getenv("NANOIDP_S3_CONFIG_PREFIX", os.getenv("S3_CONFIG_PREFIX", ""))
        self._s3_client = None

        if self.bucket_name:
            logger.info(f"S3 config sync enabled: bucket={self.bucket_name}, prefix='{self.prefix}'")
        else:
            logger.info("S3 config sync disabled (no bucket specified). Using local filesystem only.")

    @property
    def is_enabled(self) -> bool:
        return bool(self.bucket_name)

    @property
    def client(self) -> Any:
        if self._s3_client is None and self.is_enabled:
            import boto3  # type: ignore[import-untyped]
            self._s3_client = boto3.client("s3")
        return self._s3_client

    def _get_s3_key(self, filename: str) -> str:
        if self.prefix:
            clean_prefix = self.prefix.strip("/")
            return f"{clean_prefix}/{filename}"
        return filename

    def pull_all(self) -> bool:
        """Download all configuration files from S3 to local config_dir."""
        if not self.is_enabled:
            return False

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            files_to_sync = ["settings.yaml", "users.yaml", "saml.crt", "saml.key", "idp.crt", "idp.key"]
            downloaded = 0

            # List existing objects in prefix
            response = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=self.prefix)
            remote_keys = {item["Key"] for item in response.get("Contents", [])}

            for filename in files_to_sync:
                s3_key = self._get_s3_key(filename)
                local_path = self.config_dir / filename

                if s3_key in remote_keys:
                    logger.info(f"Downloading s3://{self.bucket_name}/{s3_key} -> {local_path}")
                    self.client.download_file(self.bucket_name, s3_key, str(local_path))
                    downloaded += 1
                elif local_path.exists():
                    # If file exists locally but not in S3, seed S3 with the local copy
                    logger.info(f"Seeding remote S3 bucket with local file: {local_path} -> s3://{self.bucket_name}/{s3_key}")
                    self.client.upload_file(str(local_path), self.bucket_name, s3_key)

            logger.info(f"S3 config pull completed: {downloaded} files downloaded")
            return True
        except Exception as e:
            logger.error(f"Failed to pull configuration from S3: {e}", exc_info=True)
            return False

    def push_file(self, filename: str) -> bool:
        """Upload a specific configuration file to S3."""
        if not self.is_enabled:
            return False

        local_path = self.config_dir / filename
        if not local_path.exists():
            logger.warning(f"Cannot upload non-existent local file to S3: {local_path}")
            return False

        try:
            s3_key = self._get_s3_key(filename)
            logger.info(f"Uploading {local_path} -> s3://{self.bucket_name}/{s3_key}")
            self.client.upload_file(str(local_path), self.bucket_name, s3_key)
            return True
        except Exception as e:
            logger.error(f"Failed to push {filename} to S3: {e}", exc_info=True)
            return False

    def push_all(self) -> bool:
        """Upload all local configuration files to S3."""
        if not self.is_enabled:
            return False

        files_to_sync = ["settings.yaml", "users.yaml", "saml.crt", "saml.key", "idp.crt", "idp.key"]
        success = True
        for filename in files_to_sync:
            local_path = self.config_dir / filename
            if local_path.exists():
                if not self.push_file(filename):
                    success = False
        return success
