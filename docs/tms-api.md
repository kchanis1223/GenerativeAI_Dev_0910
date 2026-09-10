# SK TMS API 목업

2026-09-10에 SK TMS 문서의 사이드바에 공개된 센터·권역·차량·배송지·배차·교차금지선 24개 API의 요청 필드와 응답 예제를 확인했습니다. 아래 각 링크는 확인한 원문입니다. 정리한 필드·예제는 `src/data/tms-api-catalog.json`에 있으며 앱의 **API 탐색**에서 직접 확인할 수 있습니다. 문서의 인증 키 값은 수집한 카탈로그에 포함하지 않습니다.

| 구분                 | API                  | 메서드 | 원문                                                                                                                                  |
| -------------------- | -------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| 센터 목록조회        | `/centerList`        | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%84%BC%ED%84%B0-%EB%AA%A9%EB%A1%9D%EC%A1%B0%ED%9A%8C)                             |
| 센터 추가            | `/centerInsert`      | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%84%BC%ED%84%B0-%EC%B6%94%EA%B0%80)                                               |
| 센터 수정            | `/centerUpdate`      | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%84%BC%ED%84%B0-%EC%88%98%EC%A0%95)                                               |
| 센터 삭제            | `/centerDelete`      | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%84%BC%ED%84%B0-%EC%82%AD%EC%A0%9C)                                               |
| 권역 목록조회        | `/zoneList`          | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EA%B6%8C%EC%97%AD-%EB%AA%A9%EB%A1%9D%EC%A1%B0%ED%9A%8C)                             |
| 권역 추가            | `/zoneInsert`        | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EA%B6%8C%EC%97%AD-%EC%B6%94%EA%B0%80)                                               |
| 권역 여러건 추가     | `/zoneListInsert`    | POST   | [명세](https://tms-skopenapi.readme.io/reference/%EA%B6%8C%EC%97%AD-%EC%97%AC%EB%9F%AC%EA%B1%B4-%EC%B6%94%EA%B0%80)                   |
| 권역 수정            | `/zoneUpdate`        | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EA%B6%8C%EC%97%AD%EC%88%98%EC%A0%95)                                                |
| 권역 삭제            | `/zoneDelete`        | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EA%B6%8C%EC%97%AD-%EC%82%AD%EC%A0%9C)                                               |
| 차량 목록조회        | `/vehicleList`       | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%B0%A8%EB%9F%89-%EB%AA%A9%EB%A1%9D%EC%A1%B0%ED%9A%8C)                             |
| 차량 추가            | `/vehicleInsert`     | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%B0%A8%EB%9F%89-%EC%B6%94%EA%B0%80)                                               |
| 차량 여러건 추가     | `/vehicleListInsert` | POST   | [명세](https://tms-skopenapi.readme.io/reference/%EC%B0%A8%EB%9F%89-%EC%97%AC%EB%9F%AC%EA%B1%B4-%EC%B6%94%EA%B0%80)                   |
| 차량 수정            | `/vehicleUpdate`     | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%B0%A8%EB%9F%89-%EC%88%98%EC%A0%95)                                               |
| 차량 삭제            | `/vehicleDelete`     | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EC%B0%A8%EB%9F%89-%EC%82%AD%EC%A0%9C)                                               |
| 배송지 목록 조회     | `/orderList`         | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EB%B0%B0%EC%86%A1%EC%A7%80-%EB%AA%A9%EB%A1%9D-%EC%A1%B0%ED%9A%8C)                   |
| 배송지 추가          | `/orderInsert`       | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EB%B0%B0%EC%86%A1%EC%A7%80-%EC%B6%94%EA%B0%80)                                      |
| 배송지 여러건 추가   | `/orderListInsert`   | POST   | [명세](https://tms-skopenapi.readme.io/reference/%EB%B0%B0%EC%86%A1%EC%A7%80-%EC%97%AC%EB%9F%AC%EA%B1%B4-%EC%B6%94%EA%B0%80)          |
| 배송지 수정          | `/orderUpdate`       | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EB%B0%B0%EC%86%A1%EC%A7%80-%EC%88%98%EC%A0%95)                                      |
| 배송지 삭제          | `/orderDelete`       | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EB%B0%B0%EC%86%A1%EC%A7%80-%EC%82%AD%EC%A0%9C)                                      |
| 배차 요청            | `/allocation`        | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EB%B0%B0%EC%B0%A8-%EC%9A%94%EC%B2%AD)                                               |
| 배차 결과 요청       | `/allocationData`    | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EB%B0%B0%EC%B0%A8-%EA%B2%B0%EA%B3%BC-%EC%9A%94%EC%B2%AD)                            |
| 교차금지선 목록 조회 | `/banLineList`       | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EA%B5%90%EC%B0%A8%EA%B8%88%EC%A7%80%EC%84%A0-%EB%AA%A9%EB%A1%9D-%EC%A1%B0%ED%9A%8C) |
| 교차금지선 추가      | `/banLineInsert`     | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EA%B5%90%EC%B0%A8%EA%B8%88%EC%A7%80%EC%84%A0-%EC%B6%94%EA%B0%80)                    |
| 교차금지선 삭제      | `/banLineDelete`     | GET    | [명세](https://tms-skopenapi.readme.io/reference/%EA%B5%90%EC%B0%A8%EA%B8%88%EC%A7%80%EC%84%A0-%EC%82%AD%EC%A0%9C)                    |

## 데이터 연결

`src/stores/tms.ts`가 Vue 반응형 상태를 보관하고 `src/services/tms-mock.ts`가 순수 TypeScript로 요청을 처리합니다. 센터 조회 목업도 이 상태에서 읽습니다. 프록시 조회 결과는 목업 상태를 덮어쓰지 않습니다.

- 기본 데이터: 센터 8곳, 권역 3개, 차량 6대, 배송지 8곳, 교차금지선 1개.
- 차량은 상온·냉장·투입 제외·숙련도 차이를 포함합니다. 배송지에는 차량이 없는 인천 권역의 미배차 예제가 포함됩니다.
- 등록·수정·삭제는 동일한 상태에 반영되며, 일괄 등록은 전체 검증 후 한 번에 저장합니다.
- 차량 `weight`는 ton, 배송 `deliveryWeight`는 kg, 부피는 cbm, `serviceTime`은 분입니다.
- 차량/배송지 선택 삭제는 `deleteFlag: "2"`와 쉼표로 구분한 ID, 전체 삭제는 `"1"`입니다.
- API 요청 기록은 최근 50회, 배차 결과 스냅샷은 최근 30개까지만 메모리에 보관합니다. 새로고침하면 초기화됩니다.

## 배차 시연

1. `/allocation`에 전체/선택 대상, HHmm 출발 시간, 중량/부피/배송지 수, 거리/시간 균등화, 센터 복귀 여부를 전달합니다.
2. 목업은 요청 당시 데이터를 복사해 계산하고 `mappingKey`를 반환합니다.
3. `/allocationData`를 해당 키로 조회합니다. 목업은 약 1.2초 동안 `102` 처리 중을 반환합니다. 화면은 최대 8회 조회 후 종료합니다.
4. 차량별 배송 순서·예상 도착/출발 시간·적재량·직선 거리와 미배차 사유를 표시합니다. `routeYn: "Y"`일 때만 경로 데이터를 포함합니다.

목업 계산은 최초 등록 센터에서 출발해 가까운 배송지 순으로 배분합니다. 차량 유형, 권역, 투입 여부, 적재 한도, 교차금지선을 검사하고 선택한 배차·균등화 기준과 숙련도로 차량을 선택합니다. `weight * 1000`으로 단위를 맞추며 부피 0은 제한 미설정, 빈 권역은 권역 제한 없음으로 간주합니다. 숙련도는 배분 점수에만 반영합니다. 차량 별도 도착 좌표가 있으면 이를 우선하고, 없으면 복귀 설정을 따릅니다.

경로는 좌표 간 직선, 시간은 시속 30km와 서비스 시간의 합입니다. 교차금지선도 직선 교차만 검사합니다. **실제 도로·교통·운영시간·비용·TMS 최적화 계산은 구현하지 않았습니다.** 비용·영업시간 같은 문서 예제의 추가 필드는 상세 JSON에 보존하되 계산에는 사용하지 않습니다.

## 문서와 목업의 차이

- 문서의 `vehicleList`, `vehicleRouteList` 성공 예제는 배열이 아닌 단일 객체입니다. 원문 예제는 그대로 제공하고 목업 결과는 여러 차량용 배열로 정규화했습니다.
- 배송 무게·부피는 API별 문자열/숫자 타입이 혼재합니다. 입력을 숫자로 검증하고 계산에 사용합니다. 배차 결과의 좌표·시간은 문서처럼 문자열입니다.
- 배송지 일괄 등록 문서의 성공 응답 예제는 실제로 `reqDatas` 요청 모양입니다. 목업은 다른 등록 API 형태의 완료 응답을 반환합니다.
- 교차금지선 예제의 비표준 따옴표는 JSON으로 읽을 수 있도록 수정했습니다. 예제 인증 키는 제거했습니다.
- `inputYn`, `skillPer`는 등록/수정에서 지원하지만 차량 조회 예제에는 없습니다. 목업 조회에는 편집/배차 상태 확인을 위해 포함했습니다.
- `102` 처리 중, `mock` 설명·미배차 정보, 404/409 검증 오류, 권역 참조 무결성·일괄 등록 원자성·100건 제한은 **시연용 정책**입니다. SK TMS가 같은 동작을 보장한다는 뜻이 아닙니다.
- 실제 API 전환 시 인증 방식, 배열/객체, 숫자 타입, 처리 중 응답, 에러 코드 및 결과 준비 시간을 실제 응답으로 확인하고 어댑터를 연결해야 합니다. 확장 API는 전부 목업 전용이며, 기존 센터 목록조회만 별도 서버 프록시 연결 경로가 있습니다.

## 검증

단위 테스트는 24개 API 실행, CRUD 반영, 일괄 등록 원자성, 오류 시 데이터 보존, 단위 환산·차종·권역·적재·교차금지선, 결과 키·스냅샷·복귀 여부를 확인합니다. 브라우저 테스트는 차량 변경→배차 결과, API 일괄 등록→배송지 목록, 오류 시나리오, 모바일 선택 배차, 로고 진입 전환을 확인합니다.
