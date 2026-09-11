# 노량진 배송 샘플 · B-04

배송일은 **2026-09-11 (Asia/Seoul)**입니다. 센터·지점은 실제 도로명 주소를
사용하며 지점명·차량·주문은 가상입니다. 해당 시설과 실제 납품 관계가 있다는 뜻은 아닙니다.

| 파일                   | 행 수 | 내용                                                   |
| ---------------------- | ----: | ------------------------------------------------------ |
| centers.csv            |     1 | 노량진센터                                             |
| branches.csv           |    20 | 서울의 서로 다른 주소, 지점 ID와 좌표                  |
| vehicles.csv           |     5 | 활어차 2·냉장차 2·일반차 1, 적재량과 지원 품목         |
| delivery_orders.csv    |    40 | 지점별 2건, 품목별 10건, 총 3,125kg                    |
| geocoding_results.csv  |    21 | 지점 20곳·센터 1곳의 저장된 Nominatim 응답             |
| geocoding_rejected.csv |     4 | 건물번호가 없는 도로 대표점 응답, 최종 데이터에서 제외 |

UTF-8 BOM·쉼표 구분 CSV입니다. `vehicleType`과 `openTime`·`closeTime`은
앞자리 0을 유지하는 문자열입니다. 주문 `deliveryWeight`는 kg, 차량 `weight`는 ton,
`maxLoadKg`는 kg, 부피는 m³, `serviceTime`은 분입니다.
`branchId`·`centerId`로 참조하며 한 주문 행은 한 품목입니다.

## Python 조회 Tool과의 연결

원본은 기존 Vue/TMS 필드명을 유지합니다. Python 모델에 CSV 행을 그대로 전달하면
검증에 실패합니다. [호환성·주소 검증 결과](validation-report.md)의 필드 매핑이 필요합니다.
PR #29가 병합된 main의 `Order`·`Vehicle` 모델을 고정 커밋에서 가져와 변환한 40건·5대를 검증합니다.
`get_delivery_orders`와 `get_available_vehicles`의 조회 로직 연결은 #10의 범위입니다.

- 주문 `priority=normal`을 명시했습니다. 차량 근무시간은 샘플 가정인
  `2026-09-11 06:00~18:00 +09:00`을 `shift_start`·`shift_end`에 명시했습니다.
- `closeTime`을 납품 마감 `deadline`으로 변환합니다. 희망시각
  `desiredDeliveryTime`과 시간창 시작 `openTime`은 원본에 보존합니다.
- `deliveryDate`·`centerId`는 조회 필터용입니다. Pydantic 모델에서 보존되지 않는
  필드는 원본 조회 계층에서 보관해야 합니다. 날짜가 자동으로 오늘로 바뀌지는 않습니다.
- 냉장차 2호는 냉동 설정이 가능한 차량으로 가정합니다. 활어차는 수조·산소 장비를
  가정하며, 적재량은 시연용 가용 화물 중량입니다. 실차 성능 검증은 아닙니다.

## 지오코딩 근거와 재현

원본 응답에서 도로명·건물번호·구·도시·국가·좌표를 대조합니다. 지점은 **20/20**,
센터는 **1/1** 일치합니다. 조회 시각·요청 URL·HTTP 상태·OSM ID·원본 JSON과
주소 출처는 `geocoding_results.csv`에 있습니다. 재검증은 저장된 응답을 사용하며
TMAP API 성공이나 차량 출입구 좌표 검증을 뜻하지 않습니다.

좌표는 주소에 해당하는 OSM 객체의 대표점입니다. 주소 출처는 각 CSV의
`addressSource`이며, 지오코딩 데이터는 © OpenStreetMap contributors · ODbL 1.0입니다.
[저작권](https://www.openstreetmap.org/copyright) ·
[Nominatim 정책](https://operations.osmfoundation.org/policies/nominatim/)

검증 코드 PR의 `agent/data/validate_samples.py`와 `agent/tests/test_sample_data.py`를
함께 적용합니다. 실행 명령과 모델 커밋은 검증 결과 문서에 기록합니다.

## 자동 검증

`python3 agent/data/validate_samples.py` 또는 `npm run test:data`는 CSV·저장된 주소 근거와
현재 체크아웃된 `agent/badaro/schemas/models.py`의 Order·Vehicle 모델을 함께 검사합니다.
Python 3.11 이상과 `agent/requirements.txt` 의존성이 필요합니다. 모델 파일이나 의존성이
없으면 실패하며, 기본 pytest도 모델 검증을 생략하지 않습니다. 별도 모델 비교는 `--models`로 지정합니다.
품목별 적재량은 `inputYn=1`인 차량만 합산합니다. 사용 불가 차량도 행 형식은 검증합니다.
