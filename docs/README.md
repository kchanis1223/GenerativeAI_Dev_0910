# 설계 및 개발 문서

[설계서 v1.3](6반_3조_설계서_v1.3.docx)가 현재 기준입니다. 2.4·2.5·3.1에 B-03의 스키마·Tool·State 계약을 반영했습니다. [v1.2](6반_3조_설계서_v1.2.docx)는 미들웨어·가드레일 기준, [v1.1](6반_3조_설계서_v1.1.docx)은 설명 문구를 정리한 이전 개정본입니다. [초안 v1](6반_3조_설계서_v1.docx)도 보관합니다.

## 문서별 용도

- 설계서: 사용자 시나리오, Structured Output, Tools, Context, Middleware, Guardrails, TS-01~12 테스트 기준.
- [CONTRIBUTING.md](../CONTRIBUTING.md): 실제 폴더 소유와 브랜치·PR 규칙.
- [프론트 가이드](frontend.md)와 [프론트 설계](design.md): 현재 Vue 화면의 실행 방법과 구현 범위.
- [TMS API 정리](tms-api.md): 24개 API 명세와 프론트 목업의 차이.
- [실제 API 호출 예시](api/README.md): TMAP 주소 변환과 TMS 배차 요청·결과 조회 예시, 인증 방식, 단위·옵션 설명.

## 설계와 코드 연결

설계서 2.4의 `DispatchRequest`·`DispatchResult`는 `agent/badaro/schemas/`, 2.5의 네 Tool은 `agent/badaro/tools/`에서 구현합니다. 3.1~3.3의 Context·State·Store와 Middleware·Guardrails는 각 담당 패키지에 두고, PM이 `agent/badaro/agent.py`에서 통합합니다. 공통 Pydantic 모델과 네 공개 Tool 스텁, 내부 배차 데이터 검사가 있습니다. 실제 API 호출과 State·Agent 연결은 후속 작업입니다.

초기 이슈의 `src/badaro/`와 루트 Python `tests/`는 최신 협업 규칙에 따라 각각 `agent/badaro/`, `agent/tests/`로 해석합니다. 루트 `src/`와 `tests/`는 Vue 전용입니다. 2026-09-11 PM 결정에 따라 #15는 기존 Vue 화면에 Python 에이전트를 연결합니다. 서버 호출 방식은 #15·#17에서 정합니다.

## 통합 전 확인할 항목

- 설계서 2.3: 메인·경량 모델명과 계정 사용 가능 여부.
- 설계서 2.4: `StorageType.live`를 포함한 보관 조건과 차량 지원유형의 실제 검증. 시각은 Asia/Seoul 기준으로 해석합니다.
- 설계서 2.5: 주문·차량 데이터 공급원, TMS가 지원하는 보관·시간·인접 지역 제약.
- 설계서 3.1: 운영자 승인과 기사별 조회 권한을 실제 화면·인증에 연결하는 방식.

확인 전에는 해당 요구가 구현되거나 외부 API로 보장된다고 표시하지 않습니다. 설계 변경이 확정되면 원본 초안과 구분한 개정본 및 문서 변경 이력을 함께 반영합니다.

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
