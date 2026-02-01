# office2pdf - Implementation Roadmap

This document outlines the implementation phases needed to complete the office2pdf library.

## Current Status

✅ Project scaffolding complete
✅ Modern Python tooling configured (uv, ruff, pyright)
✅ CI/CD pipeline with GitHub Actions
✅ Public API defined and documented
✅ Type-safe with Pydantic configuration
✅ Comprehensive test suite for scaffolding (22 tests)

## Phase 1: Core Graph API Integration

### 1.1 Authentication Flow ⏳
**File:** `src/office2pdf/auth.py`

- [ ] Test token acquisition with real Azure credentials
- [ ] Implement token refresh logic (tokens expire after 1 hour)
- [ ] Add token caching with expiration tracking
- [ ] Handle authentication errors (invalid credentials, expired secrets)
- [ ] Add unit tests with mocked MSAL responses
- [ ] Add integration tests with real Azure test tenant

**Acceptance Criteria:**
- Successfully acquire access token from Azure
- Token automatically refreshes before expiration
- Clear error messages for auth failures

### 1.2 Drive/Site Resolution 🔜
**File:** `src/office2pdf/upload.py`

- [ ] Implement drive ID resolution (if not explicitly provided)
- [ ] Support OneDrive personal vs. business
- [ ] Support SharePoint site resolution by site ID
- [ ] Create folder structure: `{drive_root}/{uuid}/filename`
- [ ] Handle drive/site not found errors
- [ ] Add tests for different drive configurations

**Acceptance Criteria:**
- Automatically resolve user's default drive if not specified
- Create temporary folder structure in correct location
- Support both OneDrive and SharePoint targets

## Phase 2: File Upload Implementation

### 2.1 Simple Upload (< 4MB) 📝
**File:** `src/office2pdf/upload.py::_upload_simple()`

**Graph API Endpoint:**
```
PUT /drives/{drive-id}/root:/{path}:/content
```

- [ ] Implement simple PUT request with file bytes
- [ ] Set correct Content-Type header
- [ ] Parse response to extract drive_id and item_id
- [ ] Handle upload errors (quota exceeded, invalid path)
- [ ] Add retry logic for transient failures (5xx errors)
- [ ] Add tests with small test files (< 4MB)

**Acceptance Criteria:**
- Successfully upload files < 4MB to OneDrive/SharePoint
- Return valid drive_id and item_id for uploaded file
- Proper error handling with specific error types

### 2.2 Resumable Upload (≥ 4MB) 📝
**File:** `src/office2pdf/upload.py::_upload_large()`

**Graph API Endpoints:**
```
POST /drives/{drive-id}/root:/{path}:/createUploadSession
PUT {uploadUrl} (upload chunks)
```

- [ ] Create upload session via Graph API
- [ ] Split file into 10MB chunks (configurable)
- [ ] Upload chunks sequentially with progress tracking
- [ ] Handle chunk upload failures with retry
- [ ] Resume from last successful chunk on error
- [ ] Delete upload session on completion/failure
- [ ] Add tests with files > 4MB (use generated test data)

