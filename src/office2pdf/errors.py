"""Custom exceptions for office2pdf."""


class OfficeToPdfError(Exception):
    """Base exception for all office2pdf errors."""


class AuthenticationError(OfficeToPdfError):
    """Authentication failed."""


class UploadError(OfficeToPdfError):
    """File upload failed."""


class ConversionError(OfficeToPdfError):
    """PDF conversion failed."""


class CleanupError(OfficeToPdfError):
    """Cleanup operation failed."""


class RateLimitError(OfficeToPdfError):
    """Request was throttled (429)."""


class AccessDeniedError(OfficeToPdfError):
    """Insufficient permissions."""


class UnsupportedFileError(OfficeToPdfError):
    """File type or operation not supported."""
