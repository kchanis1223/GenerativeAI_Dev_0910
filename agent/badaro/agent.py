"""B-17 통합 위치: 모델, Tools, Middleware, Context와 State/Store를 연결한다."""

from collections.abc import Sequence
from typing import Any

from .middleware import (
    INTENT_CLASSIFICATION_SYSTEM_PROMPT,
    IntentModel,
    LangChainModelRoutingMiddleware,
    LightweightIntentClassifier,
    ModelRoutingMiddleware,
    create_prompted_lightweight_intent_model,
)

DEFAULT_MAIN_MODEL = "gpt-5.4-mini"
DEFAULT_CLASSIFIER_MODEL = "gpt-5.4-mini"

_B07_AGENT_PROMPT_ADDENDUM = f"""\n\n# B-07 라우팅 추가 규칙

이번 실행 범위에는 재배차(`re_dispatch`) 분류를 포함한다. 기존 배차 State가
확인되면 기존 출발지·배송지·차량 조건을 유지하고 사용자 변경사항만 적용한다.
기존 배차 State가 없으면 조건을 추정하지 말고 확인을 요청한다.

경량 분류 모델의 허용 출력은 다음 지침을 따른다:
{INTENT_CLASSIFICATION_SYSTEM_PROMPT}
"""


def create_model_routing_middleware(
    lightweight_model: IntentModel,
    *,
    confidence_threshold: float = 0.75,
) -> ModelRoutingMiddleware:
    """주입된 경량 모델을 B-07 라우팅 미들웨어에 연결한다.

    모델 생성과 인증 설정은 호출자가 담당한다. 따라서 이 조립 함수는 import
    시 외부 통신을 하지 않으며, 운영 계층에서 모델을 교체하거나 테스트 대역을
    주입할 수 있다.
    """

    classifier = LightweightIntentClassifier(lightweight_model)
    return ModelRoutingMiddleware(
        classifier,
        confidence_threshold=confidence_threshold,
    )


def create_langchain_model_routing_middleware(
    lightweight_model: IntentModel,
    *,
    confidence_threshold: float = 0.75,
) -> LangChainModelRoutingMiddleware:
    """주입된 경량 모델을 LangChain v1 Middleware로 연결한다."""

    if callable(getattr(lightweight_model, "with_structured_output", None)):
        lightweight_model = create_prompted_lightweight_intent_model(lightweight_model)
    classifier = LightweightIntentClassifier(lightweight_model)
    return LangChainModelRoutingMiddleware(
        classifier,
        confidence_threshold=confidence_threshold,
    )


def compose_dispatch_system_prompt(system_prompt: str | None = None) -> str:
    """B-06 기본 프롬프트에 B-07 재배차 규칙을 덧붙인다."""

    if system_prompt is None:
        from prompts import load_prompt_bundle

        prompt_bundle = load_prompt_bundle()
        system_prompt = f"{prompt_bundle.system}\n\n{prompt_bundle.fewshot}"
    return f"{system_prompt}{_B07_AGENT_PROMPT_ADDENDUM}"


def create_dispatch_agent(
    main_model: Any,
    lightweight_model: IntentModel,
    *,
    tools: Sequence[Any] = (),
    system_prompt: str | None = None,
    confidence_threshold: float = 0.75,
) -> Any:
    """B-06 프롬프트와 B-07 라우팅을 포함한 LangChain Agent를 만든다.

    모델 인스턴스와 Tool은 호출자가 생성·주입한다. 이 함수는 Agent 그래프만
    조립하며, 모델 호출이나 외부 API 요청을 실행하지 않는다.
    """

    from langchain.agents import create_agent

    system_prompt = compose_dispatch_system_prompt(system_prompt)

    routing_middleware = create_langchain_model_routing_middleware(
        lightweight_model,
        confidence_threshold=confidence_threshold,
    )
    return create_agent(
        model=main_model,
        tools=list(tools),
        system_prompt=system_prompt,
        middleware=[routing_middleware],
    )


__all__ = [
    "DEFAULT_CLASSIFIER_MODEL",
    "DEFAULT_MAIN_MODEL",
    "compose_dispatch_system_prompt",
    "create_langchain_model_routing_middleware",
    "create_dispatch_agent",
    "create_model_routing_middleware",
]
