"""The reload probe is tested against the case it would have missed (OBS-4)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dev/timings.sh"

READY = "Application startup complete"


def _ready_count_from_the_script() -> str:
    """The function as the script defines it, not a copy."""
    source = SCRIPT.read_text()
    found = re.search(r"^ready_count\(\) \{.*?\}$", source, re.M | re.S)
    assert found, "timings.sh no longer defines ready_count()"
    return found.group(0)


def _count(log: Path) -> int:
    ran = subprocess.run(
        [
            "bash",
            "-c",
            f'READY="{READY}"\nAGENT_LOG="{log}"\n'
            f"{_ready_count_from_the_script()}\nready_count",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(ran.stdout.strip())


class TestTheCaseItWouldHaveMissed:
    def test_a_log_that_already_says_ready(self, tmp_path):
        """The first probe's blind spot, as a number."""
        log = tmp_path / "agent.log"
        log.write_text(f"INFO: {READY}\n")

        before = _count(log)
        assert before == 1, "a started agent should already have one ready line"

        assert _count(log) == before

        log.write_text(log.read_text() + f"INFO: {READY}\n")
        assert _count(log) > before, (
            "a reload happened and the probe did not see it; it would wait "
            "the full 120s and report that autoreload is off"
        )

    def test_a_log_that_does_not_exist_counts_zero(self, tmp_path):
        assert _count(tmp_path / "nothing.log") == 0

    def test_an_empty_log_counts_zero(self, tmp_path):
        log = tmp_path / "agent.log"
        log.write_text("")
        assert _count(log) == 0


class TestTheScriptStillWorksThisWay:
    """The two rejected probes stay rejected."""

    def test_it_counts_log_lines_rather_than_polling_the_socket(self):
        source = SCRIPT.read_text()
        loop = source[source.index('before="$(ready_count)"') :]
        waiting = loop[: loop.index("agent_ms=")]
        assert "ready_count" in waiting, (
            "the reload wait no longer counts ready lines. A /health poll "
            "answers throughout a reload and measures one curl."
        )

    @pytest.mark.parametrize("rejected", ["pgrep", "lsof", "fuser"])
    def test_it_does_not_go_back_to_the_pid_on_the_port(self, rejected):
        assert rejected not in SCRIPT.read_text(), (
            f"{rejected} is back. The pid on the port is the reloader's; "
            "the worker is a child, so it never changes and the probe "
            "never fires."
        )

    def test_the_reason_is_written_down_where_it_is_made(self):
        source = SCRIPT.read_text()
        assert "measuring one curl" in source
