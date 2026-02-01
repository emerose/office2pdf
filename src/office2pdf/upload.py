"""File upload module for Microsoft Graph."""

import asyncio
from uuid import uuid4

import httpx

from .types import Config


class Uploader:
    """Handles file uploads to OneDrive/SharePoint via Microsoft Graph."""

    def __init__(
        self,
        config: Config,
        http_client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
    ) -> None:
        """Initialize uploader.

        Args:
            config: Graph configuration
            http_client: Shared HTTP client
            semaphore: Concurrency limiter
        """
        self.config = config
        self.http = http_client
        self.semaphore = semaphore

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> tuple[str, str]:
        """Upload a file to OneDrive/SharePoint.

        Args:
            file_bytes: File content as bytes
            filename: Original filename
            content_type: MIME type (optional)

        Returns:
            Tuple of (drive_id, item_id)

        Raises:
            UploadError: If upload fails
        """
        # Create unique path for this file
        job_id = uuid4()
        upload_path = f"{self.config.drive_root}/{job_id}/{filename}"

        # Determine if we should use simple or resumable upload
        # Microsoft recommends resumable for files > 4MB
        if len(file_bytes) > 4 * 1024 * 1024:
            return await self._upload_large(upload_path, file_bytes, content_type)
        return await self._upload_simple(upload_path, file_bytes, content_type)

    async def _upload_simple(
        self,
        path: str,
        file_bytes: bytes,
        content_type: str | None,
    ) -> tuple[str, str]:
        """Simple upload for small files.

        Args:
            path: Upload path
            file_bytes: File content
            content_type: MIME type

        Returns:
            Tuple of (drive_id, item_id)
        """
        # Placeholder - to be implemented
        msg = "Simple upload not yet implemented"
        raise NotImplementedError(msg)

    async def _upload_large(
        self,
        path: str,
        file_bytes: bytes,
        content_type: str | None,
    ) -> tuple[str, str]:
        """Resumable upload for large files.

        Args:
            path: Upload path
            file_bytes: File content
            content_type: MIME type

        Returns:
            Tuple of (drive_id, item_id)
        """
        # Placeholder - to be implemented
        msg = "Resumable upload not yet implemented"
        raise NotImplementedError(msg)
