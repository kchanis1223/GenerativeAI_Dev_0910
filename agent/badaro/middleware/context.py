"""Runtime Context — 설계서 3.1 (이슈 #11)

호출 시점에 정해지고 대화 내내 바뀌지 않는 값.
create_agent(context_schema=BadaroContext) 로 등록하고 미들웨어는 읽기만 한다.

차량·좌표·보관유형 타입은 badaro.schemas(B-03)를 그대로 쓴다. 같은 개념을 두 번 정의하지 않는다.
depot_profile 은 센터 ID·확정 출발 좌표·보유 차량의 출처다.
화면에서 고른 역할은 권한 근거로 쓰지 않는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import uuid4
from zoneinfo import ZoneInfo

from badaro.schemas import GeocodeCandidate, StorageType, Vehicle

KST = ZoneInfo("Asia/Seoul")

UserRole = Literal["operator", "driver", "viewer"]
RoleSource = Literal["server", "ui"]

_ENV_NAME_RE = re.compile(r"[A-Z][A-Z0-9_]{2,39}")


@dataclass(frozen=True)
class DepotProfile:
    """물류센터 마스터. 실행 시 depot_id 와 origin 의 출처가 된다.

    차량의 supported_storage_types 가 비어 있으면 적합성 검사 불가이며 추정하지 않는다.
    """
    depot_id: str
    name: str
    origin: GeocodeCandidate
    vehicles: tuple[Vehicle, ...] = ()

    def vehicle(self, vehicle_id: str) -> Vehicle | None:
        """차량 ID 로 제원 1건을 찾는다. 없으면 None."""
        for v in self.vehicles:
            if v.vehicle_id == vehicle_id:
                return v
        return None

    def candidates_for(self, storage_type: StorageType) -> tuple[Vehicle, ...]:
        """해당 보관유형을 실을 수 있다고 확정된 가용 차량만 반환한다."""
        return tuple(
            v for v in self.vehicles
            if v.available and storage_type in v.supported_storage_types
        )

    def unverifiable(self) -> tuple[Vehicle, ...]:
        """지원 보관유형이 확정되지 않아 적합성을 검사할 수 없는 차량."""
        return tuple(v for v in self.vehicles if not v.supported_storage_types)


@dataclass
class BadaroContext:
    """설계서 3.1 Runtime Context.

    role_source 가 'ui' 이면 화면에서 고른 역할이므로 권한 판단에 쓰지 않는다.
    실제 권한은 서버 인증정보(role_source='server')로만 인정한다.
    """
    tenant_id: str
    user_id: str
    user_role: UserRole
    depot_profile: DepotProfile

    role_source: RoleSource = "ui"
    assigned_vehicle_ids: tuple[str, ...] = ()
    app_key_ref: str = "TMAP_APP_KEY"
    request_id: str = field(default_factory=lambda: str(uuid4()))
    now_kst: datetime = field(default_factory=lambda: datetime.now(KST))

    def __post_init__(self) -> None:
        """비밀값 오입력을 막는다. 오류 메시지에 입력값을 넣지 않는다."""
        if not _ENV_NAME_RE.fullmatch(self.app_key_ref):
            raise ValueError(
                "app_key_ref 에는 환경변수 이름만 넣습니다 (예: 'TMAP_APP_KEY'). "
                "받은 값의 형식이 이름 규칙에 맞지 않습니다."
            )

    @property
    def is_server_verified(self) -> bool:
        return self.role_source == "server"

    @property
    def is_driver(self) -> bool:
        return self.user_role == "driver"

    @property
    def can_confirm(self) -> bool:
        """배차를 확정할 수 있는가. 서버가 확인한 운영자만 True."""
        return self.is_server_verified and self.user_role == "operator"

    def visible_vehicle_ids(self, all_vehicle_ids: tuple[str, ...]) -> tuple[str, ...] | None:
        """조회 가능한 차량 범위. 확인할 수 없으면 None 이며 호출자가 조회를 중단한다."""
        if not self.is_server_verified:
            return None
        if not self.is_driver:
            return all_vehicle_ids
        if not self.assigned_vehicle_ids:
            return None
        return tuple(v for v in all_vehicle_ids if v in self.assigned_vehicle_ids)
