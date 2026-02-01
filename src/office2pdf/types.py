"""Type definitions and configuration models."""

from typing import Any

from pydantic import BaseModel, Field


class Config(BaseModel):
    """Configuration for Microsoft Graph Office to PDF conversion.

    Required:
        tenant_id: Azure tenant ID
        client_id: Azure application (client) ID
        client_secret: Azure application client secret

    Optional:
        authority: OAuth authority URL
        scope: OAuth scope
        graph_base_url: Microsoft Graph API base URL
        drive_id: OneDrive/SharePoint drive ID
        site_id: SharePoint site ID
        drive_root: Root path for temporary files
        cleanup: Whether to delete temporary files after conversion
        request_timeout_s: HTTP request timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_backoff_base_s: Base backoff time for retries
        concurrency_limit: Maximum concurrent operations
    """

    # Required
    tenant_id: str
    client_id: str
    client_secret: str

    # Optional with defaults
    authority: str = Field(default="")
    scope: str = "https://graph.microsoft.com/.default"
    graph_base_url: str = "https://graph.microsoft.com/v1.0"
    drive_id: str | None = None
    site_id: str | None = None
    drive_root: str = "/Apps/office2pdf"
    cleanup: bool = True
    request_timeout_s: float = 120.0
    max_retries: int = 5
    retry_backoff_base_s: float = 0.5
    concurrency_limit: int = 8

    def model_post_init(self, __context: Any) -> None:
        """Set default authority if not provided."""
        if not self.authority:
            self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"


# Common Office file MIME types
OFFICE_MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
}
