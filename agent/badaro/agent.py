"""본사 배차 Agent. 요청별 세션을 보관하고 구조화된 결과만 반환한다."""

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from threading import RLock
from uuid import uuid4

from pydantic import ValidationError

from badaro.guardrails.injection import BLOCK_MESSAGE, scan
from badaro.guardrails.pii import mask_text
from badaro.middleware import KST, initial_state
from badaro.middleware.input_validation import validate_dispatch_input
from badaro.middleware.tool_logging import emit
from badaro.runtime.backend import Backend
from badaro.runtime.contracts import AgentReply, RequestDraft, Settings
from badaro.runtime.data import catalog, depot_profile
from badaro.runtime.graph import build_graph
from badaro.runtime.models import models
from badaro.runtime.tools import RunContext
from badaro.schemas import DispatchRequest, ToolError, ToolErrorCode, ToolErrorException


@dataclass
class Session:
    request_id: str = field(default_factory=lambda: str(uuid4()))
    draft: RequestDraft = field(default_factory=RequestDraft)
    model_calls: int = 0
    reply: AgentReply | None = None
    addresses: list[str] = field(default_factory=list)
    finished: bool = False
    lookup: dict = field(default_factory=dict)
    lookup_request: dict = field(default_factory=dict)


class DispatchAgent:
    def __init__(self, settings=None, *, extractor=None, model=None, backend=None, now=None):
        self.settings = settings or Settings.from_env()
        self.extractor, self.model = (
            (extractor, model)
            if extractor is not None and model is not None
            else models(self.settings)
        )
        self.backend = backend or Backend(self.settings)
        self.graph = build_graph(self.model, self.settings.max_model_calls)
        self.profile = depot_profile(self.settings.depot_id)
        self.sessions = {}
        self.lock = RLock()
        self.now = now or (lambda: datetime.now(KST))

    def chat(self, text, thread_id=None):
        """thread_id는 서버가 발급한다. 완료한 요청을 재전송하면 저장된 응답만 돌려준다."""
        with self.lock:
            if thread_id is not None and thread_id not in self.sessions:
                return AgentReply(
                    thread_id=thread_id,
                    request_id="",
                    mode=self.settings.mode,
                    status="error",
                    message="요청을 찾을 수 없습니다. 새 요청을 시작해 주세요",
                    error=ToolError(
                        code=ToolErrorCode.MISSING_CONTEXT,
                        message="요청 State 조회 실패",
                        retryable=False,
                    ),
                )
            thread_id = thread_id or str(uuid4())
            session = self.sessions.setdefault(thread_id, Session())
            if session.finished:
                return session.reply.model_copy(deep=True)
            try:
                reply = self._chat(text, thread_id, session)
            except ValidationError:
                reply = self._reply(
                    thread_id,
                    session,
                    "needs_clarification",
                    "날짜·차량 수 등 입력 조건의 형식을 확인해 주세요",
                )
            except ToolErrorException as exc:
                safe = exc.error.model_copy(update={"message": mask_text(exc.error.message)})
                reply = self._reply(thread_id, session, "error", safe.message, error=safe)
            except Exception:
                reply = self._reply(
                    thread_id,
                    session,
                    "error",
                    "요청 처리 중 오류가 발생했습니다",
                    error=ToolError(
                        code=ToolErrorCode.INTERNAL_ERROR,
                        message="Agent 실행 오류",
                        retryable=False,
                    ),
                )
            session.reply = reply
            session.finished = reply.status != "needs_clarification"
            return reply.model_copy(deep=True)

    def _reply(self, thread_id, session, status, message, **kwargs):
        return AgentReply(
            thread_id=thread_id,
            request_id=session.request_id,
            mode=self.settings.mode,
            status=status,
            message=mask_text(message),
            model_calls=session.model_calls,
            **kwargs,
        )

    def _chat(self, text, thread_id, session):
        if not isinstance(text, str) or not text.strip() or len(text) > 8000:
            return self._reply(
                thread_id, session, "needs_clarification", "배차 조건을 입력해 주세요"
            )
        if scan(text):
            emit({"request_id": session.request_id, "event": "guardrail_block"})
            return self._reply(thread_id, session, "blocked", BLOCK_MESSAGE)
        if session.model_calls >= self.settings.max_model_calls:
            return self._reply(thread_id, session, "error", "모델 호출 한도에 도달했습니다")
        session.model_calls += 1
        previous_corrections = session.draft.address_corrections
        draft = self.extractor.extract(
            mask_text(text),
            session.draft,
            {
                "today": self.now().date().isoformat(),
                "depot_id": self.settings.depot_id,
                "delivery_date": str(self.settings.default_date)
                if self.settings.default_date
                else None,
                "queried_addresses": session.addresses,
            },
        )
        draft = RequestDraft.model_validate(draft)
        if any(
            c not in previous_corrections and c.replacement not in text
            for c in draft.address_corrections
        ):
            return self._reply(
                thread_id,
                session,
                "needs_clarification",
                "수정할 배송지의 전체 주소를 직접 입력해 주세요",
            )
        session.draft = draft
        if draft.out_of_scope:
            return self._reply(
                thread_id, session, "blocked", "이번 MVP는 본사의 새 배차 요청만 지원합니다"
            )
        values = draft.request_values()
        values["depot_id"] = values["depot_id"] or self.settings.depot_id
        values["delivery_date"] = values["delivery_date"] or self.settings.default_date
        issues = validate_dispatch_input(values, now_kst=self.now())
        if draft.destination_ids is None and not draft.all_destinations:
            issues.append({"message": "배송 지점 또는 전체 주문 여부를 알려주세요"})
        known = set(catalog())
        if set(draft.destination_ids or []) - known:
            issues.append({"message": "등록된 배송 지점 이름을 확인해 주세요"})
        if values["depot_id"] != self.settings.depot_id:
            issues.append({"message": "현재 서버에 설정된 출발 센터와 다릅니다"})
        if issues:
            questions = [item["message"] for item in issues]
            return self._reply(
                thread_id, session, "needs_clarification", " ".join(questions), questions=questions
            )
        # 현재 센터의 시연 운행 시작은 06:00이다. 입력한 출발 시각이 있으면 그 값을 쓴다.
        values["departure_time"] = values["departure_time"] or datetime.combine(
            values["delivery_date"],
            time(6),
            tzinfo=KST,
        )
        for key in ["departure_time", "deadline"]:
            if values[key] and values[key].tzinfo is None:
                values[key] = values[key].replace(tzinfo=KST)
        request = DispatchRequest.model_validate(values)
        context = RunContext(
            tenant_id="local",
            user_id="local-operator",
            user_role="operator",
            role_source="server",
            depot_profile=self.profile,
            request_id=session.request_id,
            now_kst=self.now(),
            backend=self.backend,
            request=request,
            corrections={c.original: c.replacement for c in draft.address_corrections},
        )
        lookup = session.lookup if session.lookup_request == request.model_dump(mode="json") else {}
        if lookup and draft.address_corrections:
            fixes = context.corrections
            if set(fixes) - {o.address for o in lookup.get("orders", {}).values()}:
                return self._reply(thread_id, session, "error", "현재 요청에 없는 주소 수정입니다")
            lookup = {
                **lookup,
                "orders": {
                    k: o.model_copy(update={"address": fixes.get(o.address, o.address)})
                    for k, o in lookup["orders"].items()
                },
                "geocodes": {k: v for k, v in lookup.get("geocodes", {}).items() if k not in fixes},
            }
        visible = {
            k: {name: obj.model_dump(mode="json") for name, obj in v.items()}
            for k, v in lookup.items()
        }
        state = {
            **initial_state(),
            **lookup,
            "dispatch_request": request,
            "errors": [],
            "model_calls": session.model_calls,
            "messages": [
                (
                    "user",
                    json.dumps(
                        {"request": request.model_dump(mode="json"), "lookup": visible},
                        ensure_ascii=False,
                    ),
                )
            ],
        }
        result = self.graph.invoke(
            state,
            context=context,
            config={"recursion_limit": 40, "configurable": {"thread_id": thread_id}},
        )
        session.model_calls = result.get("model_calls", session.model_calls)
        session.lookup = {k: result.get(k, {}) for k in ["orders", "vehicles", "geocodes"]}
        session.lookup_request = request.model_dump(mode="json")
        session.addresses = sorted({o.address for o in result.get("orders", {}).values()})
        if result.get("errors"):
            error = ToolError.model_validate(result["errors"][0])
            clarify = error.code in {
                ToolErrorCode.GEOCODE_AMBIGUOUS,
                ToolErrorCode.GEOCODE_NOT_FOUND,
            }
            status = (
                "needs_clarification" if clarify and not context.allocation_attempted else "error"
            )
            return self._reply(
                thread_id,
                session,
                status,
                error.message,
                error=error,
                request=request,
                questions=[error.message] if status == "needs_clarification" else [],
            )
        dispatch = result.get("last_dispatch_result")
        if dispatch is None:
            return self._reply(
                thread_id, session, "error", "배차 결과를 얻지 못했습니다", request=request
            )
        label = {"success": "완료", "partial": "일부 미배정", "failed": "배정 없음"}[
            dispatch.status
        ]
        source = "시연용 Mock" if self.settings.use_mock else "TMS"
        message = (
            f"{source} 배차 결과: {label}. 차량 {len(dispatch.routes)}대, "
            f"미배정 {len(dispatch.unassigned_orders)}건. 제공되지 않은 ETA는 표시하지 않습니다."
        )
        return self._reply(
            thread_id, session, "completed", message, request=request, result=dispatch
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(description="바다로 Agent CLI")
    parser.add_argument("message", nargs="?")
    args = parser.parse_args()
    service = DispatchAgent()
    thread_id = None
    while True:
        text = args.message or input("배차 요청> ")
        reply = service.chat(text, thread_id)
        print(json.dumps(reply.model_dump(mode="json"), ensure_ascii=False, indent=2))
        if args.message or reply.status != "needs_clarification":
            break
        thread_id = reply.thread_id


if __name__ == "__main__":
    main()
