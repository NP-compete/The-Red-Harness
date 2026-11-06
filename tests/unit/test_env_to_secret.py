"""`.env` means one thing to the shell and another to kubectl."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "deploy"))

from env_to_secret import parse, unwrap  # noqa: E402

KEYS = {"LANGFUSE_BASE_URL", "MCP_TOKEN_ENCRYPTION_KEY", "SIZE", "ADC"}


class TestTheShellAndKubectlAgree:
    def test_quotes_are_stripped_as_the_shell_would(self):
        assert (
            unwrap('"https://us.cloud.langfuse.com"') == "https://us.cloud.langfuse.com"
        )

    def test_single_quotes_too_because_json_needs_them(self):
        assert unwrap('\'{"type":"service_account"}\'') == '{"type":"service_account"}'

    def test_an_inline_comment_is_not_part_of_the_value(self):
        assert unwrap("10485760  # 10MB") == "10485760"

    def test_a_hash_inside_a_value_survives(self):
        """A generated password may contain `#`; only a commented"""
        assert unwrap("p#ssw0rd") == "p#ssw0rd"


class TestOnlyTheAllowlistTravels:
    def test_connection_details_are_refused(self):
        """`.env` says localhost because `make dev` runs the"""
        env = "POSTGRES_HOST=localhost\nREDIS_URL=redis://localhost:6379/0\n"
        assert parse(env, KEYS) == []

    def test_an_allowlisted_key_is_carried(self):
        assert parse("MCP_TOKEN_ENCRYPTION_KEY=abc123\n", KEYS) == [
            ("MCP_TOKEN_ENCRYPTION_KEY", "abc123")
        ]

    def test_an_empty_value_is_dropped_not_carried_as_empty(self):
        """An empty entry in the Secret shadows the ConfigMap default"""
        assert parse("LANGFUSE_BASE_URL=\n", KEYS) == []

    def test_comments_and_blank_lines_are_ignored(self):
        env = "\n# a comment\n  # indented\nSIZE=5\n"
        assert parse(env, KEYS) == [("SIZE", "5")]

    def test_a_value_containing_equals_is_not_split(self):
        """Base64 keys end in `=` padding."""
        assert parse("MCP_TOKEN_ENCRYPTION_KEY=YWJjZA==\n", KEYS) == [
            ("MCP_TOKEN_ENCRYPTION_KEY", "YWJjZA==")
        ]
