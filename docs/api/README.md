# B-02 TMAP 및 TMS API 첫 호출

2026-09-11에 바다로 앱의 Free TMAP 및 Free TMAP TMS 상품으로 실제 호출을 확인했다. 저장된 예시에서는 앱키를 제거했으며 실제 키는 `agent/.env`의 `TMAP_APP_KEY`에서만 관리한다.

## 확인 결과

| API | Method | Endpoint | HTTP | 결과 |
|---|---|---|---:|---|
| TMAP Full Text Geocoding | GET | `https://apis.openapi.sk.com/tmap/geo/fullAddrGeo` | 200 | 주소 1건과 WGS84 좌표 반환 |
| TMS 배차 요청 | GET | `https://apis.openapi.sk.com/tms/allocation` | 200 | `mappingKey` 반환 |
| TMS 배차 결과 조회 | GET | `https://apis.openapi.sk.com/tms/allocationData` | 200 | 차량 1대와 배송지 1건 반환 |

## 인증

세 호출 모두 `appKey` 쿼리 파라미터 방식으로 성공했다.

```text
?appKey=<TMAP_APP_KEY>
```

TMAP Full Text Geocoding 호출에서 앱키를 요청 헤더에만 넣은 방식은 `403 INVALID_API_KEY`를 반환했다. 현재 연동에서는 실제로 성공한 쿼리 파라미터 방식을 사용하되, 키가 URL을 포함한 로그에 노출되지 않도록 요청 URL과 쿼리 문자열을 마스킹해야 한다.

## TMAP Full Text Geocoding

### 요청

```http
GET https://apis.openapi.sk.com/tmap/geo/fullAddrGeo
    ?version=1
    &addressFlag=F00
    &coordType=WGS84GEO
    &fullAddr=<URL encoded address>
    &appKey=<TMAP_APP_KEY>
Accept: application/json
```

필수 또는 사용 파라미터:

| 필드 | 값 | 설명 |
|---|---|---|
| `version` | `1` | API 버전 |
| `addressFlag` | `F00` | 지번 및 도로명 주소 모두 허용 |
| `coordType` | `WGS84GEO` | 응답 좌표계 |
| `fullAddr` | 주소 문자열 | 변환할 주소 |
| `appKey` | 비공개 앱키 | 인증 |

주요 응답 필드는 `coordinateInfo.totalCount`, `coordinateInfo.coordinate`, `newMatchFlag`, `newLat`, `newLon`, `newRoadName`, `newBuildingIndex`다. 도로명 주소 결과에서는 `lat`과 `lon`이 비어 있고 `newLat`과 `newLon`에 좌표가 들어올 수 있으므로 Adapter에서 두 형식을 모두 처리해야 한다.

실제 응답 예시는 [tmap-geocode-response.json](./tmap-geocode-response.json)을 참고한다.

## TMS 배차 요청

테스트 전에 다음 최소 데이터를 실제 TMS 계정에 등록했다.

| 종류 | 테스트 ID |
|---|---|
| 센터 | `badaro-b02-center` |
| 차량 | `badaro-b02-vehicle` |
| 배송지 | `badaro-b02-order` |

### 요청

```http
GET https://apis.openapi.sk.com/tms/allocation
    ?allocationType=2
    &orderIdList=badaro-b02-order
    &vehicleIdList=badaro-b02-vehicle
    &startTime=1100
    &optionType=1
    &equalizationType=1
    &centerReturnYn=Y
    &appKey=<TMAP_APP_KEY>
Accept: application/json
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `allocationType` | 예 | `1`은 저장 데이터 전체, `2`는 지정 데이터 사용 |
| `orderIdList` | 조건부 | `allocationType=2`에서 사용할 배송지 ID |
| `vehicleIdList` | 조건부 | `allocationType=2`에서 사용할 차량 ID |
| `startTime` | 예 | 배송 시작 희망 시각, `HHmm` |
| `optionType` | 아니오 | 무게, 부피 또는 배송지 건수 균등 옵션 |
| `equalizationType` | 아니오 | 거리 또는 시간 균등 옵션 |
| `centerReturnYn` | 아니오 | 배송 후 센터 복귀 여부 |

성공 응답의 핵심 필드는 `resultCode`, `resultMessage`, `mappingKey`다. 실제 응답 예시는 [tms-allocation-response.json](./tms-allocation-response.json)을 참고한다.

## TMS 배차 결과 조회

### 요청

```http
GET https://apis.openapi.sk.com/tms/allocationData
    ?mappingKey=<allocation response mappingKey>
    &routeYn=N
    &appKey=<TMAP_APP_KEY>
Accept: application/json
```

| 필드 | 필수 | 설명 |
|---|---|---|
| `mappingKey` | 예 | 배차 요청 응답에서 받은 키 |
| `routeYn` | 아니오 | 상세 경로 좌표 포함 여부 |

주요 응답 필드는 다음과 같다.

- 전체: `resultCode`, `resultMessage`, `vehicleCount`, `processTime`
- 차량: `vehicleId`, `vehicleName`, `deliveryCount`, `deliveryTime`, `deliveryDistance`, `deliveryWeight`
- 방문지: `orderId`, `orderName`, `address`, `latitude`, `longitude`, `serviceTime`, `expectedArrivalTime`, `expectedDepartureTime`

실제 응답에서는 `vehicleList`가 배열로 반환됐다. 시간 필드는 `yyyyMMddHHmm`, 거리와 시간은 문자열로 반환될 수 있으므로 내부 스키마 변환 시 타입 정규화가 필요하다.

실제 응답 예시는 [tms-allocation-data-response.json](./tms-allocation-data-response.json)을 참고한다.
