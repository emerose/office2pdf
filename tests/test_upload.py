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
    """Test that upload_file calls drive resolution and performs upload."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "test-drive-id-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock successful upload
    mock_put_response = MagicMock()
    mock_put_response.status_code = 201
    mock_put_response.json.return_value = {
        "id": "test-item-id-456",
        "name": "test.txt",
        "parentReference": {"driveId": "test-drive-id-123"},
    }
    http_client.put = AsyncMock(return_value=mock_put_response)

    # Upload the file
    drive_id, item_id = await uploader.upload_file(b"test content", "test.txt")

    # Verify results
    assert drive_id == "test-drive-id-123"
    assert item_id == "test-item-id-456"

    # Verify drive resolution was called
    http_client.get.assert_called_once()
    assert uploader._resolved_drive_id == "test-drive-id-123"

    # Verify upload was called
    http_client.put.assert_called_once()


@pytest.mark.asyncio
async def test_upload_file_path_traversal_prevention(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test that path traversal attacks are prevented via filename sanitization."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "test-drive-id-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock successful upload
    mock_put_response = MagicMock()
    mock_put_response.status_code = 201
    mock_put_response.json.return_value = {
        "id": "test-item-id-456",
        "name": "passwd",  # Sanitized filename
        "parentReference": {"driveId": "test-drive-id-123"},
    }
    http_client.put = AsyncMock(return_value=mock_put_response)

    # Upload with path traversal filename - should be sanitized to just "passwd"
    drive_id, item_id = await uploader.upload_file(b"test content", "../../etc/passwd")

    # Verify upload succeeded with sanitized filename
    assert drive_id == "test-drive-id-123"
    assert item_id == "test-item-id-456"

    # Verify the upload URL contained only "passwd", not the path traversal
    call_args = http_client.put.call_args
    url = call_args.args[0]
    assert "passwd" in url
    assert "../" not in url
    assert "/etc/" not in url


@pytest.mark.asyncio
async def test_upload_file_empty_filename_error(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test that empty filename after sanitization raises error."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": "test-drive-id-123"}
    http_client.get = AsyncMock(return_value=mock_response)

    # Try to upload with filename that becomes empty after sanitization
    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(b"test content", "../../")

    assert "Invalid filename" in str(exc_info.value)


@pytest.mark.asyncio
async def test_verify_drive_non_json_error_response(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when server returns non-JSON error response."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock 500 response with plain text (not JSON)
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_response.json.side_effect = ValueError("Not JSON")  # Simulate JSON parse error
    http_client.get = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=mock_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader._resolve_drive_id()

    # Should handle non-JSON gracefully
    assert "Failed to verify drive" in str(exc_info.value)


@pytest.mark.asyncio
async def test_simple_upload_success(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test successful simple upload."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock successful upload
    mock_put_response = MagicMock()
    mock_put_response.status_code = 201
    mock_put_response.json.return_value = {
        "id": "item-456",
        "name": "document.docx",
        "size": 1024,
        "parentReference": {"driveId": "drive-123"},
    }
    http_client.put = AsyncMock(return_value=mock_put_response)

    # Perform upload
    file_content = b"test file content"
    drive_id, item_id = await uploader.upload_file(file_content, "document.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    assert drive_id == "drive-123"
    assert item_id == "item-456"

    # Verify PUT was called with correct URL and headers
    put_call = http_client.put.call_args
    assert "/drives/drive-123/root:/" in put_call.args[0]
    assert "document.docx" in put_call.args[0]
    assert put_call.kwargs["headers"]["Content-Type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert put_call.kwargs["content"] == file_content


@pytest.mark.asyncio
async def test_simple_upload_file_too_large_error(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when file is too large for simple upload."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock 413 response (file too large)
    mock_put_response = MagicMock()
    mock_put_response.status_code = 413
    http_client.put = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "413 Payload Too Large",
            request=MagicMock(),
            response=mock_put_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(b"test content", "large.docx")

    assert "File too large" in str(exc_info.value)


@pytest.mark.asyncio
async def test_simple_upload_access_denied_error(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling for access denied during upload."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock 403 response (access denied)
    mock_put_response = MagicMock()
    mock_put_response.status_code = 403
    http_client.put = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "403 Forbidden",
            request=MagicMock(),
            response=mock_put_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(b"test content", "document.docx")

    assert "Access denied" in str(exc_info.value)
    assert "permissions" in str(exc_info.value)


@pytest.mark.asyncio
async def test_simple_upload_quota_exceeded_error(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling for quota exceeded."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock 507 response (insufficient storage)
    mock_put_response = MagicMock()
    mock_put_response.status_code = 507
    http_client.put = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "507 Insufficient Storage",
            request=MagicMock(),
            response=mock_put_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(b"test content", "document.docx")

    assert "Insufficient storage quota" in str(exc_info.value)


@pytest.mark.asyncio
async def test_simple_upload_network_error(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling for network errors during upload."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock network error
    http_client.put = AsyncMock(
        side_effect=httpx.RequestError("Connection timeout")
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(b"test content", "document.docx")

    assert "Network error" in str(exc_info.value)
    assert "Connection timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_simple_upload_non_json_error_response(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when server returns non-JSON error response."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Mock successful drive verification
    mock_get_response = MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_get_response)

    # Mock 500 response with plain text (not JSON)
    mock_put_response = MagicMock()
    mock_put_response.status_code = 500
    mock_put_response.text = "Internal Server Error"
    mock_put_response.json.side_effect = ValueError("Not JSON")  
    http_client.put = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "500 Server Error",
            request=MagicMock(),
            response=mock_put_response,
        )
    )

    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(b"test content", "document.docx")

    # Should handle non-JSON gracefully
    assert "Upload failed" in str(exc_info.value)


# Large file upload tests (resumable upload session)


@pytest.mark.asyncio
async def test_large_upload_success(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test successful large file upload using upload session."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    # Create a 5MB file
    file_content = b"X" * (5 * 1024 * 1024)

    # Mock drive resolution
    mock_drive_response = MagicMock()
    mock_drive_response.status_code = 200
    mock_drive_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_drive_response)

    # Mock session creation
    mock_session_response = MagicMock()
    mock_session_response.status_code = 200
    mock_session_response.json.return_value = {
        "uploadUrl": "https://upload.example.com/session-456",
        "expirationDateTime": "2025-02-01T12:00:00Z",
    }
    http_client.post = AsyncMock(return_value=mock_session_response)

    # Mock chunk upload - 5MB file fits in one 10MB chunk, so only one PUT
    mock_chunk_201 = MagicMock()
    mock_chunk_201.status_code = 201
    mock_chunk_201.json.return_value = {
        "id": "item-789",
        "name": "large.bin",
        "size": 5 * 1024 * 1024,
        "parentReference": {"driveId": "drive-123"},
    }

    http_client.put = AsyncMock(return_value=mock_chunk_201)

    # Upload
    drive_id, item_id = await uploader.upload_file(file_content, "large.bin")

    assert drive_id == "drive-123"
    assert item_id == "item-789"

    # Verify session creation
    session_call = http_client.post.call_args
    assert "/createUploadSession" in session_call.args[0]
    assert session_call.kwargs["json"]["item"]["@microsoft.graph.conflictBehavior"] == "replace"

    # Verify one chunk was uploaded (5MB < 10MB chunk size)
    assert http_client.put.call_count == 1


@pytest.mark.asyncio
async def test_large_upload_session_creation_fails(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test error handling when upload session creation fails."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    file_content = b"X" * (5 * 1024 * 1024)

    # Mock drive resolution
    mock_drive_response = MagicMock()
    mock_drive_response.status_code = 200
    mock_drive_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_drive_response)

    # Mock session creation failure
    mock_error_response = MagicMock()
    mock_error_response.status_code = 403
    mock_error_response.json.return_value = {
        "error": {"message": "Access denied"}
    }
    http_client.post = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=mock_error_response
        )
    )

    # Should raise UploadError
    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(file_content, "large.bin")

    assert "Access denied" in str(exc_info.value)


@pytest.mark.asyncio
async def test_large_upload_chunk_fails_and_cancels_session(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test that upload session is canceled when chunk upload fails."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    file_content = b"X" * (5 * 1024 * 1024)

    # Mock drive resolution
    mock_drive_response = MagicMock()
    mock_drive_response.status_code = 200
    mock_drive_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_drive_response)

    # Mock session creation
    mock_session_response = MagicMock()
    mock_session_response.status_code = 200
    mock_session_response.json.return_value = {
        "uploadUrl": "https://upload.example.com/session-456",
        "expirationDateTime": "2025-02-01T12:00:00Z",
    }
    http_client.post = AsyncMock(return_value=mock_session_response)

    # Mock chunk upload failure
    mock_error_response = MagicMock()
    mock_error_response.status_code = 507
    mock_error_response.json.return_value = {
        "error": {"message": "Insufficient storage"}
    }
    http_client.put = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Insufficient Storage", request=MagicMock(), response=mock_error_response
        )
    )

    # Mock session cancellation
    mock_delete_response = MagicMock()
    mock_delete_response.status_code = 204
    http_client.delete = AsyncMock(return_value=mock_delete_response)

    # Should raise UploadError
    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(file_content, "large.bin")

    assert "Insufficient storage" in str(exc_info.value)

    # Verify session was canceled
    delete_call = http_client.delete.call_args
    assert "upload.example.com" in delete_call.args[0]


@pytest.mark.asyncio
async def test_large_upload_network_error_cancels_session(
    config_with_drive: office2pdf.Config,
    http_client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    authenticator: Authenticator,
) -> None:
    """Test that upload session is canceled on network error."""
    uploader = Uploader(config_with_drive, http_client, semaphore, authenticator)

    file_content = b"X" * (5 * 1024 * 1024)

    # Mock drive resolution
    mock_drive_response = MagicMock()
    mock_drive_response.status_code = 200
    mock_drive_response.json.return_value = {"id": "drive-123"}
    http_client.get = AsyncMock(return_value=mock_drive_response)

    # Mock session creation
    mock_session_response = MagicMock()
    mock_session_response.status_code = 200
    mock_session_response.json.return_value = {
        "uploadUrl": "https://upload.example.com/session-456",
        "expirationDateTime": "2025-02-01T12:00:00Z",
    }
    http_client.post = AsyncMock(return_value=mock_session_response)

    # Mock network error during chunk upload
    http_client.put = AsyncMock(
        side_effect=httpx.RequestError("Connection timeout")
    )

    # Mock session cancellation
    mock_delete_response = MagicMock()
    mock_delete_response.status_code = 204
    http_client.delete = AsyncMock(return_value=mock_delete_response)

    # Should raise UploadError
    with pytest.raises(UploadError) as exc_info:
        await uploader.upload_file(file_content, "large.bin")

    assert "Network error" in str(exc_info.value)

    # Verify session was canceled
    delete_call = http_client.delete.call_args
    assert "upload.example.com" in delete_call.args[0]
