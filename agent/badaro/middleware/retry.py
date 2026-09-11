"""RetryMiddleware — 3.2 (이슈 #13 B-13 · 우선순위 P0)

Hook  : wrap_tool_call (도구 호출을 감싼다)
목적  : TMAP·TMS 의 '일시적인' 오류만 다시 시도한다.
v2 보완: ⭐ 4xx(입력 오류)는 재시도 대상에서 제외하고 즉시 입력 수정을 요청한다 (TS-04-C03)

왜 4xx 를 빼야 하나:
  4xx 는 "네가 보낸 값이 틀렸다"는 뜻이다. 같은 값을 세 번 더 보내면 세 번 다 똑같이 거절당한다.
  그동안 하루 20건 한도만 깎인다. 고쳐야 할 건 요청이지 타이밍이 아니다.
"""
from __future__ import annotations

from typing import Any

MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0

RETRYABLE_STATUS = frozenset({
    408,
    425,
    429,
    500, 502, 503, 504,
})


def extract_status(exc: BaseException) -> int | None:
    """예외에서 HTTP 상태코드를 꺼낸다. 라이브러리마다 위치가 달라 순서대로 뒤진다."""
    resp = getattr(exc, "response", None)
    code = getattr(resp, "status_code", None)
    if isinstance(code, int):
        return code
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    code = getattr(exc, "status", None)
    if isinstance(code, int):
        return code
    return None


def should_retry(exc: BaseException) -> bool:
    """이 오류를 다시 시도해도 되는가?

    판정 ① 상태코드가 재시도 목록에 있으면 → 예
          ② 4xx 인데 목록에 없으면 → 아니오 (입력을 고쳐야 함) ⭐ v2 보완
          ③ 상태코드가 아예 없으면 → 예 (타임아웃·연결 끊김 같은 네트워크 오류)
    """
    code = extract_status(exc)
    if code is None:
        return True
    if code in RETRYABLE_STATUS:
        return True
    if 400 <= code < 500:
        return False
    return code >= 500


def backoff_delay(attempt: int) -> float:
    """attempt 번째 재시도 전에 몇 초 쉴지. 1회차 1초, 2회차 2초, 3회차 4초."""
    return BACKOFF_FACTOR ** (attempt - 1)


def retry_hint(exc: BaseException) -> str:
    """재시도를 포기했을 때 사용자에게 돌려줄 안내문. 값을 만들어내지 않고 사유만 말한다 (G-04)."""
    code = extract_status(exc)
    if code is not None and 400 <= code < 500 and code not in RETRYABLE_STATUS:
        return (f"요청 값에 문제가 있어 외부 API가 거절했습니다 (HTTP {code}). "
                f"같은 값으로는 다시 시도하지 않았습니다. 입력을 확인해 주세요.")
    if code == 429:
        return "외부 API 호출량 한도에 걸렸습니다. 3회 재시도했으나 실패했습니다."
    return (f"외부 API 호출이 {MAX_RETRIES}회 재시도 후에도 실패했습니다"
            f"{f' (HTTP {code})' if code else ''}. 결과를 임의로 생성하지 않았습니다.")


def build_tool_retry() -> Any:
    """내장 ToolRetryMiddleware 를 4xx 제외 설정으로 만든다. 없으면 None (agent.py 가 알아서 건너뜀)."""
    try:
        from langchain.agents.middleware import ToolRetryMiddleware
    except ImportError:
        return None
    return ToolRetryMiddleware(
        max_retries=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        retry_on=should_retry,
    )
