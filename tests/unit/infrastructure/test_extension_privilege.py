"""What an in-process extension can reach, stated rather than assumed."""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest

from agent.src.infrastructure.extensions import Extension, declared_extension


class TestItCannotArriveUnnoticed:
    def test_loading_one_is_logged(self):
        said = []
        with (
            patch("agent.src.infrastructure.extensions.logger") as log,
            patch.object(Extension, "_make", return_value=object()),
        ):
            Extension(path="somewhere:thing", required=True).load()
            said.extend(str(call) for call in log.info.call_args_list)
        assert said

    def test_the_log_names_it(self):
        said = []
        with (
            patch("agent.src.infrastructure.extensions.logger") as log,
            patch.object(Extension, "_make", return_value=object()),
        ):
            Extension(path="house.style:Redactor", required=True).load()
            said.extend(str(call) for call in log.info.call_args_list)
        assert "house.style:Redactor" in str(said)

    def test_one_that_will_not_load_and_is_required_stops_the_agent(self):
        from agent.src.infrastructure.extensions import ExtensionUnavailable

        with pytest.raises(ExtensionUnavailable):
            Extension(path="nothing.here:absent", required=True).load()

    def test_the_default_is_to_refuse(self):
        assert declared_extension("nothing.here:absent").required is True


class TestWhatIsNotPrevented:
    """Written down because the alternative is implying it is."""

    def test_an_extension_runs_in_this_process(self):
        assert "importlib" in inspect.getsource(inspect.getmodule(Extension))

    def test_the_untrusted_record_is_importable_by_anything(self):
        from agent.src.security import untrusted_reads

        assert hasattr(untrusted_reads, "forget_reads")

    def test_the_loader_says_so_in_its_own_words(self):
        source = inspect.getsource(inspect.getmodule(Extension))
        assert "privileges" in source
