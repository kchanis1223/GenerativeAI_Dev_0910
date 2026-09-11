"""제출용 등록 스크립트: 기존값 보존, 신규 등록 대조, 실패 시 자동 재전송 금지."""

import runpy
from pathlib import Path

import httpx
import pytest

API = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/register_tms_data.py"))
EXPECTED = {("order", "ORD-1"): {"orderId": "ORD-1", "deliveryWeight": "80"}}


def client(rows, calls, fail=False):
    def handler(request):
        endpoint = request.url.path.rsplit("/", 1)[-1]
        calls.append(endpoint)
        if endpoint.endswith("Insert"):
            if fail:
                raise httpx.ReadTimeout("appKey=test-secret", request=request)
            rows.append({k: v for k, v in request.url.params.items() if k != "appKey"})
            return httpx.Response(200, json={"resultCode": "200"})
        data = rows if endpoint == "orderList" else []
        return httpx.Response(200, json={"resultCode": "200", "resultCount": len(data),
                                        "resultData": data})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_preflight_does_not_insert():
    calls = []
    with client([], calls) as connection:
        API["register"](connection, "test-secret", EXPECTED)
    assert not any(c.endswith("Insert") for c in calls)


def test_existing_mismatch_stops_before_insert():
    calls = []
    with client([{"orderId": "ORD-1", "deliveryWeight": 999}], calls) as connection:
        with pytest.raises(ValueError, match="기존 등록값 불일치"):
            API["register"](connection, "test-secret", EXPECTED, apply=True)
    assert not any(c.endswith("Insert") for c in calls)


def test_new_order_is_read_back_and_second_run_does_not_duplicate():
    rows, calls = [], []
    with client(rows, calls) as connection:
        API["register"](connection, "test-secret", EXPECTED, apply=True)
        API["register"](connection, "test-secret", EXPECTED, apply=True)
    assert calls.count("orderInsert") == 1
    assert calls.count("orderList") == 4
    assert rows == list(EXPECTED.values())


def test_uncertain_insert_is_not_retried_or_leaked(capsys):
    calls = []
    with client([], calls, fail=True) as connection:
        with pytest.raises(RuntimeError) as error:
            API["register"](connection, "test-secret", EXPECTED, apply=True)
    assert calls.count("orderInsert") == 1
    assert "test-secret" not in str(error.value) + capsys.readouterr().out
