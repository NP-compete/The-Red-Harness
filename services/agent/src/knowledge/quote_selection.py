"""Choosing the passage to show as evidence for a claim."""

from __future__ import annotations

import re
from dataclasses import dataclass

DEFAULT_MAX_WORDS = 40

_SENTENCE = re.compile(r"[^.!?]+[.!?]?")
_WORD = re.compile(r"[A-Za-z0-9]+")

_STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "to",
    "of",
    "and",
    "or",
    "in",
    "on",
    "for",
    "with",
    "that",
    "this",
    "it",
    "its",
    "as",
    "at",
    "by",
    "from",
    "per",
    "has",
    "have",
}

_LEANING = {
    "it",
    "its",
    "they",
    "them",
    "their",
    "this",
    "that",
    "these",
    "those",
    "he",
    "she",
}


@dataclass(frozen=True)
class Passage:
    """One passage a quote could be taken from."""

    source: str
    text: str

    def __post_init__(self) -> None:
        """Reject a passage with nothing to quote."""
        if not self.text.strip():
            raise ValueError("there is nothing here to quote")


@dataclass(frozen=True)
class Quote:
    """The chosen quote, where it starts, and whether it was shortened."""

    source: str
    text: str
    offset: int
    shortened: bool


def _content(text: str) -> set[str]:
    """The meaningful words of `text`, lowercased."""
    return {word.lower() for word in _WORD.findall(text)} - _STOPWORDS


def _sentences(text: str) -> list[tuple[int, str]]:
    """Each sentence of `text` with the offset it starts at."""
    found = []
    for match in _SENTENCE.finditer(text):
        body = match.group().strip()
        if body:
            found.append((match.start() + match.group().index(body[0]), body))
    return found


def _shorten(sentence: str, wanted: set[str], max_words: int) -> str:
    """`sentence` trimmed to `max_words` around the words that matter."""
    words = sentence.split()
    hits = [i for i, word in enumerate(words) if _content(word) & wanted]
    centre = (hits[0] + hits[-1]) // 2 if hits else 0
    start = max(0, min(centre - max_words // 2, len(words) - max_words))
    return " ".join(words[start : start + max_words])


def choose_quote(
    passage: Passage, *, claim: str, max_words: int = DEFAULT_MAX_WORDS
) -> Quote | None:
    """Choose the best evidence for `claim` from `passage`."""
    if not claim.strip():
        raise ValueError("there is no claim to find evidence for")
    if max_words < 1:
        raise ValueError("a quote needs room for at least one word")

    wanted = _content(claim)
    sentences = _sentences(passage.text)

    best = max(
        range(len(sentences)),
        key=lambda i: len(_content(sentences[i][1]) & wanted),
        default=None,
    )
    if best is None or not _content(sentences[best][1]) & wanted:
        return None

    offset, text = sentences[best]
    leading = _WORD.findall(text)[:1]
    if best > 0 and leading and leading[0].lower() in _LEANING:
        offset, before = sentences[best - 1]
        text = f"{before} {text}"

    shortened = len(text.split()) > max_words
    if shortened:
        text = _shorten(text, wanted, max_words)

    return Quote(source=passage.source, text=text, offset=offset, shortened=shortened)
