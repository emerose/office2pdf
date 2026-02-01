"""File upload module for Microsoft Graph."""

import asyncio
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import httpx

from .auth import Authenticator
from .errors import UploadError
from .types import Config

# HTTP status code constants
HTTP_NOT_FOUND = 404
HTTP_FORBIDDEN = 403
HTTP_PAYLOAD_TOO_LARGE = 413
HTTP_INSUFFICIENT_STORAGE = 507


class Uploader:
    """Handles file uploads to OneDrive/SharePoint via Microsoft Graph."""

    def __init__(
        self,
        config: Config,
        http_client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        authenticator: Authenticator,
    ) -> None:
        """Initialize uploader.

        Args:
            config: Graph configuration
            http_client: Shared HTTP client
            semaphore: Concurrency limiter
            authenticator: Authenticator for Graph API access
        """
        self.config = config
        self.http = http_client
        self.semaphore = semaphore
        self.authenticator = authenticator
        self._resolved_drive_id: str | None = None

    async def _resolve_drive_id(self) -> str:
        """Resolve the drive ID to use for uploads.

        Resolution strategy:
        1. If drive_id is explicitly provided in config, use it directly
        2. If site_id is provided, resolve to the site's default drive
        3. Otherwise, raise error (can't determine drive without user context)

        Returns:
            Drive ID to use for uploads

        Raises:
            UploadError: If drive cannot be resolved
        """
        # Return cached drive ID if already resolved
        if self._resolved_drive_id:
            return self._resolved_drive_id

        # If drive_id is explicitly provided, verify it exists
        if self.config.drive_id:
            drive_id = await self._verify_drive(self.config.drive_id)
            self._resolved_drive_id = drive_id
            return drive_id

        # If site_id is provided, get the site's default drive
        if self.config.site_id:
            drive_id = await self._get_site_drive(self.config.site_id)
            self._resolved_drive_id = drive_id
            return drive_id

        # No drive or site ID provided - cannot determine drive
        msg = (
            "Cannot determine drive ID. "
            "Please provide either 'drive_id' or 'site_id' in the configuration. "
            "For application permissions (client credentials flow), "
            "a specific drive or site must be specified."
        )
        raise UploadError(msg)

    async def _verify_drive(self, drive_id: str) -> str:
        """Verify a drive exists and is accessible.

        Args:
            drive_id: Drive ID to verify

        Returns:
            Verified drive ID

        Raises:
            UploadError: If drive not found or not accessible
        """
        token = await self.authenticator.get_access_token()
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = await self.http.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return str(data["id"])

        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTP_NOT_FOUND:
                msg = f"Drive not found: {drive_id}"
                raise UploadError(msg) from e
            if e.response.status_code == HTTP_FORBIDDEN:
                msg = f"Access denied to drive: {drive_id}. Check app permissions."
                raise UploadError(msg) from e

            # Other HTTP errors
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except (ValueError, KeyError, TypeError):
                # JSON decode error or unexpected response structure
                error_msg = str(e)
            msg = f"Failed to verify drive {drive_id}: {error_msg}"
            raise UploadError(msg) from e

        except httpx.RequestError as e:
            msg = f"Network error while verifying drive {drive_id}: {e}"
            raise UploadError(msg) from e

    async def _get_site_drive(self, site_id: str) -> str:
        """Get the default drive for a SharePoint site.

        Args:
            site_id: SharePoint site ID

        Returns:
            Drive ID for the site's default document library

        Raises:
            UploadError: If site not found or no drive available
        """
        token = await self.authenticator.get_access_token()
        url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
        headers = {"Authorization": f"Bearer {token}"}

        try:
            response = await self.http.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return str(data["id"])

        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTP_NOT_FOUND:
                msg = f"Site not found or has no default drive: {site_id}"
                raise UploadError(msg) from e
            if e.response.status_code == HTTP_FORBIDDEN:
                msg = f"Access denied to site: {site_id}. Check app permissions."
                raise UploadError(msg) from e

            # Other HTTP errors
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except (ValueError, KeyError, TypeError):
                # JSON decode error or unexpected response structure
                error_msg = str(e)
            msg = f"Failed to get drive for site {site_id}: {error_msg}"
            raise UploadError(msg) from e

        except httpx.RequestError as e:
            msg = f"Network error while getting site drive {site_id}: {e}"
            raise UploadError(msg) from e

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
        # Resolve drive ID (cached after first resolution)
        drive_id = await self._resolve_drive_id()

        # Sanitize filename to prevent path traversal attacks
        # Extract just the filename component, stripping any directory path
        safe_filename = Path(filename).name
        if not safe_filename or safe_filename in (".", ".."):
            msg = "Invalid filename: cannot be empty or consist only of path separators"
            raise UploadError(msg)

        # Create unique path for this file
        job_id = uuid4()
        upload_path = f"{self.config.drive_root}/{job_id}/{safe_filename}"

        # Determine if we should use simple or resumable upload
        # Microsoft recommends resumable for files > 4MB
        if len(file_bytes) > 4 * 1024 * 1024:
            return await self._upload_large(drive_id, upload_path, file_bytes, content_type)
        return await self._upload_simple(drive_id, upload_path, file_bytes, content_type)

    async def _upload_simple(
        self,
        drive_id: str,
        path: str,
        file_bytes: bytes,
        content_type: str | None,
    ) -> tuple[str, str]:
        """Simple upload for small files.

        Uses the simple PUT endpoint for files < 4MB.
        Graph API endpoint: PUT /drives/{drive-id}/root:/{path}:/content

        Args:
            drive_id: Target drive ID
            path: Upload path (relative to drive root)
            file_bytes: File content
            content_type: MIME type (defaults to application/octet-stream)

        Returns:
            Tuple of (drive_id, item_id)

        Raises:
            UploadError: If upload fails
        """
        token = await self.authenticator.get_access_token()
        # URL-encode the path to handle special characters like #, ?, %
        # Use safe="/" to preserve intended slashes in the path
        encoded_path = quote(path, safe="/")
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root:/{encoded_path}:/content"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type or "application/octet-stream",
        }

        try:
            async with self.semaphore:
                response = await self.http.put(url, headers=headers, content=file_bytes)
                response.raise_for_status()
                data = response.json()

                # Extract drive_id and item_id from response
                item_id = str(data["id"])
                response_drive_id = str(data["parentReference"]["driveId"])

                return (response_drive_id, item_id)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == HTTP_PAYLOAD_TOO_LARGE:
                msg = f"File too large for simple upload: {len(file_bytes)} bytes (max 4MB)"
                raise UploadError(msg) from e
            if e.response.status_code == HTTP_FORBIDDEN:
                msg = f"Access denied when uploading to path: {path}. Check app permissions."
                raise UploadError(msg) from e
            if e.response.status_code == HTTP_INSUFFICIENT_STORAGE:
                msg = "Insufficient storage quota available"
                raise UploadError(msg) from e

            # Other HTTP errors
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except (ValueError, KeyError, TypeError):
                # JSON decode error or unexpected response structure
                error_msg = str(e)
            msg = f"Upload failed for {path}: {error_msg}"
            raise UploadError(msg) from e

        except httpx.RequestError as e:
            msg = f"Network error during upload to {path}: {e}"
            raise UploadError(msg) from e

    async def _upload_large(
        self,
        drive_id: str,
        path: str,
        file_bytes: bytes,
        content_type: str | None,
    ) -> tuple[str, str]:
        """Resumable upload for large files.

        Args:
            drive_id: Target drive ID
            path: Upload path
            file_bytes: File content
            content_type: MIME type

        Returns:
            Tuple of (drive_id, item_id)
        """
        # Placeholder - to be implemented in Phase 2.2
        msg = "Resumable upload not yet implemented"
        raise NotImplementedError(msg)
