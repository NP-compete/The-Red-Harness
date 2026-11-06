"""The notes an answer carries about how far it can be trusted."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from agent.src.agent.answer_confidence import Signals, decide_stance
from agent.src.knowledge.numeric_check import check_numbers

router = APIRouter(prefix="/answers", tags=["answers"])


class Source(BaseModel):
    """One source an answer rests on."""

    id: str
    text: str = ""


class NotesRequest(BaseModel):
    """Request body asking for notes on an answer."""

    answer: str
    sources: list[Source] = Field(default_factory=list)
    coverage: float = Field(ge=0.0, le=1.0)
    claims_supported: float = Field(ge=0.0, le=1.0)
    sources_disagree: bool = False
    oldest_source_days: int = Field(default=0, ge=0)
    freshness_matters: bool = False
    built_on_untrusted: bool = False
    withheld: int = Field(default=0, ge=0)
    requestable: list[str] = Field(default_factory=list)

    @field_validator("answer")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        """Reject an answer with nothing in it."""
        if not value.strip():
            raise ValueError("there is no answer to take notes on")
        return value


class FiguresOut(BaseModel):
    """How many figures were checked, and which went unsupported."""

    checked: int = 0
    unsupported: list[Any] = []


class AccessOut(BaseModel):
    """What was withheld from the answer, and what could be requested."""

    withheld: int = 0
    requestable: list[Any] = []
    nothing_left: bool = False


class AnswerNoteOut(BaseModel):
    """What the agent will say about its own answer."""

    stance: str
    hedge: str = ""
    concerns: list[Any] = []
    what_would_help: list[Any] = []
    figures: FiguresOut
    access: AccessOut


@router.post("/notes", responses={200: {"model": AnswerNoteOut}})
async def answer_notes(request: NotesRequest) -> dict:
    """Take notes on an answer: its stance, figures and withheld sources."""
    stated = decide_stance(
        Signals(
            coverage=request.coverage,
            claims_supported=request.claims_supported,
            sources=len(request.sources),
            sources_disagree=request.sources_disagree,
            oldest_source_days=request.oldest_source_days,
            freshness_matters=request.freshness_matters,
            built_on_untrusted=request.built_on_untrusted,
        )
    )

    read = [source.text for source in request.sources if source.text.strip()]
    figures = check_numbers(request.answer, read=read) if read else None

    return {
        "stance": stated.stance.value,
        "hedge": stated.hedge,
        "concerns": stated.concerns,
        "what_would_help": stated.what_would_help,
        "figures": {
            "checked": figures.checked if figures else 0,
            "unsupported": figures.unsupported if figures else [],
        },
        "access": {
            "withheld": request.withheld,
            "requestable": request.requestable,
            "nothing_left": request.withheld > 0 and not request.sources,
        },
    }
