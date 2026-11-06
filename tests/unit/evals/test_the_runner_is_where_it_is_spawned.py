"""The subprocess the orchestration spawns has to be on disk.

`_run_eval_pattern_sync` builds a path and hands it to
`subprocess.run`. A wrong name is not an ImportError and not a
traceback: each tag exits 2, the per-turn table stays empty, and
the run is scored `error` with no indication of why. It cost a
full deploy-and-run cycle to see. These are cheap.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

from agent.src.evals import runs


def test_the_runner_file_exists():
    source = inspect.getsource(runs._run_eval_pattern_sync)
    named = re.search(r'Path\(__file__\)\.parent / "([^"]+)"', source)
    assert named, "the runner is no longer resolved from a literal; update this test"
    runner = Path(runs.__file__).parent / named.group(1)
    assert runner.is_file(), f"{runner} is spawned per tag and is not there"


def test_the_agent_url_is_not_a_bind_address():
    """`AGENT_HOST` is 0.0.0.0 in the pod; connecting to it fails."""
    assert not runs.AGENT_URL.startswith("0.0.0.0")


def test_no_harness_only_keys_reach_the_validator():
    """lightspeed rejects unknown keys and kills the whole tag.

    `requires_shortening` is ours: the runner reads it, then has
    to drop it. The Postgres dataset path never emits it, so the
    config-file fallback was the only way to hit this — and that
    is the path Kind uses.
    """
    source = inspect.getsource(runs)
    runner = (Path(runs.__file__).parent / "lightspeed_runner.py").read_text()
    assert 'pop("requires_shortening", None)' in runner, (
        "the runner must strip requires_shortening before the dataset "
        "goes to lightspeed-evaluation"
    )
    del source


def test_no_tool_calls_is_a_failure_not_an_error():
    """An agent that calls nothing must not score better than one that calls wrong.

    `custom:tool_eval` needs a non-empty `tool_calls`; lightspeed's
    validator marks the metric invalid when it is empty and records
    ERROR, and `_score_from_counts` leaves errors out of the
    denominator. So "made no tool call at all" used to delete the
    assertion instead of failing it.
    """
    runner = (Path(runs.__file__).parent / "lightspeed_runner.py").read_text()
    assert 'turn["tool_calls"] = [[]]' in runner, (
        "a turn that expected tool calls and got none must still give "
        "custom:tool_eval something to judge"
    )
