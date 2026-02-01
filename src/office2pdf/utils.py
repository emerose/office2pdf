"""Utility functions."""

import mimetypes
from pathlib import Path

from .types import OFFICE_MIME_TYPES


def get_content_type(filename: str) -> str | None:
    """Determine content type from filename.

    Args:
        filename: The filename to check

    Returns:
        Content type string or None if unknown
    """
    ext = Path(filename).suffix.lower()

    # Check our known Office types first
    if ext in OFFICE_MIME_TYPES:
        return OFFICE_MIME_TYPES[ext]

    # Fall back to standard mimetypes
    content_type, _ = mimetypes.guess_type(filename)
    return content_type
