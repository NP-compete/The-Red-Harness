"""Laying out an answer part by part, with its sources attached."""

from __future__ import annotations

from dataclasses import dataclass

NO_ANSWER = "No answer was found for this."


@dataclass(frozen=True)
class Answered:
    """One part of a question, answered, with its sources."""

    question: str
    text: str
    sources: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject an answer that says nothing."""
        if not self.text.strip():
            raise ValueError("an answer must say something")


@dataclass(frozen=True)
class Section:
    """One part of the assembled answer, answered or not."""

    question: str
    text: str
    sources: tuple[str, ...]
    answered: bool
    unsourced: bool


@dataclass(frozen=True)
class Assembled:
    """The whole answer, its sources, and whether anything was left out."""

    sections: tuple[Section, ...]
    all_sources: tuple[str, ...]
    complete: bool
    use_headings: bool


def assemble(answers: tuple[Answered, ...], *, asked: tuple[str, ...]) -> Assembled:
    """Assemble `answers` into one answer covering everything `asked`."""
    if not asked:
        raise ValueError("nothing was asked")

    questions = [answer.question for answer in answers]
    if len(questions) != len(set(questions)):
        raise ValueError("a part cannot be answered twice")

    stray = sorted(set(questions) - set(asked))
    if stray:
        raise ValueError(f"answers to things nobody asked: {', '.join(stray)}")

    by_question = {answer.question: answer for answer in answers}

    sections = tuple(
        _section(question, by_question.get(question)) for question in asked
    )

    return Assembled(
        sections=sections,
        all_sources=tuple(sorted({source for s in sections for source in s.sources})),
        complete=all(section.answered for section in sections),
        use_headings=len(asked) > 1,
    )


def _section(question: str, answer: Answered | None) -> Section:
    """The section for `question`, standing in if it was not answered."""
    if answer is None:
        return Section(
            question=question,
            text=NO_ANSWER,
            sources=(),
            answered=False,
            unsourced=False,
        )

    return Section(
        question=question,
        text=answer.text,
        sources=tuple(sorted(set(answer.sources))),
        answered=True,
        unsourced=not answer.sources,
    )
