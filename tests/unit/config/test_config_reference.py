"""The config reference must not drift from the models."""

from pathlib import Path

import pytest

REPO = Path(__file__).parents[3]
REFERENCE = REPO / "docs" / "reference" / "config-reference.md"


@pytest.fixture(scope="module")
def generated() -> str:
    import sys

    sys.path.insert(0, str(REPO))
    from scripts.config.config_reference import build

    return build()


class TestCommittedFileIsCurrent:
    def test_reference_exists(self):
        assert REFERENCE.is_file(), "run: make config-reference"

    def test_reference_matches_the_models(self, generated: str):
        """Fails when a config field is added without regenerating."""
        assert REFERENCE.read_text() == generated, (
            "docs/reference/config-reference.md is stale — run: make config-reference"
        )


class TestCoverage:
    def test_documents_a_realistic_number_of_keys(self, generated: str):
        """Guards against a generator that silently emits empty tables."""
        assert generated.count("\n| `") > 50

    @pytest.mark.parametrize(
        "key",
        [
            "human_approval.policies",
            "human_approval.default_decision",
            "effects",
            "enabled",
        ],
    )
    def test_documents_keys_people_actually_edit(self, generated: str, key: str):
        assert f"`{key}`" in generated

    def test_covers_every_validated_file(self, generated: str):
        """Anything the validator checks should be documented."""
        for where in (
            "runtime/agent.yaml",
            "runtime/observability.yaml",
            "runtime/router.yaml",
        ):
            assert where in generated, f"{where} missing from the reference"

    def test_names_the_files_it_does_not_cover(self, generated: str):
        """Silence about PROMPT.md or skills/ reads as 'not configurable'."""
        for unvalidated in ("PROMPT.md", "mcp.json", "skills/"):
            assert unvalidated in generated


class TestRendering:
    def test_union_types_do_not_break_table_cells(self, generated: str):
        """A bare pipe inside a cell ends the column early."""
        for line in generated.splitlines():
            if line.startswith("| `") and "'all'" in line:
                assert r"\|" in line, f"unescaped union pipe: {line}"

    def test_every_table_row_has_four_columns(self, generated: str):
        for line in generated.splitlines():
            if not line.startswith("| `"):
                continue
            columns = line.replace(r"\|", "").split("|")
            assert len(columns) == 6, f"malformed row: {line}"


class TestTheDocumentedCommandWorks:
    """`make config-reference` must regenerate what the test expects."""

    def test_the_generator_reads_this_checkout(self):
        """Not any script — this one, which is the one with the fix."""
        import subprocess
        import sys

        found = subprocess.run(
            [
                sys.executable,
                "-c",
                "import runpy, sys;"
                "sys.argv=['config_reference'];"
                f"runpy.run_path({str(REPO / 'scripts' / 'config' / 'config_reference.py')!r},"
                " run_name='probe');"
                "import agent.src.agent.config.middleware as m;"
                "print(m.__file__)",
            ],
            capture_output=True,
            text=True,
            cwd="/",
        ).stdout.strip()
        assert found.startswith(str(REPO)), (
            f"the generator imported {found}, which is outside {REPO}"
        )

    def test_the_script_writes_what_the_models_say(self, generated: str):
        import subprocess
        import sys

        before = REFERENCE.read_text()
        try:
            subprocess.run(
                [
                    sys.executable,
                    str(REPO / "scripts" / "config" / "config_reference.py"),
                ],
                capture_output=True,
                text=True,
                cwd=REPO,
            )
            assert REFERENCE.read_text() == generated
        finally:
            REFERENCE.write_text(before)
