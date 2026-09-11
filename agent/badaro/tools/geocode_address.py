"""주소 좌표 변환 Tool 인터페이스."""

from badaro.schemas import GeocodeResult


def geocode_address(address: str) -> GeocodeResult:
    """주소를 좌표 후보로 변환한다.

    ``ambiguous`` 또는 ``not_found`` 결과는 사용자 확인 없이는 배차에
    사용하지 않는다. 외부 API 오류는 ToolError로 전달한다.
    """
    raise NotImplementedError
