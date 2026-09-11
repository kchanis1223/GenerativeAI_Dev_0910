"""B-03 공통 배송 요청·조회·배차 결과 모델."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class StorageType(StrEnum):
    LIVE = "live"
    REFRIGERATED = "refrigerated"
    FROZEN = "frozen"
    AMBIENT = "ambient"


class Priority(StrEnum):
    NORMAL = "normal"
    URGENT = "urgent"


class GeocodeStatus(StrEnum):
    OK = "ok"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


class DispatchStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ToolErrorCode(StrEnum):
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UPSTREAM_ERROR = "upstream_error"
    UNAUTHORIZED = "unauthorized"
    INVALID_INPUT = "invalid_input"
    MISSING_CONTEXT = "missing_context"
    GEOCODE_NOT_FOUND = "geocode_not_found"
    GEOCODE_AMBIGUOUS = "geocode_ambiguous"
    INTERNAL_ERROR = "internal_error"


class DispatchRequest(BaseModel):
    """LLM이 사용자 배송 요청에서 추출하는 구조화된 입력."""

    depot_id: str
    destination_ids: list[str] | None = None
    delivery_date: date
    departure_time: datetime | None = None
    vehicle_count: int | None = Field(default=None, ge=1)
    excluded_destination_ids: list[str] = Field(default_factory=list)
    excluded_vehicle_ids: list[str] = Field(default_factory=list)
    product_names: list[str] | None = None
    deadline: datetime | None = None
    priority: Priority = Priority.NORMAL
    storage_types: list[StorageType] | None = None


class OrderItem(BaseModel):
    product_name: str
    weight_kg: float = Field(ge=0)


class Order(BaseModel):
    order_id: str
    destination_id: str
    address: str
    items: list[OrderItem]
    weight_kg: float = Field(ge=0)
    volume_m3: float | None = Field(default=None, ge=0)
    storage_type: StorageType
    priority: Priority
    deadline: datetime | None = None
    service_seconds: int = Field(ge=0)


class Vehicle(BaseModel):
    vehicle_id: str
    capacity_weight_kg: float = Field(ge=0)
    capacity_volume_m3: float | None = Field(default=None, ge=0)
    supported_storage_types: list[StorageType]
    available: bool
    shift_start: datetime
    shift_end: datetime


class GeocodeCandidate(BaseModel):
    matched_address: str
    lat: float
    lon: float

    @field_validator("lat")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("lat must be between -90 and 90")
        return value

    @field_validator("lon")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("lon must be between -180 and 180")
        return value


class GeocodeResult(BaseModel):
    status: GeocodeStatus
    input_address: str
    candidates: list[GeocodeCandidate]


class DispatchRuntimeContext(BaseModel):
    """서버가 Tool 실행 계층에 주입하는 배차 실행 컨텍스트.

    이 값은 LLM이 생성하거나 Tool 입력 스키마에 노출하지 않는다. ``depot_id``와
    ``origin``은 센터 마스터에서 서버가 확정하고, 지오코딩 결과는
    ``destination_id``를 키로 보관하여 배차 Tool이 임의로 주소나 좌표를
    바꾸지 못하게 한다.
    """

    depot_id: str | None = None
    origin: GeocodeCandidate | None = None
    orders: dict[str, Order] = Field(default_factory=dict)
    vehicles: dict[str, Vehicle] = Field(default_factory=dict)
    geocodes: dict[str, GeocodeResult] = Field(default_factory=dict)


class DispatchConstraints(BaseModel):
    priority: Priority
    deadline: datetime | None = None
    storage_types: list[StorageType] | None = None
    departure_time: datetime | None = None
    excluded_destination_ids: list[str] = Field(default_factory=list)


class Stop(BaseModel):
    sequence: int = Field(ge=1)
    order_id: str
    destination_id: str
    eta: datetime | None = None


class VehicleRoute(BaseModel):
    vehicle_id: str
    stops: list[Stop]
    estimated_duration_seconds: int | None = Field(default=None, ge=0)
    distance_meters: int | None = Field(default=None, ge=0)


class UnassignedOrder(BaseModel):
    order_id: str
    reason_code: str | None = None
    reason_message: str | None = None


class DispatchResult(BaseModel):
    status: DispatchStatus
    routes: list[VehicleRoute]
    unassigned_orders: list[UnassignedOrder]


class ToolError(BaseModel):
    """Tool 호출 실패를 LLM에 전달하기 위한 구조화된 오류 데이터.

    재시도 여부는 이 값을 소비하는 Tool 실행 계층이 ``retryable``을
    기준으로 판단한다. 개별 Tool은 재시도 자체를 수행하지 않는다.
    """

    code: ToolErrorCode
    message: str
    retryable: bool


class ToolErrorException(Exception):
    """Tool 구현이 발생시킬 typed exception의 기반 클래스."""

    def __init__(self, error: ToolError) -> None:
        self.error = error
        super().__init__(error.message)
