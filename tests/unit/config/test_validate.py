"""Tests for `make validate-config`."""

from pathlib import Path

import pytest
import yaml

from agent.src.agent.config.validate import validate_config

SHIPPED = Path(__file__).parents[3] / "config" / "agent"


@pytest.fixture
def config_copy(tmp_path: Path) -> Path:
    """A writable copy of the shipped example config."""
    import shutil

    target = tmp_path / "agent"
    shutil.copytree(SHIPPED, target)
    return target


class TestShippedConfig:
    def test_example_config_has_no_errors(self):
        """The shipped example must validate — it is what forks start from."""
        assert validate_config(SHIPPED).errors == []

    def test_example_config_is_flagged_as_unmodified(self):
        """Forking and shipping without editing config ships someone else's"""
        warnings = {w.message for w in validate_config(SHIPPED).warnings}
        assert any("still the example's" in w for w in warnings)


class TestFieldValidation:
    def test_invalid_enum_is_reported_with_its_path(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        raw = yaml.safe_load(path.read_text())
        raw["middleware"]["human_approval"]["policies"][0]["decision"] = "maybe"
        path.write_text(yaml.safe_dump(raw))

        errors = validate_config(config_copy).errors

        assert any("decision" in e.location for e in errors)
        assert any("allow" in e.message for e in errors)

    def test_wrong_type_is_reported(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        raw = yaml.safe_load(path.read_text())
        raw["middleware"]["human_approval"]["enabled"] = "yes-please"
        path.write_text(yaml.safe_dump(raw))

        assert validate_config(config_copy).errors

    def test_malformed_yaml_is_reported_not_raised(self, config_copy: Path):
        (config_copy / "runtime" / "agent.yaml").write_text("key: [unclosed\n")

        report = validate_config(config_copy)

        assert any("valid YAML" in e.message for e in report.errors)

    def test_router_config_is_validated(self, config_copy: Path):
        """router.yaml rejects a single tier — there is nothing to route between."""
        path = config_copy / "runtime" / "router.yaml"
        raw = yaml.safe_load(path.read_text())
        raw["enabled"] = True
        raw["tiers"] = [{"name": "only", "model": "m", "criteria": "c"}]
        path.write_text(yaml.safe_dump(raw))

        assert validate_config(config_copy).errors


class TestRequiredFiles:
    def test_missing_prompt_is_an_error(self, config_copy: Path):
        (config_copy / "PROMPT.md").unlink()

        report = validate_config(config_copy)

        assert any(e.file == "PROMPT.md" for e in report.errors)

    def test_absent_config_directory_is_an_error(self, tmp_path: Path):
        assert validate_config(tmp_path / "nope").errors


class TestCleanFork:
    def test_a_fully_customised_config_produces_no_findings(self, config_copy: Path):
        """What a real agent should look like: no errors, no example warnings."""
        import shutil

        agent_yaml = config_copy / "runtime" / "agent.yaml"
        raw = yaml.safe_load(agent_yaml.read_text())
        raw["name"] = "Invoice Assistant"
        agent_yaml.write_text(yaml.safe_dump(raw))

        (config_copy / "PROMPT.md").write_text(
            "---\nname: orchestrator\ndescription: Handles invoices.\n---\n"
        )
        (config_copy / "mcp.json").write_text('{"mcpServers": {}}')
        shutil.rmtree(config_copy / "skills")
        (config_copy / "skills").mkdir()

        report = validate_config(config_copy)

        assert report.errors == []
        assert report.warnings == []


class TestExampleMarkersComeFromConfig:
    """The needles live in config, not in Python."""

    def test_a_renamed_example_is_caught_by_editing_config_alone(
        self, config_copy: Path
    ):
        markers = config_copy / "runtime" / "template-markers.yaml"
        markers.write_text(
            yaml.safe_dump(
                {
                    "markers": [
                        {
                            "needle": "Sales Copilot",
                            "file": "runtime/agent.yaml",
                            "message": "agent name is still the example's",
                        }
                    ]
                }
            )
        )
        agent_yaml = config_copy / "runtime" / "agent.yaml"
        raw = yaml.safe_load(agent_yaml.read_text())
        raw["name"] = "Sales Copilot"
        agent_yaml.write_text(yaml.safe_dump(raw))

        warnings = [w.message for w in validate_config(config_copy).warnings]
        assert any("still the example's" in w for w in warnings)

    def test_deleting_the_marker_file_turns_the_checks_off(self, config_copy: Path):
        (config_copy / "runtime" / "template-markers.yaml").unlink()

        warnings = [w.message for w in validate_config(config_copy).warnings]
        assert not any("still the example's" in w for w in warnings)

    def test_a_malformed_marker_file_does_not_fail_validation(self, config_copy: Path):
        (config_copy / "runtime" / "template-markers.yaml").write_text("{[not yaml")

        report = validate_config(config_copy)
        assert not any("still the example's" in w.message for w in report.warnings)

    def test_an_entry_missing_a_field_is_skipped(self, config_copy: Path):
        (config_copy / "runtime" / "template-markers.yaml").write_text(
            yaml.safe_dump({"markers": [{"needle": "Example Agent"}, "not a mapping"]})
        )

        report = validate_config(config_copy)
        assert not any("still the example's" in w.message for w in report.warnings)


class TestASettingWrittenTwice:
    """The last of two keys wins and the first is discarded in"""

    def test_the_shipped_config_sets_nothing_twice(self):
        assert validate_config(SHIPPED).errors == []

    def test_a_key_set_twice_is_an_error(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        path.write_text(path.read_text() + "\nmiddleware:\n  extra: []\n")
        report = validate_config(config_copy)
        assert any("more than once" in finding.message for finding in report.errors)

    def test_the_error_names_the_key(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        path.write_text(path.read_text() + "\nmiddleware:\n  extra: []\n")
        report = validate_config(config_copy)
        assert any("middleware" in finding.message for finding in report.errors)

    def test_the_error_says_which_file(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        path.write_text(path.read_text() + "\nmiddleware:\n  extra: []\n")
        report = validate_config(config_copy)
        found = [f for f in report.errors if "more than once" in f.message]
        assert "agent.yaml" in found[0].file

    def test_a_duplicate_in_any_configured_file_is_caught(self, config_copy: Path):
        path = config_copy / "runtime" / "observability.yaml"
        if not path.is_file():
            pytest.skip("this config has no observability file")
        path.write_text(path.read_text() + "\nservice_name: again\nservice_name: and\n")
        report = validate_config(config_copy)
        assert any("more than once" in finding.message for finding in report.errors)


class TestAKeyNothingReads:
    """A misspelled key validates cleanly today: the model ignores"""

    def test_the_shipped_config_has_no_keys_nothing_reads(self):
        assert validate_config(SHIPPED).errors == []

    def test_an_unknown_key_is_an_error(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        lines = path.read_text().split("\n")
        lines.insert(lines.index("middleware:") + 1, "  totally_made_up: 1")
        path.write_text("\n".join(lines))
        report = validate_config(config_copy)
        assert any("totally_made_up" in f.message for f in report.errors)

    def test_the_error_suggests_what_to_do(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        lines = path.read_text().split("\n")
        lines.insert(lines.index("middleware:") + 1, "  totally_made_up: 1")
        path.write_text("\n".join(lines))
        report = validate_config(config_copy)
        found = [f for f in report.errors if "totally_made_up" in f.message]
        assert "spelling" in found[0].message


class TestSectionsThatWereNeverReallyChecked:
    """Two targets were pointed at the wrong shape, so they validated"""

    def test_observability_is_actually_validated(self, config_copy: Path):
        path = config_copy / "runtime" / "observability.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        data.setdefault("otel", {})["enabled"] = "not a boolean at all"
        path.write_text(yaml.safe_dump(data))
        assert validate_config(config_copy).errors

    def test_a_misspelled_observability_key_is_caught(self, config_copy: Path):
        path = config_copy / "runtime" / "observability.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        data.setdefault("otel", {})["enabledd"] = True
        path.write_text(yaml.safe_dump(data))
        report = validate_config(config_copy)
        assert any("enabledd" in f.message for f in report.errors)

    def test_a_misspelled_key_inside_a_provider_is_caught(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        first = next(iter(data["providers"]))
        data["providers"][first]["init_kwargz"] = {}
        path.write_text(yaml.safe_dump(data))
        report = validate_config(config_copy)
        assert any("init_kwargz" in f.message for f in report.errors)

    def test_the_provider_names_themselves_are_not_mistaken_for_keys(
        self, config_copy: Path
    ):
        report = validate_config(config_copy)
        assert not any("google_genai" in f.message for f in report.errors)


class TestThePrivacyRulesAreChecked:
    """A mistake in pii.yaml is the one worth catching before a"""

    def test_the_shipped_rules_validate(self):
        assert validate_config(SHIPPED).errors == []

    def test_a_rule_of_the_wrong_shape_is_reported(self, config_copy: Path):
        path = config_copy / "runtime" / "pii.yaml"
        path.write_text("enabled: true\nrules:\n  - 'just a string'\n")
        assert validate_config(config_copy).errors

    def test_a_misspelled_privacy_key_is_reported(self, config_copy: Path):
        path = config_copy / "runtime" / "pii.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        data["trace_strategyy"] = "hash"
        path.write_text(yaml.safe_dump(data))
        report = validate_config(config_copy)
        assert any("trace_strategyy" in f.message for f in report.errors)

    def test_an_absent_file_is_not_an_error(self, config_copy: Path):
        (config_copy / "runtime" / "pii.yaml").unlink()
        report = validate_config(config_copy)
        assert not any("pii" in f.file for f in report.errors)


class TestUploadSettingsAreChecked:
    """The agent now refuses to start on these, so finding out from"""

    def test_a_bad_attachment_limit_is_reported(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        data["attachments"] = {"max_file_bytes": "enormous"}
        path.write_text(yaml.safe_dump(data))
        assert validate_config(config_copy).errors

    def test_a_misspelled_attachment_key_is_reported(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        data["attachments"] = {"enabledd": False}
        path.write_text(yaml.safe_dump(data))
        report = validate_config(config_copy)
        assert any("enabledd" in f.message for f in report.errors)

    def test_an_unknown_extraction_engine_is_reported(self, config_copy: Path):
        path = config_copy / "runtime" / "agent.yaml"
        data = yaml.safe_load(path.read_text()) or {}
        data["extraction"] = {"engine": "whatever"}
        path.write_text(yaml.safe_dump(data))
        assert validate_config(config_copy).errors
