"""Following redirects, checking each hop as if it were the first."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from agent.src.security.url_safety import check_url


@dataclass(frozen=True)
class FollowResult:
    """Where a redirect chain ended, and why it stopped."""

    ok: bool
    final: str = ""
    chain: tuple[str, ...] = ()
    reason: str = ""


def follow(
    url: str,
    *,
    next_hop: Callable[[str], str | None],
    allowed_hosts: list[str],
    max_hops: int = 5,
) -> FollowResult:
    """Follow redirects from `url`, checking every hop against `allowed_hosts`."""
    if max_hops <= 0:
        raise ValueError(
            "a fetch that may not follow anything needs no redirect handling"
        )

    chain: list[str] = []
    seen: set[str] = set()
    current = url

    for _ in range(max_hops):
        checked = check_url(current, allowed_hosts=allowed_hosts)
        if not checked.ok:
            return FollowResult(
                ok=False,
                chain=tuple(chain),
                reason=f"{checked.reason}: {checked.host or current}",
            )

        if current in seen:
            return FollowResult(
                ok=False,
                chain=tuple(chain),
                reason="this redirect loops back on itself",
            )

        seen.add(current)
        chain.append(current)

        following = next_hop(current)
        if following is None:
            return FollowResult(ok=True, final=current, chain=tuple(chain))
        current = following

    return FollowResult(
        ok=False, chain=tuple(chain), reason="too many redirect hops to follow safely"
    )
