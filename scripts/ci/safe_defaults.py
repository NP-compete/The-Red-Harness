"""A setting that widens exposure defaults to off (CFG-3)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services"))

WIDENS_EXPOSURE: dict[str, str] = {
    "REQUEST_LOG_HEADERS": (
        "writes request headers to the log, and `Authorization` is a header"
    ),
    "REQUEST_LOG_BODY": (
        "writes request bodies to the log, and a request body is what somebody typed"
    ),
    "ENABLE_DCR_REREGISTER_API": (
        "exposes an endpoint that re-registers OAuth clients against a provider"
    ),
}

NARROWS_EXPOSURE = (
    "ENABLE_AUTH",
    "MCP_BLOCK_SECRETS",
    "GUARDIAN_SSL_VERIFY",
    "PLATFORM_AUDIT_ENABLED",
)

CONFIG_DEFAULTS: dict[tuple[str, str, str], tuple[object, str]] = {
    ("agent.src.agent.config.otel", "OtelExporterConfig", "insecure"): (
        False,
        "OBS-2: telemetry goes over TLS unless a deployment says otherwise. "
        "This shipped True, so trace ids, user ids, model names and token "
        "counts left the pod in plaintext by default",
    ),
}


def _config_defaults() -> list[str]:
    """Every config field whose default disagrees with what is wanted."""
    import importlib

    found: list[str] = []
    for (module, klass, field), (want, why) in CONFIG_DEFAULTS.items():
        model = getattr(importlib.import_module(module), klass)
        got = model.model_fields[field].default
        if got is not want:
            found.append(f"{klass}.{field} defaults to {got!r}, want {want!r}. {why}.")
    return found


def _defaults() -> dict[str, object]:
    """The default of every settings field."""
    from agent.src.settings import Settings

    return {name: field.default for name, field in Settings.model_fields.items()}


def problems() -> list[str]:
    """Every setting whose default does not match the safe one."""
    declared = _defaults()
    found: list[str] = []

    for name, exposes in WIDENS_EXPOSURE.items():
        if name not in declared:
            found.append(f"{name} is on the list and is not a setting any more")
        elif declared[name] is not False:
            found.append(
                f"{name} defaults to {declared[name]!r} and it {exposes}. "
                "A setting that widens exposure ships off."
            )

    for name in NARROWS_EXPOSURE:
        if name not in declared:
            found.append(f"{name} is listed as a control and is not a setting")
        elif declared[name] is not True:
            found.append(
                f"{name} defaults to {declared[name]!r}. It narrows exposure, "
                "so off is the hole — if this was deliberate, move it."
            )

    found += _config_defaults()
    return found


def main() -> int:
    """Check that settings default to the safe side."""
    found = problems()
    print(f"  {len(WIDENS_EXPOSURE)} setting(s) that widen exposure, each off:")
    for name in sorted(WIDENS_EXPOSURE):
        print(f"    {name}")
    print(f"  {len(NARROWS_EXPOSURE)} that narrow it, each on")
    for (_module, klass, field), (want, _why) in sorted(CONFIG_DEFAULTS.items()):
        print(f"    config    {klass}.{field} = {want!r}")

    if not found:
        print("\nevery exposure-widening setting ships off")
        return 0
    print("\nsafe defaults do not hold:", file=sys.stderr)
    for one in found:
        print(f"  {one}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
