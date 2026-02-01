# Claude Development Guide for office2pdf

This file contains project-specific instructions for AI assistants working on this codebase.

## Testing Workflow

**CRITICAL: Always follow this pattern for new feature development:**

1. **Write Live Integration Tests First**
   - Create tests in `tests/integration/` that use real Microsoft Graph API
   - Tests MUST skip if credentials not available (use `pytest.mark.skipif`)
   - Required environment variables: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
   - These tests are for **debugging and observing actual API behavior**

2. **Run Live Tests and Iterate**
   - **Actually run the tests** with real credentials to validate behavior
   - Debug issues against the live API
   - Observe actual response structures, error messages, edge cases
   - Document unexpected behaviors or quirks

3. **Develop Fixtures/Fakes from Observed Behavior**
   - Based on what you learned from live tests, create realistic mocks
   - Copy actual response structures from live API calls
   - Include real error messages and edge cases you observed

4. **Write Unit Tests with Fixtures**
   - Create fast unit tests in `tests/` that use the fixtures/fakes
   - These tests run without network access (no credentials needed)
   - Should have high coverage of edge cases discovered during live testing
   - Must pass in CI without credentials

**Never skip step 2!** Don't write unit tests based on assumptions. Always validate against the real API first.

## Code Organization

- **Src Layout**: Use `src/office2pdf/` for all package code
- **Public API**: Only export in `__all__` what users should import directly
- **Namespaced Config**: Users should use `office2pdf.Config`, not import Config directly

## Code Quality Standards

### Type Safety
- Use pyright in strict mode
- All functions must have type annotations
- No `type: ignore` comments without explanation

### Linting
- Ruff configured with maximally strict rules
- Run `uv run ruff format` before committing
- Run `uv run ruff check --fix` to auto-fix issues

### Error Handling
- Raise specific exceptions from `office2pdf.errors`
- Include helpful error messages with context
- For Graph API errors, include error codes from response

## Git Workflow

### Branch Naming
- Use descriptive branch names: `phase-X.Y-feature-name`
- Example: `phase-1.1-authentication-flow`

### Commit Messages
- Use conventional commit style
- Include "why" not just "what"
- End with Claude Code attribution:
  ```
  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
  ```

### Pull Requests
- One PR per sub-phase (e.g., Phase 1.1, Phase 1.2)
- Include test results in PR description
- Update TODO.md to mark completed items with ✅
- **Use the `submit-pr` skill** for complete PR workflow:
  - Thorough code review before submission
  - Fix all identified issues
  - Open PR and monitor continuously
  - Respond to comments and keep tests passing
  - Continue until merged

## Testing Best Practices

### Integration Tests
- Skip if credentials not available
- Test against real Microsoft Graph API
- Print useful debugging info (like token expiration or response keys), but avoid printing raw tokens or other secrets
- Use descriptive test names that explain what's being validated

### Unit Tests
- Use pytest fixtures for mocks
- Mock at the MSAL library boundary (`msal.ConfidentialClientApplication`)
- Test both success and error paths
- Include edge cases (expired tokens, invalid responses, missing fields)

### Test Organization
```
tests/
  integration/          # Live API tests (require credentials)
    __init__.py        # Documents required env vars
    test_*_live.py     # Integration tests
  test_*.py            # Unit tests (run in CI)
```

## Common Patterns

### Async Context Managers
```python
async with OfficeToPdf(config) as client:
    pdf_bytes = await client.convert_to_pdf(file_bytes, "document.docx")
```

### Error Handling
```python
try:
    result = await operation()
except AuthenticationError as e:
    logger.error(f"Auth failed: {e}")
    raise
```

### Token Refresh
- Always check token validity before use
- Refresh tokens 5 minutes before expiry (buffer)
- Cache tokens to minimize API calls

## Documentation

- Keep README.md user-focused
- Keep TODO.md updated with progress
- Document Azure setup requirements
- Include code examples for common use cases

## Security

- **Never log secrets** (access tokens, client secrets)
- Validate file paths to prevent directory traversal
- Don't include sensitive data in error messages
- Run `bandit` security linter before releases

## Performance

- Stream large files (don't load fully into memory)
- Use chunked uploads for files ≥ 4MB
- Respect rate limits (429 responses)
- Implement exponential backoff for retries
