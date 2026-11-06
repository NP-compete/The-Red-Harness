"""Every retry in the tree, and why it is safe to repeat (REL-5)."""

from __future__ import annotations

import inspect

import pytest

RETRIERS: dict[str, str] = {
    "error_handling.llm_retry": (
        "create_model, which constructs a client and sends nothing — the "
        "retry is on constructing it, not on a completion"
    ),
    "error_handling.mcp_retry": (
        "nothing. Exported in the module's usage example and applied to no "
        "function in the tree, tests included"
    ),
    "error_handling.subagent_retry": (
        "nothing. Declared beside the other two with the same shape"
    ),
    "error_handling.mongo_retry": (
        "nothing. Declared for the token-usage store, which this deployment "
        "does not run"
    ),
    "nodes.with_retry": (
        "nothing. Three tests and no node. Its default was every exception "
        "there is, which is the REL-5 hazard rather than a violation of it"
    ),
    "opa.middleware": (
        "a policy evaluation — POST /v1/data, which OPA treats as a query. "
        "It decides, it does not change anything"
    ),
    "ldap.service": (
        "a directory search. The second attempt exists because a pooled "
        "connection can be dead on arrival"
    ),
    "mcp._connect_single_server": (
        "opening a connection and listing tools. No tool is called"
    ),
    "llm.create_model max_retries=2": (
        "handed to the provider client, which applies it to the HTTP call "
        "for a completion. Repeating a completion costs tokens and is not "
        "a write anywhere outside the provider's billing"
    ),
}


class TestTheInventoryIsComplete:
    def test_every_entry_says_what_it_wraps(self):
        thin = [name for name, why in RETRIERS.items() if len(why) < 40]
        assert not thin, f"{thin} are classified too briefly to mean anything"

    def test_the_declared_retriers_exist(self):
        from agent.src import error_handling

        for name in ("llm_retry", "mcp_retry", "subagent_retry"):
            assert hasattr(error_handling, name), (
                f"{name} is in the map and gone from the module — a map to a "
                "retrier that no longer exists reads as audited"
            )

    def test_the_node_decorator_exists(self):
        from agent.aegra.nodes import with_retry

        assert callable(with_retry)


class TestNothingRetriesEverything:
    def test_the_node_decorator_does_not_default_to_every_exception(self):
        from agent.aegra.nodes import with_retry

        default = inspect.signature(with_retry).parameters["retry_on"].default
        assert Exception not in default, (
            "with_retry retries every exception by default, so the first node "
            "to use it repeats a write on any failure (REL-5)"
        )
        assert ConnectionError in default

    @pytest.mark.parametrize("name", ["llm_retry", "mcp_retry", "subagent_retry"])
    def test_the_decorators_name_the_exceptions_they_retry(self, name):
        from agent.src import error_handling

        source = inspect.getsource(error_handling)
        block = source.split(f"{name} = retry(")[1].split(")\n\n")[0]
        assert "retry_if_exception_type" in block, f"{name} retries on anything raised"
        assert "Exception))" not in block.replace(" ", "")
