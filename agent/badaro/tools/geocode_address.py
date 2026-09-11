"""TMAP 주소 좌표 변환 Tool과 주소 결과 캐시."""

from __future__ import annotations

import math
import os
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
    response = _request_once(params)
    result = _parse_response(normalized_address, response)
    _CACHE[normalized_address] = result
    return result


def clear_geocode_cache() -> None:
    """테스트 또는 운영자 명령에서 주소 캐시를 비운다."""

    _CACHE.clear()


def _request_once(params: dict[str, str]) -> dict[str, Any]:
    """단일 HTTP 호출. 재시도는 공통 실행 계층(#13)이 담당한다."""
    try:
        response = httpx.get(TMAP_GEOCODE_URL, params=params, timeout=10.0)
    except httpx.TimeoutException as exc:
        _raise_error(ToolErrorCode.TIMEOUT, "TMAP 지오코딩 요청 시간이 초과되었습니다", True)
        raise AssertionError("unreachable") from exc
    except httpx.HTTPError:
        _raise_error(
            ToolErrorCode.UPSTREAM_ERROR, "TMAP 지오코딩 요청에 실패했습니다", True
        )
    if response.status_code == 429:
        _raise_error(ToolErrorCode.RATE_LIMITED, "TMAP 지오코딩 호출 한도를 초과했습니다", True)
    if response.status_code >= 500:
        _raise_error(
            ToolErrorCode.UPSTREAM_ERROR,
            f"TMAP 지오코딩 서버 오류 ({response.status_code})",
            True,
        )
    if response.status_code in (401, 403):
        _raise_error(ToolErrorCode.UNAUTHORIZED, "TMAP 앱키가 유효하지 않습니다", False)
    if response.status_code >= 400:
        _raise_error(
            ToolErrorCode.UPSTREAM_ERROR,
            f"TMAP 지오코딩 요청 오류 ({response.status_code})",
            False,
        )
    try:
        payload = response.json()
    except ValueError as exc:
        _raise_error(ToolErrorCode.UPSTREAM_ERROR, "TMAP 응답이 올바른 JSON이 아닙니다", False)
        raise AssertionError("unreachable") from exc
    if not isinstance(payload, dict):
        _raise_error(ToolErrorCode.UPSTREAM_ERROR, "TMAP 응답 구조가 올바르지 않습니다", False)
    return payload


def _parse_response(input_address: str, payload: dict[str, Any]) -> GeocodeResult:
    info = payload.get("coordinateInfo")
    if not isinstance(info, dict):
        _raise_error(ToolErrorCode.UPSTREAM_ERROR, "TMAP 응답에 coordinateInfo가 없습니다", False)
    raw_coordinates = info.get("coordinate")
    total_count = str(info.get("totalCount", "")).strip()
    if total_count == "0" and (raw_coordinates is None or raw_coordinates == []):
        return GeocodeResult(
            status=GeocodeStatus.NOT_FOUND, input_address=input_address, candidates=[]
        )
    if not isinstance(raw_coordinates, list):
        _raise_error(ToolErrorCode.UPSTREAM_ERROR, "TMAP coordinate가 배열이 아닙니다", False)

    candidates: list[GeocodeCandidate] = []
    exact_candidates: list[GeocodeCandidate] = []
    for item in raw_coordinates:
        if not isinstance(item, dict):
            _raise_error(
                ToolErrorCode.UPSTREAM_ERROR,
                "TMAP 좌표 항목 구조가 올바르지 않습니다",
                False,
            )
        road_exact = item.get("newMatchFlag") == "N51"
        lot_exact = item.get("matchFlag") in {"M11", "M21"}
        use_road = road_exact or (
            not lot_exact and bool(item.get("newLat")) and bool(item.get("newLon"))
        )
        lat = item.get("newLat") if use_road else item.get("lat")
        lon = item.get("newLon") if use_road else item.get("lon")
        try:
            lat_value, lon_value = float(lat), float(lon)
        except (TypeError, ValueError) as exc:
            _raise_error(ToolErrorCode.UPSTREAM_ERROR, "TMAP 좌표 값이 숫자가 아닙니다", False)
            raise AssertionError("unreachable") from exc
        if not math.isfinite(lat_value) or not math.isfinite(lon_value):
            _raise_error(ToolErrorCode.UPSTREAM_ERROR, "TMAP 좌표 값이 유효하지 않습니다", False)
        if not -90 <= lat_value <= 90 or not -180 <= lon_value <= 180:
            _raise_error(
                ToolErrorCode.UPSTREAM_ERROR, "TMAP 좌표가 허용 범위를 벗어났습니다", False
            )
        address_fields = (
            ("city_do", "gu_gun", "newRoadName", "newBuildingIndex", "newBuildingName")
            if use_road else
            ("city_do", "gu_gun", "eup_myun", "legalDong", "ri", "bunji", "buildingName")
        )
        matched_address = (
            " ".join(
                str(item.get(key, "")).strip()
                for key in address_fields
                if item.get(key)
            )
            or input_address
        )
        candidates.append(
            GeocodeCandidate(matched_address=matched_address, lat=lat_value, lon=lon_value)
        )
        is_exact = road_exact if use_road else lot_exact
        if is_exact:
            exact_candidates.append(candidates[-1])

    if not candidates:
        return GeocodeResult(
            status=GeocodeStatus.NOT_FOUND, input_address=input_address, candidates=[]
        )
    if len(exact_candidates) == 1:
        return GeocodeResult(
            status=GeocodeStatus.OK,
            input_address=input_address,
            candidates=exact_candidates,
        )
    return GeocodeResult(
        status=GeocodeStatus.AMBIGUOUS,
        input_address=input_address,
        candidates=candidates,
    )


def _raise_error(code: ToolErrorCode, message: str, retryable: bool) -> None:
    raise ToolErrorException(ToolError(code=code, message=message, retryable=retryable))
