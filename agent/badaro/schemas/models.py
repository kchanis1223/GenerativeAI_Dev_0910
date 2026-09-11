"""B-03 공통 배송 요청·조회·배차 결과 모델."""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


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

    depot_id: str = Field(description="출발 물류센터 ID")
    destination_ids: list[str] | None = Field(
        default=None, description="배송 대상 지점 ID 목록. None이면 해당 배송일 전체 주문"
    )
    delivery_date: date = Field(description="배송 대상일")
    departure_time: datetime | None = Field(default=None, description="출발 예정 시각")
    vehicle_count: int | None = Field(default=None, ge=1, description="사용할 차량 수")
    excluded_destination_ids: list[str] = Field(
        default_factory=list, description="배차에서 제외할 지점 ID 목록"
    )
    excluded_vehicle_ids: list[str] = Field(
        default_factory=list, description="배차에서 제외할 차량 ID 목록"
    )
    product_names: list[str] | None = Field(
        default=None, description="주문 조회를 좁히는 상품명 조건"
    )
    deadline: datetime | None = Field(default=None, description="납품 마감 시각")
    priority: Priority = Field(default=Priority.NORMAL, description="배송 우선순위")
    storage_types: list[StorageType] | None = Field(default=None, description="필요한 보관 조건")


class OrderItem(BaseModel):
    product_name: str = Field(description="상품명")
    weight_kg: float = Field(ge=0, description="상품 중량(kg)")


class Order(BaseModel):
    order_id: str = Field(description="주문 ID")
    destination_id: str = Field(description="배송 지점 ID")
    address: str = Field(description="배송 지점 주소")
    items: list[OrderItem] = Field(description="주문 상품 목록")
    weight_kg: float = Field(ge=0, description="주문 총중량(kg)")
    volume_m3: float | None = Field(default=None, ge=0, description="주문 총부피(m3)")
    storage_type: StorageType = Field(description="주문 보관 유형")
    priority: Priority = Field(description="주문 우선순위")
    deadline: datetime | None = Field(default=None, description="지점별 납품 마감 시각")
    service_seconds: int = Field(ge=0, description="하역 소요시간(초)")


class Vehicle(BaseModel):
    vehicle_id: str = Field(description="차량 ID")
    capacity_weight_kg: float = Field(ge=0, description="최대 적재 중량(kg)")
    capacity_volume_m3: float | None = Field(default=None, ge=0, description="최대 적재 부피(m3)")
    supported_storage_types: list[StorageType] = Field(description="적재 가능한 보관 유형")
    available: bool = Field(description="해당 배송일 운행 가능 여부")
    shift_start: datetime = Field(description="운행 가능 시작 시각")
    shift_end: datetime = Field(description="운행 가능 종료 시각")

    @model_validator(mode="after")
    def validate_shift(self) -> "Vehicle":
        if self.shift_end < self.shift_start:
            raise ValueError("shift_end must be greater than or equal to shift_start")
        return self


class GeocodeCandidate(BaseModel):
    matched_address: str = Field(description="매칭된 주소")
    lat: float = Field(description="위도(WGS84)")
    lon: float = Field(description="경도(WGS84)")

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
    status: GeocodeStatus = Field(description="지오코딩 상태")
    input_address: str = Field(description="조회 요청 주소")
    candidates: list[GeocodeCandidate] = Field(description="조회된 주소 후보 목록")

    @model_validator(mode="after")
    def validate_candidates_for_status(self) -> "GeocodeResult":
        candidate_count = len(self.candidates)
        if self.status is GeocodeStatus.OK and candidate_count != 1:
            raise ValueError("status=ok requires exactly one candidate")
        if self.status is GeocodeStatus.NOT_FOUND and candidate_count != 0:
            raise ValueError("status=not_found requires no candidates")
        if self.status is GeocodeStatus.AMBIGUOUS and candidate_count < 2:
            raise ValueError("status=ambiguous requires at least two candidates")
        return self


class DispatchRuntimeContext(BaseModel):
    """서버가 Tool 실행 계층에 주입하는 배차 실행 컨텍스트.

    이 값은 LLM이 생성하거나 Tool 입력 스키마에 노출하지 않는다. ``depot_id``와
    ``origin``은 센터 마스터에서 서버가 확정하고, 지오코딩 결과는
    ``GeocodeResult.input_address``를 키로 보관하여 같은 주소의 결과를
    재사용하고 배차 Tool이 임의로 주소나 좌표를 바꾸지 못하게 한다.
    """

    depot_id: str | None = None
    origin: GeocodeCandidate | None = None
    orders: dict[str, Order] = Field(default_factory=dict)
    vehicles: dict[str, Vehicle] = Field(default_factory=dict)
    geocodes: dict[str, GeocodeResult] = Field(default_factory=dict)


class DispatchConstraints(BaseModel):
    priority: Priority = Field(description="배송 우선순위")
    deadline: datetime | None = Field(default=None, description="납품 마감 시각")
    storage_types: list[StorageType] | None = Field(default=None, description="필요한 보관 조건")
    departure_time: datetime | None = Field(default=None, description="출발 예정 시각")
    excluded_destination_ids: list[str] = Field(
        default_factory=list, description="배차에서 제외할 지점 ID 목록"
    )


class Stop(BaseModel):
    sequence: int = Field(ge=1, description="방문 순서")
    order_id: str = Field(description="주문 ID")
    destination_id: str = Field(description="배송 지점 ID")
    eta: datetime | None = Field(default=None, description="도착 예정 시각")


class VehicleRoute(BaseModel):
    vehicle_id: str = Field(description="배정된 차량 ID")
    stops: list[Stop] = Field(description="TMAP/TMS가 반환한 방문 순서")
    estimated_duration_seconds: int | None = Field(
        default=None, ge=0, description="예상 소요시간(초)"
    )
    distance_meters: int | None = Field(default=None, ge=0, description="예상 이동거리(m)")


class UnassignedOrder(BaseModel):
    order_id: str = Field(description="미배정 주문 ID")
    reason_code: str | None = Field(default=None, description="미배정 사유 코드")
    reason_message: str | None = Field(default=None, description="미배정 사유 설명")


class DispatchResult(BaseModel):
    status: DispatchStatus = Field(description="배차 처리 상태")
    routes: list[VehicleRoute] = Field(description="차량별 배정 및 방문 순서")
    unassigned_orders: list[UnassignedOrder] = Field(description="미배정 주문 목록")


class ToolError(BaseModel):
    """Tool 호출 실패를 LLM에 전달하기 위한 구조화된 오류 데이터.

    재시도 여부는 이 값을 소비하는 Tool 실행 계층이 ``retryable``을
    기준으로 판단한다. 개별 Tool은 재시도 자체를 수행하지 않는다.
    """

    code: ToolErrorCode = Field(description="오류 유형")
    message: str = Field(description="사용자 안내용 오류 설명")
    retryable: bool = Field(description="실행 계층에서 재시도할 수 있는지 여부")


class ToolErrorException(Exception):
    """Tool 구현이 발생시킬 typed exception의 기반 클래스."""

    def __init__(self, error: ToolError) -> None:
        self.error = error
        super().__init__(error.message)
