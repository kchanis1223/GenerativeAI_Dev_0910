"""G-02 프롬프트 인젝션 · Secret 보호 — 설계서 3.3 (심각도 High)

프롬프트 인젝션(prompt injection) = 사용자 입력에 '지시문'을 섞어 넣어
모델이 원래 받은 시스템 지침 대신 그걸 따르게 만드는 공격.
injection 은 '주입'이라는 뜻으로, SQL 인젝션에서 온 이름이다.

v2 배치: 1단 규칙 필터(before_agent) → 통과한 것만 2단 경량 분류 모델(before_model).
        싼 것부터 거르고 비싼 판별기는 나중에 쓴다는 3.3 설계 원칙.
        여기서는 1단(규칙)만 구현한다. 2단은 이준형의 의도 분류(#7)와 묶인다.
"""
from __future__ import annotations

import re
from typing import Any

_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(이전|앞선|위의|기존)\s*(지시|지침|규칙|명령)\w*\s*(을|를)?\s*(무시|잊|폐기)"),
     "override_instruction"),
    (re.compile(r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instruction|prompt|rule)"),
     "override_instruction"),
    (re.compile(r"(너의|네)\s*(규칙|지침|역할)\w*\s*(을|를)?\s*(바꿔|해제|잊)"),
     "override_instruction"),

    (re.compile(r"(시스템\s*프롬프트|system\s*prompt|초기\s*지침)\w*\s*(을|를)?"
                r"\s*(보여|출력|알려|말해)"),
     "prompt_exfiltration"),
    (re.compile(r"(?i)(reveal|show|print|repeat)\s+(your\s+)?(system\s+)?(prompt|instruction)"),
     "prompt_exfiltration"),

    (re.compile(r"(?i)(app\s*key|api\s*key|인증\s*키|비밀\s*키|access\s*token)\w*\s*(을|를)?\s*"
                r"(알려|보여|출력|말해|줘|내놔|print|show|tell)"), "secret_exfiltration"),
    (re.compile(r"(?i)\.env\s*(파일)?\s*(을|를)?\s*(보여|출력|읽어|cat)"), "secret_exfiltration"),

    (re.compile(r"(?i)(developer|debug|god)\s*mode"), "role_escape"),
    (re.compile(r"(넌|너는)\s*이제\s*\w*(아니|아냐)"), "role_escape"),
)

BLOCK_MESSAGE = (
    "요청에 시스템 지침이나 인증 정보를 바꾸려는 문장이 포함되어 있어 처리하지 않았습니다. "
    "배차 조건만 말씀해 주세요."
)


def scan(text: str) -> list[dict[str, Any]]:
    """입력을 훑어 걸린 규칙 목록을 돌려준다. 빈 리스트면 통과.

    순수 함수 — langchain 없이 TS-07 케이스를 그대로 테스트할 수 있다.
    """
    if not isinstance(text, str) or not text.strip():
        return []
    hits: list[dict[str, Any]] = []
    for pattern, reason in _RULES:
        m = pattern.search(text)
        if m:
            hits.append({
                "reason": reason,
                "matched": m.group(0)[:60],
                "guardrail": "G-02",
            })
    return hits


def is_blocked(text: str) -> bool:
    """차단 대상인가? 한 건이라도 걸리면 차단 (심각도 High — 경고가 아니라 차단)."""
    return len(scan(text)) > 0


def security_log_record(request_id: str, hits: list[dict[str, Any]]) -> dict[str, Any]:
    """보안 로그 한 줄. 완료 기준이 '차단 + 로그'라서 기록 형태를 여기서 정한다."""
    return {
        "request_id": request_id,
        "event": "guardrail_block",
        "guardrail": "G-02",
        "severity": "High",
        "reasons": [h["reason"] for h in hits],
        "samples": [h["matched"] for h in hits],
    }
