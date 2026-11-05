"""E26-T6 and T7, asserted rather than reviewed."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOWS = sorted((Path(__file__).parents[2] / ".github" / "workflows").glob("*.y*ml"))

ON_KEY = True

_SECRET = re.compile(r"secrets\.([A-Za-z_][A-Za-z0-9_]*)")
ALLOWED_FORK_SECRETS = {"GITHUB_TOKEN"}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def _triggers(doc: dict) -> set[str]:
    on = doc.get(ON_KEY, doc.get("on"))
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return set(on)
    if isinstance(on, dict):
        return set(on)
    return set()


def test_there_are_workflows_to_check():
    """A path typo here would make every test below vacuously pass."""
    assert WORKFLOWS, "no workflow files found"


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_workflow_declares_permissions(path: Path):
    doc = _load(path)
    jobs = doc.get("jobs") or {}
    top = "permissions" in doc
    assert top or all("permissions" in j for j in jobs.values()), (
        f"{path.name} inherits the repository default; declare "
        "`permissions:` at the workflow or on every job"
    )


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_pull_request_target(path: Path):
    assert "pull_request_target" not in _triggers(_load(path)), (
        f"{path.name} uses pull_request_target: the fork's code would run "
        "with this repository's secrets"
    )


FORK_GUARD = "github.event.pull_request.head.repo.fork != true"


def _secrets_in(obj) -> set[str]:
    return set(_SECRET.findall(yaml.safe_dump(obj))) - ALLOWED_FORK_SECRETS


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_a_fork_triggered_workflow_reads_no_secret(path: Path):
    """Per step, because a guarded step is genuinely unreachable."""
    doc = _load(path)
    if "pull_request" not in _triggers(doc):
        return

    exposed: dict[str, list[str]] = {}
    for job_name, job in (doc.get("jobs") or {}).items():
        job_guarded = FORK_GUARD in str(job.get("if", ""))
        for step in job.get("steps") or []:
            if job_guarded or FORK_GUARD in str(step.get("if", "")):
                continue
            found = _secrets_in(step)
            if found:
                exposed[f"{job_name}.{step.get('name', '?')}"] = sorted(found)

    assert not exposed, (
        f"{path.name} runs on pull_request, which fires on forks, and these "
        f"steps read a secret without the fork guard: {exposed}. Add "
        f"`if: {FORK_GUARD}`, or move the step to a post-merge job."
    )


_PINNED = re.compile(r"@[0-9a-f]{40}$")
_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.M)


def _external_uses(path: Path) -> list[str]:
    """Actions this workflow pulls from elsewhere."""
    found = []
    for match in _USES.finditer(path.read_text()):
        reference = match.group(1).strip("\"'")
        if not reference.startswith("./"):
            found.append(reference)
    return found


def test_there_are_actions_to_check():
    """Pattern 5 again: no `uses:` found means no rule applied."""
    total = sum(len(_external_uses(path)) for path in WORKFLOWS)
    assert total >= 20, total


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_every_action_is_pinned_to_a_sha(path: Path):
    loose = [one for one in _external_uses(path) if not _PINNED.search(one)]
    assert not loose, (
        f"{path.name} pulls {loose} by tag or branch. A tag is a pointer the "
        "action's owner can move, and it runs here with this workflow's "
        "permissions. Pin it to the 40-character commit SHA; Dependabot "
        "bumps SHA-pinned actions and leaves the comment naming the version."
    )


RELEASE_WORKFLOW = (
    Path(__file__).parents[2] / ".github" / "workflows" / ("build-base-image.yml")
)


def test_the_release_workflow_is_there():
    assert RELEASE_WORKFLOW.is_file()


def _release_steps() -> list[dict]:
    doc = yaml.safe_load(RELEASE_WORKFLOW.read_text()) or {}
    return [
        step
        for job in (doc.get("jobs") or {}).values()
        for step in (job.get("steps") or [])
    ]


def test_every_release_artefact_is_checked_by_one_hard_step():
    """One gate, after all three, that cannot be skipped."""
    gates = [
        step
        for step in _release_steps()
        if not step.get("continue-on-error") and "missing" in str(step.get("run", ""))
    ]
    assert gates, (
        "no step fails the release when the signature, the SBOM or the "
        "provenance is absent"
    )
    script = str(gates[0]["run"])
    for artefact in ("signature", "sbom", "provenance"):
        assert artefact in script, f"the gate does not mention {artefact}"


def test_the_gate_itself_may_not_be_soft():
    gates = [
        step
        for step in _release_steps()
        if "CI-6 requires all three" in str(step.get("run", ""))
    ]
    assert gates, "the gate has been renamed or removed"
    assert not gates[0].get("continue-on-error"), (
        "the step that enforces CI-6 is itself continue-on-error, which is "
        "the same hole one level up"
    )
