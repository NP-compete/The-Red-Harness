# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| latest  | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Use [GitHub's private vulnerability reporting](https://github.com/redhat-data-and-ai/template-agent/security/advisories/new) to submit the details.
3. Include steps to reproduce, impact assessment, and any suggested fix.

We aim to acknowledge reports within 48 hours and provide a fix or mitigation within 7 days for critical issues.

## Signed commits

Every commit on `main` carries a signature GitHub can verify. The
branch rule enforces it, so an unsigned or unverifiable commit is
refused at push time rather than noticed later.

Set it up once, with the SSH key you already push with:

```sh
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

Then register that **same key a second time**, as a *signing* key:

```sh
gh auth refresh -h github.com -s admin:ssh_signing_key
gh api user/ssh_signing_keys -f title="$(hostname)" \
  -f key="$(cat ~/.ssh/id_ed25519.pub)"
```

or paste it at <https://github.com/settings/keys> under *New SSH
key* with the type set to **Signing Key**.

The second step is the one that is easy to miss and gives the
least helpful error. An authentication key and a signing key are
separate entries on a GitHub account even when they are the same
key: without the signing entry, `git log --show-signature` is
happy locally, the commit carries a real signature, and GitHub
still reports `verified=false reason=unknown_key` — and the push
is refused with nothing on screen explaining which of the two
things is missing.

To check before you push:

```sh
git log --format='%h %G? %s' -5      # G is good, N is unsigned
```

`%G?` reads `N` until `gpg.ssh.allowedSignersFile` exists, which is
a local verification setting and separate again from both of the
above:

```sh
printf '%s %s\n' "$(git config user.email)" \
  "$(cat ~/.ssh/id_ed25519.pub)" > ~/.config/git/allowed_signers
git config --global gpg.ssh.allowedSignersFile ~/.config/git/allowed_signers
```

## Branch and tag rules

`.github/required-checks.yml` is the declaration; the rules are
generated from it by `scripts/ci/protect_main.py`.

```sh
make protect-check   # do the live rules match the file?
make protect         # make them match
```

`Branch Rules` compares the two nightly. Changing protection in
the browser is how the declaration and reality drift apart, and
that job exists to make the drift visible rather than permanent.

## Security Measures

This project uses the following automated security tooling:

- **Trivy** -- container image vulnerability scanning on every build
- **Bandit** -- Python SAST via pre-commit
- **CodeQL** -- GitHub's semantic code analysis on every PR and weekly
- **Dependabot** -- automated dependency updates for pip, Docker, and GitHub Actions
- **Dependency Review** -- blocks PRs that introduce dependencies with known high/critical CVEs
- **OpenSSF Scorecard** -- weekly supply chain security health assessment
- **Cosign** -- keyless image signing for provenance verification
- **SBOM** -- CycloneDX bill of materials generated with every image build
