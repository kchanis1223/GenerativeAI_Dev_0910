"""LangChain 미들웨어 데코레이터 호환 층 (담당: 윤소영)

왜 필요한가:
  팀 requirements.txt(#17, 김동찬)가 아직 안 올라와서 langchain 이 설치되지 않은 상태다.
  그런데 미들웨어 파일이 langchain import 로 바로 죽어버리면 CI 의 ruff·pytest 가 전부 깨진다.
  그래서 langchain 이 있으면 진짜 데코레이터를, 없으면 '아무것도 안 하는' 데코레이터를 쓴다.
  → 검증 로직(순수 함수)은 langchain 없이도 지금 바로 테스트할 수 있다.
"""
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
        return ToolMessage(content=text, tool_call_id=tool_call_id or "unknown")
    except ImportError:
        return {"role": "tool", "content": text, "tool_call_id": tool_call_id}
