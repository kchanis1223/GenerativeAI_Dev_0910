# 설계 및 개발 문서

현재 기준은 [설계서 v2](6반_3조_설계서_v2.docx)다. 2026-09-11 PM 수정 문서를 반영하고 #21에서 현재 코드와 대조했다. [사용자 수정 원본](archive/6반_3조_설계서_v2_사용자수정본.docx)은 별도 보관한다.

## 문서별 용도

| 문서 | 내용 |
| --- | --- |
| [v2 설계와 코드 대조](design-code-review.md) | 실제 연결 위치, 4.2의 8개 테스트 대응, 검사 결과, 남은 확인 |
| [Agent 실행 안내](agent-integration.md) | offline·LLM Mock·실제 API 실행, 서버 설정, Vue 연결과 시연 기록 |
| [프론트 가이드](frontend.md) / [화면 설계](design.md) | Agent 채팅·점선 지도와 별도 프론트 목업 |
| [TMS API 목업](tms-api.md) | 24개 프론트 목업 API의 필드와 계산 범위 |
| [실제 API 첫 호출](api/README.md) | B-02 당시의 인증·요청·응답 기록과 저장 응답 재생 |
| [데이터 안내](../agent/data/README.md) | 주문·차량 CSV와 검증 방법 |
| [협업 규칙](../CONTRIBUTING.md) | 폴더 소유와 브랜치·PR 절차 |

## 변경 시 확인

`python scripts/check_design.py`로 Tool 공개 인자·등록 미들웨어·스키마 필드를 코드 및 DOCX와 대조한다. `runtime-contract.json`은 이 검사의 기준 목록이다. 설명·도식·검증 범위는 함께 검토하고 설계서 변경 이력에 날짜·사유를 기록한다.

배차 자동 재전송, LLM 결과 재생성, 점주·기사 권한, 재배차는 이번 구현에 추가하지 않았다. 전체 40건 실배차와 차량 유형·TMS 등록값 대조는 [남은 확인](design-code-review.md#남은-확인과-mvp-범위)을 따른다.

## 이전 기록

이전 설계서 DOCX와 초기 PDF는 [정리 전 Git 이력](https://github.com/kchanis1223/GenerativeAI_Dev_0910/tree/208ef80/docs)에서 확인한다. 현재 폴더에는 v2와 사용자 수정 원본을 보관한다. [v1 대조 기록](archive/design-notes-v1.md)의 미구현·미정 표시는 당시 상태이며 현재 완료 여부로 사용하지 않는다.
