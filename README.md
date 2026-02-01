# office2pdf

[![CI](https://github.com/emerose/office2pdf/workflows/CI/badge.svg)](https://github.com/emerose/office2pdf/actions)

Lightweight async Python library for converting Office files to PDF using Microsoft Graph.

## Features

- **Async-first**: Built with `asyncio` and `httpx` for high performance
- **Simple API**: Convert files with just a few lines of code
- **Flexible input/output**: Work with bytes or file paths
- **Automatic cleanup**: Temporary files are deleted after conversion
- **Type-safe**: Full type hints and Pydantic configuration
- **Production-ready**: Retry logic, concurrency limits, and error handling

## Supported File Types

- Microsoft Word: `.docx`, `.doc`
- Microsoft PowerPoint: `.pptx`, `.ppt`
- Microsoft Excel: `.xlsx`, `.xls`

## Installation

Using uv (recommended):

```bash
uv add office2pdf
```

Using pip:

```bash
pip install office2pdf
```

## Prerequisites

### Azure Setup

1. **Create an Azure App Registration**:
   - Go to [Azure Portal](https://portal.azure.com)
   - Navigate to Microsoft Entra ID > Add > App registrations
   - Click "New registration"
   - Note the Tenant ID and Client ID

2. **Create a Client Secret**:
   - In your app registration, go to "Certificates & secrets"
   - Click "New client secret"
   - Save the secret value (shown only once)

3. **Configure API Permissions**:
   - In your app registration, go to "API permissions"
   - Add Microsoft Graph **Application** permissions:
     - `Files.ReadWrite.All` (or more specific drive permissions)
     - `Sites.ReadWrite.All` (if using SharePoint)
   - Click "Grant admin consent"

4. **Set up OneDrive/SharePoint**:
   - Option A: Use the default OneDrive for the app
   - Option B: Create a dedicated SharePoint site/document library

## Quick Start

### Basic Usage

```python
import asyncio
import office2pdf

async def main():
    config = office2pdf.Config(
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        client_secret="your-client-secret",
    )

    async with office2pdf.OfficeToPdf(config) as converter:
        # Convert from bytes
        with open("input.docx", "rb") as f:
            office_bytes = f.read()

        pdf_bytes = await converter.convert_bytes(
            office_bytes,
            filename="input.docx",
        )

        with open("output.pdf", "wb") as f:
            f.write(pdf_bytes)

if __name__ == "__main__":
    asyncio.run(main())
```

### Convert File Directly

```python
async with office2pdf.OfficeToPdf(config) as converter:
    # Read input file, write output file
    await converter.convert_file(
        input_path="report.docx",
        output_path="report.pdf",
    )
```

### Get PDF Bytes Without Writing

```python
async with office2pdf.OfficeToPdf(config) as converter:
    # Returns bytes instead of writing to disk
    pdf_bytes = await converter.convert_file(
        input_path="report.docx",
    )
```

## Configuration

### Config Options

```python
config = office2pdf.Config(
    # Required
    tenant_id="...",
    client_id="...",
    client_secret="...",

    # Optional (with defaults shown)
    drive_root="/Apps/office2pdf",      # Temp file location
    cleanup=True,                        # Delete files after conversion
    request_timeout_s=120.0,            # HTTP timeout
    max_retries=5,                       # Retry attempts
    retry_backoff_base_s=0.5,           # Retry backoff
    concurrency_limit=8,                 # Max concurrent operations
)
```

### Using a Specific Drive or Site

```python
config = office2pdf.Config(
    tenant_id="...",
    client_id="...",
    client_secret="...",
    drive_id="your-drive-id",           # Optional: specific drive
    site_id="your-site-id",             # Optional: specific site
)
```

## Error Handling

```python
import office2pdf
from office2pdf import (
    AuthenticationError,
    UploadError,
    ConversionError,
    RateLimitError,
)

async with office2pdf.OfficeToPdf(config) as converter:
    try:
        pdf_bytes = await converter.convert_bytes(
            office_bytes,
            filename="input.docx",
        )
    except AuthenticationError:
        print("Authentication failed")
    except UploadError:
        print("Upload failed")
    except ConversionError:
        print("Conversion failed")
    except RateLimitError:
        print("Rate limited")
```

## Limitations

- **Authentication**: Currently supports application (client credentials) only
- **File Size**: Limited by Microsoft Graph upload limits (typically 250MB)
- **Rate Limiting**: Subject to Microsoft Graph API throttling
- **Conversion Quality**: Depends on Microsoft Graph's conversion engine
- **Supported Formats**: Only Microsoft Office formats (DOCX, PPTX, XLSX, etc.)

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/emerose/office2pdf.git
cd office2pdf

# Install dependencies with uv
uv sync --dev

# Activate virtual environment
source .venv/bin/activate
```

### Testing

```bash
# Run tests
uv run pytest

# Type checking
uv run pyright src/office2pdf

# Linting
uv run ruff check src/office2pdf

# Format code
uv run ruff format src/office2pdf
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please use the [GitHub issue tracker](https://github.com/emerose/office2pdf/issues).
