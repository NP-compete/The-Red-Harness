"""The preflight must look at the arguments, not the envelope."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from agent.src.security.tool_preflight import look_before


class _Args(BaseModel):
    question: str


class _Tool:
    name = "ask"
    description = "Ask something"
    args_schema = _Args


def _call(**args):
    return {"name": "ask", "args": args, "id": "call-1", "type": "tool_call"}


class TestTheEnvelopeIsUnwrapped:
    def test_a_good_call_is_permitted(self):
        assert look_before(_Tool(), _call(question="how many?")).permitted is True

    def test_a_call_missing_a_required_argument_is_still_refused(self):
        assert look_before(_Tool(), _call()).permitted is False

    def test_the_refusal_still_names_the_argument(self):
        assert "question" in look_before(_Tool(), _call()).reason

    def test_a_wrongly_typed_argument_is_still_refused(self):
        assert (
            look_before(_Tool(), _call(question={"not": "a string"})).permitted is False
        )

    def test_bare_arguments_still_work(self):
        assert look_before(_Tool(), {"question": "how many?"}).permitted is True

    def test_an_envelope_with_no_args_is_refused_like_empty_arguments(self):
        assert look_before(_Tool(), {"name": "ask", "id": "call-1"}).permitted is False

    def test_a_tool_whose_own_arguments_are_called_name_and_id_still_works(self):
        class _Odd(BaseModel):
            name: str
            id: str

        class _OddTool:
            name = "odd"
            description = ""
            args_schema = _Odd

        assert look_before(_OddTool(), {"name": "x", "id": "y"}).permitted is True

    def test_a_tool_call_for_a_tool_with_no_required_arguments_runs(self):
        class _Bare:
            name = "ls"
            description = ""
            args_schema = None

        assert look_before(_Bare(), _call()).permitted is True


class TestTheRefusalIsShapedForTheGraph:
    """A refusal must be something the graph can put on the turn."""

    @staticmethod
    async def _refused(response_format):
        from langchain_core.tools import StructuredTool

        from agent.src.capability.manifest import CapabilityManifest
        from agent.src.capability.tool_proxy import CapabilityToolProxy

        def _run(question: str):
            return ("ran", []) if response_format == "content_and_artifact" else "ran"

        inner = StructuredTool.from_function(
            func=_run,
            name="ask",
            description="Ask something",
            args_schema=_Args,
            response_format=response_format,
        )
        proxy = CapabilityToolProxy(
            inner,
            CapabilityManifest(
                agent_name="agent",
                allowed_tool_names=frozenset({"ask"}),
                source="EXPLICIT",
            ),
        )
        return await proxy.ainvoke(_call())

    @pytest.mark.asyncio
    async def test_a_plain_tool_gets_a_message(self):
        found = await self._refused("content")
        assert "question" in str(found)

    @pytest.mark.asyncio
    async def test_a_tool_that_returns_an_artifact_does_not_get_a_bare_string(self):
        found = await self._refused("content_and_artifact")
        assert not isinstance(found, str)

    @pytest.mark.asyncio
    async def test_the_reason_still_reaches_the_model(self):
        found = await self._refused("content_and_artifact")
        assert "question" in str(getattr(found, "content", found))

    @pytest.mark.asyncio
    async def test_it_is_marked_as_a_failure_rather_than_an_answer(self):
        found = await self._refused("content_and_artifact")
        assert getattr(found, "status", "") == "error"

    @pytest.mark.asyncio
    async def test_it_carries_the_call_it_answers(self):
        found = await self._refused("content_and_artifact")
        assert getattr(found, "tool_call_id", "") == "call-1"
