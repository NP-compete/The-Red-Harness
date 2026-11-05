"""PII scrubbing engine with per-request token map."""

import hashlib
import hmac
import os
import re
from contextvars import ContextVar
from typing import Any

from agent.src.pii.config import PIIConfig
from agent.src.pii.detector import PIIDetector, PIIMatch
from agent.utils.pylogger import get_python_logger

logger = get_python_logger()

_token_map: ContextVar[dict[str, str] | None] = ContextVar(
    "pii_token_map", default=None
)
_value_map: ContextVar[dict[str, str] | None] = ContextVar(
    "pii_value_map", default=None
)
_label_counters: ContextVar[dict[str, int] | None] = ContextVar(
    "pii_label_counters", default=None
)

_shared_token_map_ref: ContextVar[dict[str, str] | None] = ContextVar(
    "pii_shared_token_map_ref", default=None
)

try:
    from cachetools import TTLCache

    _thread_token_maps: TTLCache = TTLCache(maxsize=10_000, ttl=7 * 86_400)
except ImportError:
    _thread_token_maps: dict = {}  # type: ignore[no-redef]

_TOKEN_RE = re.compile(r"\[([A-Z_]+)_(\d+)\]")

_ID_LIKE_KEYS = frozenset(
    {
        "id",
        "run_id",
        "parent_run_id",
        "tool_call_id",
        "thread_id",
        "checkpoint_id",
        "checkpoint_ns",
        "trace_id",
        "span_id",
        "session_id",
        "request_id",
        "correlation_id",
        "call_id",
    }
)


class PerRuleDetector:
    """Routes each rule to its configured detector backend (regex / presidio / custom)."""

    def __init__(self, rules: list) -> None:
        """Build regex and/or Presidio sub-detectors from the rule list."""
        regex_rules = [r for r in rules if r.detector in ("regex", "custom")]
        presidio_rules = [r for r in rules if r.detector == "presidio"]

        self._regex = PIIDetector(regex_rules) if regex_rules else None
        if presidio_rules:
            try:
                from agent.src.pii.presidio_detector import PresidioDetector
            except ImportError as missing:  # pragma: no cover - slim image only
                names = ", ".join(sorted(r.name for r in presidio_rules))
                raise RuntimeError(
                    f"PII rules {names} need the presidio detector, which "
                    "this image does not contain. Use the full image, or "
                    "change those rules to a provider that is present "
                    "(regex, custom). Built with VENV_STAGE=deps-slim."
                ) from missing

            self._presidio: Any = PresidioDetector(presidio_rules)
        else:
            self._presidio = None

    def find_all(self, text: str) -> list[PIIMatch]:
        """Return all non-overlapping PII matches ordered by position."""
        combined: list[PIIMatch] = []
        if self._regex:
            combined.extend(self._regex.find_all(text))
        if self._presidio:
            combined.extend(self._presidio.find_all(text))
        combined.sort(key=lambda m: (m.start, m.end))
        deduped: list[PIIMatch] = []
        last_end = -1
        for match in combined:
            if match.start >= last_end:
                deduped.append(match)
                last_end = match.end
        return deduped


def _build_detector(config: PIIConfig) -> Any:
    """Build a PerRuleDetector from the config rules."""
    if not config.rules:
        if config.enabled:
            logger.warning(
                "pii_enabled_no_rules: PII is enabled but no rules are defined — scrubbing is inactive"
            )
        return None
    return PerRuleDetector(config.rules)


