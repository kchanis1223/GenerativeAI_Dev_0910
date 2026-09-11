"""실제 Tool과 명시적인 합성 시연 응답을 선택한다."""

import json
from importlib.resources import files

from badaro.schemas import GeocodeResult, ToolError, ToolErrorCode, ToolErrorException
from badaro.tools import geocode_address, get_available_vehicles, get_delivery_orders
from badaro.tools._http import mock_enabled
from badaro.tools.optimize_dispatch import _parse_dispatch_result, execute_optimize_dispatch


def fail(message, code=ToolErrorCode.INVALID_INPUT):
    raise ToolErrorException(ToolError(code=code, message=message, retryable=False))


class Backend:
    def __init__(self, settings):
        self.settings = settings

    orders = staticmethod(get_delivery_orders)
    vehicles = staticmethod(get_available_vehicles)

    def geocode(self, address):
        if not self.settings.use_mock:
            if mock_enabled():
                fail("서버 설정과 USE_MOCK가 다릅니다")
            return geocode_address(address)
        value = self.fixture()["geocodes"].get(address)
        if value is None:
            fail("해당 주소의 시연용 저장 응답이 없습니다")
        return GeocodeResult.model_validate(value)

    def dispatch(self, order_ids, vehicle_ids, constraints, context):
        if not self.settings.use_mock:
            if mock_enabled():
                fail("서버 설정과 USE_MOCK가 다릅니다")
            if not self.settings.master_verified:
                fail("실제 TMS 마스터 데이터 일치를 먼저 확인해 주세요")
            return execute_optimize_dispatch(order_ids, vehicle_ids, constraints, context)
        fixture = self.fixture()
        if (
            set(order_ids) != set(fixture["order_ids"])
            or set(vehicle_ids) != set(fixture["vehicle_ids"])
            or constraints.departure_time.isoformat() != fixture["departure_time"]
        ):
            fail("해당 주문·차량·출발시각의 시연용 저장 응답이 없습니다")
        return _parse_dispatch_result(
            fixture["response"],
            order_ids,
            context,
            requested_vehicle_ids=vehicle_ids,
            constraints=constraints,
        )

    @staticmethod
    def fixture():
        try:
            return json.loads(files("badaro.runtime").joinpath("demo.json").read_text())
        except (OSError, ValueError):
            fail("시연용 저장 응답을 읽을 수 없습니다", ToolErrorCode.INTERNAL_ERROR)
