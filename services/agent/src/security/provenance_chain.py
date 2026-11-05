"""Everything needed to say where a result came from."""

from __future__ import annotations

from dataclasses import dataclass

_REQUIRED = {
    "config_fingerprint": "the configuration that produced it",
    "model": "the model that answered",
    "image": "the build that ran",
    "resolver_version": "the decision rules in force",
}


@dataclass(frozen=True)
class Provenance:
    """Everything that identifies what produced a run."""

    config_fingerprint: str
    schema_version: int
    resolver_version: str
    model: str
    rate_card_version: str
    image: str

    def __post_init__(self) -> None:
        """Reject a schema version below one."""
        if self.schema_version <= 0:
            raise ValueError("a configuration schema version starts at 1")


@dataclass(frozen=True)
class Verification:
    """Whether a provenance record is complete."""

    ok: bool
    missing: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def verify(provenance: Provenance) -> Verification:
    """Check that `provenance` records everything it must."""
    missing = tuple(
        description
        for field, description in _REQUIRED.items()
        if not str(getattr(provenance, field)).strip()
    )

    notes = (
        ("no rate card recorded, so this result cannot be priced",)
        if not provenance.rate_card_version.strip()
        else ()
    )

    return Verification(ok=not missing, missing=missing, notes=notes)


def describe(provenance: Provenance) -> str:
    """A one-line description of what produced a run."""
    return (
        f"configuration {provenance.config_fingerprint} "
        f"(schema {provenance.schema_version}), "
        f"model {provenance.model}, build {provenance.image}, "
        f"rules {provenance.resolver_version}"
    )
