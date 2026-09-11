"""LangChain Agent에 요청 검증·호출 제한·Tool 실행을 연결한다."""

import time

from langchain.agents import create_agent
from langchain.agents.middleware import after_model, before_model, wrap_model_call, wrap_tool_call
from langchain_core.messages import ToolMessage
from langgraph.types import Command

from badaro.guardrails.allow_list import check_tool_args
from badaro.guardrails.pii import mask_text
from badaro.middleware import dispatch_context, input_validation
from badaro.middleware.retry import as_tool_error, tool_retry
from badaro.middleware.tool_logging import build_log_record, emit
from badaro.schemas import ToolError, ToolErrorCode
from prompts import load_prompt_bundle

from .tools import TOOLS, RunContext, RunState


def error_update(message, code=ToolErrorCode.INVALID_INPUT):
    return {
        "errors": [ToolError(code=code, message=message, retryable=False).model_dump()],
        "jump_to": "end",
    }


@after_model(can_jump_to=["end"])
def validate_calls(state, runtime):
    calls = getattr(state["messages"][-1], "tool_calls", [])
    names = [call["name"] for call in calls]
    if (
        len(names) != len(set(names))
        and set(names) != {"geocode_address"}
        or ("optimize_dispatch" in names and len(names) != 1)
    ):
        return error_update("배차 실행 또는 같은 조회를 중복·혼합 호출할 수 없습니다")
    geo_addresses = [c["args"].get("address") for c in calls if c["name"] == "geocode_address"]
    if len(geo_addresses) != len(set(str(a) for a in geo_addresses)):
        return error_update("같은 주소를 한 번에 중복 조회할 수 없습니다")
    if any(check_tool_args(call["name"], call["args"]) for call in calls):
        return error_update("허용되지 않은 Tool 또는 인자를 차단했습니다")
    return None


@wrap_tool_call
def execute_tool(request, handler):
    """공통 Retry를 적용하고 최종 오류를 State와 최소 로그에 남긴다."""
    failures = []

    def tracked(req):
        try:
            return handler(req)
        except Exception as exc:
            failures.append(as_tool_error(exc))
            raise

    start = time.monotonic()
    result = tool_retry.wrap_tool_call(request, tracked)
    failed = isinstance(result, ToolMessage) and result.status == "error"
    emit(
        build_log_record(
            request_id=request.runtime.context.request_id,
            tool_name=request.tool_call["name"],
            ok=not failed,
            elapsed_ms=int((time.monotonic() - start) * 1000),
        )
    )
    if not failed:
        return result
    source = (
        failures[-1]
        if failures and failures[-1]
        else ToolError(
            code=ToolErrorCode.INTERNAL_ERROR,
            message="Tool 실행에 실패했습니다",
            retryable=False,
        )
    )
    error = source.model_copy(update={"message": mask_text(source.message), "retryable": False})
    return Command(update={"errors": [error.model_dump()], "messages": [result]})


@wrap_model_call
def require_tool(request, handler):
    """입력 보완이 끝난 실행 단계는 Tool 호출로 진행한다."""
    return handler(request.override(tool_choice="required"))


def build_graph(model, max_calls):
    @before_model(can_jump_to=["end"])
    def budget(state, runtime):
        if state.get("errors"):
            return {"jump_to": "end"}
        if state.get("model_calls", 0) >= max_calls:
            return error_update("모델 호출 한도에 도달했습니다")
        return {"model_calls": state.get("model_calls", 0) + 1}

    prompts = load_prompt_bundle()
    return create_agent(
        model,
        tools=TOOLS,
        state_schema=RunState,
        context_schema=RunContext,
        middleware=[
            input_validation, dispatch_context, budget, require_tool, validate_calls, execute_tool,
        ],
        system_prompt=prompts.system + "\n" + prompts.fewshot + "\n"
        "서버가 확인한 요청 JSON을 그대로 사용한다. 먼저 주문과 차량을 각각 한 번 조회하고, "
        "주문 주소들을 확인한 뒤 조회한 주문 ID 전체와 가용 차량 ID 전체로 배차한다. "
        "실제 배정 차량은 TMS가 선택하므로 모델이 후보 차량을 줄이지 않는다. "
        "constraints는 request의 동일 필드를 그대로 복사한다. null과 빈 목록도 유지한다. "
        "특히 storage_types=null을 주문에서 찾은 보관유형 목록으로 바꾸지 않는다. "
        "조회끼리는 동시 호출할 수 있고, 서로 다른 주소는 한 번에 병렬 조회한다. "
        "배차는 다른 Tool과 동시에 호출하지 않는다. 배차 결과를 문장으로 재작성하지 않는다.",
    )
