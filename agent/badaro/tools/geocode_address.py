"""주소 좌표 변환 Tool 인터페이스."""

from badaro.schemas import GeocodeResult


def geocode_address(address: str) -> GeocodeResult:
    """주소를 좌표 후보로 변환한다."""
    raise NotImplementedError
