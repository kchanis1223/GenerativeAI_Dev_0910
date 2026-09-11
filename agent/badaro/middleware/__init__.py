"""바다로 미들웨어 — 설계서 3.2 (담당: 윤소영)

#11  context / state / store          3.1 Context·State·Store
#12  input_validation (P0)            3.2 InputValidation, G-01
     dispatch_context (P0)            3.2 DispatchContext
     model_routing (P1)               3.2 ModelRouting
#13  retry (P0)                       3.2 Retry, 4xx 제외
     tool_logging (P0)                3.2 Logging, request_id·PII 마스킹
#14  result_validation (P0)           3.2.3 대조 기준 6항목, G-04
"""
from . import store
from .context import (
    KST,
    STORAGE_TO_VEHICLE,
    BadaroContext,
    DepotProfile,
    StorageType,
    UserRole,
    VehicleSpec,
    VehicleType,
)
from .dispatch_context import dispatch_context, request_ref, summarize_request
from .input_validation import (
    KR_LAT,
    KR_LON,
    MAX_DAYS_AHEAD,
    MAX_DESTINATIONS,
    MAX_VEHICLES,
    MIN_VEHICLES,
    build_clarification_message,
    input_validation,
    validate_dispatch_input,
)
from .model_routing import model_routing, route_model
from .result_validation import (
    build_error_response,
    build_regenerate_instruction,
    validate_response,
)
from .retry import backoff_delay, build_tool_retry, retry_hint, should_retry
from .state import (
    BadaroState,
    DispatchStatus,
    initial_state,
    is_confirmed,
    latest_snapshot,
)
from .tool_logging import build_log_record, tool_logging

__all__ = [
    "store",
    "KST", "STORAGE_TO_VEHICLE", "BadaroContext", "DepotProfile",
    "StorageType", "UserRole", "VehicleSpec", "VehicleType",
    "BadaroState", "DispatchStatus", "initial_state", "is_confirmed", "latest_snapshot",
    "KR_LAT", "KR_LON", "MAX_DAYS_AHEAD", "MAX_DESTINATIONS", "MAX_VEHICLES", "MIN_VEHICLES",
    "build_clarification_message", "input_validation", "validate_dispatch_input",
    "dispatch_context", "request_ref", "summarize_request",
    "model_routing", "route_model",
    "backoff_delay", "build_tool_retry", "retry_hint", "should_retry",
    "build_log_record", "tool_logging",
    "build_error_response", "build_regenerate_instruction", "validate_response",
]
