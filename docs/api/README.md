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
| `optionType` | 아니오 | `1`: 무게 균등, `2`: 부피 균등, `3`: 배송지 건수 균등 |
| `equalizationType` | 아니오 | `1`: 설정 안 함, `2`: 거리 균등, `3`: 시간 균등 |
| `centerReturnYn` | 아니오 | `Y`: 배송 후 센터 복귀, `N`: 복귀 안 함 |

위 요청 예시는 무게 균등 배차를 사용하고 거리·시간 균등화는 적용하지 않는다. 옵션 값은 [공식 배차 요청 명세](https://tms-skopenapi.readme.io/reference/배차-요청)를 기준으로 정리했다.

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
| `routeYn` | 아니오 | `Y`: 상세 경로 좌표 포함, `N`: 미포함 |

주요 응답 필드는 다음과 같다.

- 전체: `resultCode`, `resultMessage`, `vehicleCount`, `processTime`
- 차량: `vehicleId`, `vehicleName`, `deliveryCount`, `deliveryTime`, `deliveryDistance`, `deliveryWeight`
- 방문지: `orderId`, `orderName`, `address`, `latitude`, `longitude`, `serviceTime`, `expectedArrivalTime`, `expectedDepartureTime`

실제 응답에서는 `vehicleList`가 배열로 반환됐다. 소요 시간·거리 값은 문자열로 반환될 수 있으므로 내부 스키마 변환 시 숫자로 변환하고 아래 단위를 적용한다.

| 필드 | 단위·형식 | 변환 예시 |
|---|---|---|
| `deliveryTime` | 초, 예상 주행 시간 | `"4518"` → `4518`초 (75분 18초) |
| `deliveryDistance` | 미터, 예상 주행 거리 | `"19423"` → `19423`m (19.423km) |
| `deliveryWeight` | kg | `100` → 100kg |
| `serviceTime` | 분, 배송지 작업 시간 | `10` → 10분. 내부 모델이 초 단위이면 `600`초로 변환 |
| `expectedArrivalTime`, `expectedDepartureTime` | `yyyyMMddHHmm` | `202609111139` → 2026-09-11 11:39 |

단위는 [공식 배차 결과 응답 설명](https://tms-skopenapi.readme.io/reference/배차결과요청-샘플예제)을 기준으로 정리했다. `processTime`의 단위는 이번 확인에서 확정하지 않았으므로 주행 시간이나 작업 시간으로 사용하지 않는다.

실제 응답 예시는 [tms-allocation-data-response.json](./tms-allocation-data-response.json)을 참고한다.

## 저장 응답 Mock 실행

`USE_MOCK=1`은 위 B-02 요청을 재생하는 모드다. 앱키가 없어도 동작하며 외부 HTTP를 호출하지 않는다. 다른 주소·주문·차량·출발시각이나 지원하지 않는 API는 저장 응답이 없다는 오류로 중단한다. 이를 실제 주소 검색 실패로 간주하지 않는다.

응답 JSON은 설치된 Python 패키지에서도 사용할 수 있도록 `agent/badaro/tools/mock_responses/`에 포함한다. 원본은 이 폴더의 B-02 기록이며 테스트로 두 사본의 일치를 확인한다. 지오코딩 캐시는 Mock과 실제 모드를 구분한다. `USE_MOCK=0`은 기존 실제 HTTP 경로를 사용한다.

이 PR은 B-02 저장 응답 어댑터다. 기존 CSV의 MVP 시연 주문·차량에 맞는 응답 준비와 Agent 실행 연결은 #17·#19에 남아 있다. CSV 전체가 이 응답으로 배차되는 것은 아니다.

## 배차 미배정과 검증 오류

현재 `DispatchResult.unassigned_orders[*].reason_code`로 반환하는 값은 `not_assigned`다. 요청한 주문이 TMS 경로에 없다는 뜻이며, TMS가 그 원인을 설명했다는 의미는 아니다.

보관유형·중량·부피·마감시간·가용 상태 위반은 정상 미배정 목록으로 바꾸지 않고 `ToolErrorException`의 `upstream_error`로 반환한다. 내부 검사 식별자인 `incompatible_vehicle`, `capacity_exceeded`, `volume_exceeded`, `deadline_exceeded`, `unavailable_vehicle`은 현재 공개 미배정 사유 코드가 아니다.
