"""LoggingMiddleware — 3.2 (이슈 #13 B-13 · 우선순위 P0)

Hook  : wrap_tool_call
목적  : Tool 호출 이력을 남긴다 — Request ID, Tool명, 성공·실패.
v2 보완: ⭐ 기록 키를 3.1 request_id 로 확정
         ⭐ 배차 '확정' 이벤트는 dispatch_audit_log 로 분리 기록
         ⭐ 전화번호·주소·인증키는 마스킹 (G-05, 심각도 High)

파일 이름이 logging.py 가 아닌 이유:
  파이썬 표준 라이브러리에 logging 모듈이 있어서, 같은 이름을 쓰면 그걸 가려버린다(shadowing).
  v2 3.2.1 의 등록 이름도 tool_logging 이라 그대로 맞췄다.

실패 정책 (3.4): fail-open — 로그 기록이 실패해도 배차 업무 자체는 계속 진행한다.
"""
from __future__ import annotations

import json
import logging as _stdlib_logging
import time
from typing import Any

from ..guardrails.pii import mask_obj, mask_text
from ._compat import wrap_tool_call

_log = _stdlib_logging.getLogger("badaro.tool")

AUDIT_TOOLS = frozenset({"confirm_dispatch", "cancel_dispatch"})


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


def write_audit(store: Any, tenant_id: str, record: dict[str, Any]) -> None:
    """배차 확정·취소만 Store 의 dispatch_audit_log 에 따로 쌓는다 (⭐ v2 분리 기록).

    일반 Tool 로그와 섞으면 나중에 '누가 언제 확정했나'를 찾기 어렵다.
    화물자동차 운수사업법 제47조의2 운송실적 신고 대응 기반.
    """
    try:
        from .store import append_audit
        append_audit(store, tenant_id, mask_obj(record))
    except Exception:
        pass


@wrap_tool_call
def tool_logging(request: Any, handler: Any) -> Any:
    """도구 호출을 감싸서 앞뒤로 시각을 재고, 결과를 기록한다."""
    ctx = getattr(request, "runtime", None)
    ctx = getattr(ctx, "context", None) if ctx else None
    request_id = getattr(ctx, "request_id", "unknown")
    tenant_id = getattr(ctx, "tenant_id", "unknown")
    tool_name = getattr(getattr(request, "tool_call", None), "get", lambda *_: None)("name") \
        or getattr(request, "tool_name", "unknown")
    args = getattr(request, "tool_call", None)
    args = args.get("args") if isinstance(args, dict) else None

    start = time.monotonic()
    try:
        result = handler(request)
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        emit(build_log_record(request_id=request_id, tool_name=tool_name, ok=False,
                              elapsed_ms=elapsed, args=args, error=str(exc)))
        raise
    else:
        elapsed = int((time.monotonic() - start) * 1000)
        rec = build_log_record(request_id=request_id, tool_name=tool_name, ok=True,
                               elapsed_ms=elapsed, args=args)
        emit(rec)
        if tool_name in AUDIT_TOOLS:
            store = getattr(request, "store", None)
            if store is not None:
                write_audit(store, tenant_id, {**rec, "actor": getattr(ctx, "user_id", "unknown")})
        return result
