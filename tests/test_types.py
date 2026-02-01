"""Tests for office2pdf.types module."""

import pytest

import office2pdf


def test_config_creation() -> None:
    """Test Config can be created with required fields."""
    config = office2pdf.Config(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
    )

    assert config.tenant_id == "test-tenant"
    assert config.client_id == "test-client"
    assert config.client_secret == "test-secret"


def test_config_defaults() -> None:
    """Test office2pdf.Config has correct default values."""
    config = office2pdf.Config(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
    )

    assert config.scope == "https://graph.microsoft.com/.default"
    assert config.graph_base_url == "https://graph.microsoft.com/v1.0"
    assert config.drive_root == "/Apps/office2pdf"
    assert config.cleanup is True
    assert config.request_timeout_s == 120.0
    assert config.max_retries == 5
    assert config.retry_backoff_base_s == 0.5
    assert config.concurrency_limit == 8


def test_config_authority_auto_generated() -> None:
    """Test authority is auto-generated from tenant_id."""
    config = office2pdf.Config(
        tenant_id="my-tenant-id",
        client_id="test-client",
        client_secret="test-secret",
    )

    assert config.authority == "https://login.microsoftonline.com/my-tenant-id"


def test_config_custom_authority() -> None:
    """Test custom authority is preserved."""
    custom_authority = "https://login.microsoftonline.us/custom-tenant"
    config = office2pdf.Config(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
        authority=custom_authority,
    )

    assert config.authority == custom_authority


def test_config_optional_fields() -> None:
    """Test optional fields can be set."""
    config = office2pdf.Config(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
        drive_id="custom-drive",
        site_id="custom-site",
        drive_root="/Custom/Path",
        cleanup=False,
        request_timeout_s=60.0,
        max_retries=3,
        retry_backoff_base_s=1.0,
        concurrency_limit=4,
    )

    assert config.drive_id == "custom-drive"
    assert config.site_id == "custom-site"
    assert config.drive_root == "/Custom/Path"
    assert config.cleanup is False
    assert config.request_timeout_s == 60.0
    assert config.max_retries == 3
    assert config.retry_backoff_base_s == 1.0
    assert config.concurrency_limit == 4


def test_config_validation() -> None:
    """Test office2pdf.Config validates required fields."""
    with pytest.raises(Exception):  # Pydantic will raise ValidationError
        office2pdf.Config()  # type: ignore[call-arg]