**Acceptance Criteria:**
- Successfully upload large files (test with 50MB+ files)
- Resilient to network interruptions (retry chunks)
- Efficient memory usage (stream chunks, don't load full file)

### 2.3 Upload Error Handling 🛡️
**Files:** `src/office2pdf/upload.py`, `src/office2pdf/errors.py`

- [ ] Implement retry logic with exponential backoff
- [ ] Handle 429 (rate limit) with Retry-After header
- [ ] Handle 507 (insufficient storage)
- [ ] Handle 413 (file too large)
- [ ] Handle invalid file path characters
- [ ] Add comprehensive error tests

**Acceptance Criteria:**
- Automatic retry on transient failures (5xx, network errors)
- Respect rate limits (429) with proper backoff
- Clear error messages for permanent failures

## Phase 3: PDF Conversion

### 3.1 Convert Endpoint Implementation 📄
**File:** `src/office2pdf/convert.py::convert_to_pdf()`

**Graph API Endpoint:**
```
GET /drives/{drive-id}/items/{item-id}/content?format=pdf
```

- [ ] Implement PDF conversion request
- [ ] Add authorization header with access token
- [ ] Stream PDF response to bytes
- [ ] Handle conversion errors (unsupported format, timeout)
- [ ] Add retry logic for transient failures
- [ ] Handle 202 (conversion in progress) responses
- [ ] Add tests with various Office file formats

**Acceptance Criteria:**
- Successfully convert DOCX, PPTX, XLSX to PDF
- Handle large files (test with 20MB+ presentations)
- Proper timeout handling (configurable, default 120s)

### 3.2 Conversion Error Handling 🛡️
**Files:** `src/office2pdf/convert.py`, `src/office2pdf/errors.py`

- [ ] Handle unsupported file types (raise UnsupportedFileError)
- [ ] Handle corrupted files (raise ConversionError)
- [ ] Handle timeout during conversion
- [ ] Add retry logic for transient conversion failures
- [ ] Add tests for error conditions

**Acceptance Criteria:**
- Clear error for unsupported formats (e.g., EML, MSG)
- Timeout after configured duration
- Automatic retry on temporary conversion failures

## Phase 4: Cleanup Implementation

### 4.1 File Deletion 🗑️
**File:** `src/office2pdf/cleanup.py::delete_item()`

**Graph API Endpoint:**
```
DELETE /drives/{drive-id}/items/{item-id}
```

- [ ] Implement DELETE request to remove uploaded file
- [ ] Handle 404 (already deleted) gracefully
- [ ] Log cleanup failures without raising exceptions
- [ ] Add optional cleanup of parent folder (if empty)
- [ ] Add tests for successful and failed cleanup

**Acceptance Criteria:**
- Successfully delete temporary files after conversion
- Gracefully handle already-deleted files
- Never fail conversion due to cleanup errors (best-effort)

### 4.2 Cleanup Configuration ⚙️
**File:** `src/office2pdf/client.py`

- [ ] Implement cleanup toggle (config.cleanup flag)
- [ ] Add cleanup timeout to prevent hanging
- [ ] Log cleanup operations for debugging
- [ ] Test cleanup disabled mode
- [ ] Test cleanup with failures

**Acceptance Criteria:**
- Cleanup can be disabled via config
- Cleanup runs asynchronously without blocking
- Detailed logging for troubleshooting

## Phase 5: Robustness & Production Readiness

### 5.1 Retry & Backoff Logic 🔄
**Files:** All modules

- [ ] Implement exponential backoff utility
- [ ] Respect Retry-After headers (429, 503)
- [ ] Make max_retries configurable per operation
- [ ] Add jitter to prevent thundering herd
- [ ] Log retry attempts for debugging
- [ ] Add tests for retry scenarios

**Acceptance Criteria:**
- Automatic retry on transient failures (up to max_retries)
- Exponential backoff: 0.5s, 1s, 2s, 4s, 8s (configurable)
- Respect server-provided Retry-After headers

### 5.2 Concurrency Control 🚦
**File:** `src/office2pdf/client.py`

- [ ] Test semaphore-based concurrency limiting
- [ ] Verify concurrent conversions don't exceed limit
- [ ] Add integration tests with parallel operations
- [ ] Document concurrency best practices

**Acceptance Criteria:**
- Never exceed config.concurrency_limit simultaneous operations
- Efficient queueing of requests when limit reached

### 5.3 Logging & Observability 📊
**Files:** All modules

- [ ] Add structured logging throughout
- [ ] Log authentication events (token acquired, refreshed)
- [ ] Log upload progress (file size, chunks uploaded)
- [ ] Log conversion timing (start, duration, result)
- [ ] Log cleanup operations
- [ ] Add correlation IDs for request tracing
- [ ] Make logging configurable (level, format)

**Acceptance Criteria:**
- Clear logs for debugging production issues
- Performance metrics visible in logs
- Correlation IDs for multi-step operations

### 5.4 Resource Cleanup 🧹
**File:** `src/office2pdf/client.py`

- [ ] Test HTTP client cleanup on __aexit__
- [ ] Verify no leaked connections
- [ ] Test cleanup on exceptions
- [ ] Add tests for resource leak detection

**Acceptance Criteria:**
- No connection leaks after conversion
- Proper cleanup even on exceptions
- All async resources properly closed

## Phase 6: Testing & Documentation

### 6.1 Integration Tests 🧪
**New file:** `tests/integration/`

- [ ] Set up test Azure tenant/app registration
- [ ] Create integration test fixtures
- [ ] Test full conversion flow (upload → convert → cleanup)
- [ ] Test with various Office formats (DOCX, PPTX, XLSX)
- [ ] Test large file handling (50MB+)
- [ ] Test error scenarios (invalid auth, quota exceeded)
- [ ] Test concurrent conversions
- [ ] Add CI job for integration tests (manual trigger)

**Acceptance Criteria:**
- Full end-to-end tests with real Microsoft Graph API
- Tests can run in CI (with secrets)
- Coverage of all supported file types

### 6.2 Performance Testing ⚡
**New file:** `tests/performance/`

- [ ] Benchmark upload speed for various file sizes
- [ ] Benchmark conversion time for different formats
- [ ] Test memory usage with large files
- [ ] Test concurrent conversion throughput
- [ ] Document performance characteristics

**Acceptance Criteria:**
- Baseline performance metrics documented
- Memory usage stays bounded with large files
- Acceptable throughput for concurrent operations

### 6.3 Documentation Updates 📚
**Files:** `README.md`, docstrings

- [ ] Add troubleshooting guide
- [ ] Document Azure setup in detail (screenshots)
- [ ] Add performance tuning guide
- [ ] Document rate limits and quotas
- [ ] Add migration guide (if breaking changes)
- [ ] Add FAQ section
- [ ] Update examples with real-world use cases

**Acceptance Criteria:**
- Complete Azure setup guide for new users
- Clear documentation of limitations
- Examples cover common use cases

### 6.4 Example Applications 💡
**New directory:** `examples/`

- [ ] Add batch conversion script
- [ ] Add CLI wrapper example
- [ ] Add FastAPI integration example
- [ ] Add error handling examples
- [ ] Add progress tracking example

**Acceptance Criteria:**
- Working examples for common scenarios
- Examples demonstrate best practices

## Phase 7: Release Preparation

### 7.1 Security Audit 🔒
**All files**

- [ ] Review secret handling (no secrets in logs)
- [ ] Review file path validation (prevent directory traversal)
- [ ] Review error messages (no sensitive data leakage)
- [ ] Add security documentation
- [ ] Run bandit security linter

**Acceptance Criteria:**
- No secrets in logs or error messages
- Secure file path handling
- Security best practices documented

### 7.2 Package Publishing 📦
**Files:** `pyproject.toml`, `README.md`

- [ ] Test package building with `uv build`
- [ ] Test package installation from wheel
- [ ] Set up PyPI account/token
- [ ] Configure GitHub Actions for publishing
- [ ] Create release checklist
- [ ] Tag v0.1.0 release

**Acceptance Criteria:**
- Package builds successfully
- Package installable via pip
- Automated publishing on tagged releases

### 7.3 Versioning & Changelog 📋
**New file:** `CHANGELOG.md`

- [ ] Create CHANGELOG.md following Keep a Changelog
- [ ] Document version 0.1.0 features
- [ ] Set up semantic versioning strategy
- [ ] Add version bump automation

**Acceptance Criteria:**
- Clear changelog for users
- Semantic versioning followed
- Release notes template

## Future Enhancements (Post-v0.1.0)

### Delegated Authentication
- [ ] Support delegated (user) authentication flow
- [ ] Add OAuth device code flow for CLI apps
- [ ] Add OAuth web flow for web apps

### Advanced Features
- [ ] Add batch conversion support (multiple files)
- [ ] Add conversion options (page range, quality)
- [ ] Add support for other cloud storage (Google Drive, Dropbox)
- [ ] Add local LibreOffice fallback option
- [ ] Add conversion job queueing for high volume

### Developer Experience
- [ ] Add async context manager for batch operations
- [ ] Add progress callbacks for long-running conversions
- [ ] Add conversion caching (hash-based deduplication)
- [ ] Add webhook support for async conversions

---

## Priority Order

**Must Have (v0.1.0):**
1. Phase 1: Core Graph API Integration
2. Phase 2: File Upload Implementation
3. Phase 3: PDF Conversion
4. Phase 4: Cleanup Implementation
5. Phase 5: Robustness & Production Readiness
6. Phase 6.1: Integration Tests

**Should Have (v0.2.0):**
7. Phase 6.2-6.4: Performance Testing, Docs, Examples
8. Phase 7: Release Preparation

**Nice to Have (Future):**
9. Future Enhancements

---

## Getting Started

To start development:

```bash
# Set up test Azure tenant
# See: https://learn.microsoft.com/azure/active-directory/develop/quickstart-create-new-tenant

# Configure test credentials
export AZURE_TENANT_ID="your-test-tenant"
export AZURE_CLIENT_ID="your-test-app"
export AZURE_CLIENT_SECRET="your-test-secret"

# Run integration tests
uv run pytest tests/integration -v

# Start with Phase 1.1: Authentication Flow
```

## Notes

- Each phase should include unit tests
- Integration tests run only when credentials available
- Keep backward compatibility after v1.0.0
- Security is paramount (never log secrets)
