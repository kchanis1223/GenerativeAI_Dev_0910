"""실행 디렉터리와 무관하게 바다로 프롬프트 파일을 읽는다."""

from dataclasses import dataclass
from pathlib import Path

_PROMPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PromptBundle:
    """모델 초기화 계층에 전달할 프롬프트 묶음."""

    system: str
    fewshot: str


def _read_prompt(filename: str) -> str:
    path = _PROMPT_DIR / filename
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {path}") from exc
    except OSError as exc:
        raise OSError(f"프롬프트 파일을 읽을 수 없습니다: {path}") from exc


def load_system_prompt() -> str:
    """RICE 구조의 시스템 프롬프트를 반환한다."""

    return _read_prompt("system.md")


def load_fewshot_prompt() -> str:
    """정상 배차·입력 보완·실패 안내 예시를 반환한다."""

    return _read_prompt("fewshot.md")


def load_prompt_bundle() -> PromptBundle:
    """시스템 프롬프트와 Few-shot 예시를 함께 반환한다."""

    return PromptBundle(system=load_system_prompt(), fewshot=load_fewshot_prompt())
