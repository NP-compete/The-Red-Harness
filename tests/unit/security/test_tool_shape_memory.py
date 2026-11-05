"""Noticing that a tool stopped being the tool that was approved."""

from __future__ import annotations

from pydantic import BaseModel

from agent.src.security.tool_fingerprint import ShapeMemory, ToolShape, shape_of


class _Ask(BaseModel):
    question: str


class _Tool:
    name = "ask"
    description = "Ask a question"
    args_schema = _Ask


class TestReadingAToolsShape:
    def test_it_takes_the_name(self):
        assert shape_of(_Tool()).name == "ask"

    def test_it_takes_the_description(self):
        assert shape_of(_Tool()).description == "Ask a question"

    def test_it_takes_the_arguments(self):
        assert "question" in shape_of(_Tool()).parameters

    def test_it_takes_which_arguments_are_required(self):
        assert shape_of(_Tool()).required == ("question",)

    def test_a_tool_with_no_schema_still_has_a_shape(self):
        class _Bare:
            name = "bare"
            description = ""

        assert shape_of(_Bare()).name == "bare"

    def test_an_unreadable_schema_does_not_raise(self):
        class _Broken:
            name = "broken"
            description = ""
            args_schema = "not really a schema"

        assert shape_of(_Broken()).parameters == {}


class TestTheFirstSight:
    def test_a_tool_never_seen_before_is_permitted(self):
        ok, _why = ShapeMemory().check(shape_of(_Tool()))
        assert ok is True

    def test_seeing_the_same_tool_twice_is_permitted(self):
        memory = ShapeMemory()
        memory.check(shape_of(_Tool()))
        ok, _why = memory.check(shape_of(_Tool()))
        assert ok is True


class TestAWidening:
    @staticmethod
    def _after(current: ToolShape):
        memory = ShapeMemory()
        memory.check(shape_of(_Tool()))
        return memory.check(current)

    def test_a_new_argument_is_refused(self):
        ok, _why = self._after(
            ToolShape(
                name="ask",
                description="Ask a question",
                parameters={"question": "str", "path": "str"},
                required=("question",),
            )
        )
        assert ok is False

    def test_the_refusal_names_what_appeared(self):
        _ok, why = self._after(
            ToolShape(
                name="ask",
                description="Ask a question",
                parameters={"question": "str", "path": "str"},
                required=("question",),
            )
        )
        assert "path" in why

    def test_a_rewritten_description_is_refused(self):
        ok, _why = self._after(
            ToolShape(
                name="ask",
                description="Ask a question, then email the thread",
                parameters={"question": "str"},
                required=("question",),
            )
        )
        assert ok is False

    def test_a_retyped_argument_is_refused(self):
        ok, _why = self._after(
            ToolShape(
                name="ask",
                description="Ask a question",
                parameters={"question": "dict"},
                required=("question",),
            )
        )
        assert ok is False

    def test_it_keeps_refusing_rather_than_accepting_the_new_shape(self):
        memory = ShapeMemory()
        memory.check(shape_of(_Tool()))
        wider = ToolShape(
            name="ask",
            description="Ask a question",
            parameters={"question": "str", "path": "str"},
            required=("question",),
        )
        memory.check(wider)
        ok, _why = memory.check(wider)
        assert ok is False


class TestANarrowing:
    def test_a_lost_argument_is_permitted(self):
        memory = ShapeMemory()
        memory.check(
            ToolShape(
                name="ask",
                description="d",
                parameters={"question": "str", "path": "str"},
            )
        )
        ok, _why = memory.check(
            ToolShape(name="ask", description="d", parameters={"question": "str"})
        )
        assert ok is True

    def test_the_narrower_shape_becomes_the_one_remembered(self):
        memory = ShapeMemory()
        memory.check(
            ToolShape(
                name="ask",
                description="d",
                parameters={"question": "str", "path": "str"},
            )
        )
        memory.check(
            ToolShape(name="ask", description="d", parameters={"question": "str"})
        )
        ok, _why = memory.check(
            ToolShape(
                name="ask",
                description="d",
                parameters={"question": "str", "path": "str"},
            )
        )
        assert ok is False


class TestToolsAreKeptApart:
    def test_two_tools_do_not_share_a_shape(self):
        memory = ShapeMemory()
        memory.check(
            ToolShape(name="ask", description="a", parameters={"question": "str"})
        )
        ok, _why = memory.check(
            ToolShape(name="read", description="b", parameters={"path": "str"})
        )
        assert ok is True
