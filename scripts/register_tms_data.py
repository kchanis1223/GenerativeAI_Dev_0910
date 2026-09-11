"""시연 CSV를 TMS 등록값과 대조한다. --apply를 지정하면 없는 항목만 등록한다."""

import argparse
import csv
import json
import logging
import math
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = {"center": "centerId", "zone": "code", "vehicle": "vehicleId", "order": "orderId"}
NUMERIC = {"latitude", "longitude", "weight", "volume", "endLatitude", "endLongitude",
           "inputYn", "skillPer", "serviceTime", "deliveryWeight", "deliveryVolume"}


def plan(data_dir):
    catalog = {x["path"]: x for x in json.loads(
        (ROOT / "src/data/tms-api-catalog.json").read_text())}
    result = {}
    for kind, filename in (("center", "centers.csv"), ("vehicle", "vehicles.csv"),
                           ("order", "delivery_orders.csv")):
        with (data_dir / filename).open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        params = catalog[f"/{kind}Insert"]["parameters"]
        allowed = {p["name"] for p in params}
        required = {p["name"] for p in params if p["required"]}
        for row in rows:
            values = {k: v for k, v in row.items() if k in allowed and v != ""}
            if kind == "order":
                values["deliveryVolume"] = str(math.ceil(float(row["deliveryVolume"])))
            if not required <= values.keys():
                raise ValueError(f"{filename}: 필수 필드 누락")
            identity = (kind, values[IDENTITY[kind]])
            if identity in result and result[identity] != values:
                raise ValueError(f"{filename}: 같은 ID의 등록값이 다릅니다")
            result[identity] = values
    zones = {v["zoneCode"] for v in result.values() if v.get("zoneCode")}
    if zones != {"SEOUL"}:
        raise ValueError("이 도구는 제출 샘플의 SEOUL 권역만 지원합니다")
    centers = {k: v for k, v in result.items() if k[0] == "center"}
    return {**centers, ("zone", "SEOUL"): {"code": "SEOUL", "name": "서울 전역"}, **result}


def call(client, key, endpoint, values=None):
    try:
        response = client.get("https://apis.openapi.sk.com/tms/" + endpoint,
                              params={"appKey": key, **(values or {})})
        body = response.json()
    except (httpx.HTTPError, ValueError):
        raise RuntimeError(f"{endpoint}: 통신 실패. 재실행 전 목록을 확인하세요") from None
    if response.status_code != 200 or str(body.get("resultCode")) != "200":
        raise RuntimeError(f"{endpoint}: 요청 실패 (HTTP {response.status_code})")
    return body


def inventory(client, key):
    result = {}
    for kind, field in IDENTITY.items():
        body = call(client, key, kind + "List")
        rows = body.get("resultData") or []
        rows = [rows] if isinstance(rows, dict) else rows
        found = {str(row[field]): row for row in rows}
        if len(found) != len(rows) or len(rows) != int(body["resultCount"]):
            raise ValueError(kind + ": 목록 개수 또는 ID 중복 확인 필요")
        result.update({(kind, identity): row for identity, row in found.items()})
    return result


def matches(expected, actual):
    for field, value in expected.items():
        if field not in actual:
            return False
        try:
            equal = (math.isclose(float(value), float(actual[field]), rel_tol=0, abs_tol=1e-6)
                     if field in NUMERIC else str(value) == str(actual[field]))
        except (ValueError, TypeError):
            return False
        if not equal:
            return False
    return True


def register(client, key, expected, apply=False):
    before = inventory(client, key)
    for identity, values in expected.items():
        if identity in before and not matches(values, before[identity]):
            raise ValueError(f"기존 등록값 불일치: {identity[1]}. 수정하지 않았습니다")
    missing = {identity: values for identity, values in expected.items() if identity not in before}
    print(f"대상 {len(expected)}건, 기존 일치 {len(expected) - len(missing)}건, "
          f"추가 {len(missing)}건")
    if not apply:
        return
    for index, ((kind, identity), values) in enumerate(missing.items(), 1):
        call(client, key, kind + "Insert", values)
        if index % 25 == 0 or index == len(missing):
            print(f"등록 {index}/{len(missing)}", flush=True)
    after = inventory(client, key)
    if any(identity not in after or not matches(values, after[identity])
           for identity, values in expected.items()):
        raise ValueError("등록 후 대조 실패. TMS_MASTER_VERIFIED를 1로 설정하지 마세요")
    print(f"등록값 {len(expected)}건 대조 완료. 배차 접수 0회.")
    print("담당자 확인 후 TMS_MASTER_VERIFIED=1로 설정하세요.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)  # HTTP 쿼리에 들어가는 인증키를 출력하지 않는다.
    config = dotenv_values(ROOT / "agent/.env")
    key = config.get("TMS_APP_KEY") or config.get("TMAP_APP_KEY")
    if not key:
        parser.error("agent/.env의 TMS_APP_KEY를 확인하세요")
    try:
        expected = plan(args.data_dir)
        print("TMS 예약 부피는 m³ 정수 올림, 원본 CSV의 실제 부피는 유지합니다.")
        with httpx.Client(timeout=20, follow_redirects=False) as client:
            register(client, key, expected, args.apply)
    except (RuntimeError, ValueError, KeyError, OSError) as exc:
        raise SystemExit(str(exc).replace(key, "[MASKED]")) from None


if __name__ == "__main__":
    main()
