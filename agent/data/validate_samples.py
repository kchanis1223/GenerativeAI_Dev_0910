"""B-04 CSV·저장된 주소 응답과 외부에서 지정한 B-03 모델을 오프라인 검증한다."""

import argparse
import csv
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

DATA = Path(__file__).parent
STORAGE = {"활어": "live", "냉장": "refrigerated", "냉동": "frozen", "일반": "ambient"}
VEHICLE_TYPES = {"활어": "99", "냉장": "02", "냉동": "02", "일반": "01"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def rows(directory, name):
    with (directory / name).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, strict=True)
        header = reader.fieldnames or []
        require(header and all(header) and len(set(header)) == len(header), "CSV 헤더")
        records = list(reader)
        require(all(None not in row and None not in row.values() for row in records), "CSV 컬럼")
        return records


def deadline(row):
    return datetime.strptime(row["deliveryDate"] + row["closeTime"], "%Y-%m-%d%H%M").replace(
        tzinfo=ZoneInfo("Asia/Seoul")
    )


def order_payload(row):
    return {
        "order_id": row["orderId"], "destination_id": row["branchId"],
        "address": row["address"], "items": [{
            "product_name": row["itemName"], "weight_kg": float(row["deliveryWeight"]),
        }],
        "weight_kg": float(row["deliveryWeight"]),
        "volume_m3": float(row["deliveryVolume"]), "storage_type": STORAGE[row["itemType"]],
        "priority": row["priority"], "deadline": deadline(row),
        "service_seconds": int(row["serviceTime"]) * 60,
    }


def vehicle_payload(row):
    require(row["inputYn"] in {"0", "1"}, "차량 투입 여부: inputYn")
    return {
        "vehicle_id": row["vehicleId"], "capacity_weight_kg": float(row["maxLoadKg"]),
        "capacity_volume_m3": float(row["volume"]),
        "supported_storage_types": [STORAGE[item] for item in row["supportedItemTypes"].split("|")],
        "available": row["inputYn"] == "1", "shift_start": row["shift_start"],
        "shift_end": row["shift_end"],
    }


