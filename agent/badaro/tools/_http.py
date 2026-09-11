"""외부 HTTP 호출과 저장된 Mock 응답을 전환하는 공통 어댑터."""

import json
import os
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = {
    "/tmap/geo/fullAddrGeo": "tmap-geocode-response.json",
    "/tms/allocation": "tms-allocation-response.json",
    "/tms/allocationData": "tms-allocation-data-response.json",
}


def get(url: str, *, params: dict[str, str], timeout: float) -> httpx.Response:
    """USE_MOCK=1이면 docs/api fixture를 반환하고, 아니면 실제 GET을 수행한다."""
    if os.getenv("USE_MOCK", "0").strip() == "1":
        fixture = next(
            (name for suffix, name in _FIXTURES.items() if url.endswith(suffix)), None
        )
        if fixture is not None:
            payload = json.loads((_ROOT / "docs" / "api" / fixture).read_text(encoding="utf-8"))
            request = httpx.Request("GET", url, params=params)
            return httpx.Response(200, json=payload, request=request)
    return httpx.get(url, params=params, timeout=timeout)
