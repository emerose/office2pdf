"""Unit tests for upload module with mocked Graph API responses."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

import office2pdf
from office2pdf.auth import Authenticator
from office2pdf.errors import UploadError
from office2pdf.upload import Uploader


@pytest.fixture
def config() -> office2pdf.Config:
    """Create test configuration."""
    return office2pdf.Config(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


@pytest.fixture
def config_with_drive() -> office2pdf.Config:
    """Create configuration with drive_id."""
    return office2pdf.Config(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        drive_id="test-drive-id-123",
    )


@pytest.fixture
def config_with_site() -> office2pdf.Config:
    """Create configuration with site_id."""
    return office2pdf.Config(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
        site_id="contoso.sharepoint.com,site-guid,web-guid",
    )


@pytest.fixture
async def http_client() -> httpx.AsyncClient:
    """Create mock HTTP client."""
    return MagicMock(spec=httpx.AsyncClient)


@pytest.fixture
async def authenticator() -> Authenticator:
    """Create mock authenticator."""
    auth = MagicMock(spec=Authenticator)
    auth.get_access_token = AsyncMock(return_value="test-token")
    return auth


@pytest.fixture
def semaphore() -> asyncio.Semaphore:
    """Create semaphore."""
    return asyncio.Semaphore(5)


@pytest.mark.asyncio
async def test_resolve_drive_with_explicit_drive_id(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test drive resolution when drive_id is explicitly provided."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "test-drive-id-123",
        "driveType": "business",
        "owner": {"user": {"displayName": "Test User"}},
    }
    http_client.get = AsyncMock(return_value=mock_response)

    drive_id = await uploader._resolve_drive_id()

    assert drive_id == "test-drive-id-123"
    http_client.get.assert_called_once_with(
        "https://graph.microsoft.com/v1.0/drives/test-drive-id-123",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest.mark.asyncio
async def test_resolve_drive_with_site_id(
    config_with_site: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test drive resolution when site_id is provided."""
    uploader = Uploader(config_with_site, http_client, semaphore, authenticator)

    # Mock successful site drive retrieval
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": "resolved-drive-id-456",
        "driveType": "documentLibrary",
    }
    http_client.get = AsyncMock(return_value=mock_response)

    drive_id = await uploader._resolve_drive_id()

    assert drive_id == "resolved-drive-id-456"
    http_client.get.assert_called_once_with(
        "https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com,site-guid,web-guid/drive",
        headers={"Authorization": "Bearer test-token"},
    )


@pytest.mark.asyncio
async def test_resolve_drive_caching(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test that drive ID is cached after first resolution."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "test-drive-id-123"}
    http_client.get = AsyncMock(return_value=mock_response)

    # First call - should hit API
    drive_id1 = await uploader._resolve_drive_id()
    assert drive_id1 == "test-drive-id-123"
    assert http_client.get.call_count == 1

    # Second call - should use cached value
    drive_id2 = await uploader._resolve_drive_id()
    assert drive_id2 == "test-drive-id-123"
    assert http_client.get.call_count == 1  # No additional call


@pytest.mark.asyncio
async def test_resolve_drive_no_config(
    config: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error when neither drive_id nor site_id provided."""
    uploader = Uploader(config, http_client, semaphore, authenticator)

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    error_msg = str(exc_info.value)
    assert "Cannot determine drive ID" in error_msg
    assert "drive_id" in error_msg
    assert "site_id" in error_msg


@pytest.mark.asyncio
async def test_verify_drive_not_found(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when drive not found."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = '{"error": {"code": "itemNotFound"}}'
    http_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    assert "Drive not found" in str(exc_info.value)
    assert "test-drive-id-123" in str(exc_info.value)


@pytest.mark.asyncio
async def test_verify_drive_access_denied(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when access denied to drive."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock 403 response
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = '{"error": {"code": "accessDenied"}}'
    http_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    assert "Access denied" in str(exc_info.value)
    assert "permissions" in str(exc_info.value)


@pytest.mark.asyncio
async def test_verify_drive_other_http_error(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling for other HTTP errors."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock 400 response with error details
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = '{"error": {"message": "Invalid drive ID format"}}'
    mock_response.json.return_value = {
        "error": {"code": "badRequest", "message": "Invalid drive ID format"}
    }
    http_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "400 Bad Request",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    assert "Failed to verify drive" in str(exc_info.value)
    assert "Invalid drive ID format" in str(exc_info.value)


@pytest.mark.asyncio
async def test_verify_drive_network_error(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling for network errors."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock network error
    http_client.get = AsyncMock(
        side_effect=httpx.RequestError("Connection timeout")
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    assert "Network error" in str(exc_info.value)
    assert "Connection timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_site_drive_not_found(
    config_with_site: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when site not found."""
    uploader = Uploader(config_with_site, http_client, semaphore, authenticator)

    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = '{"error": {"code": "itemNotFound"}}'
    http_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    assert "Site not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_site_drive_access_denied(
    config_with_site: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when access denied to site."""
    uploader = Uploader(config_with_site, http_client, semaphore, authenticator)

    # Mock 403 response
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = '{"error": {"code": "accessDenied"}}'
    http_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    assert "Access denied to site" in str(exc_info.value)
    assert "permissions" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_file_resolves_drive_id(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test that upload_file calls drive resolution."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "test-drive-id-123"}
    http_client.get = AsyncMock(return_value=mock_response)

    # Try to upload a file (will fail with NotImplementedError, but that's OK)
    with pytest.raises(NotImplementedError):
        await uploader.upload_file(b"test content", "test.txt")

    # Verify drive resolution was called
    http_client.get.assert_called_once()
    assert uploader._resolved_drive_id == "test-drive-id-123"
