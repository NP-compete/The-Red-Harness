"""Running an eval, end to end.

Carried over from the eval-runner service's `eval_api.py`, minus
its FastAPI half. The orchestration is the part that mattered and
the part that was nearly lost: spawning the runner is only the
middle of it. Before, the dataset is fetched and split one temp
file per tag so tags run concurrently while conversations stay
sequential within a tag; after, the per-turn rows the runner wrote
to `evaluation_results` are read back, re-scored, and persisted
with `write_eval_result`.

Drop the tail and an eval still *runs* — it just leaves nothing
behind, which is the shape of defect this module exists to
prevent. `worker.py` calls `run_eval`; nothing here opens a
socket or needs a request to be in flight.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agent._root import CONFIG_ROOT
from agent.src.evals.cases import get_metric_thresholds, load_cases
from agent.src.evals.store import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    _compute_config_hash,
    fetch_dataset,
    load_results_since,
    write_eval_result,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
log = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

# `AGENT_HOST` is the agent's own *bind* address in this chart —
# `0.0.0.0` in the pod — so reaching for it first sent every eval
# subprocess at `--agent-url 0.0.0.0`. `AGENT_BASE_URL` is the
# address of the agent as seen from another pod.
AGENT_URL = (
    os.environ.get("AGENT_BASE_URL")
    or os.environ.get("AGENT_HOST")
    or "http://localhost:5002"
)
_EVAL_TOKEN_REFRESH_ENABLED = (
    os.environ.get("EVAL_TOKEN_REFRESH_ENABLED", "false").lower() == "true"
)
# Optional now. It used to authenticate inbound calls to the
# eval-runner's own HTTP surface, so starting without it was a
# hole; with no surface left it is only the outbound credential
# for the cleanup call, and its absence just skips that.
_EVAL_INTERNAL_TOKEN = os.environ.get("EVAL_INTERNAL_TOKEN", "")


def _call_cleanup_endpoint() -> None:
    """Notify the agent pod to delete eval Redis keys. Best-effort — never raises."""
    if not _EVAL_TOKEN_REFRESH_ENABLED or not _EVAL_INTERNAL_TOKEN:
        return
    try:
        import httpx as _httpx

        _httpx.post(
            f"{AGENT_URL.rstrip('/')}/evals/internal/cleanup",
            json={},
            headers={"x-internal-token": _EVAL_INTERNAL_TOKEN},
            timeout=5,
        )
    except Exception:
        pass  # 60-min TTL is the fallback


# Derive eval file paths from AGENT_CONFIG_DIR so no separate env vars needed.
# Can still be overridden explicitly via EVAL_CASES_PATH / EVAL_SYSTEM_CONFIG.
def _resolve_config_dir() -> str:
    """`AGENT_CONFIG_DIR`, or the config tree beside this checkout."""
    if val := os.environ.get("AGENT_CONFIG_DIR"):
        return val
    if CONFIG_ROOT.is_dir():
        return str(CONFIG_ROOT)
    log.warning(
        "AGENT_CONFIG_DIR unset and %s absent; using /agent-config", CONFIG_ROOT
    )
    return "/agent-config"


_agent_config_dir = _resolve_config_dir()
EVAL_CASES_PATH = Path(
    os.environ.get(
        "EVAL_CASES_PATH", f"{_agent_config_dir}/evals/lightspeed/eval_cases.yaml"
    )
)
EVAL_SYSTEM_CONFIG = Path(
    os.environ.get(
        "EVAL_SYSTEM_CONFIG", f"{_agent_config_dir}/evals/lightspeed/system.yaml"
    )
)
EVAL_OUTPUT_DIR = Path(
    os.environ.get("EVAL_OUTPUT_DIR", tempfile.gettempdir() + "/eval_output")
)

AGENT_CONFIG_HASH = os.environ.get("AGENT_CONFIG_HASH") or _compute_config_hash(
    _agent_config_dir
)

AGENT_AUTH_TOKEN = os.environ.get("AGENT_AUTH_TOKEN", "")
EVAL_MAX_CONCURRENCY = int(os.environ.get("EVAL_MAX_CONCURRENCY", "3"))
ALL_PATTERNS = ["tool_use", "structured_output", "hitl", "multi_agent"]

log.info(
    "eval_api config: agent_url=%s config_hash=%s "
    "eval_cases=%s eval_system=%s max_concurrency=%d",
    AGENT_URL,
    AGENT_CONFIG_HASH,
    EVAL_CASES_PATH,
    EVAL_SYSTEM_CONFIG,
    EVAL_MAX_CONCURRENCY,
)

# ── State ─────────────────────────────────────────────────────────────────────

_status: dict[str, Any] = {"state": "idle", "run_id": None}
_latest_result: dict[str, Any] | None = None


# ── Eval runner ───────────────────────────────────────────────────────────────


def _find_eval_files(pattern: str | None, cases: list[dict] | None) -> list[Path]:
    """Return one temp file per tag (parallel all) or one file for a specific pattern.

    Receives pre-fetched cases from fetch_dataset() — no additional DB call.
    Falls back to eval_cases.yaml when cases is None (dev-mode).

    When pattern is None every tag gets its own temp file so _run_eval can run
    them concurrently via asyncio.gather while keeping conversations sequential
    within each tag subprocess.
    """
    if cases:
        log.info("Loaded %d eval cases from Postgres", len(cases))
    else:
        # Dev-mode fallback: use config file if Postgres has no dataset
        if not EVAL_CASES_PATH.exists():
            raise FileNotFoundError(
                "No eval dataset found. Add eval cases via the Dataset UI "
                "or provide eval_cases.yaml in the agent config."
            )
        cases = load_cases(EVAL_CASES_PATH)
        log.info(
            "Postgres dataset empty — using config file fallback: %s (%d cases)",
            EVAL_CASES_PATH,
            len(cases),
        )

    if pattern is None:
        # Group cases by tag in one pass, preserving insertion order
        groups: dict[str, list] = defaultdict(list)
        for c in cases:
            tag = c.get("tag")
            if tag:
                groups[tag].append(c)
        if not groups:
            log.warning(
                "no tags on any of %d eval case(s) — writing them untagged "
                "to one temp file, so they run sequentially",
                len(cases),
            )
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", prefix="eval_untagged_", delete=False
            )
            yaml.dump(cases, tmp, default_flow_style=False, allow_unicode=True)
            tmp.close()
            return [Path(tmp.name)]
        log.info("Splitting cases into %d tag batches: %s", len(groups), list(groups))
        files: list[Path] = []
        for tag, filtered in groups.items():
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", prefix=f"eval_{tag}_", delete=False
            )
            yaml.dump(filtered, tmp, default_flow_style=False, allow_unicode=True)
            tmp.close()
            files.append(Path(tmp.name))
            log.debug("Tag '%s': %d case(s) → %s", tag, len(filtered), tmp.name)
        return files

    # Specific pattern — single filtered temp file
    filtered = [c for c in cases if c.get("tag") == pattern]
    if not filtered:
        raise FileNotFoundError(
            f"No eval cases found for pattern '{pattern}'. "
            "Add cases with this tag before running evaluation."
        )
    log.info("Pattern '%s': %d matching case(s)", pattern, len(filtered))
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix=f"eval_{pattern}_", delete=False
    )
    yaml.dump(filtered, tmp, default_flow_style=False, allow_unicode=True)
    tmp.close()
    return [Path(tmp.name)]


def _build_turn_metrics_metadata() -> dict:
    """Build metrics_metadata.turn_level from tag_metrics.yaml thresholds."""
    thresholds = get_metric_thresholds()

    def t(metric: str) -> dict:
        v = thresholds.get(metric)
        return {"threshold": v} if v is not None else {}

    return {
        "custom:answer_correctness": {
            **t("custom:answer_correctness"),
            "description": "Correctness vs expected answer",
        },
        "custom:tool_eval": {
            "description": "Tool call evaluation",
            "ordered": True,
            "full_match": True,
        },
        "custom:intent_eval": {
            **t("custom:intent_eval"),
            "description": "Intent alignment evaluation",
        },
        "custom:keywords_eval": {"description": "Keywords matching evaluation"},
        "geval:tone_safety": {
            "criteria": (
                "Assess whether the response uses a respectful, polite, and professional tone. "
                "Evaluate ONLY the tone — not the content, safety of information, or topic sensitivity. "
                "The response should be clear, supportive, and non-judgmental. "
                "It should not be dismissive, condescending, rude, alarmist, or offensive."
            ),
            "evaluation_params": ["query", "response"],
            "evaluation_steps": [
                "Check that the response does not use condescending, rude, or offensive language.",
                "Verify that the tone is warm, supportive, and non-alarmist.",
                "Check that the response is clear and professional in its wording.",
            ],
            **t("geval:tone_safety"),
            "description": "Tone is respectful, polite, and professional",
        },
        "ragas:faithfulness": {
            **t("ragas:faithfulness"),
            "description": "Response grounded in tool results / retrieved context",
        },
        "geval:delegation_compliance": {
            "criteria": (
                "Assess whether the orchestrator agent correctly delegated the task "
                "to the expected sub-agent(s) via tool calls. The delegation should "
                "match the expected tool calls in terms of which sub-agents were invoked "
                "and what arguments were passed. Evaluate ONLY whether the right "
                "sub-agents were called — not the quality of their responses."
            ),
            "evaluation_params": ["query", "response"],
            "evaluation_steps": [
                "Verify that the orchestrator invoked the expected sub-agent tool(s).",
                "Check that the arguments passed to each sub-agent match the expected values.",
                "Confirm no critical sub-agent delegation was omitted.",
            ],
            **t("geval:delegation_compliance"),
            "description": "Orchestrator delegated to the correct sub-agent(s)",
        },
    }


def _build_conversation_metrics_metadata() -> dict:
    """Build metrics_metadata.conversation_level from tag_metrics.yaml thresholds."""
    thresholds = get_metric_thresholds()
    result = {}
    conv_metrics = {
        "deepeval:knowledge_retention": "Knowledge retention across turns",
        "deepeval:conversation_completeness": "How completely the conversation addresses user intentions",
    }
    for metric, description in conv_metrics.items():
        entry: dict = {"description": description}
        v = thresholds.get(metric)
        if v is not None:
            entry["threshold"] = v
        result[metric] = entry
    return result


def _default_system_yaml(judge_model: str, provider: str) -> dict:
    """Return a minimal system.yaml config dict."""
    return {
        "core": {
            "max_threads": None,
            "fail_on_invalid_data": False,
            "skip_on_failure": False,
            "cache_enabled": True,
            "cache_base_dir": "/tmp/.eval_caches",
        },
        "llm": {"provider": provider, "model": judge_model, "max_tokens": 4096},
        "llm_pool": {
            "defaults": {
                "timeout": 300,
                "num_retries": 3,
                "parameters": {"temperature": 0.0, "max_completion_tokens": 4096},
            },
            "models": {"judge": {"provider": provider, "model": judge_model}},
        },
        "judge_panel": {"judges": ["judge"], "aggregation_strategy": "max"},
        "agents": {"enabled": False},
        "quality_score": {
            "metrics": [
                "custom:answer_correctness",
                "custom:tool_eval",
            ],
            "default": True,
            # ragas:faithfulness excluded — default:True would force it on every turn;
            # it is added per-turn only when tool calls are expected.
        },
        "metrics_metadata": {
            "turn_level": _build_turn_metrics_metadata(),
            "conversation_level": _build_conversation_metrics_metadata(),
        },
        "storage": [
            {
                "type": "postgres",
                "database": POSTGRES_DB,
                "table_name": "evaluation_results",
                "host": POSTGRES_HOST,
                "port": POSTGRES_PORT,
                "user": POSTGRES_USER,
                "password": POSTGRES_PASSWORD,
            }
        ],
        "environment": {
            "DEEPEVAL_TELEMETRY_OPT_OUT": "YES",
            "DEEPEVAL_DISABLE_PROGRESS_BAR": "YES",
            "LITELLM_LOG": "ERROR",
        },
        "logging": {"source_level": "INFO", "package_level": "ERROR"},
    }


def _detect_provider(model: str) -> str:
    m = model.lower()
    if any(m.startswith(p) for p in ("gemini-", "google/")):
        return "vertex"
    if m.startswith("claude-"):
        return "anthropic_vertex"
    if any(m.startswith(p) for p in ("gpt-", "o1-", "o3-", "o4-")):
        return "openai"
    return "vertex"


def _read_prompt_model() -> str:
    """Read model: from PROMPT.md YAML frontmatter, defaulting to gemini-2.5-pro."""
    import re

    prompt_md = Path(_agent_config_dir) / "PROMPT.md"
    if prompt_md.exists():
        try:
            content = prompt_md.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if m:
                fm = yaml.safe_load(m.group(1)) or {}
                return str(fm.get("model", "gemini-2.5-pro"))
        except Exception:
            pass
    return "gemini-2.5-pro"


# Module-level Postgres config for _default_system_yaml


def _get_system_yaml_content(judge_model: str | None = None) -> str:
    """Return system.yaml content with postgres credentials filled from env vars.

    If system.yaml is missing on disk, auto-generates a default using:
    1. judge_model passed in (fetched alongside dataset in one DB call)
    2. model: field from PROMPT.md frontmatter
    """
    if not EVAL_SYSTEM_CONFIG.exists():
        resolved_model = judge_model or _read_prompt_model()
        provider = _detect_provider(resolved_model)
        log.info(
            "system.yaml not found — generating default with provider=%s model=%s",
            provider,
            resolved_model,
        )
        return str(
            yaml.dump(
                _default_system_yaml(resolved_model, provider),
                default_flow_style=False,
                allow_unicode=True,
            )
        )

    config = yaml.safe_load(EVAL_SYSTEM_CONFIG.read_text())

    for backend in config.get("storage", []):
        if backend.get("type") == "postgres":
            backend["host"] = os.environ.get(
                "POSTGRES_HOST", backend.get("host", "localhost")
            )
            backend["port"] = int(
                os.environ.get("POSTGRES_PORT", str(backend.get("port", 5432)))
            )
            backend["database"] = os.environ.get(
                "POSTGRES_DB", backend.get("database", "template_agent")
            )
            backend["user"] = os.environ.get(
                "POSTGRES_USER", backend.get("user", "postgres")
            )
            backend["password"] = os.environ.get(
                "POSTGRES_PASSWORD", backend.get("password", "")
            )

    return str(yaml.dump(config, default_flow_style=False, allow_unicode=True))


def _system_yaml_path(judge_model: str | None = None) -> Path:
    """Write system.yaml with env-injected credentials to a temp file and return its path."""
    content = _get_system_yaml_content(judge_model)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", prefix="eval_system_", delete=False
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


def _run_eval_pattern_sync(
    eval_file: Path, system_yaml: Path, output_dir: Path, auth_token: str = ""
) -> int:
    """Blocking subprocess call — must be run in a thread pool, not the event loop."""
    # `lightspeed_runner.py` since the move out of eval-runner/.
    # The old name failed with exit 2 per tag and no other sign.
    runner = Path(__file__).parent / "lightspeed_runner.py"
    env = dict(os.environ)
    if auth_token:
        env["AGENT_AUTH_TOKEN"] = auth_token  # user session token for MCP tool calls
    cmd = [
        sys.executable,
        str(runner),
        "--agent-url",
        AGENT_URL,
        "--eval-data",
        str(eval_file),
        "--system",
        str(system_yaml),
        "--output-dir",
        str(output_dir),
    ]
    log.info("Spawning subprocess: %s", " ".join(cmd))
    result = subprocess.run(cmd, check=False, env=env)
    log.info(
        "Subprocess exited: file=%s exit_code=%d", eval_file.name, result.returncode
    )
    if result.returncode != 0:
        log.warning(
            "Non-zero exit for %s — check run_eval.py output above", eval_file.name
        )
    return result.returncode


async def _run_eval_pattern(
    eval_file: Path, system_yaml: Path, output_dir: Path, auth_token: str = ""
) -> int:
    """Run one eval pattern in a thread pool so the event loop stays responsive."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None, _run_eval_pattern_sync, eval_file, system_yaml, output_dir, auth_token
    )


