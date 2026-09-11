# 노량진 당일 배송 샘플

배송일은 **2026-09-11, Asia/Seoul**입니다. 센터·지점의 도로명 주소는 실제 주소이며, 지점명·주문·차량과 적재량은 가상 시연 데이터입니다. 주소 검증을 위해 공공시설과 상업시설의 주소를 사용했으며, 그 시설에 바다로 지점이 입점했거나 실제 납품 관계가 있다는 뜻은 아닙니다.

## 파일

| 파일                     | 행 수 | 내용                                                      |
| ------------------------ | ----: | --------------------------------------------------------- |
| `centers.csv`            |     1 | 노량진센터 · 서울특별시 동작구 노들로 674                 |
| `branches.csv`           |    20 | 서울 20개 가상 지점 · 실제 도로명 주소와 좌표             |
| `vehicles.csv`           |     5 | 활어차 2대 · 냉장차 2대 · 일반차 1대                      |
| `delivery_orders.csv`    |    40 | 지점당 2건, 활어·냉장·냉동·일반 각 10건, 총 3,125kg       |
| `geocoding_results.csv`  |    21 | 지점 20곳과 센터 1곳의 성공 응답·조회 시각·주소 일치 근거 |
| `geocoding_rejected.csv` |     4 | 건물번호가 확인되지 않아 교체한 후보 주소와 실패 근거     |

CSV는 UTF-8 BOM, 쉼표 구분, LF 줄바꿈입니다. 쉼표·따옴표가 들어간 필드는 CSV 규칙에 맞춰 인용했습니다. `vehicleType`의 `01`·`02`와 시간창의 앞자리 0을 유지하기 위해 코드는 문자열로 읽어야 합니다. 무게 단위는 주문 `deliveryWeight`가 **kg**, 차량 `weight`가 **ton**, `maxLoadKg`가 **kg**이며 부피는 **cbm**입니다.

## 기존 주문 조회와 연결

이 저장소에는 `get_delivery_orders` 함수가 없으며, 동일한 역할의 기존 목업은 `executeTms(state, '/orderList')`입니다. 요청한 예시 함수 대신 **기존 주문 필드명을 그대로 사용하는** CSV와 읽기 어댑터 `src/services/delivery-csv.ts`를 제공합니다. 별도의 백엔드 Tool 함수를 만들지 않았습니다.

```ts
import centersCsv from '../../data/centers.csv?raw'
import branchesCsv from '../../data/branches.csv?raw'
import vehiclesCsv from '../../data/vehicles.csv?raw'
import ordersCsv from '../../data/delivery_orders.csv?raw'
import { readDeliveryDataset } from './delivery-csv'
import { executeTms } from './tms-mock'

const { state, branches } = readDeliveryDataset(
  {
    centers: centersCsv,
    branches: branchesCsv,
    vehicles: vehiclesCsv,
    orders: ordersCsv,
  },
  '2026-09-11',
)
const response = executeTms(state, '/orderList')
// resultCode: '200', resultCount: 40, resultData: 주문 배열
```

이 코드는 `src/services/`에서 사용하는 예입니다. `readDeliveryOrdersCsv(ordersCsv, '2026-09-11')`로 주문만 읽을 수도 있습니다. 날짜를 생략하면 CSV의 모든 주문을, 해당 날짜가 없으면 빈 배열을 반환합니다. 주문 외 센터·차량도 동일한 목업 상태에 들어가므로 `/centerList`, `/vehicleList`로 조회할 수 있습니다. 통합 배차 화면은 `src/data/noryangjin.ts`에서 이 어댑터로 CSV를 읽어 기본 데이터로 사용합니다.

### 주문 CSV 컬럼

| 컬럼                    | 형식 / 의미                                                             |
| ----------------------- | ----------------------------------------------------------------------- |
| `orderId`               | 유일한 주문 품목행 ID · `ORD-20260911-001`                              |
| `orderName`             | 가상 지점명 + 품목명                                                    |
| `address`               | 지점의 서울 도로명 주소                                                 |
| `latitude`, `longitude` | WGS84 위도·경도 · 검증된 지점 좌표                                      |
| `deliveryWeight`        | 주문 품목의 중량, kg                                                    |
| `deliveryVolume`        | 시연용 부피, cbm                                                        |
| `vehicleType`           | 기존 TMS 코드 · 일반 `01`, 냉장/냉동 `02`, 활어 `99`                    |
| `serviceTime`           | 해당 품목행의 작업 시간, 분                                             |
| `zoneCode`              | `SEOUL` · 시연용 서울 공통 권역                                         |
| `deliveryDate`          | `YYYY-MM-DD` · 한국 날짜                                                |
| `branchId`, `centerId`  | 지점·센터 CSV를 참조하는 ID                                             |
| `itemType`              | `활어`, `냉장`, `냉동`, `일반`                                          |
| `itemName`              | 활광어·활우럭·냉장 연어·냉장 고등어·냉동 새우·냉동 오징어·건미역·다시마 |
| `desiredDeliveryTime`   | 납품 희망시각 · `HH:mm`                                                 |
| `openTime`, `closeTime` | 희망시각 전후 30분 시간창 · 문자열 `HHmm`                               |
| `seq`, `updateDate`     | 목업 행 번호와 갱신 일시                                                |

