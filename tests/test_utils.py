"""Tests for office2pdf.utils module."""

from office2pdf.utils import get_content_type


def test_get_content_type_docx() -> None:
    """Test content type detection for DOCX files."""
    content_type = get_content_type("document.docx")
    assert content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_get_content_type_doc() -> None:
    """Test content type detection for DOC files."""
    content_type = get_content_type("document.doc")
    assert content_type == "application/msword"


def test_get_content_type_pptx() -> None:
    """Test content type detection for PPTX files."""
    content_type = get_content_type("presentation.pptx")
    expected = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    assert content_type == expected


def test_get_content_type_ppt() -> None:
    """Test content type detection for PPT files."""
    content_type = get_content_type("presentation.ppt")
    assert content_type == "application/vnd.ms-powerpoint"


def test_get_content_type_xlsx() -> None:
    """Test content type detection for XLSX files."""
    content_type = get_content_type("spreadsheet.xlsx")
    assert content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_get_content_type_xls() -> None:
    """Test content type detection for XLS files."""
    content_type = get_content_type("spreadsheet.xls")
    assert content_type == "application/vnd.ms-excel"


def test_get_content_type_case_insensitive() -> None:
    """Test content type detection is case insensitive."""
    content_type = get_content_type("document.DOCX")
    assert content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_get_content_type_with_path() -> None:
    """Test content type detection works with full paths."""
    content_type = get_content_type("/path/to/document.docx")
    assert content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_get_content_type_unknown() -> None:
    """Test unknown file types return None."""
    content_type = get_content_type("unknown.unknownextension12345")
    assert content_type is None
