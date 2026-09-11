"""바다로 Dispatch Copilot — 3.1 Runtime Context (이슈 #11 B-11 / 설계서 v2 3.1)

Runtime Context = 호출 시점에 정해지고 대화 내내 바뀌지 않는 값.
create_agent(context_schema=BadaroContext) 로 등록하고,
미들웨어 안에서는 runtime.context 로 "읽기만" 한다. 바뀌는 값은 state.py 로.

설계 원칙 ① 비밀값은 참조(ref)만 두고 실제 문자열은 모델에 노출하지 않는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

UserRole = Literal["operator", "driver", "viewer"]
StorageType = Literal["live_fish", "chilled", "frozen", "normal"]
VehicleType = Literal["tank", "refrigerated", "normal"]

_ENV_NAME_RE = re.compile(r"[A-Z][A-Z0-9_]{2,39}")

STORAGE_TO_VEHICLE: dict[str, tuple[str, ...]] = {
    "live_fish": ("tank",),
    "chilled":   ("refrigerated",),
    "frozen":    ("refrigerated",),
    "normal":    ("tank", "refrigerated", "normal"),
}


@dataclass(frozen=True)
class VehicleSpec:
    """depot_profile 안에 들어가는 차량 1대의 제원. 3.2.2 검사 기준값의 출처."""
    vehicle_id: str
    vehicle_type: VehicleType
    max_payload_kg: int
    tank_capacity_kg: int | None = None
    temp_range_c: tuple[float, float] | None = None

    def accepts(self, storage_type: StorageType) -> bool:
        """이 차가 해당 보관유형을 실을 수 있나? (G-08 콜드체인·차량 적합성)"""
        return self.vehicle_type in STORAGE_TO_VEHICLE[storage_type]


@dataclass(frozen=True)
class DepotProfile:
    """중앙 물류센터 1곳 + 보유 차량 목록 (설계서 1.1 — 노량진 센터, 차량 5대)."""
    depot_id: str
    name: str
    lat: float
    lon: float
    vehicles: tuple[VehicleSpec, ...] = ()

    def vehicle(self, vehicle_id: str) -> VehicleSpec | None:
        """차량 ID 로 제원 1건을 찾는다. 없으면 None — 없는 차량을 지어내지 않기 위함 (G-04)."""
        for v in self.vehicles:
            if v.vehicle_id == vehicle_id:
                return v
        return None

    def candidates_for(self, storage_type: StorageType) -> tuple[VehicleSpec, ...]:
        """해당 보관유형을 실을 수 있는 차량만 골라낸다. G-08 차단 판정의 후보 집합."""
        return tuple(v for v in self.vehicles if v.accepts(storage_type))


@dataclass
class BadaroContext:
    """3.1 Runtime Context 8항목. create_agent(context_schema=BadaroContext) 로 등록한다.

    ⭐ = v2 신규:  user_id / request_id / now_kst / tms_daily_quota
    """
    tenant_id: str
    user_id: str
    user_role: UserRole
    depot_profile: DepotProfile

    app_key_ref: str = "TMAP_APP_KEY"
    tms_daily_quota: int = 20
    request_id: str = field(
        default_factory=lambda: str(uuid4())
    )
    now_kst: datetime = field(
        default_factory=lambda: datetime.now(KST)
    )

    def __post_init__(self) -> None:
        """dataclass 가 __init__ 을 끝낸 직후 자동 호출된다. 여기서 비밀값 오입력을 막는다."""
        ref = self.app_key_ref
        if not _ENV_NAME_RE.fullmatch(ref):
            raise ValueError(
                f"app_key_ref 에는 환경변수 '이름'만 넣습니다 (예: 'TMAP_APP_KEY'). "
                f"받은 값의 형식이 이름 규칙에 맞지 않습니다 — 설계서 3.1 설계원칙 ①"
            )

    @property
    def is_driver(self) -> bool:
        """기사 계정인가? 기사는 조회만 가능하고 확정·취소는 못 한다."""
        return self.user_role == "driver"

    @property
    def can_confirm(self) -> bool:
        """배차를 확정할 수 있는 역할인가? 운영자만 True (G-06 / G-11)."""
        return self.user_role == "operator"
