"""Looking at a tool call before making it."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field

from agent.src.security.tool_preflight import LIVE_CHECKS, look_before


class _Args(BaseModel):
    question: str = Field(description="what to ask")
    count: int = 1


class _Tool:
    name = "ask"
    args_schema = _Args


class TestArgumentsThatFit:
    def test_the_call_is_permitted(self):
        found = look_before(_Tool(), {"question": "how many?"})
        assert found.permitted is True

    def test_optional_arguments_may_be_left_out(self):
        assert look_before(_Tool(), {"question": "how many?"}).permitted is True

    def test_and_may_be_given(self):
        found = look_before(_Tool(), {"question": "how many?", "count": 3})
        assert found.permitted is True


class TestArgumentsThatDoNot:
    def test_a_missing_one_is_refused(self):
        assert look_before(_Tool(), {}).permitted is False

    def test_the_refusal_names_the_tool(self):
        assert "ask" in look_before(_Tool(), {}).reason

    def test_the_refusal_says_which_argument(self):
        assert "question" in look_before(_Tool(), {}).reason

    def test_a_wrong_type_is_refused(self):
        found = look_before(_Tool(), {"question": "x", "count": "many"})
        assert found.permitted is False

    def test_it_is_not_worth_retrying_unchanged(self):
        assert look_before(_Tool(), {}).retryable is False


class TestWhatIsNotCheckedYet:
    def test_a_tool_with_no_schema_is_permitted(self):
        class _Bare:
            name = "ls"
            args_schema = None

        assert look_before(_Bare(), {"anything": 1}).permitted is True

    def test_the_dormant_checks_are_named(self):
        assert "arguments" in LIVE_CHECKS
        assert len(LIVE_CHECKS) < 7

    def test_a_schema_that_cannot_be_read_permits_the_call(self):
        class _Broken:
            name = "odd"

            class args_schema:  # noqa: N801
                @staticmethod
                def model_validate(_data):
                    raise RuntimeError("not really a schema")

        assert look_before(_Broken(), {}).permitted is True


class TestTheRefusalIsUsable:
    def test_it_comes_back_as_words(self):
        assert isinstance(look_before(_Tool(), {}).reason, str)

    def test_it_is_not_an_exception(self):
        look_before(_Tool(), {})

    @pytest.mark.parametrize("arguments", [None, "not a mapping", 7])
    def test_arguments_that_are_not_a_mapping_are_refused_not_crashed(self, arguments):
        assert look_before(_Tool(), arguments).permitted is False


class TestItRunsBeforeTheToolDoes:
    """A check nothing calls looks at nothing."""

    @staticmethod
    def _proxy(inner):
        from agent.src.capability.manifest import CapabilityManifest
        from agent.src.capability.tool_proxy import CapabilityToolProxy

        return CapabilityToolProxy(
            inner_tool=inner,
            manifest=CapabilityManifest(
                agent_name="test",
                allowed_tool_names=frozenset({inner.name}),
                source="EXPLICIT",
            ),
        )

    @pytest.mark.asyncio
    async def test_a_bad_call_never_reaches_the_tool(self):
        reached = []

        class _Inner:
            name = "ask"
            args_schema = _Args
            description = "ask something"

            async def ainvoke(self, value, config=None, **kwargs):
                reached.append(value)
                return "ran"

        found = await self._proxy(_Inner()).ainvoke({})
        assert reached == []

    @pytest.mark.asyncio
    async def test_the_model_is_told_why(self):
        class _Inner:
            name = "ask"
            args_schema = _Args
            description = "ask something"

            async def ainvoke(self, value, config=None, **kwargs):
                return "ran"

        found = await self._proxy(_Inner()).ainvoke({})
        assert "question" in str(found)

    @pytest.mark.asyncio
    async def test_a_good_call_goes_through_untouched(self):
        class _Inner:
            name = "ask"
            args_schema = _Args
            description = "ask something"

            async def ainvoke(self, value, config=None, **kwargs):
                return f"ran with {value}"

        found = await self._proxy(_Inner()).ainvoke({"question": "how many?"})
        assert "ran with" in str(found)


class TestTheShapeIsNowOneOfThem:
    """A tool that changed since this run started is refused."""

    @staticmethod
    def _memory():
        from agent.src.security.tool_fingerprint import ShapeMemory

        return ShapeMemory()

    def test_the_shape_is_a_live_check_now(self):
        assert "shape" in LIVE_CHECKS

    def test_a_tool_seen_for_the_first_time_runs(self):
        found = look_before(_Tool(), {"question": "x"}, shapes=self._memory())
        assert found.permitted is True

    def test_the_same_tool_twice_runs(self):
        memory = self._memory()
        look_before(_Tool(), {"question": "x"}, shapes=memory)
        assert look_before(_Tool(), {"question": "x"}, shapes=memory).permitted is True

    def test_a_tool_that_gains_an_argument_is_refused(self):
        memory = self._memory()
        look_before(_Tool(), {"question": "x"}, shapes=memory)

        class _Wider(BaseModel):
            question: str
            count: int = 1
            path: str = ""

        class _Changed:
            name = "ask"
            args_schema = _Wider

        assert (
            look_before(_Changed(), {"question": "x"}, shapes=memory).permitted is False
        )

    def test_the_refusal_names_the_argument_that_appeared(self):
        memory = self._memory()
        look_before(_Tool(), {"question": "x"}, shapes=memory)

        class _Wider(BaseModel):
            question: str
            count: int = 1
            path: str = ""

        class _Changed:
            name = "ask"
            args_schema = _Wider

        found = look_before(_Changed(), {"question": "x"}, shapes=memory)
        assert "path" in found.reason

    def test_the_refusal_is_not_worth_retrying(self):
        memory = self._memory()
        look_before(_Tool(), {"question": "x"}, shapes=memory)

        class _Wider(BaseModel):
            question: str
            count: int = 1
            path: str = ""

        class _Changed:
            name = "ask"
            args_schema = _Wider

        assert (
            look_before(_Changed(), {"question": "x"}, shapes=memory).retryable is False
        )

    def test_a_tool_with_no_name_is_not_shape_checked(self):
        class _Nameless:
            name = ""
            args_schema = _Args

        memory = self._memory()
        look_before(_Nameless(), {"question": "x"}, shapes=memory)
        assert look_before(_Tool(), {"question": "x"}, shapes=memory).permitted is True

    def test_it_uses_one_memory_across_calls_by_default(self):
        from agent.src.security import tool_preflight

        assert tool_preflight.remembered_shapes() is tool_preflight.remembered_shapes()