한 행이 한 품목 주문입니다. 동일 지점의 2개 주문은 주소·좌표·희망시각이 같지만 ID와 품목은 다릅니다. 지점 단위 합배송 묶음이나 작업 시간 병합은 별도 계산 로직에서 처리해야 합니다.

`itemType`, `itemName`, `deliveryDate`, `branchId`, `centerId`, `desiredDeliveryTime`은 이 데이터셋의 확장 필드입니다. 조회 어댑터는 이를 보존하며 TMS 요청 파라미터로 새로 정의하지 않습니다. 목업 배차 엔진은 `supportedItemTypes`와 `itemType`을 비교해 냉장·냉동 세부 구분을 지킵니다. 납품 희망시간/시간창은 표에 표시하지만 배차 제약으로 계산하지 않습니다. 냉장차 2호는 냉동 설정이 가능한 차량으로 가정하며 실제 장비 성능을 검증한 데이터는 아닙니다.

### 차량 적재량과 품목 구분

| 차량      | 구분   | 가용 화물 적재량 | 품목 설정                       |
| --------- | ------ | ---------------: | ------------------------------- |
| LIVE01    | 활어차 |          2,000kg | 활어 · 수조/산소 공급 장비 가정 |
| LIVE02    | 활어차 |          2,000kg | 활어 · 수조/산소 공급 장비 가정 |
| COLD01    | 냉장차 |          3,000kg | 냉장                            |
| COLD02    | 냉장차 |          3,000kg | 냉동 설정 가능 차량을 가정      |
| GENERAL01 | 일반차 |          1,000kg | 일반                            |

`vehicleClass`는 차종, `supportedItemTypes`는 품목 설정입니다. 이 값은 시연용 장비/가용 적재량 가정이며 실차 제원이 아닙니다. 실제 TMS 코드에는 활어 전용 코드가 없어 `99`(기타)로 표현했습니다. 냉장·냉동은 모두 `02`로 표현되므로 세부 호환성은 `supportedItemTypes`와 `itemType`을 함께 사용해야 합니다.

## 주소·지오코딩 검증

**최종 지점 20/20곳과 센터 1/1곳이 도로명·건물번호까지 일치하는 결과를 반환했습니다.** 조회일은 2026-09-11입니다.

성공 조건은 HTTP 200, `place_rank: 30`, 국가 `kr`, 도시 `서울특별시`, 구·도로명·건물번호가 입력 주소와 정확히 일치하는 것입니다. 도로 중심점이나 구 단위 결과, 장소명으로 대신 검색한 좌표는 성공으로 인정하지 않았습니다. 지오코딩 결과는 건물/주소에 연결된 OSM 객체의 대표 좌표이며 배송차량 출입구나 정차 지점의 측량 좌표가 아닙니다.

`geocoding_results.csv`에는 입력 주소, 매칭 주소, 위·경도, OSM 객체 ID, 요청 URL, 검증 시각, 원본 응답 JSON을 CSV 필드로 보관합니다. `npm run test:data`는 이 응답에서 건물번호를 다시 검사하고 센터·지점·주문 좌표와 대조합니다. 이 명령은 **저장된 실제 응답의 오프라인 재검증**이며 API를 재호출하지 않습니다.

최초 후보 중 목동동로 105, 학동로 426, 성내로 25, 창경궁로 17은 도로 대표점만 반환해 제외했습니다. 각각 목동동로 257, 압구정로 165, 천호대로 1005, 남대문로 81로 교체한 후 주소 일치를 확인했습니다.

주소 출처는 각 CSV의 `addressSource`에 있습니다.

- [노량진수산시장 공식 홈페이지](https://www.susansijang.co.kr/nsis/miw/ko/intro)
- [서울특별시 자치구 안내](https://www.seoul.go.kr/seoul/autonomy.do)
- [현대백화점 목동점](https://www.e-hyundai.com/newPortal/DP/DP000000_V.do?branchCd=B00142000), [압구정본점 안내](https://e-hyundai.com/newPortal/CS/CS006000_M.do), [천호점](https://www.ehyundai.com/newPortal/DP/WC/WC000000_V.do?branchCd=B00126000)
- [롯데백화점 공식 홈페이지](https://mw.lotteshopping.com/main)
- [광진구청의 자양로 117 주소 기록](https://www.gwangjin.go.kr/portal/bbs/B0000043/list.do?menuNo=200259&pageIndex=): 현재 청사 위치를 뜻하지 않으며 이 데이터에서는 실재 도로명 주소의 근거로만 사용했습니다.

지오코딩 데이터: **© OpenStreetMap contributors · ODbL 1.0**. [저작권/라이선스](https://www.openstreetmap.org/copyright), [Nominatim 이용 정책](https://operations.osmfoundation.org/policies/nominatim/). 이번 소량 일회성 검증은 식별 가능한 User-Agent, 단일 실행 흐름, 요청 간 1.15초 이상 간격과 응답 캐시를 적용했습니다. 이 공개 API를 앱의 일반 주소검색·자동완성 서비스로 연결하지 않았습니다. 재조회가 필요하면 제공자의 최신 정책을 확인해야 합니다.

## 검증 실행

```sh
npm run test:data
```

행 개수·ID 유일성·지점별 품목·단위·시간창·참조 관계·원본 지오코딩 응답·기존 `/orderList` 호환성을 검사합니다. 네트워크나 API 키가 필요하지 않습니다.
