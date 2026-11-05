"""Usage, as a file somebody can open."""

from __future__ import annotations

import csv
import io

from agent.aegra.analytics_export import as_csv


def _rows(text: str) -> list[list[str]]:
    return list(csv.reader(io.StringIO(text)))


class TestTheShape:
    def test_it_has_a_header(self):
        rows = _rows(as_csv([{"model": "a", "runs": 1}]))
        assert rows[0] == ["model", "runs"]

    def test_each_record_is_a_row(self):
        rows = _rows(as_csv([{"model": "a", "runs": 1}, {"model": "b", "runs": 2}]))
        assert len(rows) == 3

    def test_the_columns_keep_the_order_they_were_given(self):
        rows = _rows(as_csv([{"z": 1, "a": 2}]))
        assert rows[0] == ["z", "a"]

    def test_nothing_to_export_still_has_a_header(
        self,
    ):
        assert as_csv([], columns=["model", "runs"]).strip() == "model,runs"

    def test_nothing_at_all_is_empty_rather_than_invented(self):
        assert as_csv([]) == ""


class TestValuesThatBreakCsv:
    def test_a_comma_inside_a_value_does_not_become_two_columns(self):
        rows = _rows(as_csv([{"name": "Smith, John", "runs": 1}]))
        assert rows[1] == ["Smith, John", "1"]

    def test_a_quote_inside_a_value_survives(self):
        rows = _rows(as_csv([{"name": 'say "hello"', "runs": 1}]))
        assert rows[1][0] == 'say "hello"'

    def test_a_newline_inside_a_value_does_not_become_two_rows(self):
        rows = _rows(as_csv([{"name": "two\nlines", "runs": 1}]))
        assert len(rows) == 2


class TestValuesASpreadsheetWouldExecute:
    """A cell starting `=` is a formula, not text."""

    def test_an_equals_sign_is_defused(self):
        rows = _rows(as_csv([{"name": "=1+1"}]))
        assert not rows[1][0].startswith("=")

    def test_the_value_is_still_readable(self):
        rows = _rows(as_csv([{"name": "=1+1"}]))
        assert "=1+1" in rows[1][0]

    def test_the_other_three_leading_characters_are_defused(self):
        for lead in ("+", "-", "@"):
            rows = _rows(as_csv([{"name": f"{lead}danger"}]))
            assert not rows[1][0].startswith(lead)

    def test_an_ordinary_value_is_left_alone(self):
        rows = _rows(as_csv([{"name": "gpt-4o"}]))
        assert rows[1][0] == "gpt-4o"

    def test_a_negative_number_is_not_mangled(self):
        rows = _rows(as_csv([{"delta": -5}]))
        assert rows[1][0] == "-5"


class TestMissingNumbers:
    def test_a_missing_value_is_blank_rather_than_zero(self):
        rows = _rows(as_csv([{"rate": None}]))
        assert rows[1][0] == ""

    def test_a_real_zero_is_still_zero(self):
        rows = _rows(as_csv([{"rate": 0}]))
        assert rows[1][0] == "0"

    def test_a_row_missing_a_column_others_have_is_blank_there(self):
        rows = _rows(as_csv([{"a": 1, "b": 2}, {"a": 3}]))
        assert rows[2] == ["3", ""]


class TestTheEndpoint:
    """What a browser gets when it asks for the file."""

    @staticmethod
    async def _export(what="models", rows=None, fails=None):
        from unittest.mock import AsyncMock, patch

        from agent.aegra.analytics_routes import analytics_export

        rows = (
            rows
            if rows is not None
            else [
                {"model": "gpt-4o", "runs": 12, "input_tokens": 900},
            ]
        )
        target = "agent.aegra.analytics_routes.queries"
        with patch(target) as q:
            q.MAX_WINDOW_DAYS = 90
            q.EXPORTABLE = {"models": "by_model", "errors": "errors"}
            if fails:
                q.export_rows = AsyncMock(side_effect=RuntimeError(fails))
            else:
                q.export_rows = AsyncMock(return_value=rows)
            return await analytics_export(what=what, days=7, _token="operator")

    async def test_it_answers_with_csv(self):
        answer = await self._export()
        assert answer.media_type == "text/csv"

    async def test_the_body_is_the_rows(self):
        answer = await self._export()
        assert "gpt-4o" in answer.body.decode()

    async def test_it_is_offered_as_a_download(self):
        answer = await self._export()
        assert "attachment" in answer.headers["content-disposition"]

    async def test_the_filename_says_what_it_is(self):
        answer = await self._export()
        said = answer.headers["content-disposition"]
        assert "models" in said and ".csv" in said

    async def test_the_filename_cannot_be_chosen_by_the_caller(self):
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await self._export(what="models\r\nX-Evil: 1")

    async def test_an_unknown_report_is_refused(self):
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await self._export(what="everything")

    async def test_nothing_to_export_is_still_a_file(self):
        answer = await self._export(rows=[])
        assert answer.status_code == 200

    async def test_a_failure_is_not_an_empty_file(self):
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await self._export(fails="the database is down")
