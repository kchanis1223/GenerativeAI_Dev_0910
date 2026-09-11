"""TMAP 주소 좌표 변환 Tool과 주소 결과 캐시."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

from badaro.schemas import (
    GeocodeCandidate,
    GeocodeResult,
    GeocodeStatus,
    ToolError,
    ToolErrorCode,
    ToolErrorException,
)

TMAP_GEOCODE_URL = "https://apis.openapi.sk.com/tmap/geo/fullAddrGeo"
_CACHE: dict[str, GeocodeResult] = {}

load_dotenv()


def geocode_address(address: str) -> GeocodeResult:
    """주소를 좌표 후보로 변환한다.

    정상 결과는 State ``geocodes``에 ``input_address``를 key로 기록하여
    같은 주소의 좌표를 재사용한다.
    ``ambiguous`` 또는 ``not_found`` 결과는 사용자 확인 없이는 배차에
    사용하지 않는다. 외부 API 오류는 ToolError로 전달한다.
    """
    normalized_address = address.strip() if isinstance(address, str) else ""
    if not normalized_address:
        _raise_error(ToolErrorCode.INVALID_INPUT, "주소가 비어 있습니다", retryable=False)

    cached = _CACHE.get(normalized_address)
    if cached is not None:
        return cached

    app_key = os.getenv("TMAP_APP_KEY", "").strip()
    if not app_key:
        _raise_error(
            ToolErrorCode.UNAUTHORIZED, "TMAP_APP_KEY가 설정되지 않았습니다", retryable=False
        )

    params = {
        "version": "1",
        "addressFlag": "F00",
        "coordType": "WGS84GEO",
        "fullAddr": normalized_address,
        "appKey": app_key,
    }
    response = _request_with_retry(params)
    result = _parse_response(normalized_address, response)
    _CACHE[normalized_address] = result
    return result


def clear_geocode_cache() -> None:
    """테스트 또는 운영자 명령에서 주소 캐시를 비운다."""

    _CACHE.clear()


def _request_with_retry(params: dict[str, str]) -> dict[str, Any]:
    max_retries = max(0, int(os.getenv("TOOL_MAX_RETRIES", "3")))
    for attempt in range(max_retries + 1):
        try:
            response = httpx.get(TMAP_GEOCODE_URL, params=params, timeout=10.0)
        except httpx.TimeoutException as exc:
            if attempt < max_retries:
                time.sleep(min(2**attempt, 4))
                continue
            _raise_error(
                ToolErrorCode.TIMEOUT, "TMAP 지오코딩 요청 시간이 초과되었습니다", retryable=True
            )
            raise AssertionError("unreachable") from exc
        except httpx.HTTPError as exc:
            _raise_error(
                ToolErrorCode.UPSTREAM_ERROR,
                f"TMAP 지오코딩 요청에 실패했습니다: {exc}",
                retryable=True,
            )

        if response.status_code == 429 or response.status_code >= 500:
            if attempt < max_retries:
                time.sleep(min(2**attempt, 4))
                continue
            code = (
                ToolErrorCode.RATE_LIMITED
                if response.status_code == 429
                else ToolErrorCode.UPSTREAM_ERROR
            )
            _raise_error(code, f"TMAP 지오코딩 서버 오류 ({response.status_code})", retryable=True)
        if response.status_code in (401, 403):
            _raise_error(
                ToolErrorCode.UNAUTHORIZED, "TMAP 앱키가 유효하지 않습니다", retryable=False
            )
        if response.status_code >= 400:
            _raise_error(
                ToolErrorCode.UPSTREAM_ERROR,
                f"TMAP 지오코딩 요청 오류 ({response.status_code})",
                retryable=False,
            )
        try:
            return response.json()
        except ValueError as exc:
            _raise_error(
                ToolErrorCode.UPSTREAM_ERROR, "TMAP 응답이 올바른 JSON이 아닙니다", retryable=False
            )
            raise AssertionError("unreachable") from exc
    raise AssertionError("unreachable")


def _parse_response(input_address: str, payload: dict[str, Any]) -> GeocodeResult:
    info = payload.get("coordinateInfo") or {}
    raw_coordinates = info.get("coordinate") or []
    if not raw_coordinates or str(info.get("totalCount", "0")) == "0":
        return GeocodeResult(
            status=GeocodeStatus.NOT_FOUND, input_address=input_address, candidates=[]
        )

    candidates: list[GeocodeCandidate] = []
    for item in raw_coordinates:
        lat = item.get("newLat") or item.get("lat")
        lon = item.get("newLon") or item.get("lon")
        if not lat or not lon:
            continue
        matched_address = (
            " ".join(
                str(item.get(key, "")).strip()
                for key in (
                    "city_do",
                    "gu_gun",
                    "newRoadName",
                    "newBuildingIndex",
                    "newBuildingName",
                )
                if item.get(key)
            )
            or input_address
        )
        candidates.append(
            GeocodeCandidate(matched_address=matched_address, lat=float(lat), lon=float(lon))
        )

    status = GeocodeStatus.OK if len(candidates) == 1 else GeocodeStatus.AMBIGUOUS
    return GeocodeResult(status=status, input_address=input_address, candidates=candidates)


def _raise_error(code: ToolErrorCode, message: str, retryable: bool) -> None:
    raise ToolErrorException(ToolError(code=code, message=message, retryable=retryable))
