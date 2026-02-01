"""Basic usage example for office2pdf.

This example demonstrates how to convert an Office file to PDF using Microsoft Graph.

Before running:
1. Set up Azure App Registration (see README.md for instructions)
2. Set environment variables:
   - AZURE_TENANT_ID
   - AZURE_CLIENT_ID
   - AZURE_CLIENT_SECRET
3. Place a test Office file (e.g., test.docx) in this directory
"""

import asyncio
import os
from pathlib import Path

import office2pdf


async def main() -> None:
    """Convert an Office file to PDF."""
    # Get credentials from environment
    config = office2pdf.Config(
        tenant_id=os.environ["AZURE_TENANT_ID"],
        client_id=os.environ["AZURE_CLIENT_ID"],
        client_secret=os.environ["AZURE_CLIENT_SECRET"],
    )

    # Path to input file
    input_file = Path(__file__).parent / "test.docx"

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        print("Please create a test.docx file in the examples directory")
        return

    print(f"Converting {input_file.name} to PDF...")

    async with office2pdf.OfficeToPdf(config) as converter:
        # Example 1: Convert file to file
        output_file = input_file.with_suffix(".pdf")
        await converter.convert_file(
            input_path=input_file,
            output_path=output_file,
        )
        print(f"✓ Converted to: {output_file}")

        # Example 2: Convert and get bytes
        pdf_bytes = await converter.convert_file(input_path=input_file)
        print(f"✓ Got PDF bytes: {len(pdf_bytes)} bytes")

        # Example 3: Convert from bytes
        office_bytes = input_file.read_bytes()
        pdf_bytes = await converter.convert_bytes(
            office_bytes,
            filename=input_file.name,
        )
        print(f"✓ Converted from bytes: {len(pdf_bytes)} bytes")


if __name__ == "__main__":
    asyncio.run(main())
