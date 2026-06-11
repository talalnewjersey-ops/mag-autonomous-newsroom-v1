"""
NEXUS-14: Storage Service
Handles file storage for agent outputs.
Supports local filesystem and AWS S3.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class StorageService:
    """
    Storage service for NEXUS-14.
    
    Supports:
    - Local filesystem storage (default)
    - AWS S3 storage (when configured)
    """

    def __init__(self, config: Dict):
        self.config = config
        self.base_output_dir = config.get("output_dir", "output")
        self.s3_bucket = os.environ.get("S3_BUCKET", "")
        self.aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID", "")
        self.aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY", "")
        self.use_s3 = bool(self.s3_bucket and self.aws_access_key)
        
        # Ensure output directory exists
        Path(self.base_output_dir).mkdir(parents=True, exist_ok=True)

    async def save(self, path: str, data: Any, run_id: str = None) -> str:
        """Save data to storage. Returns the path where data was saved."""
        if run_id:
            full_path = os.path.join(self.base_output_dir, run_id, path)
        else:
            full_path = os.path.join(self.base_output_dir, path)
        
        # Ensure directory exists
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Serialize data
        if isinstance(data, (dict, list)):
            content = json.dumps(data, indent=2, ensure_ascii=False)
            mode = "w"
        elif isinstance(data, str):
            content = data
            mode = "w"
        elif isinstance(data, bytes):
            content = data
            mode = "wb"
        else:
            content = json.dumps(data, indent=2, default=str)
            mode = "w"
        
        # Write locally
        with open(full_path, mode, encoding="utf-8" if mode == "w" else None) as f:
            f.write(content)
        
        logger.info(f"Saved to {full_path}")
        
        # Optionally upload to S3
        if self.use_s3:
            try:
                await self._upload_to_s3(full_path, path)
            except Exception as e:
                logger.warning(f"S3 upload failed (continuing with local): {e}")
        
        return full_path

    async def load(self, path: str, run_id: str = None) -> Any:
        """Load data from storage."""
        if run_id:
            full_path = os.path.join(self.base_output_dir, run_id, path)
        else:
            full_path = os.path.join(self.base_output_dir, path)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(f"Storage file not found: {full_path}")
        
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return content

    async def exists(self, path: str, run_id: str = None) -> bool:
        """Check if a file exists in storage."""
        if run_id:
            full_path = os.path.join(self.base_output_dir, run_id, path)
        else:
            full_path = os.path.join(self.base_output_dir, path)
        return os.path.exists(full_path)

    async def list_files(self, prefix: str = "", run_id: str = None) -> list:
        """List files in storage."""
        if run_id:
            base = os.path.join(self.base_output_dir, run_id, prefix)
        else:
            base = os.path.join(self.base_output_dir, prefix)
        
        if not os.path.exists(base):
            return []
        
        files = []
        for root, dirs, filenames in os.walk(base):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, self.base_output_dir)
                files.append(rel_path)
        return files

    async def _upload_to_s3(self, local_path: str, s3_key: str) -> None:
        """Upload a file to S3."""
        try:
            import boto3
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            s3_client.upload_file(local_path, self.s3_bucket, s3_key)
            logger.info(f"Uploaded {local_path} to s3://{self.s3_bucket}/{s3_key}")
        except ImportError:
            logger.warning("boto3 not available, skipping S3 upload")
        except Exception as e:
            raise e

    def get_run_dir(self, run_id: str) -> str:
        """Get the directory for a specific run."""
        run_dir = os.path.join(self.base_output_dir, run_id)
        Path(run_dir).mkdir(parents=True, exist_ok=True)
        return run_dir
