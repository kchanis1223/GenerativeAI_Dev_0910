"""바다로 Dispatch Copilot — 3.1 Store (이슈 #11 B-11 / 설계서 v2 3.1)

Store = 대화(thread)를 넘어 남는 값. checkpointer 가 아니라 BaseStore 가 보관한다.
State 와의 차이: State 는 "이번 대화", Store 는 "이 조직의 계속 쓰는 데이터".
"""
from __future__ import annotations

from typing import Any

_ROOT = "badaro"


def ns_prefs(tenant_id: str) -> tuple[str, ...]:
    """default_dispatch_prefs — 기본 센터·선호 옵션 등 개인화 값."""
    return (_ROOT, tenant_id, "prefs")

def ns_store_master(tenant_id: str) -> tuple[str, ...]:
    """⭐ store_master — 지점별 오픈시간·하역장 특이사항·담당자 연락처.
    시나리오 4의 '여의도점은 하역장이 지하' 안내는 이 값이 있어야 생성 가능하고,
    없으면 G-04(근거 없는 생성)에 걸린다."""
    return (_ROOT, tenant_id, "store_master")

def ns_geocode(tenant_id: str) -> tuple[str, ...]:
    """⭐ geocode_cache — 확정된 주소→좌표. 1.5 성능 항목의 캐싱이 실제로 저장되는 곳."""
    return (_ROOT, tenant_id, "geocode_cache")

def ns_audit(tenant_id: str) -> tuple[str, ...]:
    """⭐ dispatch_audit_log — 확정·변경·취소 이벤트 누적 (append-only).
    화물자동차 운수사업법 제47조의2 운송실적 신고 대응 기반."""
    return (_ROOT, tenant_id, "audit")


def get_store_info(store, tenant_id: str, store_code: str) -> dict[str, Any] | None:
    """지점 1곳의 마스터 정보를 읽는다. 없으면 None — 지어내지 않는다 (G-04)."""
    item = store.get(ns_store_master(tenant_id), store_code)
    return item.value if item else None

def get_cached_coord(store, tenant_id: str, address: str) -> dict[str, float] | None:
    """이미 변환해 둔 좌표가 있으면 돌려준다. TMAP 재호출을 막는 근거 (TS-03-C02)."""
    item = store.get(ns_geocode(tenant_id), address)
    return item.value if item else None


def put_cached_coord(store, tenant_id: str, address: str, lat: float, lon: float) -> None:
    """지오코딩 성공분만 캐시에 넣는다. 실패(None)는 저장하지 않는다 — 틀린 좌표가 굳어지면 안 되니까."""
    store.put(ns_geocode(tenant_id), address, {"lat": lat, "lon": lon})

def append_audit(store, tenant_id: str, event: dict[str, Any]) -> None:
    """확정·변경·취소 이벤트를 누적 기록한다. 덮어쓰지 않고 타임스탬프 키로 계속 쌓는다."""
    from datetime import datetime
    from .context import KST
    key = datetime.now(KST).isoformat()
    store.put(ns_audit(tenant_id), key, event)
