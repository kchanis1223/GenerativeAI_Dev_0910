"""InputValidationMiddleware — 3.2 / G-01 (이슈 #12 B-12 · 우선순위 P0)

Hook  : before_agent (호출 시 1회, 모델에 가기 전)
목적  : 주소·좌표·차량 수 등 기본 형식을 모델에 보내기 전에 걸러낸다.
v2 보완: ① 상한을 수치로 명시  ② 복수 오류를 pending_clarifications 에 모아 한 번에 되묻는다

설계 원칙: 오류를 하나 만날 때마다 던지지 않는다. 전부 모아서 한 번에 물어본다(시나리오 3).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from ._compat import ai_message, before_agent

MAX_DESTINATIONS = 50
MIN_VEHICLES, MAX_VEHICLES = 1, 20
KR_LAT = (33.0, 38.7)
KR_LON = (124.5, 132.0)
MAX_DAYS_AHEAD = 14


def _issue(field: str, code: str, message: str, row: int | None = None) -> dict[str, Any]:
    """되물을 항목 1건을 만든다. 이 dict 가 그대로 State 의 pending_clarifications 에 쌓인다."""
    item = {"field": field, "code": code, "message": message}
    if row is not None:
        item["row"] = row
    return item


def validate_dispatch_input(payload: dict[str, Any], *, now_kst: datetime) -> list[dict[str, Any]]:
    """배차 입력을 검사해 '되물을 항목 목록'을 돌려준다. 빈 리스트면 통과.

    순수 함수다 — langchain 없이도 바로 테스트할 수 있다 (TS-09-C01/C02).
    """
    issues: list[dict[str, Any]] = []

    dests = payload.get("destinations")
    if not isinstance(dests, list) or len(dests) == 0:
        issues.append(_issue("destinations", "empty", "배송지가 없습니다. 지점 목록을 알려주세요."))
    elif len(dests) > MAX_DESTINATIONS:
        issues.append(_issue(
            "destinations", "too_many",
            f"배송지가 {len(dests)}건입니다. 한 번에 처리 가능한 상한은 {MAX_DESTINATIONS}건이라 나눠서 요청해 주세요.",
        ))

    if isinstance(dests, list):
        for i, d in enumerate(dests, start=1):
            if not isinstance(d, dict):
                issues.append(_issue("destinations", "bad_row", "행 형식이 올바르지 않습니다.", row=i))
                continue
            lat, lon = d.get("lat"), d.get("lon")
            if lat is None and lon is None:
                continue
            if not isinstance(lat, (int, float)) or not KR_LAT[0] <= lat <= KR_LAT[1]:
                issues.append(_issue("lat", "out_of_range",
                    f"위도 값이 국내 범위({KR_LAT[0]}~{KR_LAT[1]})를 벗어납니다.", row=i))
            if not isinstance(lon, (int, float)) or not KR_LON[0] <= lon <= KR_LON[1]:
                issues.append(_issue("lon", "out_of_range",
                    f"경도 값이 국내 범위({KR_LON[0]}~{KR_LON[1]})를 벗어납니다.", row=i))

    vc = payload.get("vehicle_count")
    if vc is not None:
        if isinstance(vc, bool) or not isinstance(vc, int):
            issues.append(_issue("vehicle_count", "not_int", "차량 수는 정수로 알려주세요."))
        elif not MIN_VEHICLES <= vc <= MAX_VEHICLES:
            issues.append(_issue("vehicle_count", "out_of_range",
                f"차량 수는 {MIN_VEHICLES}~{MAX_VEHICLES}대 사이여야 합니다. (받은 값: {vc})"))

    raw = payload.get("delivery_date")
    if raw is not None:
        try:
            d = date.fromisoformat(str(raw))
        except ValueError:
            issues.append(_issue("delivery_date", "bad_format", "배송일은 YYYY-MM-DD 형식으로 알려주세요."))
        else:
            today = now_kst.date()
            if d < today:
                issues.append(_issue("delivery_date", "past", f"배송일 {d}은 지난 날짜입니다."))
            elif d > today + timedelta(days=MAX_DAYS_AHEAD):
                issues.append(_issue("delivery_date", "too_far",
                    f"배송일은 오늘부터 {MAX_DAYS_AHEAD}일 이내로 지정해 주세요."))

    return issues


def build_clarification_message(issues: list[dict[str, Any]]) -> str:
    """모아둔 오류를 '한 번에 물어보는' 안내문 한 덩어리로 만든다 (v2 보완 ②)."""
    head = "배차를 시작하기 전에 아래 항목을 확인해 주세요."
    lines = []
    for it in issues:
        prefix = f"{it['row']}행: " if "row" in it else ""
        lines.append(f"- {prefix}{it['message']}")
    return head + "\n" + "\n".join(lines)


@before_agent(can_jump_to=["end"])
def input_validation(state: dict[str, Any], runtime: Any) -> dict[str, Any] | None:
    """오류가 있으면 모델을 부르지 않고 바로 되묻고 끝낸다 (G-01 차단)."""
    payload = state.get("dispatch_request") or {}
    now = getattr(runtime.context, "now_kst", datetime.now())
    issues = validate_dispatch_input(payload, now_kst=now)

    if not issues:
        return None

    return {
        "messages": [ai_message(build_clarification_message(issues))],
        "pending_clarifications": issues,
        "jump_to": "end",
    }
