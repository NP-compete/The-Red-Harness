"""E27-T1 and T9. One command, and a preflight that says why not."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

MAKEFILE = (Path(__file__).resolve().parents[2] / "Makefile").read_text()


def target(name: str) -> str:
    """The body of one Makefile target."""
    match = re.search(rf"^{re.escape(name)}:.*?\n((?:\t.*\n|\n)*)", MAKEFILE, re.M)
    assert match, f"no target named {name!r}"
    return match.group(1)


class TestOneCommand:
    def test_the_target_exists(self):
        assert target("dev")

    def test_it_starts_both_roles(self):
        body = target("dev")
        assert "aegra dev --port 5002" in body
        assert "npm run dev" in body

    def test_it_starts_the_dependencies_too(self):
        assert "podman-compose" in target("dev")

    def test_a_missing_ui_checkout_is_said_rather_than_failing(self):
        """A deployment that keeps the interface elsewhere should"""
        assert "skipped: no checkout" in target("dev")

    def test_the_ui_directory_is_overridable(self):
        assert "UI_DIR ?=" in MAKEFILE

    def test_it_reports_what_did_not_come_up(self):
        """A loop that silently fails on one of three ports is a"""
        assert "NOT UP" in target("dev-wait")

    def test_it_prints_how_long_it_took(self):
        """DX-1 is a budget; a budget nobody measures is a wish."""
        assert "ready in" in target("dev-wait")


class TestStopping:
    def test_it_leaves_the_dependencies_running(self):
        """The next `make dev` is ten seconds away and a Postgres"""
        body = target("dev-down")
        assert "dependencies are still up" in body
        assert "podman-compose" not in body

    def test_the_ports_are_the_backstop(self):
        """`concurrently` does not always take its children with"""
        assert "lsof" in target("dev-down")

    @pytest.mark.parametrize("name", ["dev", "dev-down"])
    def test_ports_are_asked_about_one_flag_at_a_time(self, name):
        """`lsof -ti :a :b` reads the second as a file name and"""
        for line in target(name).splitlines():
            if "lsof" in line and ":5003" in line:
                assert "-ti :5003" in line, line


class TestThePreflight:
    @pytest.mark.parametrize(
        "thing", ["podman", ".venv", "node_modules", ".env", "pg_isready", "8181"]
    )
    def test_it_checks_the_things_that_have_gone_wrong(self, thing):
        assert thing in target("doctor")

    def test_every_problem_says_what_to_do(self):
        """A preflight that prints FAIL and no next step is a"""
        body = target("doctor")
        for cue in ["podman machine start", "make install", "npm install", "make dev"]:
            assert cue in body

    @pytest.mark.parametrize("tool", ["podman-compose", "kind", "kubectl"])
    def test_it_covers_the_cluster_path_too(self, tool):
        """E26-T17 asks for one preflight across both paths, which"""
        assert tool in target("doctor")

    def test_a_missing_cluster_tool_does_not_fail_the_inner_loop(self):
        """A developer editing a route has no use for `kind`, and"""
        body = target("doctor")
        assert "not needed for the inner loop" in body
        cluster = body[body.index("the cluster path") :]
        assert "ok=1" not in cluster

    def test_it_knows_its_own_processes_from_a_stranger(self):
        assert ".local/listeners" in target("doctor")

    def test_it_recognises_a_restarted_child(self):
        """`concurrently` restarts the Vite child on its own, so a"""
        assert "pgid" in target("doctor")
        assert "pgid" in target("dev")


class TestTheSeed:
    """E27-T4. The fixture state a restart costs you."""

    def test_the_target_exists(self):
        assert "scripts.dev.seed" in target("seed")

    def test_every_fixture_is_looked_for_before_it_is_made(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2] / "scripts" / "dev" / "seed.py"
        ).read_text()
        assert source.count('"kept"') >= 4

    def test_the_conversation_rides_on_the_thread_it_just_made(self):
        """The turn has no "kept" of its own, and does not need"""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2] / "scripts" / "dev" / "seed.py"
        ).read_text()
        body = source[source.index("def _thread(") :]
        kept_first = body.index('_say(f"thread {THREAD!r}", "kept")')
        assert body.index("return", kept_first) < body.index("/runs/wait")

    def test_it_puts_this_checkout_first(self):
        """Otherwise the seed lands in another checkout's database."""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2] / "scripts" / "dev" / "seed.py"
        ).read_text()
        # The guard and the insert disagreed when this was one line:
        # it tested for REPO_ROOT and inserted REPO_ROOT/services.
        assert 'REPO_ROOT / "services"' in source
        assert "sys.path.insert" in source

    def test_the_conversation_is_a_real_turn(self):
        """Writing checkpoint rows by hand would produce a thread"""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2] / "scripts" / "dev" / "seed.py"
        ).read_text()
        assert "/runs/wait" in source

    def test_it_will_not_spend_money_to_seed(self):
        """Against a real provider it skips the turn and says so,"""
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2] / "scripts" / "dev" / "seed.py"
        ).read_text()
        assert "should not spend money" in source
        assert "/config/settings" in source


class TestTheWayInWithNoToolchain:
    """DX-6: the whole thing, one command, no interpreter."""

    BODY = None

    def setup_method(self):
        self.BODY = target("kind")

    @pytest.mark.parametrize("tool", [".venv", "npm ", "python3", "pip "])
    def test_it_needs_no_local_interpreter(self, tool):
        assert tool not in self.BODY, (
            f"`make kind` now uses {tool.strip()!r}. It is the only way in for "
            "somebody with no Python and no Node installed (DX-6, "
            "docs/guides/dev-loop.md) — put the step somewhere else, or change "
            "the page and this test together."
        )

    def test_it_really_does_bring_up_the_whole_thing(self):
        assert "Containerfile --target runtime" in self.BODY
        assert "apply -k" in self.BODY

    def test_the_page_says_so(self):
        page = (
            Path(__file__).resolve().parents[2] / "docs" / "guides" / "dev-loop.md"
        ).read_text()
        assert "With no Python and no Node installed" in page
        assert "make kind" in page


class TestWhatSurvivesARestart:
    """DX-5: nobody re-runs an OAuth dance to get back."""

    COMPOSE = None

    def setup_method(self):
        root = Path(__file__).resolve().parents[2]
        self.COMPOSE = (root / "compose.yaml").read_text()
        self.STORE = (
            root / "services" / "agent" / "aegra" / "mcp_token_store.py"
        ).read_text()

    def test_a_token_outlives_the_process_that_got_it(self):
        assert "cache_set_persistent" in self.STORE
        assert "cache_set(" not in self.STORE, (
            "the token store now writes with a TTL; an expiry nobody chose "
            "is an OAuth dance nobody scheduled (DX-5)"
        )

    def test_and_outlives_redis_too(self):
        assert "--appendonly yes" in self.COMPOSE
        assert "agent_redis_data:/data" in self.COMPOSE
