"""인증정보·전화번호·상세주소를 표시용 문자열과 로그에서 마스킹한다."""
from __future__ import annotations

import re
from typing import Any

PHONE_RE = re.compile(r"(?<![\d+])(?:\+?82[-.\s]?0?|0)\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}(?!\d)")

ADDRESS_DETAIL_RE = re.compile(r"\d+\s*동\s*\d+\s*호")

SECRET_KV_RE = re.compile(
    r"(?i)\b(app[-_]?key|api[-_]?key|access[-_]?token|authorization|secret)\b['\"]?\s*[:=]\s*"
    r"(?:Bearer\s+)?['\"]?([^\s'\",;]+)"
)
BARE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9]{24,}(?![A-Za-z0-9])")

MASK = "***"
SECRET_KEYS = {"appkey", "apikey", "accesstoken", "authorization", "secret", "token", "password"}


def mask_phone(text: str) -> str:
    """전화번호를 010-****-1234 형태로 바꾼다. 앞자리와 끝 4자리는 남긴다(본인 확인용)."""
    def _repl(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if digits.startswith("82"):
            digits = "0" + digits[2:]
        if len(digits) < 9:
            return m.group(0)
        head = "02" if digits.startswith("02") else digits[:3]
        tail = digits[-4:]
        return f"{head}-****-{tail}"
    return PHONE_RE.sub(_repl, text)


def mask_secrets(text: str) -> str:
    """인증키를 가린다. 키 '이름'은 남기고 '값'만 지운다 — 어떤 키가 문제인지는 알아야 하니까."""
    text = SECRET_KV_RE.sub(lambda m: f"{m.group(1)}={MASK}", text)
    return BARE_TOKEN_RE.sub(MASK, text)


def mask_text(text: str) -> str:
    """문자열 하나를 전부 마스킹한다.

    순서가 중요하다. 키를 먼저 지워야 키 안의 숫자를 전화번호로 오인하지 않는다.
    """
    if not isinstance(text, str):
        return text
    out = mask_secrets(text)
    out = mask_phone(out)
    out = ADDRESS_DETAIL_RE.sub(MASK, out)
    return out


def mask_obj(obj: Any, _depth: int = 0) -> Any:
    """dict·list 를 재귀로 훑으며 안쪽 문자열까지 마스킹한다.

    로그 기록 직전에 통째로 통과시킨다.
    """
    if _depth > 10:
        return MASK
    if isinstance(obj, str):
        return mask_text(obj)
    if isinstance(obj, dict):
        return {
            k: MASK if re.sub(r"[-_ ]", "", str(k).lower()) in SECRET_KEYS
            else mask_obj(v, _depth + 1)
            for k, v in obj.items()
        }
    if isinstance(obj, (list, tuple)):
        return type(obj)(mask_obj(v, _depth + 1) for v in obj)
    return obj


PII_OUTPUT_NOTE = "연락처는 개인정보 보호를 위해 일부만 표시합니다."


def build_pii_middleware() -> Any:
    """내장 PIIMiddleware 에 국내 전화번호 detector 를 등록해 만든다.

    내장 타입에는 한국 전화번호·상세주소가 없어 정규식을 직접 넣어야 한다(설계서 3.2.1 주의).
    langchain 미설치면 None 을 돌려주고 agent.py 가 건너뛴다.
    """
    try:
        from langchain.agents.middleware import PIIMiddleware
    except ImportError:
        return None
    return PIIMiddleware(
        "kr_phone_number",
        detector=PHONE_RE,
        strategy="mask",
        apply_to_input=True,
        apply_to_output=True,
        apply_to_tool_results=True,
    )
