# office2pdf — Lightweight Spec (Microsoft Graph Backend)

## 1) Goal

Create a small, async-first Python module that converts **Office files** (DOCX / PPTX / XLSX and common variants) to **PDF** using **Microsoft Graph**.

The module:
- Accepts input as **bytes** or **file path**
- Returns output as **bytes** or writes to **file path**
- Internally handles:
  1. Authentication (Azure Entra ID)
  2. Upload to OneDrive / SharePoint
  3. Conversion via Graph `content?format=pdf`
  4. Cleanup (delete temporary files)

Non-goals:
- No chunking, OCR, rasterization, or VLM work
- No long-term storage or syncing
- No UI or CLI (library-only)

---

## 2) Public API

### Package layout
```
office2pdf/
  __init__.py
  client.py
  auth.py
  upload.py
  convert.py
  cleanup.py
  errors.py
  types.py
  utils.py
```

### Primary interface

```python
from office2pdf import GraphOfficeToPdf, GraphConfig

config = GraphConfig(
    tenant_id="...",
    client_id="...",
    client_secret="...",
    drive_root="/Apps/office2pdf",
)

async with GraphOfficeToPdf(config) as converter:
    pdf_bytes = await converter.convert_bytes(
        office_bytes,
        filename="input.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    await converter.convert_file(
        input_path="report.docx",
        output_path="report.pdf",
    )
```

### Required methods
- `convert_bytes(bytes, filename, content_type | None) -> bytes`
- `convert_file(input_path: str | Path, output_path: str | Path | None = None) -> bytes | None`
- `close()`

---

## 3) Configuration

### GraphConfig

Required:
- `tenant_id: str`
- `client_id: str`
- `client_secret: str`

Optional / defaults:
- `authority: str = "https://login.microsoftonline.com/{tenant_id}"`
- `scope: str = "https://graph.microsoft.com/.default"`
- `graph_base_url: str = "https://graph.microsoft.com/v1.0"`
- `drive_id: str | None`
- `site_id: str | None`
- `drive_root: str = "/Apps/office2pdf"`
- `cleanup: bool = True`
- `request_timeout_s: float = 120.0`
- `max_retries: int = 5`
- `retry_backoff_base_s: float = 0.5`
- `concurrency_limit: int = 8`

Auth mode:
- v1 supports **application (client credentials)** only
- Delegated auth may be added later

---

## 4) Dependencies

Minimal, official-first:
- `msal` — Microsoft authentication library
- `httpx` — async HTTP client
- `pydantic` or `dataclasses` — config/types (optional)

---

## 5) Permissions & Setup

Azure Entra app registration:
- Application permissions sufficient for file upload/read/delete
  - Recommended: dedicated SharePoint site / document library
- Admin consent required

---

## 6) Conversion Pipeline

### A) Resolve upload target
- Prefer explicit `drive_id`
- Create a per-job temp path: `{drive_root}/{uuid4()}/filename.ext`

### B) Upload file
- Simple upload for small files
- Resumable upload session for large files (10 MiB chunks)

### C) Convert to PDF
```
GET /drives/{drive_id}/items/{item_id}/content?format=pdf
```

### D) Cleanup
- Best-effort delete uploaded item
- Do not fail conversion if cleanup fails

---

## 7) Error Handling

Error classes:
- `GraphAuthError`
- `GraphUploadError`
- `GraphConversionError`
- `GraphCleanupError`
- `GraphThrottleError`
- `GraphPermissionError`
- `GraphNotSupportedError`

Retry on 429 / 5xx with backoff.

---

## 8) Async & Resource Management

- Reuse a single `httpx.AsyncClient`
- Use `asyncio.Semaphore` for concurrency
- Support async context manager

---

## 9) Data Handling & Privacy

- No local disk writes unless requested
- No persistent cloud storage
- All uploaded artifacts deleted after conversion

---

## 10) Deliverables

- Python module `office2pdf`
- Example scripts
- README with setup and limitations
