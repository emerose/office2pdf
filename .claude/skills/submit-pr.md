---
description: Submit a PR with thorough review, fixes, and continuous monitoring
---

# Submit PR Skill

This skill handles the complete PR submission workflow: code review, fixes, submission, and monitoring until merge.

## Phase 1: Thorough Code Review

Before opening the PR, conduct a comprehensive code review of all changes:

### 1.1 Review Scope
- Run `git diff main...HEAD --stat` to see all changed files
- Read each changed file in full (use `git diff main...HEAD` for context)
- Review both the changes AND the surrounding code for context

### 1.2 Code Correctness
- **Logic**: Are algorithms correct? Edge cases handled?
- **Type Safety**: All functions properly typed? No unsafe casts?
- **Error Handling**: Appropriate exceptions? Good error messages?
- **Async Safety**: Proper async/await usage? Resource cleanup?
- **Security**: No secrets logged? Input validation? Path traversal prevention?

### 1.3 Code Quality
- **Elegance**: Is the code clean and readable?
- **Naming**: Are names descriptive and follow conventions?
- **Structure**: Appropriate abstraction levels? Good separation of concerns?
- **DRY**: No unnecessary duplication?
- **SOLID**: Following good design principles?

### 1.4 Testing
- **Coverage**: All new code paths tested?
- **Live Tests**: Were integration tests run against real API?
- **Unit Tests**: Based on observed behavior or assumptions?
- **Edge Cases**: Unusual inputs, errors, boundary conditions tested?
- **Test Quality**: Tests clear, maintainable, not brittle?

### 1.5 Documentation
- **Docstrings**: All public functions documented?
- **Comments**: Complex logic explained?
- **README**: Updated if public API changed?
- **Examples**: Clear examples for new features?
- **CHANGELOG**: Changes documented appropriately?

### 1.6 Project Standards
- **CLAUDE.md**: Following all project guidelines?
- **TODO.md**: Acceptance criteria met? Items marked complete?
- **Coding Style**: Consistent with existing code?
- **Dependencies**: New dependencies justified and minimal?

### 1.7 Create Review Report
After review, create a detailed report with:
- **Summary**: Overall assessment (Ready / Needs Work)
- **Strengths**: What's done well
- **Issues Found**: Categorized by severity (Critical / Important / Minor)
- **Recommendations**: Suggested improvements

## Phase 2: Fix All Issues

For each issue identified in the code review:

1. **Prioritize**: Fix Critical issues first, then Important, then Minor
2. **Fix Systematically**: Address each issue completely
3. **Verify**: Run tests after each fix
4. **Document**: Note what was changed and why

After all fixes:
- Run full test suite: `uv run pytest -v`
- Run linting: `uv run ruff check --fix && uv run ruff format`
- Run type checking: `uv run pyright`
- Verify all checks pass locally

## Phase 3: Open the PR

### 3.1 Prepare PR
- **Update TODO.md**:
  - Mark items completed in this PR with ✅
  - Add PR number reference (will be added after PR created, can add in follow-up commit)
  - Ensure all previous phases are marked complete
  - Example: Change `- [ ] Test token acquisition` to `- [x] Test token acquisition (PR #3)`
- Ensure all changes committed
- Push branch: `git push -u origin <branch-name>`
- Check current branch tracking: `git branch -vv`

### 3.2 Create PR
Use `gh pr create` with:

**Title Format**: `Phase X.Y: <Feature Name>`

**Body Structure**:
```markdown
## Summary
Brief overview of what this PR does and why.

## Changes
Detailed list of changes, grouped by category:
- **Core Implementation**: Main feature changes
- **Tests**: New test coverage
- **Documentation**: Docs updates
- **Other**: Misc changes

## Testing
Results from running tests:
- Live integration tests (with/without credentials)
- Unit tests
- Linting and type checking

## Changelog
<!--
Describe changes in a user-friendly way for the changelog.
Example:
- **Added**: Support for converting PPTX files.
- **Fixed**: A bug in token refresh logic.
-->

## Acceptance Criteria
Checklist from TODO.md for this phase, with ✅ for completed items.

## Review Notes
Any specific areas that need extra attention or decisions to be made.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

### 3.3 Initial Checks
After PR created:
- Run `gh pr checks` to monitor CI status
- If any checks fail, investigate and fix immediately
- Verify PR description renders correctly: `gh pr view --web`

## Phase 4: Monitor and Respond

### 4.1 Continuous Monitoring
**Actively poll** the PR status - don't passively wait for updates:

**Use sleep commands to check periodically:**
- `sleep 20 && gh pr checks` - Check CI status every 20-30 seconds
- `sleep 20 && gh api repos/{owner}/{repo}/issues/{pr_number}/comments` - Check for new comments
- `sleep 20 && gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews` - Check for reviews

**Example polling loop pattern:**
```bash
# Poll until CI checks are complete
echo "Waiting for CI checks..."
until gh pr checks --exit-status; do
  sleep 15
