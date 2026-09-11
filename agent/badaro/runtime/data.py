"""기존 CSV에서 센터 설정과 지점 이름을 읽는다."""

from badaro.middleware import DepotProfile
from badaro.schemas import GeocodeCandidate
from badaro.tools._sample_data import _rows


def catalog():
    return {row["branchId"]: row for row in _rows("branches.csv")}


def depot_profile(depot_id):
    row = next((r for r in _rows("centers.csv") if r["centerId"] == depot_id), None)
    if row is None:
        raise ValueError("등록된 센터가 아닙니다")
    return DepotProfile(
        depot_id=depot_id,
        name=row["centerName"],
        origin=GeocodeCandidate(
            matched_address=row["address"],
            lat=float(row["latitude"]),
            lon=float(row["longitude"]),
        ),
    )
