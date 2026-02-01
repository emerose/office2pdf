"""Live integration tests for upload/drive resolution module.

These tests use real Microsoft Graph API and require Azure credentials.
Set environment variables: AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET

Additionally, you need to provide either:
- AZURE_DRIVE_ID: A drive ID for testing (OneDrive or SharePoint)
- AZURE_SITE_ID: A SharePoint site ID for testing

The test app must have Files.ReadWrite.All application permission.
"""

import os

import httpx
import pytest

import office2pdf
from office2pdf.auth import Authenticator

# Check if credentials are available
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_DRIVE_ID = os.getenv("AZURE_DRIVE_ID")
AZURE_SITE_ID = os.getenv("AZURE_SITE_ID")

HAS_CREDENTIALS = all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET])
HAS_DRIVE_ID = HAS_CREDENTIALS and AZURE_DRIVE_ID is not None
HAS_SITE_ID = HAS_CREDENTIALS and AZURE_SITE_ID is not None

pytestmark = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="Azure credentials not provided. Set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET",
)


@pytest.fixture
async def http_client() -> httpx.AsyncClient:
    """Create HTTP client for testing."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
async def authenticator() -> Authenticator:
    """Create authenticator with real credentials."""
    assert AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET
    config = office2pdf.Config(
        tenant_id=AZURE_TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )
    return Authenticator(config)


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_DRIVE_ID, reason="AZURE_DRIVE_ID not provided")
async def test_resolve_drive_by_id_live(
    http_client: httpx.AsyncClient, authenticator: Authenticator
) -> None:
    """Test resolving a drive by explicit drive ID.

    This test verifies we can access a drive directly using its ID.
    """
    assert AZURE_DRIVE_ID

    # Get access token
    token = await authenticator.get_access_token()

    # Try to get drive metadata
    url = f"https://graph.microsoft.com/v1.0/drives/{AZURE_DRIVE_ID}"
    headers = {"Authorization": f"Bearer {token}"}

    response = await http_client.get(url, headers=headers)

    print(f"\n📊 Drive Resolution Response (status {response.status_code}):")
    if response.status_code == 200:
        data = response.json()
        print(f"  Drive ID: {data.get('id')}")
        print(f"  Drive Type: {data.get('driveType')}")
        print(f"  Owner: {data.get('owner', {}).get('user', {}).get('displayName', 'N/A')}")
        print(f"  Response keys: {list(data.keys())}")

        assert data.get("id") == AZURE_DRIVE_ID
        assert "driveType" in data
    else:
        print(f"  Error: {response.text}")
        response.raise_for_status()


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_SITE_ID, reason="AZURE_SITE_ID not provided")
async def test_resolve_site_drive_live(
    http_client: httpx.AsyncClient, authenticator: Authenticator
) -> None:
    """Test resolving a drive from a SharePoint site ID.

    This test verifies we can get the default drive for a SharePoint site.
    """
    assert AZURE_SITE_ID

    # Get access token
    token = await authenticator.get_access_token()
    headers = {"Authorization": f"Bearer {token}"}

    # First, verify the site exists
    site_url = f"https://graph.microsoft.com/v1.0/sites/{AZURE_SITE_ID}"
    site_response = await http_client.get(site_url, headers=headers)

    print(f"\n📊 Site Resolution Response (status {site_response.status_code}):")
    if site_response.status_code == 200:
        site_data = site_response.json()
        print(f"  Site ID: {site_data.get('id')}")
        print(f"  Site Name: {site_data.get('displayName')}")
        print(f"  Site URL: {site_data.get('webUrl')}")
        print(f"  Response keys: {list(site_data.keys())}")
    else:
        print(f"  Error: {site_response.text}")
        site_response.raise_for_status()

    # Now get the drive for this site
    drive_url = f"https://graph.microsoft.com/v1.0/sites/{AZURE_SITE_ID}/drive"
    drive_response = await http_client.get(drive_url, headers=headers)

    print(f"\n📊 Site Drive Resolution Response (status {drive_response.status_code}):")
    if drive_response.status_code == 200:
        drive_data = drive_response.json()
        print(f"  Drive ID: {drive_data.get('id')}")
        print(f"  Drive Type: {drive_data.get('driveType')}")
        print(f"  Response keys: {list(drive_data.keys())}")

        assert "id" in drive_data
        assert drive_data.get("driveType") == "documentLibrary"
    else:
        print(f"  Error: {drive_response.text}")
        drive_response.raise_for_status()


@pytest.mark.asyncio
async def test_invalid_drive_id_error_live(
    http_client: httpx.AsyncClient, authenticator: Authenticator
) -> None:
    """Test error handling for invalid drive ID."""
    invalid_drive_id = "invalid-drive-id-12345"

    # Get access token
    token = await authenticator.get_access_token()

    # Try to get drive metadata with invalid ID
    url = f"https://graph.microsoft.com/v1.0/drives/{invalid_drive_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = await http_client.get(url, headers=headers)

    print(f"\n📊 Invalid Drive ID Response (status {response.status_code}):")
    print(f"  Response: {response.text[:200]}")

    # Should get 404 or 400
    assert response.status_code in (400, 404)

    # Check error structure
    error_data = response.json()
    print(f"  Error keys: {list(error_data.keys())}")
    if "error" in error_data:
        print(f"  Error code: {error_data['error'].get('code')}")
        print(f"  Error message: {error_data['error'].get('message')}")


@pytest.mark.asyncio
async def test_invalid_site_id_error_live(
    http_client: httpx.AsyncClient, authenticator: Authenticator
) -> None:
    """Test error handling for invalid site ID."""
    invalid_site_id = "invalid-site-id-12345"

    # Get access token
    token = await authenticator.get_access_token()

    # Try to get site with invalid ID
    url = f"https://graph.microsoft.com/v1.0/sites/{invalid_site_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = await http_client.get(url, headers=headers)

    print(f"\n📊 Invalid Site ID Response (status {response.status_code}):")
    print(f"  Response: {response.text[:200]}")

    # Should get 404 or 400
    assert response.status_code in (400, 404)

    # Check error structure
    error_data = response.json()
    print(f"  Error keys: {list(error_data.keys())}")
    if "error" in error_data:
        print(f"  Error code: {error_data['error'].get('code')}")
        print(f"  Error message: {error_data['error'].get('message')}")