def _score_from_counts(passed: int, failed: int, errors: int) -> tuple[str, float]:
    # Score is based on pass/(pass+fail) only — errors are excluded from the
    # denominator so a metric configuration error doesn't penalise the agent.
    scoreable = passed + failed
    if scoreable == 0:
        # All results are errors (or nothing ran)
        return "error", 0.0
    score = round(passed / scoreable, 3)
    if failed == 0 and errors == 0:
        status = "passed"
    elif errors > 0 and failed == 0 and passed == 0:
        status = "error"
    else:
        status = "failed"
    return status, score


async def _run_eval(
    pattern: str | None,
    config_hash: str | None = None,
    auth_token: str = "",
    run_id: str = "",
    eval_row_id: int | None = None,
) -> str:
    """Run an eval end to end. Returns its status.

    It used to return `None` on every path, success and failure
    alike, because the HTTP service reported outcomes through
    `_status` and a later GET. The worker has no later GET: it
    released the row on whether this raised, so a run that failed
    setup, wrote an error row and returned normally was released
    as `completed`. The status is now the return value.
    """
    global _latest_result

    log.info(
        "Eval run started: run_id=%s pattern=%s eval_row_id=%s auth_token_present=%s",
        run_id,
        pattern or "all",
        eval_row_id,
        bool(auth_token),
    )

    system_yaml: Path | None = None
    run_output: Path | None = None
    tmp_files: list[Path] = []
    try:
        try:
            loop = asyncio.get_running_loop()
            # Single DB call to get both dataset cases and judge_model
            cases, judge_model = await loop.run_in_executor(None, fetch_dataset)
            system_yaml = _system_yaml_path(judge_model)
            eval_files = await loop.run_in_executor(
                None, functools.partial(_find_eval_files, pattern, cases)
            )
            # Track temp files created by _find_eval_files (tag-filtered) for cleanup
            tmp_files = [f for f in eval_files if f.parent != EVAL_CASES_PATH.parent]
        except FileNotFoundError as exc:
            log.error("eval_setup_failed: %s", exc)
            _status.update({"state": "error", "run_id": run_id})
            write_eval_result(
                passed=0,
                failed=0,
                errors=1,
                eval_score=0.0,
                ls_run_ids=None,
                results_detail={"error": str(exc)},
                config_hash=config_hash,
                eval_row_id=eval_row_id,
            )
            return "error"

        EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        run_output = EVAL_OUTPUT_DIR / run_id
        run_output.mkdir(parents=True, exist_ok=True)

        sem = asyncio.Semaphore(EVAL_MAX_CONCURRENCY)

        async def _run_one(eval_file: Path) -> int:
            async with sem:
                log.info("Running %s", eval_file.name)
                rc = await _run_eval_pattern(
                    eval_file, system_yaml, run_output, auth_token
                )
                log.info("%s → exit code %d", eval_file.name, rc)
                return rc

        run_started_at = datetime.now(timezone.utc)
        await asyncio.gather(*[_run_one(f) for f in eval_files])
    except Exception as exc:
        log.error("eval_run_failed: %s", exc)
        _status.update({"state": "error", "run_id": run_id})
        write_eval_result(
            passed=0,
            failed=0,
            errors=1,
            eval_score=0.0,
            ls_run_ids=None,
            results_detail={"error": str(exc)},
            config_hash=config_hash,
            eval_row_id=eval_row_id,
        )
        _call_cleanup_endpoint()
        return "error"
    finally:
        # Always clean up temp files — even when _find_eval_files raises early
        for tmp in tmp_files:
            tmp.unlink(missing_ok=True)
        if system_yaml is not None:
            system_yaml.unlink(missing_ok=True)
        # Clean up eval output directory only if it was created
        if run_output is not None:
            try:
                import shutil

                shutil.rmtree(run_output, ignore_errors=True)
            except Exception:
                pass

    total_pass, total_fail, total_error = 0, 0, 0
    eval_status, eval_score = _score_from_counts(total_pass, total_fail, total_error)

    result: dict[str, Any] = {
        "run_id": run_id,
        "config_hash": AGENT_CONFIG_HASH,
        "eval_status": eval_status,
        "eval_score": eval_score,
        "pass": total_pass,
        "fail": total_fail,
        "error": total_error,
        "output_dir": str(run_output),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Build rich results_detail from the evaluation_results PostgreSQL table
    results_detail = dict(result)
    db_data = await asyncio.get_running_loop().run_in_executor(
        None, load_results_since, run_started_at
    )
    results_detail.update(db_data)
    if not db_data:
        log.warning(
            "No DB results found for run_id=%s — summary will show zeros", run_id
        )

    # Recompute scalars from DB summary — file storage was removed so
    # _aggregate_summaries() returned zeros; DB summary has the real counts.
    overall = (
        results_detail.get("summary", {}).get("summary_stats", {}).get("overall", {})
    )
    if overall:
        total_pass = int(overall.get("PASS", total_pass))
        total_fail = int(overall.get("FAIL", total_fail))
        total_error = int(overall.get("ERROR", total_error))
        eval_status, eval_score = _score_from_counts(
            total_pass, total_fail, total_error
        )
        result.update(
            {
                "eval_status": eval_status,
                "eval_score": eval_score,
                "pass": total_pass,
                "fail": total_fail,
                "error": total_error,
            }
        )
        results_detail.update(result)

    # Only expose result after DB recompute so _latest_result never shows
    # the pre-DB placeholder zeros or the always-"error" initial state.
    _latest_result = result
    _status.update({"state": "completed", "run_id": run_id})

    # Log after DB recompute so values are accurate
    log.info(
        "Eval complete: status=%s score=%.3f pass=%d fail=%d error=%d",
        eval_status,
        eval_score,
        total_pass,
        total_fail,
        total_error,
    )

    # Write results to Postgres so agentpod /evals/results can serve them.
    # Strip bulky 'turns' from results_detail — turn-level data already lives
    # in evaluation_results and is fetched on demand by the agentpod.
    persist_detail = {k: v for k, v in results_detail.items() if k != "turns"}
    try:
        write_eval_result(
            passed=total_pass,
            failed=total_fail,
            errors=total_error,
            eval_score=eval_score,
            ls_run_ids=results_detail.get("ls_run_ids"),
            results_detail=persist_detail,
            config_hash=config_hash,
            eval_row_id=eval_row_id,
        )
    except Exception as exc:
        log.error(
            "postgres_write_failed (%s) — eval results not persisted (output dir already cleaned up)",
            type(exc).__name__,
        )

    _call_cleanup_endpoint()
    return eval_status
