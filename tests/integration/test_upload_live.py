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


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_DRIVE_ID, reason="AZURE_DRIVE_ID not provided")
async def test_simple_upload_small_file_live(
    http_client: httpx.AsyncClient, authenticator: Authenticator
) -> None:
    """Test uploading a small file (< 4MB) using simple PUT upload.

    This test uploads a file, verifies the response, then cleans it up.
    """
    assert AZURE_DRIVE_ID

    # Get access token
    token = await authenticator.get_access_token()

    # Create a small test file
    test_content = b"Hello from office2pdf integration test! " * 100
    test_filename = "test_simple_upload.txt"
    upload_path = f"office2pdf-tests/{test_filename}"

    # Upload the file
    url = f"https://graph.microsoft.com/v1.0/drives/{AZURE_DRIVE_ID}/root:/{upload_path}:/content"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain",
    }

    print(f"\n📤 Uploading file to {upload_path}")
    response = await http_client.put(url, headers=headers, content=test_content)

    item_id = None
    try:
        print(f"\n📊 Upload Response (status {response.status_code}):")
        if response.status_code not in (200, 201):
            print(f"  Error: {response.text}")
            response.raise_for_status()

        data = response.json()
        item_id = data.get("id")

        print(f"  Response keys: {list(data.keys())}")
        print(f"  Item ID: {data.get('id')}")
        print(f"  Name: {data.get('name')}")
        print(f"  Size: {data.get('size')}")
        print(f"  Parent Reference: {data.get('parentReference', {}).keys()}")
        if "parentReference" in data:
            print(f"    Drive ID: {data['parentReference'].get('driveId')}")
            print(f"    Item ID: {data['parentReference'].get('id')}")

        # Verify response structure
        assert "id" in data
        assert "parentReference" in data
        assert "driveId" in data["parentReference"]
        assert data.get("name") == test_filename
        assert data.get("size") == len(test_content)

    finally:
        # Clean up - delete the uploaded file
        if item_id:
            delete_url = f"https://graph.microsoft.com/v1.0/drives/{AZURE_DRIVE_ID}/items/{item_id}"
            delete_response = await http_client.delete(delete_url, headers=headers)
            print(f"\n🗑️ Cleanup: Deleted file (status {delete_response.status_code})")


@pytest.mark.asyncio
@pytest.mark.skipif(not HAS_DRIVE_ID, reason="AZURE_DRIVE_ID not provided")
async def test_resumable_upload_large_file_live(
    http_client: httpx.AsyncClient, authenticator: Authenticator
) -> None:
    """Test uploading a large file (> 4MB) using resumable upload session.

    This test creates an upload session, uploads file in chunks, and cleans up.
    """
    assert AZURE_DRIVE_ID

    # Get access token
    token = await authenticator.get_access_token()

    # Create a large test file (5 MB)
    chunk_size = 320 * 1024  # 320 KiB - required multiple for Graph API
    test_content = b"X" * (5 * 1024 * 1024)  # 5 MB
    test_filename = "test_large_upload.bin"
    upload_path = f"office2pdf-tests/{test_filename}"

    print(f"\n📤 Starting resumable upload for {len(test_content)} bytes to {upload_path}")

    # Step 1: Create upload session
    create_session_url = (
        f"https://graph.microsoft.com/v1.0/drives/{AZURE_DRIVE_ID}/root:/{upload_path}:/createUploadSession"
    )
    session_body = {"item": {"@microsoft.graph.conflictBehavior": "replace"}}
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    session_response = await http_client.post(
        create_session_url, headers=headers, json=session_body
    )

    print(f"\n📊 Upload Session Response (status {session_response.status_code}):")
    session_response.raise_for_status()
    session_data = session_response.json()

    print(f"  Upload URL: {session_data.get('uploadUrl', '')[:80]}...")
    print(f"  Expiration: {session_data.get('expirationDateTime')}")
    print(f"  Response keys: {list(session_data.keys())}")

    assert "uploadUrl" in session_data
    assert "expirationDateTime" in session_data

    upload_url = session_data["uploadUrl"]
    item_id = None

    try:
        # Step 2: Upload file in chunks
        total_size = len(test_content)
        offset = 0

        while offset < total_size:
            # Calculate chunk boundaries
            chunk_end = min(offset + chunk_size, total_size)
            chunk_data = test_content[offset:chunk_end]

            # Upload chunk with Content-Range header
            chunk_headers = {
                "Content-Length": str(len(chunk_data)),
                "Content-Range": f"bytes {offset}-{chunk_end-1}/{total_size}",
            }

            print(
                f"  Uploading chunk: bytes {offset}-{chunk_end-1}/{total_size} "
                f"({len(chunk_data)} bytes)"
            )

            chunk_response = await http_client.put(
                upload_url, headers=chunk_headers, content=chunk_data
            )

            print(f"    Response status: {chunk_response.status_code}")

            if chunk_response.status_code == 202:
                # More chunks needed
                chunk_result = chunk_response.json()
                print(f"    Next ranges: {chunk_result.get('nextExpectedRanges', [])}")
            elif chunk_response.status_code == 201:
                # Upload complete!
                result_data = chunk_response.json()
                item_id = result_data.get("id")
                print(f"    ✅ Upload complete!")
                print(f"    Item ID: {item_id}")
                print(f"    Name: {result_data.get('name')}")
                print(f"    Size: {result_data.get('size')}")

                # Verify response structure
                assert "id" in result_data
                assert result_data.get("name") == test_filename
                assert result_data.get("size") == total_size
            else:
                # Unexpected status
                print(f"    Unexpected status: {chunk_response.text}")
                chunk_response.raise_for_status()

            offset = chunk_end

    finally:
        # Clean up - delete the uploaded file
        if item_id:
            delete_headers = {"Authorization": f"Bearer {token}"}
            delete_url = f"https://graph.microsoft.com/v1.0/drives/{AZURE_DRIVE_ID}/items/{item_id}"
            delete_response = await http_client.delete(delete_url, headers=delete_headers)
            print(f"\n🗑️ Cleanup: Deleted file (status {delete_response.status_code})")
        else:
            # Cancel upload session if we didn't complete
            print("\n🗑️ Cleanup: Canceling upload session...")
            cancel_response = await http_client.delete(upload_url)
            print(f"  Session canceled (status {cancel_response.status_code})")
