"""InputValidation — 설계서 3.2 / G-01 (이슈 #12)

요청 진입 시 입력 형식을 검사한다. 오류 필드만 모아 한 번에 되묻는다.

v1.3 반영: DispatchRequest 필드는 depot_id, destination_ids, delivery_date, departure_time,
           vehicle_count, excluded_destination_ids, excluded_vehicle_ids, product_names,
           deadline, priority, storage_types 다.
           좌표는 요청이 아니라 GeocodeResult 후보에서 검사한다.

선택 필드의 기본값과 업무상 실행 가능 여부는 구분한다.
확인되지 않은 ID 를 만들지 않는다.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel

from ._compat import ai_message, before_agent

MAX_DESTINATIONS = 50
MIN_VEHICLES, MAX_VEHICLES = 1, 20
MAX_DAYS_AHEAD = 14
LAT_RANGE = (-90.0, 90.0)
LON_RANGE = (-180.0, 180.0)

PRIORITIES = ("normal", "urgent")
STORAGE_TYPES = ("live", "refrigerated", "frozen", "ambient")

_ID_LIST_FIELDS = ("destination_ids", "excluded_destination_ids", "excluded_vehicle_ids",
                   "product_names")


def _issue(field: str, code: str, message: str, row: int | None = None) -> dict[str, Any]:
    """되물을 항목 1건. 그대로 pending_clarifications 에 쌓인다."""
    item = {"field": field, "code": code, "message": message}
    if row is not None:
        item["row"] = row
    return item


def _parse_dt(raw: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None


def validate_dispatch_input(payload: dict[str, Any] | BaseModel, *,
                            now_kst: datetime,
                            max_destinations: int | None = None,
                            max_vehicles: int | None = None,
                            max_days_ahead: int | None = None) -> list[dict[str, Any]]:
    """DispatchRequest 입력을 검사해 되물을 항목 목록을 반환한다. 빈 목록이면 통과."""
    issues: list[dict[str, Any]] = []
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    if not isinstance(payload, dict):
        return [_issue("request", "bad_type", "배차 요청 형식을 확인해 주세요.")]

    if not payload.get("depot_id"):
        issues.append(_issue("depot_id", "missing", "출발 물류센터를 확인하지 못했습니다."))

    raw_date = payload.get("delivery_date")
    if raw_date is None:
        issues.append(_issue("delivery_date", "missing", "배송일을 알려주세요."))
    else:
        try:
            d = date.fromisoformat(str(raw_date))
        except ValueError:
            issues.append(_issue("delivery_date", "bad_format",
                                 "배송일은 YYYY-MM-DD 형식으로 알려주세요."))
        else:
            today = now_kst.date()
            if d < today:
                issues.append(_issue("delivery_date", "past", f"배송일 {d}은 지난 날짜입니다."))
            elif max_days_ahead is not None and d > today + timedelta(days=max_days_ahead):
                issues.append(_issue("delivery_date", "too_far",
                                     f"배송일은 오늘부터 {max_days_ahead}일 이내로 지정해 주세요."))

    dests = payload.get("destination_ids")
    if dests is not None:
        if not isinstance(dests, list):
            issues.append(_issue("destination_ids", "bad_type",
                                 "배송지 목록 형식이 올바르지 않습니다."))
        elif len(dests) == 0:
            issues.append(_issue("destination_ids", "empty",
                                 "배송지를 지정하지 않으려면 값을 비우고, "
                                 "지정하려면 지점을 알려주세요."))
        elif max_destinations is not None and len(dests) > max_destinations:
            issues.append(_issue("destination_ids", "too_many",
                                 f"배송지가 {len(dests)}건입니다. 상한 {max_destinations}건이라 "
                                 f"나눠서 요청해 주세요."))

    for fname in _ID_LIST_FIELDS:
        val = payload.get(fname)
        if val is not None and not isinstance(val, list):
            issues.append(_issue(fname, "bad_type", f"{fname} 은 목록이어야 합니다."))

    vc = payload.get("vehicle_count")
    if vc is not None:
        if isinstance(vc, bool) or not isinstance(vc, int):
            issues.append(_issue("vehicle_count", "not_int", "차량 수는 정수로 알려주세요."))
        elif vc < MIN_VEHICLES or (max_vehicles is not None and vc > max_vehicles):
            issues.append(_issue("vehicle_count", "out_of_range",
                                 "차량 수가 허용 범위를 벗어났습니다. "
                                 f"(받은 값: {vc})"))

    priority = payload.get("priority")
    if priority is not None and priority not in PRIORITIES:
        issues.append(_issue("priority", "bad_value",
                             f"우선순위는 {' 또는 '.join(PRIORITIES)} 입니다."))

    st = payload.get("storage_types")
    if st is not None:
        if not isinstance(st, list):
            issues.append(_issue("storage_types", "bad_type", "보관 조건은 목록이어야 합니다."))
        else:
            for bad in [x for x in st if x not in STORAGE_TYPES]:
                issues.append(_issue("storage_types", "bad_value",
                                     f"알 수 없는 보관 조건입니다: {bad}"))

    dep = _parse_dt(payload["departure_time"]) if payload.get("departure_time") else None
    dl = _parse_dt(payload["deadline"]) if payload.get("deadline") else None
    if payload.get("departure_time") and dep is None:
        issues.append(_issue("departure_time", "bad_format", "출발 시각 형식이 올바르지 않습니다."))
    if payload.get("deadline") and dl is None:
        issues.append(_issue("deadline", "bad_format", "마감 시각 형식이 올바르지 않습니다."))
    if dep and dl:
        if (dep.utcoffset() is None) != (dl.utcoffset() is None):
            issues.append(_issue("deadline", "timezone_mismatch",
                                 "출발과 마감 시각의 시간대를 함께 지정해 주세요."))
        elif dl <= dep:
            issues.append(_issue("deadline", "before_departure",
                                 "납품 마감 시각이 출발 시각보다 빠릅니다."))

    return issues


def validate_geocode_candidate(candidate: dict[str, Any], row: int | None = None
                               ) -> list[dict[str, Any]]:
    """GeocodeCandidate 의 좌표 범위를 검사한다. 위도 -90~90, 경도 -180~180."""
    issues: list[dict[str, Any]] = []
    lat, lon = candidate.get("lat"), candidate.get("lon")
    if not isinstance(lat, (int, float)) or not LAT_RANGE[0] <= lat <= LAT_RANGE[1]:
        issues.append(_issue("lat", "out_of_range",
                             f"위도가 허용 범위({LAT_RANGE[0]}~{LAT_RANGE[1]})를 벗어납니다.", row))
    if not isinstance(lon, (int, float)) or not LON_RANGE[0] <= lon <= LON_RANGE[1]:
        issues.append(_issue("lon", "out_of_range",
                             f"경도가 허용 범위({LON_RANGE[0]}~{LON_RANGE[1]})를 벗어납니다.", row))
    return issues


def build_clarification_message(issues: list[dict[str, Any]]) -> str:
    """모아둔 오류를 한 번에 묻는 안내문으로 만든다."""
    head = "배차를 시작하기 전에 아래 항목을 확인해 주세요."
    lines = []
    for it in issues:
        prefix = f"{it['row']}행: " if "row" in it else ""
        lines.append(f"- {prefix}{it['message']}")
    return head + "\n" + "\n".join(lines)


@before_agent(can_jump_to=["end"])
def input_validation(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    """오류가 있으면 모델을 부르지 않고 되묻고 끝낸다."""
    payload = state.get("dispatch_request") or {}
    if not payload:
        return None
    now = getattr(runtime.context, "now_kst", datetime.now())
    issues = validate_dispatch_input(payload, now_kst=now)
    if not issues:
        return None
    return {
        "messages": [ai_message(build_clarification_message(issues))],
        "pending_clarifications": issues,
        "jump_to": "end",
    }
