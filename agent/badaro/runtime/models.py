"""같은 OpenAI 모델의 요청 추출·Tool 호출과 외부 호출 없는 시연 모델."""

import json
import re
from datetime import date
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI

from .contracts import RequestDraft
from .data import catalog


def strict_schema(value):
    """서버 기본값은 유지하되 OpenAI 출력 스키마는 모든 필드를 요구한다."""
    if isinstance(value, list):
        return [strict_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: strict_schema(item) for key, item in value.items() if key != "default"}
    if result.get("type") == "object":
        result.update(additionalProperties=False, required=list(result.get("properties", {})))
    return result


class OpenAIExtractor:
    def __init__(self, model):
        self.chain = model.with_structured_output(
            strict_schema(RequestDraft.model_json_schema()), method="json_schema", strict=True
        )

    def extract(self, text, previous, defaults):
        instruction = (
            "본사 배차 요청에서 명시된 값만 추출한다. 모르는 값은 null로 둔다. "
            "직전 요청에 대한 보완 답변은 기존 조건을 유지해 합친다. 전체 주문을 명시하면 "
            "all_destinations=true로 둔다. 지점명은 제공한 목록의 ID로만 바꾼다. "
            "재배차·기사 업무·점주 탭·파일 업로드 요청은 out_of_scope=true다. "
            "주소 수정은 original과 replacement에 사용자가 확인한 주소만 기록한다. "
            "날짜의 오늘·내일은 기준일을 사용하고 시간을 추측하지 않는다. "
            "출발 시각은 배송일과 시각을 합친 ISO 8601 형식으로 쓴다. "
            "예: 2026-09-11 오전 6시 → 2026-09-11T06:00:00+09:00. "
            "시각을 연도 위치에 넣지 않는다.\n"
            + json.dumps(
                {
                    "previous": previous.model_dump(mode="json"),
                    "defaults": defaults,
                    "branches": {k: r["branchName"] for k, r in catalog().items()},
                },
                ensure_ascii=False,
            )
        )
        return self.chain.invoke([SystemMessage(instruction), HumanMessage(text)])


class OfflineExtractor:
    """명시된 날짜·지점·차량 수만 읽는 시연용 대체물. LLM이 아니다."""

    def extract(self, text, previous, defaults):
        if re.search(r"시|마감|제외|빼|냉장|냉동|활어|내일|오전|오후|출발", text):
            from .backend import fail

            fail(
                "offline 시연은 날짜·지점·차량 수만 지원합니다. "
                "자유 입력은 OpenAI 모드를 사용해 주세요"
            )
        values = previous.model_dump()
        found = re.search(r"\d{4}-\d{2}-\d{2}", text)
        if found:
            values["delivery_date"] = date.fromisoformat(found.group())
        elif "오늘" in text:
            values["delivery_date"] = date.fromisoformat(defaults["today"])
        selected = [
            k
            for k, row in catalog().items()
            if k in text or row["branchName"].replace("바다로 ", "").replace("지점", "") in text
        ]
        if selected:
            values["destination_ids"] = selected
        if "전체" in text:
            values.update(destination_ids=None, all_destinations=True)
        number = re.search(r"(\d+)\s*대", text)
        if number:
            values["vehicle_count"] = int(number.group(1))
        values["out_of_scope"] = any(word in text for word in ["재배차", "기사", "업로드", "점주"])
        return RequestDraft(**values)


class OfflineToolModel(BaseChatModel):
    """정해진 Tool 흐름을 재생한다. 외부 LLM·API를 사용하지 않는다."""

    @property
    def _llm_type(self):
        return "badaro-offline-demo"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        envelope = json.loads(next(m.content for m in messages if isinstance(m, HumanMessage)))
        request, state = envelope["request"], envelope["lookup"]
        for message in messages:
            if isinstance(message, ToolMessage) and message.status != "error":
                for key, value in json.loads(message.content).items():
                    state.setdefault(key, {}).update(value)
        base = {k: request[k] for k in ["depot_id", "delivery_date"]}
        calls = []
        if "orders" not in state:
            calls.append(
                (
                    "get_delivery_orders",
                    {**base, **{k: request[k] for k in ["destination_ids", "product_names"]}},
                )
            )
        if "vehicles" not in state:
            calls.append(
                (
                    "get_available_vehicles",
                    {**base, **{k: request[k] for k in ["vehicle_count", "excluded_vehicle_ids"]}},
                )
            )
        if not calls:
            addresses = sorted({o["address"] for o in state["orders"].values()})
            calls = [
                ("geocode_address", {"address": a})
                for a in addresses
                if a not in state.get("geocodes", {})
            ]
        if not calls:
            from badaro.schemas import DispatchConstraints

            calls = [
                (
                    "optimize_dispatch",
                    {
                        "order_ids": list(state["orders"]),
                        "vehicle_ids": list(state["vehicles"]),
                        "constraints": {k: request[k] for k in DispatchConstraints.model_fields},
                    },
                )
            ]
        response = AIMessage(
            content="",
            tool_calls=[{"name": name, "args": args, "id": uuid4().hex} for name, args in calls],
        )
        return ChatResult(generations=[ChatGeneration(message=response)])


def models(settings):
    if settings.model_mode == "offline":
        return OfflineExtractor(), OfflineToolModel()
    # SDK의 자동 재시도로 모델 호출 상한을 우회하지 않는다.
    model = ChatOpenAI(model=settings.main_model, max_retries=0, timeout=30)
    return OpenAIExtractor(model), model
