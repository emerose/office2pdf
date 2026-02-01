"""Authentication module for Microsoft Graph."""

from typing import Any

import msal  # type: ignore[import-untyped]

from .errors import AuthenticationError
from .types import Config


class Authenticator:
    """Handles authentication with Microsoft Graph using MSAL."""

    def __init__(self, config: Config) -> None:
        """Initialize authenticator.

        Args:
            config: Graph configuration
        """
        self.config = config
        self._app: msal.ConfidentialClientApplication | None = None
        self._token: dict[str, Any] | None = None

    def _get_app(self) -> msal.ConfidentialClientApplication:
        """Get or create MSAL application instance."""
        if self._app is None:
            self._app = msal.ConfidentialClientApplication(
                client_id=self.config.client_id,
                client_credential=self.config.client_secret,
                authority=self.config.authority,
            )
        return self._app

    async def get_access_token(self) -> str:
        """Get a valid access token.

        Returns:
            Access token string

        Raises:
            AuthenticationError: If authentication fails
        """
        # Check if we have a cached token
        if self._token and "access_token" in self._token:
            token: str = self._token["access_token"]
            return token

        app = self._get_app()

        # Try to acquire token
        result: dict[str, Any] | None = app.acquire_token_for_client(scopes=[self.config.scope])

        if not result or "access_token" not in result:
            error_desc = result.get("error_description", "Unknown error") if result else "No result"
            msg = f"Failed to acquire token: {error_desc}"
            raise AuthenticationError(msg)

        self._token = result
        access_token = result["access_token"]
        if not isinstance(access_token, str):
            msg = "Access token is not a string"
            raise AuthenticationError(msg)
        return access_token
