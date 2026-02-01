"""office2pdf - Convert Office files to PDF using Microsoft Graph."""

from .client import OfficeToPdf
from .errors import (
    AccessDeniedError,
    AuthenticationError,
    CleanupError,
    ConversionError,
    OfficeToPdfError,
    RateLimitError,
    UnsupportedFileError,
    UploadError,
)
from .types import Config  # noqa: F401  # pyright: ignore[reportUnusedImport]

__version__ = "0.1.0"

__all__ = [
    "AccessDeniedError",
    "AuthenticationError",
    "CleanupError",
    "ConversionError",
    "OfficeToPdf",
    "OfficeToPdfError",
    "RateLimitError",
    "UnsupportedFileError",
    "UploadError",
]
