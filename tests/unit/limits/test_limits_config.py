"""What a deployment sets, and what it gets for not setting it."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent.src.limits.config import LimitsMisconfigured, read_limits


class TestOffUntilAskedFor:
    def test_nothing_configured_is_no_cap(self):
        assert read_limits({}).per_person is None

    def test_an_empty_block_is_no_cap(self):
        assert read_limits({"limits": {}}).per_person is None

    def test_the_team_side_too(self):
        assert read_limits({"limits": {}}).per_team is None


class TestReadingThem:
    def test_a_personal_cap_is_read(self):
        found = read_limits({"limits": {"per_person": {"daily_spend": "5.00"}}})
        assert found.per_person == Decimal("5.00")

    def test_a_team_cap_is_read(self):
        found = read_limits(
            {
                "limits": {
                    "per_person": {"daily_spend": "5.00"},
                    "per_team": {"daily_spend": "20.00", "teams": ["platform"]},
                }
            }
        )
        assert found.per_team == Decimal("20.00")

    def test_it_is_read_as_a_decimal_not_a_float(self):
        found = read_limits({"limits": {"per_person": {"daily_spend": 0.1}}})
        assert found.per_person == Decimal("0.1")

    def test_a_team_cap_alone_is_allowed(self):
        found = read_limits(
            {"limits": {"per_team": {"daily_spend": "20.00", "teams": ["platform"]}}}
        )
        assert found.per_team == Decimal("20.00")


class TestSettingsThatWouldNotWork:
    def test_a_cap_that_is_not_an_amount_is_refused(self):
        with pytest.raises(LimitsMisconfigured, match="daily_spend"):
            read_limits({"limits": {"per_person": {"daily_spend": "lots"}}})

    def test_a_negative_cap_is_refused(self):
        with pytest.raises(LimitsMisconfigured):
            read_limits({"limits": {"per_person": {"daily_spend": "-1"}}})

    def test_a_team_cap_below_the_personal_one_is_refused(self):
        with pytest.raises(LimitsMisconfigured):
            read_limits(
                {
                    "limits": {
                        "per_person": {"daily_spend": "10"},
                        "per_team": {"daily_spend": "5", "teams": ["platform"]},
                    }
                }
            )

    def test_the_refusal_explains_rather_than_just_refusing(self):
        with pytest.raises(LimitsMisconfigured, match="never be spent"):
            read_limits(
                {
                    "limits": {
                        "per_person": {"daily_spend": "10"},
                        "per_team": {"daily_spend": "5", "teams": ["platform"]},
                    }
                }
            )


class TestTheShippedTree:
    def test_the_loader_reads_it(self):
        from agent.src.agent.config.loader import agent_config

        assert agent_config.get_limits_config() is not None

    def test_it_ships_with_no_cap(self):
        from agent.src.agent.config.loader import agent_config

        found = agent_config.get_limits_config()
        assert found.per_person is None and found.per_team is None

    def test_the_shipped_file_documents_how_to_set_one(self):
        from agent.src.agent.config.loader import agent_config

        said = (agent_config.base_dir / "runtime" / "agent.yaml").read_text()
        assert "per_person" in said and "daily_spend" in said

    def test_and_says_which_cap_is_the_protection(self):
        from agent.src.agent.config.loader import agent_config

        said = (agent_config.base_dir / "runtime" / "agent.yaml").read_text()
        assert "protection" in said


class TestWhichTeamsHaveABudget:
    """A team cap is one number; which teams it applies to has"""

    def test_none_named_means_no_team_enforcement(self):
        found = read_limits({"limits": {"per_person": {"daily_spend": "5"}}})
        assert found.teams == ()

    def test_the_named_teams_are_read(self):
        found = read_limits(
            {
                "limits": {
                    "per_person": {"daily_spend": "5"},
                    "per_team": {"daily_spend": "20", "teams": ["platform", "sre"]},
                }
            }
        )
        assert found.teams == ("platform", "sre")

    def test_a_team_cap_with_no_teams_is_refused(self):
        with pytest.raises(LimitsMisconfigured, match="teams"):
            read_limits(
                {
                    "limits": {
                        "per_person": {"daily_spend": "5"},
                        "per_team": {"daily_spend": "20"},
                    }
                }
            )

    def test_teams_without_a_cap_are_refused_too(self):
        with pytest.raises(LimitsMisconfigured):
            read_limits(
                {
                    "limits": {
                        "per_person": {"daily_spend": "5"},
                        "per_team": {"teams": ["platform"]},
                    }
                }
            )
