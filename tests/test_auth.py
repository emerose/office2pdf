"""Unit tests for authentication module with mocked MSAL responses."""

import time
from unittest.mock import MagicMock, patch

import pytest

import office2pdf
from office2pdf.auth import Authenticator
from office2pdf.errors import AuthenticationError


@pytest.fixture
def config() -> office2pdf.Config:
    """Create test configuration."""
    return office2pdf.Config(
        tenant_id="test-tenant-id",
        client_id="test-client-id",
        client_secret="test-client-secret",
    )


@pytest.fixture
def mock_token_response() -> dict:
    """Create a mock token response matching MSAL format."""
    return {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6Ik1yNS1BVWliZkJpaTdOZDFqQmViYXhib1hXMCIsImtpZCI6Ik1yNS1BVWliZkJpaTdOZDFqQmViYXhib1hXMCJ9.test_token",
        "token_type": "Bearer",
        "expires_in": 3599,  # ~1 hour
        "ext_expires_in": 3599,
    }


@pytest.mark.asyncio
async def test_get_access_token_success(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test successful token acquisition."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = mock_token_response
        MockApp.return_value = mock_app

        token = await authenticator.get_access_token()

        # Should return the access token
        assert token == mock_token_response["access_token"]

        # Should have called MSAL with correct scope
        # Note: run_in_executor passes scopes as positional arg, not keyword arg
        mock_app.acquire_token_for_client.assert_called_once_with(
            ["https://graph.microsoft.com/.default"]
        )


@pytest.mark.asyncio
async def test_token_caching(config: office2pdf.Config, mock_token_response: dict) -> None:
    """Test that tokens are cached and not re-acquired unnecessarily."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = mock_token_response
        MockApp.return_value = mock_app

        # First call - should acquire token
        token1 = await authenticator.get_access_token()

        # Second call - should return cached token
        token2 = await authenticator.get_access_token()

        # Should be the same token
        assert token1 == token2

        # Should only have called MSAL once (cached second time)
        assert mock_app.acquire_token_for_client.call_count == 1


@pytest.mark.asyncio
async def test_token_expiry_and_refresh(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test that expired tokens are refreshed."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = mock_token_response
        MockApp.return_value = mock_app

        # Get initial token
        token1 = await authenticator.get_access_token()
        assert token1 == mock_token_response["access_token"]

        # Manually expire the token by setting expiry to past
        authenticator._token_expires_at = time.time() - 100

        # Get token again - should refresh
        token2 = await authenticator.get_access_token()

        # Should have called MSAL twice (once initial, once refresh)
        assert mock_app.acquire_token_for_client.call_count == 2

        # Tokens should be the same content (same mock response)
        assert token1 == token2


@pytest.mark.asyncio
async def test_token_refresh_buffer(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test that tokens are refreshed before they expire (with buffer)."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = mock_token_response
        MockApp.return_value = mock_app

        # Get initial token
        await authenticator.get_access_token()

        # Set expiry to within the refresh buffer (< 5 minutes remaining)
        authenticator._token_expires_at = time.time() + 200  # 200 seconds = ~3 minutes

        # Get token again - should refresh due to buffer
        await authenticator.get_access_token()

        # Should have called MSAL twice (refreshed due to buffer)
        assert mock_app.acquire_token_for_client.call_count == 2


@pytest.mark.asyncio
async def test_authentication_error_no_token(config: office2pdf.Config) -> None:
    """Test error handling when token acquisition fails."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        # Return response without access_token
        mock_app.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid client secret provided",
        }
        MockApp.return_value = mock_app

        with pytest.raises(AuthenticationError) as exc_info:
            await authenticator.get_access_token()

        error_msg = str(exc_info.value)
        assert "Failed to acquire token" in error_msg
        assert "Invalid client secret" in error_msg
        assert "invalid_client" in error_msg


