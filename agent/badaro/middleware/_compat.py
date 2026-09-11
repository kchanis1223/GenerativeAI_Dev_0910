"""LangChain 미들웨어 데코레이터와 메시지 호환 함수.

실제 실행은 pyproject.toml의 LangChain 의존성을 설치한 환경에서 검증한다."""
from __future__ import annotations

from typing import Any, Callable

try:
    from langchain.agents.middleware import (
        after_model,
        before_agent,
        before_model,
        wrap_model_call,
        wrap_tool_call,
    )
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

    def _passthrough(*args: Any, **kwargs: Any) -> Any:
        """@deco 와 @deco(...) 두 가지 모양을 모두 받아넘기는 가짜 데코레이터."""
        if len(args) == 1 and callable(args[0]) and not kwargs:
            return args[0]
        def _wrap(fn: Callable) -> Callable:
            return fn
        return _wrap

    before_agent = before_model = wrap_model_call = _passthrough
    wrap_tool_call = after_model = _passthrough


def ai_message(text: str) -> Any:
    """AIMessage 를 만든다. langchain 이 없으면 dict 로 대체해 테스트가 돌아가게 한다."""
    try:
        from langchain_core.messages import AIMessage
        return AIMessage(content=text)
    except ImportError:
        return {"role": "assistant", "content": text}


def tool_message(text: str, tool_call_id: str | None = None) -> Any:
    """ToolMessage 를 만든다. langchain 이 없으면 dict 로 대체한다."""
    try:
        from langchain_core.messages import ToolMessage
        return ToolMessage(content=text, tool_call_id=tool_call_id or "unknown", status="error")
    except ImportError:
        return {"role": "tool", "content": text, "tool_call_id": tool_call_id, "status": "error"}
