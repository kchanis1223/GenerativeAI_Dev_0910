"""외부 HTTP 호출과 B-02 저장 응답 재생을 전환한다."""

import json
import os
from importlib.resources import files

import httpx

from badaro.schemas import ToolError, ToolErrorCode, ToolErrorException

_BASE = "https://apis.openapi.sk.com"
_FIXTURES = {
    f"{_BASE}/tmap/geo/fullAddrGeo": ("tmap-geocode-response.json", {
        "version": "1", "addressFlag": "F00", "coordType": "WGS84GEO",
        "fullAddr": "서울특별시 중구 을지로 65",
    }),
    f"{_BASE}/tms/allocation": ("tms-allocation-response.json", {
        "allocationType": "2", "orderIdList": "badaro-b02-order",
        "vehicleIdList": "badaro-b02-vehicle", "startTime": "1100",
        "optionType": "1", "equalizationType": "1", "centerReturnYn": "Y",
    }),
    f"{_BASE}/tms/allocationData": ("tms-allocation-data-response.json", {
        "mappingKey": "<mapping-key>", "routeYn": "N",
    }),
}


def _error(code: ToolErrorCode, message: str):
    raise ToolErrorException(ToolError(code=code, message=message, retryable=False))


def mock_enabled() -> bool:
    """실행 모드 오타로 실제 API가 호출되지 않게 0과 1만 허용한다."""
    value = os.getenv("USE_MOCK", "0").strip()
    if value not in {"0", "1"}:
        _error(ToolErrorCode.INVALID_INPUT, "USE_MOCK는 0 또는 1이어야 합니다")
    return value == "1"


def get(url: str, *, params: dict[str, str], timeout: float) -> httpx.Response:
    """Mock에서는 저장된 요청과 일치하는 응답만 반환하며 외부 호출하지 않는다."""
    if not mock_enabled():
        return httpx.get(url, params=params, timeout=timeout)
    fixture = _FIXTURES.get(url)
    if fixture is None:
        _error(ToolErrorCode.INVALID_INPUT, "저장된 Mock 응답이 없는 API입니다")
    name, expected = fixture
    if {k: v for k, v in params.items() if k != "appKey"} != expected:
        _error(ToolErrorCode.INVALID_INPUT, "요청 조건에 맞는 저장된 Mock 응답이 없습니다")
    try:
        resource = files("badaro.tools").joinpath("mock_responses", name)
        payload = json.loads(resource.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError
    except (OSError, ValueError):
        _error(ToolErrorCode.INTERNAL_ERROR, "저장된 Mock 응답 파일을 읽을 수 없습니다")
    request = httpx.Request("GET", url, params=expected)
    return httpx.Response(200, json=payload, request=request)
