"""One code per outcome, and `--json` on everything that returns one (CLI-3)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from agent.cli.doctor import DEGRADED_EXIT
from agent.cli.main import (
    NEEDS_DECISION,
    SERVE_ROLES,
    UNAUTHENTICATED,
    USAGE_ERROR,
    build_parser,
)

ROOT = Path(__file__).resolve().parents[3]
CLI_DOC = ROOT / "docs" / "reference" / "cli.md"

NO_PAYLOAD = {
    *SERVE_ROLES,
    "completion",
    "docs",
}


def _commands() -> dict[str, argparse.ArgumentParser]:
    """Every leaf subcommand, by the name a person types."""
    found: dict[str, argparse.ArgumentParser] = {}

    def walk(parser: argparse.ArgumentParser, prefix: str) -> None:
        subs = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
        if not subs:
            found[prefix.strip()] = parser
            return
        for action in subs:
            for name, child in action.choices.items():
                walk(child, f"{prefix} {name}")

    walk(build_parser(), "")
    found.pop("", None)
    return found


class TestEveryCommandThatReturnsSomethingSpeaksJson:
    def test_there_are_commands_to_check(self):
        assert len(_commands()) >= 20

    @pytest.mark.parametrize("name", sorted(_commands()))
    def test_it_has_json_or_is_named_as_returning_nothing(self, name):
        if name.split()[0] in NO_PAYLOAD:
            return
        options = {
            o for action in _commands()[name]._actions for o in action.option_strings
        }
        assert "--json" in options, (
            f"`harness {name}` returns something and cannot be piped into jq. "
            "Add --json, or add it to NO_PAYLOAD with a reason if it really "
            "writes no payload."
        )

    def test_the_exemptions_are_all_real_commands(self):
        heads = {name.split()[0] for name in _commands()}
        assert NO_PAYLOAD <= heads, sorted(NO_PAYLOAD - heads)


class TestOneCodePerOutcome:
    def test_usage_is_what_argparse_already_returns(self):
        assert USAGE_ERROR == 2

    def test_the_codes_do_not_collide(self):
        codes = [0, 1, USAGE_ERROR, NEEDS_DECISION, UNAUTHENTICATED, DEGRADED_EXIT]
        assert len(set(codes)) == len(codes), codes

    def test_degraded_stays_out_of_the_reserved_range(self):
        assert DEGRADED_EXIT > 4

    @pytest.mark.parametrize(
        "code,meaning",
        [
            ("0", "it worked"),
            ("1", "it did not"),
            ("2", "used wrongly"),
            ("3", "it is waiting for a decision"),
            ("4", "it does not know who you are"),
            ("5", "it worked but something is missing"),
        ],
    )
    def test_the_page_documents_it(self, code, meaning):
        line = next(
            one
            for one in CLI_DOC.read_text().splitlines()
            if one.startswith("exit codes:")
        )
        assert f"{code} {meaning}" in line, line