def validate(directory=DATA, models=None):
    centers, branches, vehicles, orders, proof, rejected = [rows(directory, name) for name in (
        "centers.csv", "branches.csv", "vehicles.csv", "delivery_orders.csv",
        "geocoding_results.csv", "geocoding_rejected.csv",
    )]
    for records, count, key in [(centers, 1, "centerId"), (branches, 20, "branchId"),
                                (vehicles, 5, "vehicleId"), (orders, 40, "orderId")]:
        require(len(records) == len({row[key] for row in records}) == count, f"개수·ID: {key}")
    require(len({row["address"] for row in branches}) == 20, "지점 주소 중복")
    require(sum(float(row["deliveryWeight"]) for row in orders) == 3125, "총 배송 중량")
    center_ids = {row["centerId"] for row in centers}
    for row in branches + vehicles + orders:
        require(row["centerId"] in center_ids, "센터 참조")
    for branch in branches:
        group = [row for row in orders if row["branchId"] == branch["branchId"]]
        require(len(group) == 2, "지점별 주문 수")
        for row in group:
            require(all(row[k] == branch[k] for k in (
                "address", "latitude", "longitude", "centerId", "zoneCode",
            )), "지점·주문 불일치")
    require({row["branchId"] for row in orders} == {r["branchId"] for r in branches}, "지점 참조")
    for row in orders:
        require(row["vehicleType"] == VEHICLE_TYPES[row["itemType"]], "품목·차종")
        require(row["deliveryDate"] == "2026-09-11", "배송일")
        start, desired, end = [datetime.strptime(value, fmt).time() for value, fmt in (
            (row["openTime"], "%H%M"), (row["desiredDeliveryTime"], "%H:%M"),
            (row["closeTime"], "%H%M"),
        )]
        require(start <= desired <= end, "납품 시간창")
        payload = order_payload(row)
        require(payload["weight_kg"] > 0 and payload["volume_m3"] >= 0, "주문 중량·부피")
        require(payload["service_seconds"] >= 0, "작업 시간")
    for row in vehicles:
        payload = vehicle_payload(row)
        require(float(row["weight"]) * 1000 == payload["capacity_weight_kg"] > 0, "ton·kg")
        start, end = [datetime.fromisoformat(row[k]) for k in ("shift_start", "shift_end")]
        require(start.utcoffset() == end.utcoffset() == deadline(orders[0]).utcoffset(), "시간대")
        require(start < end, "차량 근무시간")
        require(payload["capacity_volume_m3"] >= 0, "차량 부피")
        require(all(VEHICLE_TYPES[item] == row["vehicleType"]
                    for item in row["supportedItemTypes"].split("|")), "차량 지원 품목")
    for category in STORAGE:
        group = [r for r in orders if r["itemType"] == category]
        require(len(group) == 10, "품목별 10건")
        capacity = sum(float(r["maxLoadKg"]) for r in vehicles
                       if category in r["supportedItemTypes"].split("|"))
        require(sum(float(r["deliveryWeight"]) for r in group) <= capacity, "품목별 적재량")
    require(len(proof) == len({row["entityId"] for row in proof}) == 21, "지오코딩 근거 수")
    for row in centers + branches:
        key = row.get("branchId", row.get("centerId"))
        evidence = next(item for item in proof if item["entityId"] == key)
        require(evidence["status"] == "SUCCESS_EXACT_ADDRESS", "주소 상태")
        require(evidence["httpStatus"] == "200", "HTTP 상태")
        require(evidence["queryAddress"] == row["address"], "조회 주소")
        query = parse_qs(urlparse(evidence["requestUrl"]).query)
        require(query["q"] == [row["address"]], "요청 URL")
        match = next(item for item in json.loads(evidence["rawResponse"])
                     if str(item["osm_id"]) == evidence["osmId"]
                     and item["osm_type"] == evidence["osmType"])
        parts = dict(zip(("city", "borough", "road", "house_number"), row["address"].split()))
        require(len(parts) == 4, "입력 주소 구성")
        require(all(match["address"].get(k) == v for k, v in parts.items()), "도로명·건물번호")
        require(match["address"]["country_code"] == "kr" and match["place_rank"] == 30, "건물 주소")
        require(37.4 < float(match["lat"]) < 37.7 and 126.7 < float(match["lon"]) < 127.2,
                "서울 좌표 범위")
        for field, raw in [("latitude", "lat"), ("longitude", "lon")]:
            require(float(row[field]) == float(evidence[field]) == float(match[raw]), "좌표 불일치")
    require(len(rejected) == 4, "제외 주소 수")
    for row in rejected:
        require(row["queryAddress"] not in {r["address"] for r in branches}, "제외 주소 혼입")
        require(all(r["place_rank"] < 30 and not r["address"].get("house_number")
                    for r in json.loads(row["rawResponse"])), "제외 근거")
    report = {"branches": 20, "centers": 1, "orders": 40, "vehicles": 5,
              "weight_kg": 3125, "geocoding_exact": 21, "rejected": 4}
    if models:
        from pydantic import ValidationError

        spec = importlib.util.spec_from_file_location("b03_models", models)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, records, adapter in [("Order", orders, order_payload),
                                       ("Vehicle", vehicles, vehicle_payload)]:
            model = getattr(module, name)
            raw_failures = 0
            for row in records:
                try:
                    model.model_validate(row)
                except ValidationError:
                    raw_failures += 1
                model.model_validate(adapter(row))
            report[name] = {"raw_rejected": raw_failures, "mapped_passed": len(records)}
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, help="검증할 B-03 models.py 경로")
    args = parser.parse_args()
    if not args.models:
        print("Python 모델 검증 미실행: --models로 B-03 models.py를 지정하세요.", file=sys.stderr)
    print(json.dumps(validate(models=args.models), ensure_ascii=False, indent=2))
