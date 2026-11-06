from types import SimpleNamespace

from agent.aegra.mcp import _apply_tool_allowlist


def t(n):
    return SimpleNamespace(name=n)


ALL = [
    t(x)
    for x in (
        "dataverse_execute_sql",
        "dataverse_get_sql",
        "dataverse_identify_dataproducts",
        "dataverse_create_chart_app",
    )
]


def test_absent_key_keeps_everything():
    assert _apply_tool_allowlist("dv", {}, ALL) == ALL


def test_empty_list_keeps_everything():
    assert _apply_tool_allowlist("dv", {"tools": []}, ALL) == ALL


def test_narrows_to_named():
    kept = _apply_tool_allowlist("dv", {"tools": ["dataverse_execute_sql"]}, ALL)
    assert [k.name for k in kept] == ["dataverse_execute_sql"]


def test_unknown_name_does_not_drop_the_known_ones(caplog):
    kept = _apply_tool_allowlist(
        "dv", {"tools": ["dataverse_execute_sql", "nope"]}, ALL
    )
    assert [k.name for k in kept] == ["dataverse_execute_sql"]
