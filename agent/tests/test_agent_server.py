from threading import Thread

import httpx
import pytest

from badaro.agent import DispatchAgent
from badaro.runtime.contracts import Settings
from badaro.server import create_server


@pytest.fixture
def api():
    with create_server(DispatchAgent(Settings()), port=0) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}") as client:
            yield client
        server.shutdown()
        thread.join(timeout=2)


def test_http_request_clarification_and_result(api):
    assert api.get("/health").json()["mode"] == "offline"
    first = api.post("/api/chat", json={"message": "마포 서대문 은평 배차해줘"}).json()
    assert first["status"] == "needs_clarification"
    second = api.post(
        "/api/chat",
        json={
            "message": "2026-09-11",
            "thread_id": first["thread_id"],
        },
    ).json()
    assert second["status"] == "completed"
    assert second["result"]["status"] == "success"


def test_http_rejects_client_runtime_fields_and_unknown_thread(api):
    assert api.post("/api/chat", json={"message": "배차", "use_mock": False}).status_code == 400
    response = api.post(
        "/api/chat",
        json={
            "message": "배차",
            "thread_id": "00000000-0000-0000-0000-000000000000",
        },
    ).json()
    assert response["error"]["code"] == "missing_context"
    assert api.post("/api/chat", content="invalid-json").status_code == 400
    assert (
        api.post(
            "/api/chat", json={"message": "배차"}, headers={"Origin": "https://example.invalid"}
        ).status_code
        == 403
    )
