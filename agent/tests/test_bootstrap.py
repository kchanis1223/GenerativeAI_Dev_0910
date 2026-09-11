"""설치된 패키지의 import 경계 검증. 업무 시나리오 테스트는 B-16에서 추가한다."""

import importlib
import socket

import pytest


@pytest.mark.parametrize("module", ["agent", "schemas", "tools", "middleware", "guardrails"])
def test_package_import_requires_no_credentials_or_network(monkeypatch, module):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TMAP_APP_KEY", raising=False)
    monkeypatch.setenv("USE_MOCK", "1")

    def reject_network(*args, **kwargs):
        pytest.fail("패키지 import 중 외부 통신이 발생했습니다.")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    assert importlib.import_module(f"badaro.{module}") is not None
