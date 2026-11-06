## What

<!-- One or two sentences: what changed and why. Link the issue. -->

Fixes #

## How

<!-- Describe your approach. Call out non-obvious design decisions, trade-offs, or alternatives you considered. -->

## Testing

<!-- How did you verify this works? -->

- [ ] Unit tests added/updated
- [ ] Ran locally (`make test`) — `tests/unit` alone is no longer the suite
- [ ] Manual verification (describe below if applicable)

## Rollback

<!-- How would you revert this if it breaks production? "Revert the commit" is fine for most changes. -->

## Checklist

- [ ] PR title follows [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `ci:`, etc.)
- [ ] No secrets, credentials, or PII in the diff
- [ ] No breaking changes (or documented above with a migration path)
- [ ] Pre-commit hooks pass (`make pre-commit`)
- [ ] Checks pass (`make ci`, or `make check NAME=<job>` for one)
