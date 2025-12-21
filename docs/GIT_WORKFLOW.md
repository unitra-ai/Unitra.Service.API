# Git Workflow Guide

This document describes the Git workflow for the Unitra project.

## Workflow: GitHub Flow

We use a simplified GitHub Flow:

```
main ─────●────────●────────────●────────────●──────▶
          │        ▲            │            ▲
          │        │            │            │
          │    ┌───┴───┐        │        ┌───┴───┐
          │    │ Merge │        │        │ Merge │
          │    │  PR   │        │        │  PR   │
          │    └───────┘        │        └───────┘
          │        ▲            │            ▲
          │        │            │            │
feature ──┴────●───●            │            │
                   │            │            │
                   │            │            │
another ───────────┴────●───────┴────●───────●
feature
```

- `main` is always deployable
- All work happens in feature branches
- PRs require review before merging
- Squash merge to keep history clean

---

## Branch Naming Convention

**Pattern**: `<type>/<ticket>-<short-description>`

### Types

| Type | Description |
|------|-------------|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `hotfix/` | Urgent production fixes |
| `refactor/` | Code refactoring |
| `docs/` | Documentation only |
| `test/` | Adding tests |
| `chore/` | Maintenance tasks |
| `perf/` | Performance improvements |

### Examples

```bash
feature/W1-S01-fastapi-setup
fix/W2-C03-vad-threshold
hotfix/auth-token-expiry
refactor/client-audio-pipeline
docs/api-documentation
chore/update-dependencies
```

### Rules

- Use **lowercase**
- Use **hyphens** (not underscores)
- Keep it short but descriptive
- Include ticket ID when applicable

---

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description | Version Bump |
|------|-------------|--------------|
| `feat` | New feature | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation only | - |
| `style` | Formatting, no code change | - |
| `refactor` | Code change, no new feature or fix | - |
| `perf` | Performance improvement | - |
| `test` | Adding tests | - |
| `build` | Build system or dependencies | - |
| `ci` | CI configuration | - |
| `chore` | Other maintenance | - |

### Scopes (Optional)

| Scope | Description |
|-------|-------------|
| `api` | API endpoints |
| `auth` | Authentication |
| `billing` | Billing/Stripe |
| `usage` | Usage tracking |
| `translate` | Translation service |
| `db` | Database |
| `deps` | Dependencies |
| `ci` | CI/CD |
| `docker` | Docker configuration |

### Examples

```bash
# Simple feature
feat(auth): add JWT refresh token rotation

# Bug fix with body
fix(api): resolve 500 error on empty translation request

The endpoint was not validating empty text input,
causing a NoneType error in the translation service.

Closes #123

# Breaking change
feat(api)!: change translation response format

BREAKING CHANGE: Response now wraps data in `data` field.
Migration: Update client to access `response.data.translation`

# Chore
chore(deps): update FastAPI to v0.110.0
```

---

## Pull Request Process

### 1. Create Branch

```bash
git checkout main
git pull origin main
git checkout -b feature/W1-S01-fastapi-setup
```

### 2. Develop & Commit

- Make small, focused commits
- Follow conventional commit messages
- Push regularly

```bash
git add .
git commit -m "feat(api): add health check endpoint"
git push -u origin feature/W1-S01-fastapi-setup
```

### 3. Create Pull Request

- Use the PR template
- Link to related issues
- Add appropriate labels
- Request review

### 4. Code Review

- Reviewer checks code quality, tests, documentation
- Use "Request changes" or "Approve"
- Author addresses feedback
- Re-request review after changes

### 5. CI Checks

All checks must pass:
- Lint & Format (black, ruff, mypy)
- Unit Tests
- Build
- Security Scan

### 6. Merge

- Use **"Squash and merge"** (default)
- Clean up commit message
- Delete branch after merge

---

## Code Review Guidelines

### Reviewer Responsibilities

- **Correctness**: Does the code do what it claims?
- **Design**: Is it well-structured and maintainable?
- **Readability**: Can you understand it easily?
- **Tests**: Are there adequate tests?
- **Documentation**: Are comments and docs updated?
- **Security**: Any potential security issues?
- **Performance**: Any obvious performance concerns?

### Review Etiquette

**Do:**
- Be kind and constructive
- Explain why, not just what
- Offer suggestions, not demands
- Acknowledge good work
- Respond promptly (within 24 hours)

**Don't:**
- Be nitpicky about style (use linters)
- Request changes for personal preference
- Leave vague comments
- Let PRs sit for days

### Comment Prefixes

| Prefix | Meaning |
|--------|---------|
| `[blocking]` | Must be fixed before merge |
| `[nit]` | Minor suggestion, non-blocking |
| `[question]` | Request for clarification |
| `[suggestion]` | Optional improvement idea |
| `[praise]` | Something done well |

**Examples:**

```
[blocking] This could cause a SQL injection. Use parameterized queries.

[nit] Consider renaming `x` to `user_count` for clarity.

[praise] Great test coverage on this edge case!
```

---

## Release Process

### Versioning: Semantic Versioning (SemVer)

Format: `MAJOR.MINOR.PATCH`

| Change | Version Bump | Example |
|--------|--------------|---------|
| Breaking changes | MAJOR | 1.0.0 → 2.0.0 |
| New features (backward compatible) | MINOR | 1.0.0 → 1.1.0 |
| Bug fixes (backward compatible) | PATCH | 1.0.0 → 1.0.1 |

Pre-release: `v0.1.0-beta.1`, `v0.1.0-rc.1`

### Release Workflow

1. **Ensure main is stable**
   - All tests passing
   - Staging verified

2. **Update version**
   - `pyproject.toml`

3. **Update CHANGELOG.md**
   - Document all changes since last release

4. **Create release commit**
   ```bash
   git commit -m "chore: release v0.1.0"
   ```

5. **Tag release**
   ```bash
   git tag -a v0.1.0 -m "Release v0.1.0"
   git push origin v0.1.0
   ```

6. **GitHub Release**
   - CI creates draft release
   - Add release notes
   - Publish (triggers production deploy)

### Hotfix Process

1. Create hotfix branch from main
   ```bash
   git checkout -b hotfix/critical-bug main
   ```

2. Fix the issue (minimal changes)

3. Create PR (expedited review)

4. Merge and tag patch release
   ```bash
   # v0.1.0 → v0.1.1
   ```

5. Deploy immediately

---

## Repository Settings

### Branch Protection (main)

- Require pull request before merging
- Require 1 approval
- Require status checks to pass
- Require branches to be up to date
- Do not allow force pushes
- Do not allow deletions

### Merge Settings

- Allow squash merging (default)
- Disable merge commits
- Disable rebase merging
- Auto-delete head branches

---

## Quick Reference

```bash
# Start new feature
git checkout main && git pull
git checkout -b feature/my-feature

# Commit changes
git add .
git commit -m "feat(scope): description"

# Push and create PR
git push -u origin feature/my-feature
# Then create PR on GitHub

# After PR merged, cleanup
git checkout main && git pull
git branch -d feature/my-feature
```
