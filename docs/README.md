# 설계 및 개발 문서

[설계서 v1.1](6반_3조_설계서_v1.1.docx)은 설명 문구를 정리한 개정본입니다. 기능 요건과 테스트 기준은 유지했습니다. [초안 v1](6반_3조_설계서_v1.docx)은 원본이며 문서 내부 최신 변경 이력은 v0.2입니다.

## 문서별 용도

- 설계서: 사용자 시나리오, Structured Output, Tools, Context, Middleware, Guardrails, TS-01~12 테스트 기준.
- [CONTRIBUTING.md](../CONTRIBUTING.md): 실제 폴더 소유와 브랜치·PR 규칙.
- [프론트 가이드](frontend.md)와 [프론트 설계](design.md): 현재 Vue 화면의 실행 방법과 구현 범위.
- [TMS API 정리](tms-api.md): 24개 API 명세와 프론트 목업의 차이.
- `api/`: 담당자가 검증한 실제 요청·응답을 키 제거 후 보관할 위치. 아직 예시는 없음.

## 설계와 코드 연결

설계서 2.4의 `DispatchRequest`·`DispatchResult`는 `agent/badaro/schemas/`, 2.5의 네 Tool은 `agent/badaro/tools/`에서 구현합니다. 3.1~3.3의 Context·State·Store와 Middleware·Guardrails는 각 담당 패키지에 두고, PM이 `agent/badaro/agent.py`에서 통합합니다. 현재는 패키지 폴더만 준비되어 있으며 업무 로직은 없습니다.

초기 이슈의 `src/badaro/`와 루트 Python `tests/`는 최신 협업 규칙에 따라 각각 `agent/badaro/`, `agent/tests/`로 해석합니다. 루트 `src/`와 `tests/`는 Vue 전용입니다. 2026-09-11 PM 결정에 따라 #15는 기존 Vue 화면에 Python 에이전트를 연결합니다. 서버 호출 방식은 #15·#17에서 정합니다.

## 통합 전 확인할 항목

- 설계서 2.3: 메인·경량 모델명과 계정 사용 가능 여부.
- 설계서 2.4: 마감시간 기준 시간대, 활어·수조차 제약을 표현할 스키마. 현재 `storage_type`에는 활어 구분이 없음.
- 설계서 2.5: 주문·차량 데이터 공급원, TMS가 지원하는 보관·시간·인접 지역 제약.
- 설계서 3.1: 운영자 승인과 기사별 조회 권한을 실제 화면·인증에 연결하는 방식.

확인 전에는 해당 요구가 구현되거나 외부 API로 보장된다고 표시하지 않습니다. 설계 변경이 확정되면 원본 초안과 구분한 개정본 및 문서 변경 이력을 함께 반영합니다.
