"""Tests for office2pdf.client module."""

import pytest

import office2pdf


def test_client_creation() -> None:
    """Test OfficeToPdf can be instantiated."""
    config = office2pdf.Config(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
    )

    client = office2pdf.OfficeToPdf(config)
    assert client.config == config


@pytest.mark.asyncio
async def test_client_not_initialized_error() -> None:
    """Test client raises error when used without context manager."""
    config = office2pdf.Config(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
    )

    client = office2pdf.OfficeToPdf(config)

    with pytest.raises(RuntimeError, match="Client not initialized"):
        await client.convert_bytes(b"test", "test.docx")


@pytest.mark.asyncio
async def test_client_context_manager() -> None:
    """Test client can be used as async context manager."""
    config = office2pdf.Config(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
    )

    async with office2pdf.OfficeToPdf(config) as client:
        assert client._http_client is not None
        assert client._semaphore is not None
        assert client._authenticator is not None
        assert client._uploader is not None
        assert client._converter is not None
        assert client._cleaner is not None

    # After exit, client should be closed
    assert client._http_client is None
