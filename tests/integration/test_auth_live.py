"""Live integration tests for authentication module.

These tests use real Microsoft Graph API and require Azure credentials.
Set environment variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
"""

import os
import time
from datetime import UTC, datetime

import pytest

import office2pdf
from office2pdf.auth import Authenticator
from office2pdf.errors import AuthenticationError

# Check if credentials are available
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

HAS_CREDENTIALS = all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET])

pytestmark = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="Azure credentials not provided. Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET",
)


@pytest.fixture
def config() -> office2pdf.Config:
    """Create config with real Azure credentials."""
    assert AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET
    return office2pdf.Config(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )


@pytest.fixture
def authenticator(config: office2pdf.Config) -> Authenticator:
    """Create authenticator with real credentials."""
    return Authenticator(config)


@pytest.mark.asyncio
async def test_acquire_token_live(authenticator: Authenticator) -> None:
    """Test acquiring a real access token from Microsoft."""
    token = await authenticator.get_access_token()

    # Token should be a non-empty string
    assert isinstance(token, str)
    assert len(token) > 0

    # Token should be a JWT (starts with eyJ which is base64 for {"alg":...)
    assert token.startswith("eyJ"), "Token should be a JWT"

    print(f"\n✓ Successfully acquired token (length: {len(token)} chars)")


@pytest.mark.asyncio
async def test_token_caching_live(authenticator: Authenticator) -> None:
    """Test that tokens are cached and reused."""
    # Get first token
    token1 = await authenticator.get_access_token()

    # Get second token - should be cached
    token2 = await authenticator.get_access_token()

    # Should be the exact same token (cached)
    assert token1 == token2

    # Check internal state
    assert authenticator._token is not None
    assert "access_token" in authenticator._token
    assert authenticator._token["access_token"] == token1

    print("\n✓ Token caching works - same token returned")


@pytest.mark.asyncio
async def test_token_structure_live(authenticator: Authenticator) -> None:
    """Inspect the structure of a real MSAL token response."""
    token = await authenticator.get_access_token()

    # Inspect the cached token response
    token_response = authenticator._token
    assert token_response is not None

    print("\n📊 Token Response Structure:")
    print(f"  Keys: {list(token_response.keys())}")

    if "expires_in" in token_response:
        print(f"  expires_in: {token_response['expires_in']} seconds")

    if "ext_expires_in" in token_response:
        print(f"  ext_expires_in: {token_response['ext_expires_in']} seconds")

    if "token_type" in token_response:
        print(f"  token_type: {token_response['token_type']}")

    # Check for expiry timestamp (MSAL may add this)
    if "expires_on" in token_response:
        expires_on = token_response["expires_on"]
        print(f"  expires_on: {expires_on}")

        # Try to parse expiry time
        try:
            if isinstance(expires_on, (int, float)):
                expiry_dt = datetime.fromtimestamp(expires_on, tz=UTC)
                print(f"  expires_at: {expiry_dt.isoformat()}")
        except Exception as e:
            print(f"  (Could not parse expires_on: {e})")

    print(f"  access_token: {token[:50]}... (truncated)")


@pytest.mark.asyncio
async def test_invalid_credentials_live() -> None:
    """Test error handling with invalid credentials."""
    bad_config = office2pdf.Config(
        tenant_id="invalid-tenant",
        client_id="invalid-client",
        client_secret="invalid-secret",
    )
    authenticator = Authenticator(bad_config)

    with pytest.raises(AuthenticationError) as exc_info:
        await authenticator.get_access_token()

    error_msg = str(exc_info.value)
    print(f"\n✓ Got expected error: {error_msg}")
    # Error can be either "Failed to initialize" (invalid tenant) or "Failed to acquire" (invalid credentials)
    assert "Failed" in error_msg and ("initialize" in error_msg or "acquire" in error_msg)


@pytest.mark.asyncio
async def test_invalid_tenant_live() -> None:
    """Test error with valid client but invalid tenant."""
    assert AZURE_CLIENT_ID and AZURE_CLIENT_SECRET

    bad_config = office2pdf.Config(
        tenant_id="00000000-0000-0000-0000-000000000000",  # Invalid tenant
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )
    authenticator = Authenticator(bad_config)

    with pytest.raises(AuthenticationError) as exc_info:
        await authenticator.get_access_token()

    error_msg = str(exc_info.value)
    print(f"\n✓ Got expected error for invalid tenant: {error_msg}")


@pytest.mark.asyncio
async def test_token_refresh_simulation_live(authenticator: Authenticator) -> None:
    """Simulate token expiry to test refresh logic.

    This test acquires a token, then manually expires it to see if
    the authenticator properly requests a new one.
    """
    # Get initial token
    token1 = await authenticator.get_access_token()
    assert token1

    # Manually expire the token by modifying internal state
    assert authenticator._token_expires_at is not None
    authenticator._token_expires_at = time.time() - 1

    # Get token again. This should trigger a refresh.
    token2 = await authenticator.get_access_token()
    assert token2

    # In a live test, the new token string might be identical to the old one.
    # We can assert that the internal expiry timestamp has been updated to a
    # future time, which proves a new token response was processed.
    assert authenticator._token_expires_at > time.time()

    print("\n✓ Token refresh was triggered after manual expiry.")
    print(f"    New token acquired (token1 == token2: {token1 == token2})")
