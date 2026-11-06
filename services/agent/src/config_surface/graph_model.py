"""The configuration as a graph, derived from the tree (E34-T1, T4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agent.src.agent.config.paths import config_root

AGENT, SUBAGENT, SKILL, MCP, MODEL, CHANNEL = (
    "agent",
    "subagent",
    "skill",
    "mcp",
    "model",
    "channel",
)


def _first_time(node_id: str, seen: set[str]) -> bool:
    """Whether this id has been emitted already, remembering it."""
    if node_id in seen:
        return True
    seen.add(node_id)
    return False


def _text(path: Path) -> str:
    """What this file says *to the agent*, edits included."""
    from agent.src.agent.config.resolution import effective_text

    return effective_text(path)


def _load_yaml(path: Path) -> tuple[Any, str | None]:
    try:
        return yaml.safe_load(_text(path)) or {}, None
    except Exception as exc:  # noqa: BLE001 — any parse failure is the answer
        return {}, f"{type(exc).__name__}: {str(exc)[:200]}"


def _load_json(path: Path) -> tuple[Any, str | None]:
    """`mcp.json` is JSONC, so read it with the loader the agent uses."""
    from agent.src.agent.config.loader import _load_jsonc

    try:
        return _load_jsonc(path), None
    except Exception as exc:  # noqa: BLE001
        return {}, f"{type(exc).__name__}: {str(exc)[:200]}"


def _front_matter(path: Path) -> tuple[dict[str, Any], str | None]:
    """The `---` block at the top of a subagent or skill markdown file."""
    text = _text(path)
    if not text.startswith("---"):
        return {}, "no front matter"
    _, _, rest = text.partition("---")
    block, sep, _ = rest.partition("\n---")
    if not sep:
        return {}, "unterminated front matter"
    try:
        return yaml.safe_load(block) or {}, None
    except Exception as exc:  # noqa: BLE001
        return {}, f"{type(exc).__name__}: {str(exc)[:200]}"


def _node(
    node_id: str, kind: str, label: str, *, path: str | None = None, **extra: Any
) -> dict[str, Any]:
    return {"id": node_id, "kind": kind, "label": label, "path": path, **extra}


def _collect_skills(root: Path) -> list[dict[str, Any]]:
    out = []
    for skill_dir in sorted((root / "skills").glob("*/")):
        f = skill_dir / "SKILL.md"
        if not f.is_file():
            continue
        meta, err = _front_matter(f)
        name = meta.get("name") or skill_dir.name
        out.append(
            _node(
                f"skill:{name}",
                SKILL,
                name,
                path=str(f.relative_to(root)),
                error=err,
                description=(meta.get("description") or "").strip()[:200],
            )
        )
    return out


def _collect_subagents(root: Path) -> tuple[list[dict[str, Any]], dict[str, dict]]:
    nodes, meta_by_name = [], {}
    for f in sorted((root / "subagents").glob("*.md")):
        meta, err = _front_matter(f)
        name = meta.get("name") or f.stem
        meta_by_name[name] = meta
        nodes.append(
            _node(
                f"subagent:{name}",
                SUBAGENT,
                name,
                path=str(f.relative_to(root)),
                error=err,
                model=meta.get("model"),
                description=(meta.get("description") or "").strip()[:200],
            )
        )
    return nodes, meta_by_name


def _collect_mcp(root: Path) -> tuple[list[dict[str, Any]], str | None]:
    f = root / "integrations" / "mcp.json"
    if not f.is_file():
        return [], None
    data, err = _load_json(f)
    servers = (data or {}).get("mcpServers") or (data or {}).get("servers") or {}
    rel = str(f.relative_to(root))
    return [
        _node(f"mcp:{name}", MCP, name, path=rel, enabled=_enabled(cfg))
        for name, cfg in sorted(servers.items())
    ], err


def _enabled(cfg: Any) -> bool:
    return not (isinstance(cfg, dict) and cfg.get("disabled") is True)


def _collect_models(root: Path) -> tuple[list[dict[str, Any]], bool]:
    f = root / "runtime" / "router.yaml"
    if not f.is_file():
        return [], False
    data, _ = _load_yaml(f)
    rel = str(f.relative_to(root))
    tiers = data.get("tiers") or []
    return [
        _node(
            f"model:{t.get('model')}",
            MODEL,
            str(t.get("model")),
            path=rel,
            tier=t.get("name"),
        )
        for t in tiers
        if isinstance(t, dict) and t.get("model")
    ], bool(data.get("enabled"))


def _collect_channels(root: Path) -> list[dict[str, Any]]:
    f = root / "integrations" / "channels.yaml"
    if not f.is_file():
        return []
    data, _ = _load_yaml(f)
    rel = str(f.relative_to(root))
    entries = data.get("channels") or []
    return [
        _node(
            f"channel:{c.get('name') or c.get('type')}",
            CHANNEL,
            str(c.get("name") or c.get("type")),
            path=rel,
            enabled=bool(c.get("enabled")),
            type=c.get("type"),
        )
        for c in entries
        if isinstance(c, dict)
    ]


def _edge(src: str, dst: str, kind: str, *, broken: str | None = None) -> dict:
    return {"from": src, "to": dst, "kind": kind, "broken": broken}


def build_graph() -> dict[str, Any]:
    """Nodes, edges and unresolved references for the loaded tree."""
    root = config_root()
    agent_yaml, agent_err = _load_yaml(root / "runtime" / "agent.yaml")

    skills = _collect_skills(root)
    subagents, sub_meta = _collect_subagents(root)
    mcps, mcp_err = _collect_mcp(root)
    models, routing_on = _collect_models(root)
    channels = _collect_channels(root)

    declared = agent_yaml.get("model")
    agent_model = declared.get("name") if isinstance(declared, dict) else declared
    if isinstance(agent_model, str) and not any(
        n["label"] == agent_model for n in models
    ):
        models.append(
            _node(
                f"model:{agent_model}",
                MODEL,
                agent_model,
                path="runtime/agent.yaml",
                tier=None,
            )
        )

    root_node = _node(
        "agent:root",
        AGENT,
        str(agent_yaml.get("name") or "agent"),
        path="runtime/agent.yaml",
        error=agent_err,
        routing_enabled=routing_on,
    )

    ids = {n["id"] for n in [root_node, *skills, *subagents, *mcps, *models, *channels]}
    edges: list[dict[str, Any]] = []

    if isinstance(agent_model, str):
        edges.append(_edge("agent:root", f"model:{agent_model}", "uses-model"))
    for node in subagents:
        edges.append(_edge("agent:root", node["id"], "delegates-to"))
        meta = sub_meta.get(node["label"], {})
        for skill in meta.get("skills") or []:
            target = f"skill:{skill}"
            edges.append(
                _edge(
                    node["id"],
                    target,
                    "uses-skill",
                    broken=None
                    if target in ids
                    else f"no skill named '{skill}' in skills/",
                )
            )
        for server in meta.get("mcps") or []:
            target = f"mcp:{server}"
            edges.append(
                _edge(
                    node["id"],
                    target,
                    "uses-mcp",
                    broken=None
                    if target in ids
                    else f"no MCP server named '{server}' in integrations/mcp.json",
                )
            )
        if meta.get("model"):
            target = f"model:{meta['model']}"
            edges.append(
                _edge(
                    node["id"],
                    target,
                    "uses-model",
                    broken=None
                    if target in ids
                    else f"model '{meta['model']}' is named by no tier and is not the agent's model",
                )
            )
    for channel in channels:
        edges.append(_edge(channel["id"], "agent:root", "delivers-to"))

    seen: set[str] = set()
    nodes = [
        node
        for node in [root_node, *subagents, *skills, *mcps, *models, *channels]
        if not _first_time(node["id"], seen)
    ]

    for e in edges:
        if e["broken"] and e["to"] not in ids:
            kind = e["to"].split(":", 1)[0]
            nodes.append(_node(e["to"], kind, e["to"].split(":", 1)[1], missing=True))
            ids.add(e["to"])

    problems = [
        {"where": e["from"], "what": e["broken"]} for e in edges if e["broken"]
    ] + [{"where": n["id"], "what": n["error"]} for n in nodes if n.get("error")]
    if mcp_err:
        problems.append({"where": "integrations/mcp.json", "what": mcp_err})

    return {
        "root": str(root),
        "nodes": nodes,
        "edges": edges,
        "problems": problems,
        "element_types": sorted({n["kind"] for n in nodes}),
        "counts": {
            kind: sum(1 for n in nodes if n["kind"] == kind)
            for kind in sorted({n["kind"] for n in nodes})
        },
    }
