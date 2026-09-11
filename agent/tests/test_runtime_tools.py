from badaro.runtime.tools import TOOLS


def test_only_four_public_tools_are_exposed_without_runtime():
    from badaro.guardrails.allow_list import ALLOWED_ARGS

    assert {t.name for t in TOOLS} == set(ALLOWED_ARGS)
    for t in TOOLS:
        assert set(t.tool_call_schema.model_fields) == ALLOWED_ARGS[t.name]
