from badaro.agent import DispatchAgent
from badaro.runtime.contracts import Settings


def test_missing_session_does_not_start_a_new_dispatch():
    reply = DispatchAgent(Settings()).chat("배차해줘", "missing")
    assert reply.status == "error"
    assert reply.error.code == "missing_context"
    assert reply.model_calls == 0
