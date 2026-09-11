"""M01~M08 고정 시연. 실제 Agent·CSV·검증을 사용하고 외부 응답만 대체한다."""

import re
from datetime import datetime
from threading import RLock

from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from badaro.agent import DispatchAgent
from badaro.middleware import KST
from badaro.runtime.backend import Backend
from badaro.runtime.contracts import AddressCorrection, AgentReply, Settings
from badaro.runtime.models import OfflineExtractor, OfflineToolModel
from badaro.schemas import ToolErrorCode
from badaro.tools.optimize_dispatch import _raise_context_error, poll_dispatch_result

TEXT = "2026-09-11 마포 서대문 은평 배차해줘"
ADDRESS = "서울특별시 마포구 월드컵로 212"
CORRECTED = ADDRESS + " 정문"


class ScenarioReply(AgentReply):
    presentation: dict = Field(default_factory=dict)


class ScenarioExtractor(OfflineExtractor):
    def extract(self, text, previous, defaults):
        if text == CORRECTED:
            draft = previous.model_copy(deep=True)
            draft.address_corrections = [AddressCorrection(original=ADDRESS, replacement=text)]
            return draft
        return super().extract(text, previous, defaults)


class ForbiddenModel(OfflineToolModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "get_delivery_orders",
                    "id": "forbidden-demo",
                    "args": {
                        "endpoint": "https://invalid.example",
                        "header": {},
                        "appKey": "demo-secret",
                        "runtime_context": {},
                    },
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


class ScenarioBackend(Backend):
    def __init__(self, scenario):
        super().__init__(Settings())
        self.scenario = scenario
        self.audit = {"allocation_calls": 0, "poll_calls": 0, "communication_retries": 0}

    def geocode(self, address):
        if self.scenario == "M03" and address == CORRECTED:
            return super().geocode(ADDRESS).model_copy(update={"input_address": address})
        geo = super().geocode(address)
        if self.scenario == "M03" and address == ADDRESS:
            return geo.model_copy(update={"status": "ambiguous"})
        return geo

    def fixture(self):
        fixture = super().fixture()
        if self.scenario == "M06":
            fixture["response"]["vehicleList"].pop()
        return fixture

    def dispatch(self, *args):
        self.audit["allocation_calls"] += 1
        if self.scenario == "M05":

            def response(*args, **kwargs):
                self.audit["poll_calls"] += 1
                if self.audit["communication_retries"] < 3:
                    self.audit["communication_retries"] += 1
                    _raise_context_error(
                        ToolErrorCode.TIMEOUT, "합성 응답: 결과 조회 통신 시간 초과", retryable=True
                    )
                return {"resultCode": "102"}

            return poll_dispatch_result(
                "demo-timeout", "mock", 3, 0, request_json=response, sleep=lambda _: None
            )
        return super().dispatch(*args)


class ScenarioService:
    """명시적인 --scenarios 서버에서만 사용하는 요청별 시연 서비스."""

    settings = Settings()

    def __init__(self):
        self.sessions = {}
        self.lock = RLock()

    def chat(self, text, thread_id=None):
        with self.lock:
            if thread_id and thread_id not in self.sessions:
                return DispatchAgent(self.settings).chat(text, thread_id)
            if thread_id:
                scenario, agent, backend = self.sessions[thread_id]
            else:
                match = re.match(r"^\[(M0[1-8])\]\s*", text)
                scenario = match[1] if match else "M01"
                if match:
                    text = text[match.end() :]
                backend = ScenarioBackend(scenario)
                agent = DispatchAgent(
                    self.settings,
                    backend=backend,
                    extractor=ScenarioExtractor(),
                    model=ForbiddenModel() if scenario == "M08" else OfflineToolModel(),
                    now=lambda: datetime(2026, 9, 11, 6, tzinfo=KST),
                )
            reply = agent.chat(text, thread_id)
            self.sessions[reply.thread_id] = (scenario, agent, backend)
            session = agent.sessions[reply.thread_id]
            lookup = session.lookup
            geo = lookup.get("geocodes", {})
            orders = []
            for order in lookup.get("orders", {}).values():
                location = geo.get(order.address)
                orders.append(
                    {
                        **order.model_dump(mode="json"),
                        "coordinate": (
                            location.candidates[0].model_dump(mode="json")
                            if location and location.status == "ok"
                            else None
                        ),
                    }
                )
            candidates = (
                [CORRECTED]
                if (
                    scenario == "M03"
                    and reply.status == "needs_clarification"
                    and reply.error
                    and reply.error.code == ToolErrorCode.GEOCODE_AMBIGUOUS
                )
                else []
            )
            return ScenarioReply(
                **reply.model_dump(),
                presentation={
                    "scenario": scenario,
                    "source": "고정 시연 · 실제 외부 API 호출 없음",
                    "orders": orders,
                    "vehicle_ids": list(lookup.get("vehicles", {})),
                    "candidates": candidates,
                    "audit": dict(backend.audit),
                },
            )
