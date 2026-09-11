"""바다로 미들웨어와 검증 함수.

v2 MVP는 요청 검증·호출 제한·오류 처리·최소 로그만 연결한다.
모델 분기와 장기 저장 코드는 제거했다. 결과 문장 검증과 권한 호환 코드는
현재 Agent에 등록하지 않으며 회귀 테스트용으로 유지한다.
공통 모델은 badaro.schemas, 실제 Agent 연결은 badaro.runtime.graph를 따른다."""
from .context import KST, BadaroContext, DepotProfile, RoleSource, UserRole
from .dispatch_context import (
    STATE_LOAD_ERROR_KEY,
    dispatch_context,
    request_ref,
    resolve_mode,
    summarize_request,
)
from .input_validation import (
    LAT_RANGE,
    LON_RANGE,
    MAX_DAYS_AHEAD,
    MAX_DESTINATIONS,
    MAX_VEHICLES,
    MIN_VEHICLES,
    PRIORITIES,
    STORAGE_TYPES,
    build_clarification_message,
    input_validation,
    validate_dispatch_input,
    validate_geocode_candidate,
)
from .result_validation import (
    as_dict,
    build_error_response,
    build_regenerate_instruction,
    dispatched_vehicles,
    extract_routes,
    mentioned_vehicles,
    reported_etas,
    result_validation,
    validate_response,
    visit_sequence,
)
from .retry import (
    POLL_MAX_ATTEMPTS,
    RETRYABLE_CODES,
    as_tool_error,
    backoff_delay,
    build_tool_retry,
    can_resend,
    default_retryable,
    duplicate_risk,
    requires_duplicate_check,
    retry_hint,
    safe_error_text,
    should_retry,
    tool_retry,
)
from .runtime_context import build_runtime_context
from .state import (
    ApprovalStatus,
    BadaroState,
    confirmed_coord,
    initial_state,
    is_approved,
    is_confirmed_geocode,
    latest_snapshot,
)
from .tool_logging import build_log_record, tool_logging

__all__ = [
    "KST", "BadaroContext", "DepotProfile", "RoleSource", "UserRole",
    "ApprovalStatus", "BadaroState", "confirmed_coord", "initial_state",
    "is_approved", "is_confirmed_geocode", "latest_snapshot",
    "build_runtime_context",
    "LAT_RANGE", "LON_RANGE", "MAX_DAYS_AHEAD", "MAX_DESTINATIONS",
    "MAX_VEHICLES", "MIN_VEHICLES", "PRIORITIES", "STORAGE_TYPES",
    "build_clarification_message", "input_validation", "validate_dispatch_input",
    "validate_geocode_candidate",
    "STATE_LOAD_ERROR_KEY", "dispatch_context", "request_ref", "resolve_mode",
    "summarize_request",
    "POLL_MAX_ATTEMPTS", "RETRYABLE_CODES", "as_tool_error", "backoff_delay",
    "build_tool_retry", "can_resend", "default_retryable", "duplicate_risk",
    "requires_duplicate_check", "retry_hint", "safe_error_text", "should_retry",
    "tool_retry",
    "build_log_record", "tool_logging",
    "as_dict", "build_error_response", "build_regenerate_instruction",
    "dispatched_vehicles", "extract_routes", "mentioned_vehicles", "reported_etas",
    "result_validation", "validate_response", "visit_sequence",
]
