# Contributing

## Branching Strategy

Use short-lived branches and merge to `main` through pull requests.

- Create a branch from `main`:
  - `feat/<short-description>`
  - `fix/<short-description>`
  - `chore/<short-description>`
- Keep changes focused and small.
- Open a pull request early.
- Merge only after checks and review pass.

## Recommended Local Flow

1. Sync local `main`:
   - `git checkout main`
   - `git pull --rebase origin main`
2. Create your branch:
   - `git checkout -b feat/my-change`
3. Install local git hooks once per clone:
   - `make install-hooks`
4. Implement and commit with clear messages.
5. Run local checks before pushing:
   - `make test`
   - `make health` (when app is running)
   - `make check-paths`
6. Push branch and open PR to `main`.

## Pull Request Requirements

- CI checks are green.
- At least one human review approval.
- Scope is limited to one concern.
- Security-sensitive or config changes are called out explicitly.

## AI-Assisted Code Policy

AI tools (Copilot/agents) are allowed, but all generated code must be reviewed by a human.

Before merge:

- Validate behavior manually for changed paths.
- Ensure tests/checks cover the change.
- Confirm no secrets or tokens were introduced.
- Include a short note in PR about what AI-assisted portions were reviewed.

## Branch Protection (Repository Settings)

Configure GitHub branch protection for `main`:

- Require pull requests before merging.
- Require status checks to pass before merging.
- Require at least 1 approving review.
- Dismiss stale approvals when new commits are pushed.
- Restrict direct pushes to `main`.

## If You Commit to main by Mistake

If the commit is local and not yet pushed, move it safely to a feature branch:

```bash
git checkout -b feat/workflow-hardening
git checkout main
git fetch origin
git reset --hard origin/main
```

This keeps your work on the feature branch and restores local `main` to match remote.
