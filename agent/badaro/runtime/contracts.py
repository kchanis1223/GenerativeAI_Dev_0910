"""Agent 진입·반환 형식과 실행 설정."""

import math
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from badaro.schemas import DispatchRequest, DispatchResult, Priority, StorageType, ToolError


class AddressCorrection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original: str
    replacement: str


class RequestDraft(BaseModel):
    """누락값을 허용하는 추출 결과. 배차 전에는 DispatchRequest로 검증한다."""

    model_config = ConfigDict(extra="forbid")
    depot_id: str | None = None
    delivery_date: date | None = None
    destination_ids: list[str] | None = None
    all_destinations: bool = False
    departure_time: datetime | None = None
    vehicle_count: int | None = Field(default=None, ge=1)
    excluded_destination_ids: list[str] = Field(default_factory=list)
    excluded_vehicle_ids: list[str] = Field(default_factory=list)
    product_names: list[str] | None = None
    deadline: datetime | None = None
    priority: Priority = Priority.NORMAL
    storage_types: list[StorageType] | None = None
    address_corrections: list[AddressCorrection] = Field(default_factory=list)
    out_of_scope: bool = False

    def request_values(self):
        return self.model_dump(
            exclude={
                "all_destinations",
                "address_corrections",
                "out_of_scope",
            }
        )


class AgentReply(BaseModel):
    thread_id: str
    request_id: str
    mode: Literal["offline", "llm_mock", "live"]
    status: Literal["completed", "needs_clarification", "blocked", "error"]
    message: str
    questions: list[str] = Field(default_factory=list)
    request: DispatchRequest | None = None
    result: DispatchResult | None = None
    error: ToolError | None = None
    model_calls: int = 0


@dataclass(frozen=True)
class Settings:
    use_mock: bool = True
    model_mode: str = "offline"
    main_model: str = ""
    max_model_calls: int = 6
    depot_id: str = "CENTER-NR"
    default_date: date | None = None
    master_verified: bool = False

    def __post_init__(self):
        if self.model_mode not in {"offline", "openai"}:
            raise ValueError("MODEL_MODE는 offline 또는 openai여야 합니다")
        if not 1 <= self.max_model_calls <= 6:
            raise ValueError("MAX_TOOL_ITERATIONS는 1~6이어야 합니다")
        if not self.use_mock and self.model_mode == "offline":
            raise ValueError("offline 모델은 실제 TMS를 호출할 수 없습니다")
        if self.model_mode == "openai" and not self.main_model:
            raise ValueError("MAIN_MODEL을 설정해 주세요")

    @classmethod
    def from_env(cls):
        load_dotenv()
        flag = os.getenv("USE_MOCK", "1")
        verified = os.getenv("TMS_MASTER_VERIFIED", "0")
        if flag not in {"0", "1"} or verified not in {"0", "1"}:
            raise ValueError("USE_MOCK와 TMS_MASTER_VERIFIED는 0 또는 1이어야 합니다")
        if os.getenv("TOOL_MAX_RETRIES", "3") != "3":
            raise ValueError("현재 조회 재시도 횟수는 3회입니다")
        interval = float(os.getenv("TMS_POLL_INTERVAL_SECONDS", "1"))
        attempts = int(os.getenv("TMS_POLL_MAX_ATTEMPTS", "30"))
        if not math.isfinite(interval) or interval < 0 or attempts < 1:
            raise ValueError("TMS 폴링 설정을 확인해 주세요")
        raw_date = os.getenv("DEFAULT_DELIVERY_DATE", "")
        return cls(
            use_mock=flag == "1",
            model_mode=os.getenv("MODEL_MODE", "offline"),
            main_model=os.getenv("MAIN_MODEL", ""),
            max_model_calls=int(os.getenv("MAX_TOOL_ITERATIONS", "6")),
            depot_id=os.getenv("DEPOT_ID", "CENTER-NR"),
            default_date=date.fromisoformat(raw_date) if raw_date else None,
            master_verified=verified == "1",
        )

    @property
    def mode(self):
        if self.model_mode == "offline":
            return "offline"
        return "llm_mock" if self.use_mock else "live"
