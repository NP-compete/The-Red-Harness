"""Presidio-backed PII detection engine."""

from __future__ import annotations

from typing import Any

from agent.src.pii.config import PIIRule
from agent.src.pii.detector import PIIMatch

_RULE_TO_ENTITY: dict[str, str] = {
    "email": "EMAIL_ADDRESS",
    "phone": "PHONE_NUMBER",
    "credit_card": "CREDIT_CARD",
    "ssn": "US_SSN",
    "ip_address": "IP_ADDRESS",
    "iban": "IBAN_CODE",
    "address": "LOCATION",
}


_nlp_engine = None


def _shared_nlp_engine() -> Any:
    """The spaCy pipeline, loaded once for the process.

    A bare `AnalyzerEngine()` loads its own, and a detector is built
    per rule set — forty-three of them in one test file came to four
    gigabytes resident, which is how an xdist worker was killed in
    the pipeline with nothing to show but "worker crashed". Only the
    model is shared; the recognizer registry stays per instance,
    because custom rules are registered into it and one detector's
    patterns have no business in another's.
    """
    global _nlp_engine
    if _nlp_engine is None:
        from presidio_analyzer.nlp_engine import NlpEngineProvider

        _nlp_engine = NlpEngineProvider().create_engine()
    return _nlp_engine


class PresidioDetector:
    """Detects PII using Presidio's AnalyzerEngine."""

    def __init__(self, rules: list[PIIRule]) -> None:
        """Build analyzer with entity mappings for the given rules."""
        from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer

        self._entities: list[str] = []
        self._entity_to_rule: dict[str, PIIRule] = {}

        analyzer = AnalyzerEngine(nlp_engine=_shared_nlp_engine())

        supported = set(analyzer.get_supported_entities())

        for rule in rules:
            if rule.pattern_type == "builtin":
                entity_type = _RULE_TO_ENTITY.get(rule.name)
                if entity_type is None:
                    candidate = rule.name.upper()
                    if candidate in supported:
                        entity_type = candidate
                if entity_type is None:
                    raise ValueError(
                        f"Presidio: no entity mapping for '{rule.name}'. "
                        f"Add it to _RULE_TO_ENTITY or use a name that matches a "
                        f"Presidio entity (e.g. 'us_passport' → 'US_PASSPORT'). "
                        f"Supported: {sorted(supported)}"
                    )
            else:
                if not rule.regex:
                    raise ValueError(
                        f"Custom rule '{rule.name}' must specify a 'regex' field."
                    )
                entity_type = rule.name.upper()
                recognizer = PatternRecognizer(
                    supported_entity=entity_type,
                    patterns=[Pattern(name=rule.name, regex=rule.regex, score=0.9)],
                )
                analyzer.registry.add_recognizer(recognizer)

            self._entities.append(entity_type)
            self._entity_to_rule[entity_type] = rule

        self._analyzer = analyzer

    def find_all(self, text: str) -> list[PIIMatch]:
        """Return all non-overlapping PII matches ordered by position."""
        if not text or not self._entities:
            return []

        results = self._analyzer.analyze(
            text=text, entities=self._entities, language="en"
        )
        results.sort(key=lambda r: (r.start, r.end))

        deduped: list[PIIMatch] = []
        last_end = -1
        for result in results:
            if result.start < last_end:
                continue
            rule = self._entity_to_rule.get(result.entity_type)
            if rule is None:
                continue
            deduped.append(
                PIIMatch(
                    start=result.start,
                    end=result.end,
                    value=text[result.start : result.end],
                    rule_name=rule.name,
                    label=rule.effective_label(),
                    action=rule.action.value,
                )
            )
            last_end = result.end

        return deduped