@pytest.mark.asyncio
async def test_authentication_error_null_response(config: office2pdf.Config) -> None:
    """Test error handling when MSAL returns None."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = None
        MockApp.return_value = mock_app

        with pytest.raises(AuthenticationError) as exc_info:
            await authenticator.get_access_token()

        error_msg = str(exc_info.value)
        assert "Failed to acquire token" in error_msg
        assert "No result" in error_msg


@pytest.mark.asyncio
async def test_authentication_error_invalid_token_type(
    config: office2pdf.Config,
) -> None:
    """Test error handling when access_token is not a string."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        # Return access_token as non-string
        mock_app.acquire_token_for_client.return_value = {
            "access_token": 12345,  # Invalid: not a string
            "expires_in": 3600,
        }
        MockApp.return_value = mock_app

        with pytest.raises(AuthenticationError) as exc_info:
            await authenticator.get_access_token()

        assert "Access token is not a string" in str(exc_info.value)


@pytest.mark.asyncio
async def test_token_expiry_calculation(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test that token expiry is correctly calculated from expires_in."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        # Custom expiry time
        custom_response = mock_token_response.copy()
        custom_response["expires_in"] = 7200  # 2 hours
        mock_app.acquire_token_for_client.return_value = custom_response
        MockApp.return_value = mock_app

        current_time = time.time()
        await authenticator.get_access_token()

        # Token expiry should be approximately current_time + 7200
        expected_expiry = current_time + 7200
        assert authenticator._token_expires_at is not None
        assert abs(authenticator._token_expires_at - expected_expiry) < 1  # Within 1 second


@pytest.mark.asyncio
async def test_token_default_expiry(config: office2pdf.Config) -> None:
    """Test default expiry when expires_in is not in response."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        # Response without expires_in
        mock_app.acquire_token_for_client.return_value = {
            "access_token": "test_token",
            "token_type": "Bearer",
        }
        MockApp.return_value = mock_app

        current_time = time.time()
        await authenticator.get_access_token()

        # Should default to 3600 seconds (1 hour)
        expected_expiry = current_time + 3600
        assert authenticator._token_expires_at is not None
        assert abs(authenticator._token_expires_at - expected_expiry) < 1


@pytest.mark.asyncio
async def test_msal_app_caching(config: office2pdf.Config, mock_token_response: dict) -> None:
    """Test that MSAL app instance is reused."""
    authenticator = Authenticator(config)

    with patch("msal.ConfidentialClientApplication") as MockApp:
        mock_app = MagicMock()
        mock_app.acquire_token_for_client.return_value = mock_token_response
        MockApp.return_value = mock_app

        # Make multiple token requests
        await authenticator.get_access_token()

        # Expire token and request again
        authenticator._token_expires_at = time.time() - 100
        await authenticator.get_access_token()

        # MSAL app should only be created once
        assert MockApp.call_count == 1


@pytest.mark.asyncio
async def test_is_token_valid_no_token(config: office2pdf.Config) -> None:
    """Test _is_token_valid when no token exists."""
    authenticator = Authenticator(config)

    # No token acquired yet
    assert not authenticator._is_token_valid()


@pytest.mark.asyncio
async def test_is_token_valid_no_expiry(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test _is_token_valid when token has no expiry."""
    authenticator = Authenticator(config)

    # Set token but no expiry
    authenticator._token = mock_token_response
    authenticator._token_expires_at = None

    assert not authenticator._is_token_valid()


@pytest.mark.asyncio
async def test_is_token_valid_expired(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test _is_token_valid with expired token."""
    authenticator = Authenticator(config)

    authenticator._token = mock_token_response
    authenticator._token_expires_at = time.time() - 100  # Expired

    assert not authenticator._is_token_valid()


@pytest.mark.asyncio
async def test_is_token_valid_within_buffer(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test _is_token_valid when token is within refresh buffer."""
    authenticator = Authenticator(config)

    authenticator._token = mock_token_response
    # Expires in 4 minutes (< 5 minute buffer)
    authenticator._token_expires_at = time.time() + 240

    # Should be considered invalid (within buffer)
    assert not authenticator._is_token_valid()


@pytest.mark.asyncio
async def test_is_token_valid_outside_buffer(
    config: office2pdf.Config, mock_token_response: dict
) -> None:
    """Test _is_token_valid when token is outside refresh buffer."""
    authenticator = Authenticator(config)

    authenticator._token = mock_token_response
    # Expires in 10 minutes (> 5 minute buffer)
    authenticator._token_expires_at = time.time() + 600

    # Should be considered valid
    assert authenticator._is_token_valid()
