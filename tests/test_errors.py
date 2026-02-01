"""Tests for office2pdf.errors module."""

from office2pdf import (
    AccessDeniedError,
    AuthenticationError,
    CleanupError,
    ConversionError,
    OfficeToPdfError,
    RateLimitError,
    UnsupportedFileError,
    UploadError,
)


def test_error_inheritance() -> None:
    """Test all custom errors inherit from OfficeToPdfError."""
    assert issubclass(AuthenticationError, OfficeToPdfError)
    assert issubclass(UploadError, OfficeToPdfError)
    assert issubclass(ConversionError, OfficeToPdfError)
    assert issubclass(CleanupError, OfficeToPdfError)
    assert issubclass(RateLimitError, OfficeToPdfError)
    assert issubclass(AccessDeniedError, OfficeToPdfError)
    assert issubclass(UnsupportedFileError, OfficeToPdfError)


def test_graph_error_base() -> None:
    """Test OfficeToPdfError is a base exception."""
    assert issubclass(OfficeToPdfError, Exception)


def test_error_instantiation() -> None:
    """Test errors can be instantiated with messages."""
    error = AuthenticationError("Authentication failed")
    assert str(error) == "Authentication failed"
    assert isinstance(error, OfficeToPdfError)
    assert isinstance(error, Exception)


def test_all_errors_can_be_raised() -> None:
    """Test all error types can be raised and caught."""
    errors = [
        AuthenticationError("auth error"),
        UploadError("upload error"),
        ConversionError("conversion error"),
        CleanupError("cleanup error"),
        RateLimitError("throttle error"),
        AccessDeniedError("permission error"),
        UnsupportedFileError("not supported error"),
    ]

    for error in errors:
        try:
            raise error
        except OfficeToPdfError as e:
            assert str(e) == str(error)
        else:
            msg = f"Failed to catch {type(error).__name__}"
            raise AssertionError(msg)
