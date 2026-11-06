"""A skill whose own file cannot be read says so."""

from __future__ import annotations

import pytest

from agent.aegra import skill_routes


def _skill(tmp_path, name: str, body: str | None) -> None:
    folder = tmp_path / name
    folder.mkdir()
    if body is not None:
        (folder / "SKILL.md").write_text(body)


GOOD = "---\ndescription: Finds a dataset.\n---\n\nBody.\n"
BROKEN = "---\ndescription: [unclosed\n  - : :\n---\n\nBody.\n"


@pytest.fixture
def listing(tmp_path, monkeypatch):
    async def run(names: dict[str, str | None]):
        for name, body in names.items():
            _skill(tmp_path, name, body)

        from agent.src.agent.config import agent_config

        monkeypatch.setattr(
            agent_config,
            "get_available_skills",
            lambda: {name: tmp_path / name for name in names},
        )
        monkeypatch.setattr(agent_config, "get_orchestrator_config", lambda: {})
        monkeypatch.setattr(agent_config, "get_all_subagent_configs", lambda: {})
        found = await skill_routes.list_skills()
        return {skill["name"]: skill for skill in found["skills"]}

    return run


@pytest.mark.asyncio
async def test_a_readable_skill_reports_no_problem(listing):
    skills = await listing({"good": GOOD})
    assert skills["good"]["problem"] == ""


@pytest.mark.asyncio
async def test_a_readable_skill_keeps_its_description(listing):
    skills = await listing({"good": GOOD})
    assert skills["good"]["description"] == "Finds a dataset."


@pytest.mark.asyncio
async def test_a_skill_with_no_file_says_so(listing):
    skills = await listing({"empty": None})
    assert "SKILL.md" in skills["empty"]["problem"]


@pytest.mark.asyncio
async def test_a_malformed_skill_says_so_rather_than_looking_undescribed(listing):
    skills = await listing({"broken": BROKEN})
    assert skills["broken"]["problem"]
    assert skills["broken"]["description"] == ""


@pytest.mark.asyncio
async def test_one_broken_skill_does_not_cost_the_others(listing):
    skills = await listing({"broken": BROKEN, "good": GOOD})
    assert skills["good"]["description"] == "Finds a dataset."
    assert skills["good"]["problem"] == ""


@pytest.mark.asyncio
async def test_a_skill_that_simply_has_no_description_is_not_a_problem(listing):
    skills = await listing({"bare": "---\nname: bare\n---\n\nBody.\n"})
    assert skills["bare"]["problem"] == ""
