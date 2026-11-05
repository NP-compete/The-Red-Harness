"""What a branched conversation is called in the list."""

from __future__ import annotations

from agent.aegra.fork_routes import _forked_title


def title(name: str | None) -> str:
    return _forked_title({"thread_name": name} if name is not None else {})


def test_a_pasted_question_does_not_bring_its_newlines():
    """A title is one line in a list; a second line breaks the row."""
    assert "\n" not in title("Create a file\nwith two lines")


def test_a_long_name_is_cut_on_a_word_boundary():
    name = "What is the travel limit for contractors who are flying abroad next quarter"
    cut = title(name)
    assert cut.endswith(" (fork)")
    assert "…" in cut
    assert "contracto…" not in cut


def test_a_name_carrying_an_address_is_not_copied_into_the_list():
    """The fork's title appears in the sidebar, like any other."""
    assert title("Who manages sodutta@redhat.com?") == "Forked conversation"


def test_a_name_carrying_a_key_is_not_copied_either():
    assert title("Is sk7f3kd92mfkd0192x valid?") == "Forked conversation"


def test_an_ordinary_long_word_is_not_mistaken_for_a_secret():
    assert (
        title("Explain internationalisation") == "Explain internationalisation (fork)"
    )
