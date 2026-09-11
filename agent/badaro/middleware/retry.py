"""Retry — 설계서 3.2 / 3.2.1 (이슈 #13)

Tool 은 스스로 재시도하지 않는다. 실행 계층인 #13 이 공통 정책을 적용한다.
오류는 ToolErrorException.error 의 code·message·retryable 로 전달된다.

v1.3 반영
  - ToolError·ToolErrorCode·ToolErrorException 은 badaro.schemas(B-03)를 그대로 쓴다.
  - 429 를 제외한 입력·인증 관련 4xx 는 재시도하지 않는다.
  - 결과 조회 폴링 횟수와 통신 재시도 횟수를 구분한다.
  - 배차 요청 재전송은 중복 배차 가능성을 먼저 확인한다.
"""
from __future__ import annotations

from typing import Any

from badaro.schemas import ToolError, ToolErrorCode, ToolErrorException

MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0

POLL_MAX_ATTEMPTS = 10
POLL_INTERVAL_SEC = 3.0

TIMEOUT_STATUS = frozenset({408})
RATE_LIMIT_STATUS = frozenset({429})
SERVER_ERROR_STATUS = frozenset({500, 502, 503, 504})
RETRYABLE_STATUS = TIMEOUT_STATUS | RATE_LIMIT_STATUS | SERVER_ERROR_STATUS

RETRYABLE_CODES = frozenset({
    ToolErrorCode.TIMEOUT, ToolErrorCode.RATE_LIMITED, ToolErrorCode.UPSTREAM_ERROR,
})

NON_IDEMPOTENT_TOOLS = frozenset({"optimize_dispatch"})


def as_tool_error(exc: Any) -> ToolError | None:
    """ToolErrorException 또는 ToolError 에서 오류 값을 꺼낸다. 없으면 None."""
    if isinstance(exc, ToolError):
        return exc
    if isinstance(exc, ToolErrorException):
        err = exc.error
        return err if isinstance(err, ToolError) else None
    err = getattr(exc, "error", None)
    return err if isinstance(err, ToolError) else None


def extract_status(exc: BaseException) -> int | None:
    """예외에서 HTTP 상태코드를 꺼낸다. 라이브러리마다 위치가 달라 순서대로 확인한다."""
    resp = getattr(exc, "response", None)
    for candidate in (getattr(resp, "status_code", None),
                      getattr(exc, "status_code", None),
                      getattr(exc, "status", None)):
        if isinstance(candidate, int):
            return candidate
    return None


def should_retry(exc: BaseException | ToolError) -> bool:
    """재시도 대상인가.

    판정 순서
      1. ToolError 가 있으면 retryable 을 따른다.
      2. 상태코드가 408·429·5xx 이면 재시도한다.
      3. 그 외 4xx 는 재시도하지 않는다.
      4. 상태코드가 없으면 네트워크 오류로 보고 재시도한다.
    """
    err = as_tool_error(exc)
    if err is not None:
        return err.retryable

    code = extract_status(exc) if isinstance(exc, BaseException) else None
    if code is None:
        return True
    if code in RETRYABLE_STATUS:
        return True
    if 400 <= code < 500:
        return False
    return code >= 500


def default_retryable(code: ToolErrorCode) -> bool:
    """ToolError.code 만으로 판단해야 할 때 쓰는 기본 정책."""
    return ToolErrorCode(code) in RETRYABLE_CODES


def backoff_delay(attempt: int) -> float:
    """attempt 번째 재시도 전 대기 시간. 1초 → 2초 → 4초."""
    return BACKOFF_FACTOR ** (attempt - 1)


def requires_duplicate_check(tool_name: str) -> bool:
    """재전송 전에 중복 실행 여부를 먼저 확인해야 하는 Tool 인가."""
    return tool_name in NON_IDEMPOTENT_TOOLS


def can_resend(tool_name: str, *, prior_result_found: bool) -> bool:
    """다시 보내도 되는가. 중복 배차는 되돌릴 수 없으므로 확인되면 보내지 않는다."""
    if not requires_duplicate_check(tool_name):
        return True
    return not prior_result_found


def retry_hint(exc: BaseException | ToolError) -> str:
    """재시도를 포기했을 때의 안내문. 원본 키·주소·전화번호를 포함하지 않는다."""
    err = as_tool_error(exc)
    if err is not None:
        if err.code is ToolErrorCode.RATE_LIMITED:
            return f"외부 API 호출량 한도에 걸렸습니다. {MAX_RETRIES}회 재시도했으나 실패했습니다."
        if not err.retryable:
            return (f"요청을 진행할 수 없습니다 ({err.code}). "
                    f"같은 값으로는 다시 시도하지 않았습니다. 입력이나 조건을 확인해 주세요.")
        return (f"외부 API 호출이 {MAX_RETRIES}회 재시도 후에도 실패했습니다 ({err.code}). "
                f"결과를 임의로 생성하지 않았습니다.")

    code = extract_status(exc) if isinstance(exc, BaseException) else None
    if code in RATE_LIMIT_STATUS:
        return f"외부 API 호출량 한도에 걸렸습니다. {MAX_RETRIES}회 재시도했으나 실패했습니다."
    if code is not None and 400 <= code < 500 and code not in RETRYABLE_STATUS:
        return (f"요청 값에 문제가 있어 외부 API가 거절했습니다 (HTTP {code}). "
                f"같은 값으로는 다시 시도하지 않았습니다. 입력을 확인해 주세요.")
    suffix = f" (HTTP {code})" if code else ""
    return (f"외부 API 호출이 {MAX_RETRIES}회 재시도 후에도 실패했습니다{suffix}. "
            f"결과를 임의로 생성하지 않았습니다.")


def build_tool_retry() -> Any:
    """내장 ToolRetryMiddleware 를 구성한다. langchain 미설치 시 None."""
    try:
        from langchain.agents.middleware import ToolRetryMiddleware
    except ImportError:
        return None
    return ToolRetryMiddleware(
        max_retries=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        retry_on=should_retry,
    )