class PIIScrubber:
    """Scrubs and restores PII values using a per-request token map."""

    def __init__(self, config: PIIConfig, hash_key: bytes = b"") -> None:
        """Build the scrubber and its per-strategy detectors from config."""
        self._config = config
        self._detector = _build_detector(config)
        self._hash_key = hash_key or os.urandom(32)
        block_rules = [r for r in config.rules if r.action.value == "block"]
        self._block_rule_names: frozenset[str] = frozenset(r.name for r in block_rules)
        self._block_detector = (
            _build_detector(PIIConfig(enabled=True, rules=block_rules))
            if block_rules
            else None
        )

    def _get_map(self) -> dict[str, str]:
        m = _token_map.get()
        if m is None:
            m = {}
            _token_map.set(m)
        return m

    def _get_value_map(self) -> dict[str, str]:
        """Reverse map: value → token. O(1) lookup to avoid duplicate token assignment."""
        vm = _value_map.get()
        if vm is None:
            existing = _token_map.get()
            vm = {v: k for k, v in existing.items()} if existing else {}
            _value_map.set(vm)
        return vm

    def _get_counters(self) -> dict[str, int]:
        c = _label_counters.get()
        if c is None:
            c = {}
            _label_counters.set(c)
        return c

    def _assign_token(self, value: str, label: str) -> str:
        """Return an existing token for *value* or create a new one — O(1) via reverse map."""
        vm = self._get_value_map()
        existing = vm.get(value)
        if existing:
            return existing
        counters = self._get_counters()
        n = counters.get(label, 0) + 1
        counters[label] = n
        token = f"[{label}_{n}]"
        self._get_map()[token] = value
        vm[value] = token
        return token

    def _mask_value(self, value: str) -> str:
        """Mask a value, preserving the last 4 chars."""
        if len(value) <= 4:
            return "*" * len(value)
        return "*" * (len(value) - 4) + value[-4:]

    def _hash_value(self, value: str) -> str:
        digest = hmac.new(self._hash_key, value.encode(), hashlib.sha256).hexdigest()[
            :12
        ]
        return f"[HASH:{digest}]"

    def _apply_matches(self, text: str, matches: list, *, one_way: bool) -> str:
        parts: list[str] = []
        cursor = 0
        for m in matches:
            parts.append(text[cursor : m.start])
            if m.action == "hash":
                parts.append(self._hash_value(m.value))
            elif m.action in ("tokenize", "scrub") and not one_way:
                parts.append(self._assign_token(m.value, m.label))
            elif m.action == "mask":
                parts.append(self._mask_value(m.value))
            else:
                parts.append("***REDACTED***")
            cursor = m.end
        parts.append(text[cursor:])
        return "".join(parts)

    def scrub(self, text: str) -> str:
        """Replace PII in *text* using the token map (tokenize rules are reversible)."""
        if not text or not self._detector:
            return text
        matches = self._detector.find_all(text)
        return self._apply_matches(text, matches, one_way=False) if matches else text

    def restore(self, text: str) -> str:
        """Replace tokens in *text* with their original values."""
        if not text:
            return text
        token_map = _token_map.get()
        if not token_map:
            return text
        for token, value in token_map.items():
            if token in text:
                text = text.replace(token, value)
        return text

    def scrub_one_way(self, text: str) -> str:
        """Stateless one-way sanitization for logs/observability — token map not modified."""
        if not text or not self._detector:
            return text
        matches = self._detector.find_all(text)
        return self._apply_matches(text, matches, one_way=True) if matches else text

    def scrub_for_trace_hash(self, text: str) -> str:
        """Like scrub_one_way but replaces all PII with deterministic HMAC hashes."""
        if not text or not self._detector:
            return text
        matches = self._detector.find_all(text)
        if not matches:
            return text
        parts: list[str] = []
        cursor = 0
        for m in matches:
            parts.append(text[cursor : m.start])
            parts.append(self._hash_value(m.value))
            cursor = m.end
        parts.append(text[cursor:])
        return "".join(parts)

    def set_shared_container(self, container: dict[str, str]) -> None:
        """Register *container* as the shared token map target for this request."""
        _shared_token_map_ref.set(container)
        self._instance_container: "dict[str, str] | None" = container

    def _get_shared_container(self) -> "dict[str, str] | None":
        return _shared_token_map_ref.get() or getattr(self, "_instance_container", None)

    def snapshot_to_container(self) -> None:
        """Copy the current token map into the shared container (if registered)."""
        container = self._get_shared_container()
        if container is not None:
            container.update(self.snapshot_token_map())

    def load_token_map(self, token_map: dict[str, str]) -> None:
        """Populate the ContextVar token map from a cached snapshot."""
        _token_map.set(dict(token_map))
        _value_map.set({v: k for k, v in token_map.items()})
        counters: dict[str, int] = {}
        for token in token_map:
            m = _TOKEN_RE.fullmatch(token)
            if m:
                label, n = m.group(1), int(m.group(2))
                counters[label] = max(counters.get(label, 0), n)
        _label_counters.set(counters)

    def snapshot_token_map(self) -> dict[str, str]:
        """Return a copy of the current token map for Redis persistence."""
        return dict(_token_map.get() or {})

    def load_thread_map(self, thread_id: str) -> None:
        """Seed the per-request ContextVar map from the stable thread store."""
        existing = _thread_token_maps.get(thread_id)
        if existing:
            self.load_token_map(existing)

    def save_thread_map(self, thread_id: str) -> None:
        """Merge the current ContextVar map back into the stable thread store."""
        current = self.snapshot_token_map()
        if current:
            stored = _thread_token_maps.setdefault(thread_id, {})
            stored.update(current)
