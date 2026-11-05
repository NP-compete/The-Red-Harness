"""The PERF-7 scan catches real blocking and spares the rest."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ci"))

import blocking_calls as check  # noqa: E402


def _findings(source: str, tmp_path, monkeypatch):
    (tmp_path / "sample.py").write_text(source)
    monkeypatch.setattr(check, "SOURCE", tmp_path)
    monkeypatch.setattr(check, "ROOT", tmp_path)
    return check.blocking_calls()


class TestTheRepositoryNow:
    def test_it_is_clean(self):
        assert check.blocking_calls() == []


class TestWhatItCatches:
    @pytest.mark.parametrize(
        "line",
        [
            "time.sleep(1)",
            "requests.get('http://x')",
            "httpx.Client()",
            "psycopg.connect('')",
            "subprocess.run(['ls'])",
            "target.write_bytes(b'x')",
            "path.read_text()",
        ],
    )
    def test_a_blocking_call_in_a_coroutine(self, line, tmp_path, monkeypatch):
        found = _findings(f"async def handler():\n    {line}\n", tmp_path, monkeypatch)
        assert found, line

    def test_it_reaches_inside_a_nested_block(self, tmp_path, monkeypatch):
        found = _findings(
            "async def handler():\n"
            "    for one in things:\n"
            "        try:\n"
            "            one.read_bytes()\n"
            "        except OSError:\n"
            "            pass\n",
            tmp_path,
            monkeypatch,
        )
        assert found


class TestWhatItLeavesAlone:
    def test_the_same_call_in_a_sync_function(self, tmp_path, monkeypatch):
        assert (
            _findings("def helper():\n    path.read_text()\n", tmp_path, monkeypatch)
            == []
        )

    def test_an_async_client(self, tmp_path, monkeypatch):
        """`httpx.AsyncClient` and `httpx.Client` differ by a word."""
        assert (
            _findings(
                "async def handler():\n    httpx.AsyncClient()\n",
                tmp_path,
                monkeypatch,
            )
            == []
        )

    def test_a_lazy_import(self, tmp_path, monkeypatch):
        assert (
            _findings(
                "async def handler():\n    from agent.src import thing\n",
                tmp_path,
                monkeypatch,
            )
            == []
        )
