"""바다로 미들웨어 — 설계서 3.2 (담당: 윤소영)

#11  context / state / store / runtime_context
#12  input_validation / dispatch_context / model_routing
#13  retry / tool_logging
#14  result_validation

등록 예시 (#17):
    middleware=[input_validation, dispatch_context, model_routing,
                build_tool_retry(), tool_logging, result_validation]
여기 이름은 모두 훅 함수다. 같은 이름의 모듈이 아니라 함수가 바인딩된다.

공통 데이터 타입은 badaro.schemas(B-03)를 그대로 쓴다.
기준: 6반_3조_설계서 v1.3
"""
from . import store
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
from .model_routing import model_routing, route_model
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
    "store",
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
    "model_routing", "route_model",
    "POLL_MAX_ATTEMPTS", "RETRYABLE_CODES", "as_tool_error", "backoff_delay",
    "build_tool_retry", "can_resend", "default_retryable", "duplicate_risk",
    "requires_duplicate_check", "retry_hint", "safe_error_text", "should_retry",
    "tool_retry",
    "build_log_record", "tool_logging",
    "as_dict", "build_error_response", "build_regenerate_instruction",
    "dispatched_vehicles", "extract_routes", "mentioned_vehicles", "reported_etas",
    "result_validation", "validate_response", "visit_sequence",
]
