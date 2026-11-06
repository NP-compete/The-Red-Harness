"""Where a score is kept, and what it is a score of."""

from __future__ import annotations

import json

import pytest

from scripts.bench.results import Row, compare, read_rows, record

ROW = Row(
    fingerprint="cfg_a",
    suite="jb",
    model="gemini-2.5-pro",
    score=0.62,
    tasks=50,
    errors=1,
)


def _at(tmp_path):
    return tmp_path / "results.jsonl"


class TestRecordingARun:
    def test_it_is_written(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        assert read_rows(_at(tmp_path))

    def test_it_keeps_the_configuration_that_earned_it(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        assert read_rows(_at(tmp_path))[0].fingerprint == "cfg_a"

    def test_it_keeps_the_model(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        assert read_rows(_at(tmp_path))[0].model == "gemini-2.5-pro"

    def test_it_is_stamped_with_when(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        assert read_rows(_at(tmp_path))[0].at

    def test_a_given_time_is_kept_rather_than_overwritten(self, tmp_path):
        record(
            Row(**{**ROW.__dict__, "at": "2026-01-01T00:00:00Z"}), path=_at(tmp_path)
        )
        assert read_rows(_at(tmp_path))[0].at == "2026-01-01T00:00:00Z"

    def test_the_directory_is_made_if_it_is_not_there(self, tmp_path):
        deep = tmp_path / "a" / "b" / "results.jsonl"
        record(ROW, path=deep)
        assert deep.is_file()


class TestItOnlyEverAppends:
    def test_a_second_run_does_not_replace_the_first(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        record(Row(**{**ROW.__dict__, "score": 0.71}), path=_at(tmp_path))
        assert len(read_rows(_at(tmp_path))) == 2

    def test_a_worse_run_is_kept_too(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        record(Row(**{**ROW.__dict__, "score": 0.11}), path=_at(tmp_path))
        assert 0.11 in [r.score for r in read_rows(_at(tmp_path))]

    def test_one_run_per_line(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        record(ROW, path=_at(tmp_path))
        assert len(_at(tmp_path).read_text().strip().splitlines()) == 2

    def test_a_line_is_readable_on_its_own(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        first = _at(tmp_path).read_text().splitlines()[0]
        assert json.loads(first)["fingerprint"] == "cfg_a"


class TestReadingThemBack:
    def test_a_file_that_is_not_there_has_no_runs(self, tmp_path):
        assert read_rows(_at(tmp_path)) == []

    def test_a_damaged_line_does_not_lose_the_rest(self, tmp_path):
        record(ROW, path=_at(tmp_path))
        with _at(tmp_path).open("a") as f:
            f.write("{not json\n")
        record(Row(**{**ROW.__dict__, "score": 0.9}), path=_at(tmp_path))
        assert len(read_rows(_at(tmp_path))) == 2


class TestComparingTwoConfigurations:
    @staticmethod
    def _two(tmp_path):
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_a", "score": 0.60}),
            path=_at(tmp_path),
        )
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_b", "score": 0.72}),
            path=_at(tmp_path),
        )
        return read_rows(_at(tmp_path))

    def test_it_reports_a_delta_per_suite(self, tmp_path):
        found = compare(self._two(tmp_path), "cfg_a", "cfg_b")
        assert found[0].suite == "jb"

    def test_the_delta_is_the_difference(self, tmp_path):
        found = compare(self._two(tmp_path), "cfg_a", "cfg_b")
        assert found[0].delta == pytest.approx(0.12)

    def test_an_improvement_is_positive(self, tmp_path):
        found = compare(self._two(tmp_path), "cfg_a", "cfg_b")
        assert found[0].delta > 0

    def test_the_order_of_the_arguments_decides_the_sign(self, tmp_path):
        found = compare(self._two(tmp_path), "cfg_b", "cfg_a")
        assert found[0].delta < 0

    def test_the_latest_run_of_a_configuration_is_the_one_used(self, tmp_path):
        self._two(tmp_path)
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_a", "score": 0.80}),
            path=_at(tmp_path),
        )
        found = compare(read_rows(_at(tmp_path)), "cfg_a", "cfg_b")
        assert found[0].delta == pytest.approx(-0.08)

    def test_a_suite_only_one_side_ran_is_not_compared(self, tmp_path):
        self._two(tmp_path)
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_b", "suite": "lab"}),
            path=_at(tmp_path),
        )
        found = compare(read_rows(_at(tmp_path)), "cfg_a", "cfg_b")
        assert [f.suite for f in found] == ["jb"]

    def test_it_says_which_suites_it_could_not_compare(self, tmp_path):
        from scripts.bench.results import unmatched

        self._two(tmp_path)
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_b", "suite": "lab"}),
            path=_at(tmp_path),
        )
        assert unmatched(read_rows(_at(tmp_path)), "cfg_a", "cfg_b") == ["lab"]

    def test_comparing_across_models_is_refused(self, tmp_path):
        record(Row(**{**ROW.__dict__, "fingerprint": "cfg_a"}), path=_at(tmp_path))
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_b", "model": "something-else"}),
            path=_at(tmp_path),
        )
        with pytest.raises(ValueError, match="model"):
            compare(read_rows(_at(tmp_path)), "cfg_a", "cfg_b")

    def test_a_configuration_with_no_runs_is_said_plainly(self, tmp_path):
        self._two(tmp_path)
        with pytest.raises(ValueError, match="cfg_z"):
            compare(read_rows(_at(tmp_path)), "cfg_a", "cfg_z")


class TestReportingAComparison:
    @staticmethod
    def _written(tmp_path):
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_a", "score": 0.60}),
            path=_at(tmp_path),
        )
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_b", "score": 0.72}),
            path=_at(tmp_path),
        )
        return _at(tmp_path)

    def test_it_prints_the_delta(self, tmp_path, capsys):
        from scripts.bench.report import main

        main(["--results", str(self._written(tmp_path)), "--compare", "cfg_a", "cfg_b"])
        assert "0.12" in capsys.readouterr().out

    def test_it_names_the_suite(self, tmp_path, capsys):
        from scripts.bench.report import main

        main(["--results", str(self._written(tmp_path)), "--compare", "cfg_a", "cfg_b"])
        assert "jb" in capsys.readouterr().out

    def test_it_exits_zero_on_a_clean_comparison(self, tmp_path, capsys):
        from scripts.bench.report import main

        found = main(
            ["--results", str(self._written(tmp_path)), "--compare", "cfg_a", "cfg_b"]
        )
        assert found == 0

    def test_a_comparison_it_cannot_make_exits_non_zero(self, tmp_path, capsys):
        from scripts.bench.report import main

        found = main(
            ["--results", str(self._written(tmp_path)), "--compare", "cfg_a", "cfg_z"]
        )
        assert found != 0

    def test_it_says_which_suites_were_left_out(self, tmp_path, capsys):
        from scripts.bench.report import main

        path = self._written(tmp_path)
        record(
            Row(**{**ROW.__dict__, "fingerprint": "cfg_b", "suite": "lab"}), path=path
        )
        main(["--results", str(path), "--compare", "cfg_a", "cfg_b"])
        assert "lab" in capsys.readouterr().out
