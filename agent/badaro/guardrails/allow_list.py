"""공개 Tool 이름과 인자를 검사한다. 실행 설정과 runtime_context는 서버가 관리한다."""
from __future__ import annotations

from typing import Any

ALLOWED_ARGS: dict[str, frozenset[str]] = {
    "get_delivery_orders": frozenset({
        "depot_id", "delivery_date", "destination_ids", "product_names",
    }),
    "get_available_vehicles": frozenset({
        "depot_id", "delivery_date", "vehicle_count", "excluded_vehicle_ids",
    }),
    "geocode_address": frozenset({"address"}),
    "optimize_dispatch": frozenset({"order_ids", "vehicle_ids", "constraints"}),
}

FORBIDDEN_ARGS: frozenset[str] = frozenset({
    "endpoint", "url", "base_url", "host", "proxy", "proxies",
    "header", "headers", "cookie", "cookies",
    "appkey", "app_key", "apikey", "api_key", "authorization",
    "token", "access_token", "secret", "password",
    "verify", "verify_ssl", "cert", "timeout_override",
    "runtimecontext",
})

BLOCK_MESSAGE = (
    "도구 호출 인자에 허용되지 않은 항목이 있어 호출을 차단했습니다. "
    "통신 경로나 인증 정보는 요청으로 바꿀 수 없습니다."
)


def _normalize(key: str) -> str:
    """인자 이름을 비교하기 좋게 다듬는다. 'App-Key', 'APP_KEY' 를 모두 'appkey' 로."""
    return key.lower().replace("-", "").replace("_", "")


def check_tool_args(tool_name: str, args: Any) -> list[dict[str, Any]]:
    """도구 인자를 검사해 위반 목록을 돌려준다. 빈 리스트면 통과.

    판정 ① 금지 인자가 있으면 → 위반 (어느 도구든)
          ② 허용 목록에 없는 인자면 → 위반
          ③ 모르는 도구면 → 위반 (allow-list 의 기본은 '모르면 거부')
    """
    violations: list[dict[str, Any]] = []
    if not isinstance(args, dict):
        return [{"guardrail": "G-03", "reason": "bad_type",
                 "message": "Tool 인자는 객체여야 합니다."}]

    allowed = ALLOWED_ARGS.get(tool_name)
    if allowed is None:
        return [{"guardrail": "G-03", "reason": "unknown_tool", "tool": tool_name,
                 "message": f"등록되지 않은 도구입니다: {tool_name}"}]

    forbidden_norm = {_normalize(f) for f in FORBIDDEN_ARGS}
    for key in args:
        norm = _normalize(str(key))
        if norm in forbidden_norm:
            violations.append({"guardrail": "G-03", "reason": "forbidden_arg", "arg": str(key),
                               "message": f"'{key}' 인자는 어떤 도구에서도 허용되지 않습니다."})
        elif str(key) not in allowed:
            violations.append({"guardrail": "G-03", "reason": "not_allowed", "arg": str(key),
                               "message": f"'{tool_name}' 에 허용되지 않은 인자입니다: {key}"})
    constraints = args.get("constraints")
    if isinstance(constraints, dict):
        from badaro.schemas import DispatchConstraints
        unknown = set(constraints) - set(DispatchConstraints.model_fields)
        if unknown:
            violations.append({"guardrail": "G-03", "reason": "not_allowed",
                               "message": "배차 제약조건에 허용되지 않은 항목이 있습니다."})
    return violations


def is_blocked(tool_name: str, args: Any) -> bool:
    """호출을 막아야 하는가? 위반이 하나라도 있으면 차단 (심각도 High)."""
    return len(check_tool_args(tool_name, args)) > 0
