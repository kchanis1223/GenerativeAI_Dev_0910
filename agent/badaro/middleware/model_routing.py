"""ModelRoutingMiddleware — 3.2 (이슈 #12 B-12 · v2 우선순위 P1)

Hook  : wrap_model_call (모델 호출을 감싼다)
목적  : 단순 분류·조회는 경량 모델로, 배차 계획 같은 복합 추론은 메인 모델로 보낸다.
실패 시: 판단이 애매하면 무조건 메인 모델로 간다 (v2 "메인 모델로 fallback").

⚠ v2 에서 이 미들웨어는 P0 → P1 로 내려갔다. 시연 필수는 아니고, 시간이 되면 켜는 쪽.
   그래서 라우팅이 틀려도 '느려지거나 비싸질 뿐' 결과가 망가지지 않도록 설계했다.
"""
from __future__ import annotations

from typing import Any, Literal

from ._compat import wrap_model_call

ModelTier = Literal["light", "main"]

_HEAVY_HINTS = (
    "배차", "배정", "경로", "최적화", "다시", "재배차", "바꿔", "빼줘", "추가해", "확정",
)
_LIGHT_HINTS = (
    "몇", "언제", "어디", "누구", "알려줘", "보여줘", "안녕", "고마",
)


def route_model(text: str, state: dict[str, Any] | None = None) -> ModelTier:
    """이번 요청을 어느 모델로 보낼지 정한다. 순수 함수라 단독 테스트가 된다.

    판단 순서 ① 배차 신호가 있으면 무조건 메인
             ② 진행 중인 배차가 있으면 후속 수정일 가능성이 커서 메인
             ③ 조회·잡담 신호만 있으면 경량
             ④ 어느 쪽도 아니면 메인 (안전한 쪽으로 fallback)
    """
    t = (text or "").strip()

    if any(h in t for h in _HEAVY_HINTS):
        return "main"

    if state and state.get("last_dispatch_result"):
        return "main"

    if len(t) <= 40 and any(h in t for h in _LIGHT_HINTS):
        return "light"

    return "main"


def _last_user_text(request: Any) -> str:
    """모델 요청에서 마지막 사용자 발화를 꺼낸다. 구조가 달라도 죽지 않게 방어적으로 접근."""
    msgs = getattr(request, "messages", None) or []
    for m in reversed(msgs):
        content = getattr(m, "content", None)
        role = getattr(m, "type", getattr(m, "role", ""))
        if content and role in ("human", "user"):
            return str(content)
    return ""


@wrap_model_call
def model_routing(request: Any, handler: Any) -> Any:
    """경량으로 보내도 되는 요청이면 모델을 갈아끼우고, 아니면 그대로 흘려보낸다."""
    light = getattr(request, "light_model", None)
    if light is None:
        return handler(request)

    tier = route_model(_last_user_text(request), getattr(request, "state", None))
    if tier == "light":
        request = request.override(model=light)
    return handler(request)
