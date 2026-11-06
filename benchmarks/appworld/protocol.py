"""AppWorld's own interaction protocol, kept rather than approximated.

AppWorld is a REPL benchmark: the agent writes Python that calls
`apis.<app>.<method>(...)`, the environment runs it and shows the
result, and the agent writes the next step from what it saw. The
task is finished by calling `apis.supervisor.complete_task(...)`,
and scoring is on world state afterwards — including collateral
damage to state the task never mentioned.

**The prompt is theirs, vendored under `prompts/`.** Writing our
own would measure a different system: a benchmark number is only
comparable if the instructions are. `prompts/react_code_agent.txt`
is their ReAct baseline's, fetched from
`StonyBrookNLP/appworld@main:experiments/prompts/react_code_agent/`.
It is a few-shot dialogue of `USER:`/`ASSISTANT:` turns with Jinja
placeholders, and this module turns it into messages.

The substitution here is deliberately literal rather than Jinja:
the three placeholders are known, and a template engine would
accept a fourth silently if their prompt grew one. `render` raises
on anything it does not recognise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROMPT = HERE / "prompts" / "react_code_agent.txt"

#: A ```python fence, which is how their prompt asks for code.
CODE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)

#: `{{ a.b }}` or `{{ a }}`, with whatever spacing.
PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+(?:\.[a-z_]+)?)\s*\}\}")


@dataclass(frozen=True)
class Turn:
    """One turn of the conversation sent to the agent."""

    role: str
    content: str


class ProtocolError(RuntimeError):
    """The prompt or a reply was not the shape this expects."""


def render(template: str, values: dict[str, str]) -> str:
    """Fill the prompt's placeholders, refusing any we do not know.

    An unfilled `{{ }}` reaching the model is a silent corruption
    of the instructions, which would show up as a lower score and
    be blamed on the agent.
    """
    missing: list[str] = []

    def swap(match: re.Match[str]) -> str:
        """Substitute one placeholder, recording it if it is unknown."""
        key = match.group(1)
        if key not in values:
            missing.append(key)
            return match.group(0)
        return values[key]

    filled = PLACEHOLDER.sub(swap, template)
    if missing:
        raise ProtocolError(
            "the vendored prompt has placeholders this runner does not fill: "
            + ", ".join(sorted(set(missing)))
            + ". It has probably been updated upstream; fill them or re-vendor."
        )
    return filled


#: One framing turn, before their dialogue.
#:
#: Without it the harness refuses most of the split. `PROMPT.md`
#: tells the agent that "a system the question requires, and you do
#: not have, ends the turn" with the line "I cannot answer this
#: without <Integration>" — a good rule, which stops it inventing
#: Jira data when Jira is not connected. In AppWorld it misfires:
#: the agent reads "Spotify", checks its MCP integrations, finds
#: none, and gives up at step two without touching `apis.spotify`,
#: which is right there. Eight of nine failures in the first clean
#: run were this, and none of them had tried anything.
#:
#: So this says what is true rather than switching a safety rule
#: off: in this environment the reachable systems are the REPL's,
#: not the deployment's. AppWorld's rules allow instructing the
#: agent in the prompt — what they forbid is hardcoding API calls
#: into its logic, which this does not do. It names no app, no
#: endpoint and no task.
FRAMING = """You are working inside a sandboxed Python REPL that
provides its own applications. The apps reachable through `apis.*`
in this environment ARE the systems available to you — logging into
them with the credentials in the supervisor app is the intended way
to work here.

This replaces any instruction you have about integrations being
unavailable: that rule is about systems you genuinely cannot reach,
and here you can reach these. Do not end a turn saying you lack an
integration. If you need a capability, look for it with
`apis.api_docs.show_app_descriptions()` first."""


def conversation(
    instruction: str, supervisor: dict, app_descriptions: str
) -> list[Turn]:
    """Their few-shot dialogue, as turns, ending with the real task.

    Preceded by one framing turn — see `FRAMING` for why, and for
    the line between instructing the agent and gaming the suite.
    """
    if not PROMPT.is_file():
        raise ProtocolError(
            f"{PROMPT} is missing. It is vendored from AppWorld's repository; "
            "see this directory's README for the fetch command."
        )
    filled = render(
        PROMPT.read_text(encoding="utf-8"),
        {
            "instruction": instruction,
            "app_descriptions": app_descriptions,
            "main_user.first_name": str(supervisor.get("first_name", "")),
            "main_user.last_name": str(supervisor.get("last_name", "")),
            "main_user.email": str(supervisor.get("email", "")),
            "main_user.phone_number": str(supervisor.get("phone_number", "")),
        },
    )

    turns: list[Turn] = [Turn("human", FRAMING), Turn("ai", "Understood.")]
    role: str | None = None
    buffer: list[str] = []
    for line in filled.splitlines():
        if line.rstrip() in ("USER:", "ASSISTANT:"):
            if role:
                turns.append(Turn(role, "\n".join(buffer).strip()))
            role, buffer = ("human" if line.startswith("USER") else "ai"), []
            continue
        buffer.append(line)
    if role:
        turns.append(Turn(role, "\n".join(buffer).strip()))

    if not turns or turns[-1].role != "human":
        raise ProtocolError("the prompt should end on a USER turn with the task")
    return turns


def code_in(reply: str) -> str:
    """The Python the agent wants run, out of its reply.

    The last fence, not the first: their prompt's examples show the
    model reasoning about earlier snippets before writing the one it
    means, and taking the first would run the illustration.
    """
    blocks = CODE.findall(reply or "")
    if not blocks:
        raise ProtocolError("no ```python block in the reply")
    last: str = blocks[-1]
    return last.strip()
