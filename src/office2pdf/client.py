"""Main client for office2pdf."""

import asyncio
import contextlib
from pathlib import Path
from types import TracebackType
from typing import Self

import httpx

from .auth import Authenticator
from .cleanup import Cleaner
from .convert import PdfConverter
from .types import Config
from .upload import Uploader
from .utils import get_content_type


class OfficeToPdf:
    """Main client for converting Office files to PDF using Microsoft Graph.

    Example:
        ```python
        import office2pdf

        config = office2pdf.Config(
            tenant_id="...",
            client_id="...",
            client_secret="...",
        )

        async with office2pdf.OfficeToPdf(config) as converter:
            pdf_bytes = await converter.convert_bytes(
                office_bytes,
                filename="input.docx",
            )

            await converter.convert_file(
                input_path="report.docx",
                output_path="report.pdf",
            )
        ```
    """

    def __init__(self, config: Config) -> None:
        """Initialize converter.

        Args:
            config: Graph configuration
        """
        self.config = config
        self._http_client: httpx.AsyncClient | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._authenticator: Authenticator | None = None
        self._uploader: Uploader | None = None
        self._converter: PdfConverter | None = None
        self._cleaner: Cleaner | None = None

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        await self._initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.close()

    async def _initialize(self) -> None:
        """Initialize HTTP client and components."""
        self._http_client = httpx.AsyncClient(
            timeout=self.config.request_timeout_s,
        )
        self._semaphore = asyncio.Semaphore(self.config.concurrency_limit)
        self._authenticator = Authenticator(self.config)
        self._uploader = Uploader(self.config, self._http_client, self._semaphore)
        self._converter = PdfConverter(self.config, self._http_client, self._semaphore)
        self._cleaner = Cleaner(self.config, self._http_client, self._semaphore)

    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def convert_bytes(
        self,
        office_bytes: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> bytes:
        """Convert Office file bytes to PDF.

        Args:
            office_bytes: Office file content as bytes
            filename: Original filename (used for type detection)
            content_type: MIME type (auto-detected if not provided)

        Returns:
            PDF file content as bytes

        Raises:
            GraphError: If conversion fails
        """
        if not self._uploader or not self._converter:
            msg = "Client not initialized. Use async context manager."
            raise RuntimeError(msg)

        # Auto-detect content type if not provided
        if content_type is None:
            content_type = get_content_type(filename)

        # Upload file
        drive_id, item_id = await self._uploader.upload_file(office_bytes, filename, content_type)

        try:
            # Convert to PDF
            return await self._converter.convert_to_pdf(drive_id, item_id)

        finally:
            # Cleanup (best effort)
            if self.config.cleanup and self._cleaner:
                with contextlib.suppress(Exception):
                    await self._cleaner.delete_item(drive_id, item_id)

    async def convert_file(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
    ) -> bytes | None:
        """Convert Office file to PDF.

        Args:
            input_path: Path to Office file
            output_path: Path to save PDF (optional)

        Returns:
            PDF bytes if output_path is None, otherwise None

        Raises:
            GraphError: If conversion fails
            FileNotFoundError: If input file doesn't exist
        """
        input_path = Path(input_path)

        if not input_path.exists():
            msg = f"Input file not found: {input_path}"
            raise FileNotFoundError(msg)

        # Read input file
        office_bytes = input_path.read_bytes()

        # Convert
        pdf_bytes = await self.convert_bytes(
            office_bytes,
            filename=input_path.name,
        )

        # Write output if path provided
        if output_path is not None:
            output_path = Path(output_path)
            output_path.write_bytes(pdf_bytes)
            return None

        return pdf_bytes