done
echo "CI checks complete!"

# Poll until Gemini review is found
echo "Waiting for Gemini review..."
until gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq 'any(.user.login == "gemini-code-assist[bot]")' | grep -q true; do
  sleep 20
done
echo "Gemini review found!"
```

**IMPORTANT**: Always use `sleep` + command, never just stop and wait. Continue checking until you get the information you need.

### 4.2 Respond to CI Failures
If CI fails:
1. Get logs: `gh run view <run-id> --log-failed`
2. Analyze failure root cause
3. Fix the issue locally
4. Run tests locally to verify fix
5. Commit and push fix
6. Monitor until CI passes

### 4.3 Wait for Gemini Code Review
**IMPORTANT**: The gemini-code-assist bot will automatically review all PRs. You MUST wait for Gemini to complete its review before considering the PR done.

**Gemini Review Process**:
1. **Initial Summary**: Gemini will first post a "summary of changes" comment
   - This is just acknowledging the PR, not the actual review
   - Continue waiting after seeing this

2. **Actual Code Review**: Gemini will then perform its code review
   - If it finds issues: Gemini will add review comments on specific lines
   - If no issues: Gemini will post a comment saying nothing needs to change

3. **How to Monitor**:
   - **CRITICAL**: Use `sleep` commands and actively poll for comments - don't just stop waiting
   - Check periodically (every 20-30 seconds) using:
     - `sleep 20 && gh api repos/{owner}/{repo}/issues/{pr_number}/comments --jq '.[] | select(.user.login == "gemini-code-assist[bot]") | {created_at, body: .body | .[0:200]}'`
     - `sleep 20 && gh api repos/{owner}/{repo}/pulls/{pr_number}/reviews --jq '.[] | select(.user.login == "gemini-code-assist[bot]") | {submitted_at, state, body}'`
   - Continue polling until you see Gemini's review
   - Typically Gemini responds within 30-60 seconds of PR creation
   - **Do not passively wait** - actively check in a loop until review appears

4. **When Gemini Finds Issues**:
   - Read all of Gemini's comments carefully
   - Address each issue systematically (same as human review comments)
   - Make the requested changes
   - Push the fixes
   - Wait for Gemini to re-review if needed

5. **When Gemini Approves**:
   - Gemini will indicate no changes needed or approve the PR
   - Only then proceed to the next phase

**Do not skip this step!** Gemini's automated review often catches issues that were missed in the initial code review. Wait for Gemini to finish before proceeding.

### 4.4 Respond to Review Comments (Human and Gemini)
For each review comment:
1. **Read Carefully**: Understand the concern/question
2. **Acknowledge**: Post a response indicating you're addressing it
3. **Decide Action**:
   - If it's a good suggestion: Implement the change
   - If it's a question: Provide clear explanation
   - If you disagree: Explain reasoning respectfully
4. **Make Changes**: If code changes needed
5. **Reply**: Comment on the thread indicating what you did
6. **Resolve**: Mark conversation as resolved (if appropriate)

**Response Template**:
```markdown
Good catch! [Explanation of the issue]

Fixed in [commit-sha]:
- [What was changed]
- [Why this approach]

[Additional context if needed]
```

### 4.5 Request Re-review
After addressing comments:
- Comment on PR: "All comments addressed, ready for re-review"
- Use `gh pr comment` to add summary of changes made
- Be patient and continue monitoring

### 4.6 Keep Monitoring Until Merged
Continue the cycle:
1. Check for new comments every few hours
2. Respond promptly to feedback (both Gemini and human reviewers)
3. Keep CI green
4. Address any merge conflicts if base branch updates
5. Ensure Gemini review is complete and all issues addressed
6. Continue until PR is approved and merged

## Phase 5: Post-Merge Cleanup

After PR is merged:
1. Switch back to main: `git checkout main`
2. Pull latest: `git pull origin main`
3. Delete local branch: `git branch -d <branch-name>`
4. Delete remote branch (if not auto-deleted): `git push origin --delete <branch-name>`
5. Update TODO.md if needed (mark phase complete)

## Key Principles

1. **Be Thorough**: Don't rush the code review
2. **Be Responsive**: Address feedback quickly
3. **Be Collaborative**: Accept feedback gracefully
4. **Be Persistent**: Keep monitoring until merge
5. **Be Professional**: Clear communication, respectful tone

## Usage

Invoke this skill when:
- You've completed work on a feature branch
- You're ready to submit a PR for review
- You want to ensure high quality before requesting human review

Example:
```
User: "Run the submit-pr skill"
Claude: [Executes full workflow from code review through monitoring]
```

## Notes

- This skill may take multiple conversation turns to complete
- Stay engaged throughout the process
- Don't consider the task done until PR is merged
- Learn from review feedback to improve future PRs
