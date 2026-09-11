# v1 설계 대조 기록

아래는 v1 시점의 기록이며 현재 구현 기준이 아니다. 현재 기준은 [문서 안내](../README.md)를 따른다.

## v1.2 반영 범위

이슈 #14에 첨부된 윤소영의 3장 v2 제안 중 기존 개발에 필요한 기준을 반영했습니다. 원본 제안과 구현 상태는 [이슈 #14](https://github.com/kchanis1223/GenerativeAI_Dev_0910/issues/14)에서 확인합니다.

- 기존 미들웨어 6종과 가드레일 5종을 유지합니다. Context에는 user_id, request_id, now_kst, resolved_locations를 추가합니다.
- 모델 응답 후 Tool 실행을 판단하는 순서와 after_* 역순 실행을 명시합니다. 결과 검증과 마스킹이 최종 출력에 적용되는지 통합 테스트로 확인합니다.
- 가용 차량 목록이 아닌 실제 TMS 배차 결과의 차량·방문 순서·시간·미배정을 대조합니다. Tool 결과가 기준이며 LLM은 설명만 생성합니다.
- 업무 처리용 원본 주소와 모델·출력·로그용 보호 데이터를 분리합니다. 서버 인증을 기준으로 기사별 조회 범위를 제한합니다.
- State 조회 실패와 신규 요청을 구분하고, 재시도 종료 후 오류 원인을 보존합니다. 주입·오류 계약은 v1.3에서 확정했으며 #11·#13·#17에서 실제 연결합니다.
- 후보 차량 적합성 검사와 TMS 결과 수신 후 검사를 구분합니다. #9는 데이터 검증, #14는 LLM 설명과 정보 노출 검증을 담당합니다.
- 승인 Tool·확정 저장·감사 이력·파일 처리·공용 일일 쿼터와 캐시·새 운영 수치는 별도 합의 사항입니다. 기존 호출 상한과 권한 요구는 유지합니다.

1·2·4장과 기존 테스트 ID는 유지했습니다. #9·#11~#14·#17·#21에 세부 확인 항목을 연결했으며, 이번 변경은 구현 완료를 의미하지 않습니다.

## v1.3 반영 범위

- `DispatchRequest` 필드와 기본값, `DispatchResult.status/routes/unassigned_orders`, 내부 보조 타입을 코드와 맞췄습니다. 배차 결과는 Tool이 생성하며 LLM은 설명합니다.
- 공개 `optimize_dispatch` 입력은 `order_ids`, `vehicle_ids`, `constraints`입니다. 서버가 `DispatchRuntimeContext`를 내부 `execute_optimize_dispatch`에 주입합니다. 내부 함수는 추가 Tool로 등록하지 않습니다.
- State는 `orders`(주문 ID), `vehicles`(차량 ID), `geocodes`(입력 주소)를 키로 보관합니다. v1.2의 `resolved_locations`는 `geocodes`로 통일했습니다. `ok` 상태에 후보가 1개인 결과만 배차에 사용합니다.
- 센터 ID와 출발 좌표는 서버가 `depot_profile`에서 확인합니다. `ToolErrorException.error`를 공통 오류로 전달하고 재시도는 실행 계층에서 처리합니다.
- 테스트 21개와 Ruff를 통과했습니다. State 저장·주입·재시도·API 호출은 #9·#11·#13·#17에서 구현·검증합니다. 이전 1·4장과 미들웨어·가드레일 요구는 유지합니다.
