"""Authentication module for Microsoft Graph."""

import asyncio
import time
from typing import Any

import msal  # type: ignore[import-untyped]

from .errors import AuthenticationError
from .types import Config


class Authenticator:
    """Handles authentication with Microsoft Graph using MSAL.

    Manages OAuth2 client credentials flow for Microsoft Graph API access.
    Tokens are cached and automatically refreshed when expired.

    Token Lifecycle:
        - Tokens typically expire after 60-90 minutes
        - A 5-minute buffer is used before expiration to avoid edge cases
        - Expired tokens are automatically refreshed on next access
    """

    # Refresh buffer: Request new token this many seconds before expiry
    TOKEN_REFRESH_BUFFER_SECONDS = 300  # 5 minutes

    def __init__(self, config: Config) -> None:
        """Initialize authenticator.

        Args:
            config: Graph configuration
        """
        self.config = config
        self._app: msal.ConfidentialClientApplication | None = None
        self._token: dict[str, Any] | None = None
        self._token_expires_at: float | None = None

    def _get_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL application instance.

        Raises:
            AuthenticationError: If authority configuration fails
        """
        if self._app is None:
            try:
                self._app = msal.ConfidentialClientApplication(
                    client_id=self.config.client_id,
                    client_credential=self.config.client_secret,
                    authority=self.config.authority,
                )
            except ValueError as e:
                # MSAL raises ValueError for invalid authority/tenant
                msg = f"Failed to initialize MSAL client: {e}"
                raise AuthenticationError(msg) from e
        return self._app

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid.

        Returns:
            True if token exists and is not expired (with buffer)
        """
        if not self._token or "access_token" not in self._token:
            return False

        if self._token_expires_at is None:
            return False

        # Check if token is expired (with buffer)
        current_time = time.time()
        time_until_expiry = self._token_expires_at - current_time

        return time_until_expiry > self.TOKEN_REFRESH_BUFFER_SECONDS

    async def get_access_token(self) -> str:
        """Get a valid access token.

        Returns cached token if still valid, otherwise acquires a new one.
        Tokens are automatically refreshed 5 minutes before expiration.

        Returns:
            Access token string

        Raises:
            AuthenticationError: If authentication fails
        """
        # Return cached token if still valid
        if self._is_token_valid():
            token: str = self._token["access_token"]  # type: ignore[index]
            return token

        # Need to acquire a new token
        app = self._get_app()

        # Try to acquire token (run blocking call in executor to avoid blocking event loop)
        loop = asyncio.get_running_loop()
        result: dict[str, Any] | None = await loop.run_in_executor(
            None, app.acquire_token_for_client, [self.config.scope]
        )

        if not result or "access_token" not in result:
            error_desc = result.get("error_description", "Unknown error") if result else "No result"
            error_code = result.get("error", "unknown") if result else "no_response"
            msg = f"Failed to acquire token: {error_desc} (error: {error_code})"
            raise AuthenticationError(msg)

        # Extract and validate access token
        access_token = result["access_token"]
        if not isinstance(access_token, str):
            msg = "Access token is not a string"
            raise AuthenticationError(msg)

        # Calculate token expiration time
        # MSAL returns 'expires_in' (seconds until expiry)
        expires_in = result.get("expires_in", 3600)  # Default to 1 hour
        self._token_expires_at = time.time() + expires_in

        # Cache the token response
        self._token = result

        return access_token
