"""Run the declared judged checks against a running agent (E22-T3)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_SERVICES = str(REPO_ROOT / "services")
if _SERVICES not in sys.path:
    sys.path.insert(0, _SERVICES)

from agent.src.agent.config.paths import config_root  # noqa: E402
from agent.src.evals.declared import declared_registry  # noqa: E402
from agent.src.evals.live import load_cases, run_case  # noqa: E402

WALL_SECONDS = float(os.getenv("EVAL_WALL_SECONDS", "180"))


def _url() -> str:
    """The agent's base URL, from the environment or the local default."""
    explicit = os.getenv("AGENT_URL")
    if explicit:
        return explicit.rstrip("/")
    return f"http://127.0.0.1:{os.getenv('AGENT_PORT', '5002')}"


def _headers() -> dict[str, str]:
    """The Host header to send, if one is configured."""
    host = os.getenv("AGENT_HOST")
    return {"Host": host} if host else {}


class Agent:
    """Asking a running agent a question, one conversation per question."""

    def __init__(self, url: str) -> None:
        """Bind to the agent at `url`."""
        import httpx

        self._httpx = httpx
        self.url = url

    def model(self) -> str:
        """The model the agent is configured with, or an empty string."""
        found = self._httpx.get(
            f"{self.url}/admin/config", headers=_headers(), timeout=15
        )
        if found.status_code != 200:
            return ""
        return str((found.json().get("agent") or {}).get("model") or "")

    def connected(self, mcp_name: str) -> bool:
        """Whether an integration is actually up, as the agent sees it."""
        try:
            found = self._httpx.get(
                f"{self.url}/mcp/{mcp_name}/status", headers=_headers(), timeout=15
            )
        except Exception:  # noqa: BLE001 — unreachable is not connected
            return False
        if found.status_code != 200:
            return False
        return bool(found.json().get("connected"))

    def ask(self, question: str) -> str:
        """Put one question to the agent and return its answer."""
        from agent.cli.outcome import NoAnswer, RunFailedInBody, outcome_of

        made = self._httpx.post(
            f"{self.url}/threads", json={}, headers=_headers(), timeout=30
        )
        made.raise_for_status()
        thread_id = made.json()["thread_id"]

        answered = self._httpx.post(
            f"{self.url}/threads/{thread_id}/runs/wait",
            json={
                "assistant_id": "agent",
                "input": {"messages": [{"role": "user", "content": question}]},
            },
            headers=_headers(),
            timeout=WALL_SECONDS,
        )
        if answered.status_code not in (200, 201):
            raise RuntimeError(f"the run was refused ({answered.status_code})")

        try:
            outcome = outcome_of(answered.json(), thread_id=thread_id)
        except RunFailedInBody as threw:
            raise RuntimeError(str(threw)) from threw
        except NoAnswer as threw:
            raise RuntimeError("the agent answered with nothing") from threw

        if outcome.paused is not None:
            lines = []
            for entry in outcome.paused.get("awaiting") or []:
                action = str(entry.get("action") or "an action")
                args = entry.get("args") or {}
                described = str(entry.get("description") or "").strip()
                detail = json.dumps(args, default=str) if args else ""
                lines.append(
                    f"- {action}"
                    + (f" with {detail}" if detail else "")
                    + (f" — {described}" if described else "")
                )
            asked = "\n".join(lines) or "- an action"
            return (
                f"{outcome.text}\n\n[The assistant stopped and asked for approval "
                f"before doing this:\n{asked}]"
            ).strip()

        return outcome.text


def _quoted(answer: str, *, limit: int = 1200) -> list[str]:
    """The agent's reply, indented, trimmed to something readable."""
    text = answer.strip() or "(nothing)"
    if not os.getenv("EVAL_FULL_ANSWER") and len(text) > limit:
        text = text[:limit] + f"… [{len(answer) - limit} more characters]"
    return [f"           | {line}" for line in text.splitlines()]


def main() -> int:
    """Run the live evals against a running agent."""
    url = _url()
    agent = Agent(url)

    try:
        judged_by = agent.model()
    except Exception as exc:  # noqa: BLE001 — any reason is the same answer
        print(f"no agent at {url}: {exc}")
        print("nothing was scored, so nothing has been cleared.")
        return 2

    root = config_root()
    registry, problems = declared_registry(root)
    for problem in problems:
        print(f"  problem  {problem['where']}: {problem['what']}")

    checks = [
        registry.get(name)
        for group in registry.groups()
        for name in [c.name for c in registry.in_group(group)]
    ]
    judged = [c for c in checks if c.kind == "judged"]

    only = os.getenv("CHECK")
    if only:
        declared = {c.name for c in judged}
        if only not in declared:
            print(f"'{only}' is not a declared judged check. They are:")
            for name in sorted(declared):
                print(f"  {name}")
            return 2
        judged = [c for c in judged if c.name == only]

    print(f"agent {url}, answering and judging with {judged_by or 'an unnamed model'}")

    failed = bool(problems)
    scored_any = False
    up: dict[str, bool] = {}
    for check in judged:
        missing = [
            name
            for name in check.needs
            if not up.setdefault(name, agent.connected(name))
        ]
        if missing:
            print(
                f"  skipped  {check.name}: {', '.join(missing)} "
                f"{'is' if len(missing) == 1 else 'are'} not connected here"
            )
            continue
        if check.judge and check.judge != judged_by:
            print(
                f"  note     {check.name}: declared judge is {check.judge}, "
                f"scored by {judged_by or 'an unnamed model'}"
            )
        try:
            cases = load_cases(root, check)
        except Exception as exc:  # noqa: BLE001
            print(f"  problem  {check.name}: {exc}")
            failed = True
            continue

        for case in cases:
            try:
                scored = run_case(case, ask=agent.ask, judge=agent.ask)
            except Exception as exc:  # noqa: BLE001
                print(f"  not run  {check.name} case {case.id}: {exc}")
                failed = True
                continue
            scored_any = True
            mark = "ran" if scored.judgement.passed else "FAILED"
            print(f"  {mark:<8} {check.name}: {scored.say()}")
            if not scored.judgement.passed:
                failed = True
                print(f"           decides: {check.decides.strip()}")
                for line in _quoted(scored.answer):
                    print(line)
            elif os.getenv("EVAL_SHOW_ANSWERS"):
                for line in _quoted(scored.answer):
                    print(line)

    for check in checks:
        if check.kind != "judged":
            print(f"  skipped  {check.name}: a {check.kind} check — make evals-offline")

    if not judged:
        print("no judged checks are declared, so this scored nothing.")
        return 2
    if not scored_any:
        print("every judged check was skipped, so nothing has been cleared.")
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
