"""Tool 실행의 request_id와 성공·실패를 기록한다. 로그 저장 실패는 업무를 중단하지 않는다."""
from __future__ import annotations

import json
import logging as _stdlib_logging
import time
from typing import Any

from ..guardrails.pii import mask_obj, mask_text
from ._compat import wrap_tool_call
from .retry import safe_error_text

_log = _stdlib_logging.getLogger("badaro.tool")


def build_log_record(*, request_id: str, tool_name: str, ok: bool,
                     elapsed_ms: int, args: Any = None, error: str | None = None) -> dict[str, Any]:
    """로그 한 줄에 들어갈 내용을 만든다. 여기서 마스킹까지 끝내 원문이 밖으로 못 나가게 한다."""
    rec: dict[str, Any] = {
        "request_id": request_id,
        "tool": tool_name,
        "ok": ok,
        "elapsed_ms": elapsed_ms,
    }
    if args is not None:
        rec["args"] = mask_obj(args)
    if error:
        rec["error"] = mask_text(error)
    return rec


def emit(record: dict[str, Any]) -> None:
    """로그를 실제로 내보낸다. 실패해도 예외를 밖으로 던지지 않는다 (3.4 fail-open)."""
    try:
        _log.info(json.dumps(record, ensure_ascii=False))
    except Exception:
        pass


@wrap_tool_call
def tool_logging(request: Any, handler: Any) -> Any:
    """도구 호출을 감싸서 앞뒤로 시각을 재고, 결과를 기록한다."""
    ctx = getattr(request, "runtime", None)
    ctx = getattr(ctx, "context", None) if ctx else None
    request_id = getattr(ctx, "request_id", "unknown")
    tool_name = getattr(getattr(request, "tool_call", None), "get", lambda *_: None)("name") \
        or getattr(request, "tool_name", "unknown")

    start = time.monotonic()
    try:
        result = handler(request)
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        emit(build_log_record(request_id=request_id, tool_name=tool_name, ok=False,
                              elapsed_ms=elapsed, error=safe_error_text(exc)))
        raise
    else:
        elapsed = int((time.monotonic() - start) * 1000)
        ok = getattr(result, "status", None) != "error"
        rec = build_log_record(request_id=request_id, tool_name=tool_name, ok=ok,
                               elapsed_ms=elapsed)
        emit(rec)
        return result
