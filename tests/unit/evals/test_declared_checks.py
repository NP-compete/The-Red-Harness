"""E22-T1. Checks declared in the config tree rather than in code."""

from __future__ import annotations

import textwrap

import pytest

from agent.src.evals.declared import declared_registry, load_checks

GOOD = textwrap.dedent("""\
    name: safety-one
    group: safety
    decides: block the release
    judge: gemini-3.8-flash
    dataset: data.json
    cases: [1]
""")


@pytest.fixture
def root(tmp_path):
    (tmp_path / "evals" / "checks").mkdir(parents=True)
    (tmp_path / "data.json").write_text("{}")
    return tmp_path


def write(root, name, body=GOOD):
    (root / "evals" / "checks" / name).write_text(body)
    return root


def test_a_well_formed_check_loads(root):
    write(root, "a.yaml")
    checks, problems = load_checks(root)
    assert problems == []
    assert checks[0].name == "safety-one"
    assert checks[0].cases == (1,)
    assert checks[0].source == "evals/checks/a.yaml"


def test_no_checks_directory_is_not_an_error(root):
    """A deployment that declares none has none, not a failure."""
    (root / "evals" / "checks").rmdir()
    assert load_checks(root) == ([], [])


@pytest.mark.parametrize("field", ["name", "group", "decides"])
def test_a_check_missing_a_required_field_is_refused(root, field):
    body = "\n".join(line for line in GOOD.splitlines() if not line.startswith(field))
    write(root, "a.yaml", body + "\n")
    checks, problems = load_checks(root)
    assert checks == []
    assert field in problems[0]["what"]


def test_decides_is_the_one_that_matters(root):
    """A check informing no decision is a number nobody acts on."""
    write(root, "a.yaml", GOOD.replace("decides: block the release", "decides: '  '"))
    checks, problems = load_checks(root)
    assert checks == []
    assert "decides" in problems[0]["what"]


def test_a_missing_dataset_is_reported_but_the_check_still_loads(root):
    write(root, "a.yaml", GOOD.replace("dataset: data.json", "dataset: gone.json"))
    checks, problems = load_checks(root)
    assert len(checks) == 1
    assert "gone.json" in problems[0]["what"]


def test_two_checks_with_one_name_do_not_silently_overwrite(root):
    write(root, "a.yaml")
    write(root, "b.yaml")
    checks, problems = load_checks(root)
    assert len(checks) == 1
    assert "duplicate name" in problems[0]["what"]


def test_one_unparseable_file_does_not_empty_the_library(root):
    write(root, "a.yaml")
    write(root, "b.yaml", "name: [unclosed\n")
    checks, problems = load_checks(root)
    assert [c.name for c in checks] == ["safety-one"]
    assert len(problems) == 1


def test_the_registry_is_built_and_counts_runs(root):
    write(root, "a.yaml")
    registry, problems = declared_registry(root)
    assert problems == []
    assert registry.unused() == ("safety-one",)
    registry.record_run("safety-one")
    assert registry.usage()["safety-one"] == 1
    assert registry.unused() == ()


def test_a_check_can_name_the_integrations_its_cases_need(root):
    write(root, "a.yaml", GOOD + "needs: [gworkspace, gitlab]\n")
    checks, problems = load_checks(root)
    assert problems == []
    assert checks[0].needs == ("gworkspace", "gitlab")


def test_naming_no_integration_is_the_normal_case(root):
    write(root, "a.yaml")
    checks, _ = load_checks(root)
    assert checks[0].needs == ()


def test_the_shipped_tree_declares_checks_that_load():
    """The configuration this repo ships must itself be valid."""
    from agent.src.agent.config.paths import config_root

    checks, problems = load_checks(config_root())
    assert problems == [], problems
    assert len(checks) >= 3
    assert all(c.dataset for c in checks), "every check needs a dataset"
    judged = [c for c in checks if c.kind == "judged"]
    assert all(c.dataset and c.cases for c in judged), (
        "a judged check pointed at a whole dataset scores assertions that "
        "are not about it; name the cases"
    )
