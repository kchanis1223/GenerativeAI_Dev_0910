# v2 설계와 코드 대조

2026-09-11 · #21. PM이 수정한 v2를 기준으로 현재 실행 경로와 산출물을 대조했다. 사용자 수정 원문은 `archive/6반_3조_설계서_v2_사용자수정본.docx`에 보관했다. 현재 기준은 `6반_3조_설계서_v2.docx`다.

## 현재 연결

| 설계 항목 | 실제 코드와 동작 |
| --- | --- |
| 조건 추출 | `runtime/contracts.py`의 RequestDraft → `schemas/models.py`의 DispatchRequest. product_names 포함, 차량 수는 선택값 |
| 결과 | DispatchResult를 Tool에서 만들고 AgentReply로 반환. LLM 결과 설명·재생성 없음 |
| Tool 4개 | `runtime/tools.py`에 등록. 업무 데이터는 Command로 State와 ToolMessage에 반영. `tools/optimize_dispatch.py`의 공개 함수는 계약용 인터페이스이고 execute_optimize_dispatch가 실제 구현 |
| 미들웨어 6개 | `runtime/graph.py`: input_validation → dispatch_context → budget → require_tool → validate_calls → execute_tool. 각 Hook에서 실행 |
| Context·State | RunContext·RunState, thread_id별 메모리 Session. 기존 BadaroContext·BadaroState를 확장. Store·권한·재배차는 미연결 |
| 재시도 | 조회의 일시 오류만 최대 3회. TMS 정상 대기 응답은 기본 30회·1초 간격. HTTP별 timeout 10초. 배차 접수 자동 재전송 없음 |
| 결과 검증 | 부적합 경로는 upstream_error로 종료. 경로에 없는 주문은 not_assigned. 구체적인 원인·ETA를 만들지 않음 |
| 지도 | AgentReply.map_data → `src/services/agent-map.ts` → DeliveryMap. 확정 좌표를 방문 순서대로 점선 연결 |
| 모델·키 | gpt-5.4-mini 연결 확인. MAIN_MODEL로 설정. TMAP_APP_KEY와 TMS_APP_KEY는 서버에서 관리 |

`runtime-contract.json`은 Tool 공개 인자, 등록 미들웨어, 모델 필드 목록이다. `python scripts/check_design.py`는 코드·이 목록·DOCX의 Tool/미들웨어/요청·결과 필드를 CI에서 대조한다. 내용이 바뀌면 설계서를 검토한 뒤 `--write`로 목록도 갱신한다. 설명·그림·검증 실적까지 자동 판정하는 검사는 아니다.

## 4.2 테스트 대응

기존 Python 함수명의 M01~M08은 이력 추적을 위해 유지한다. 문서에서는 중복되었던 IT 번호를 시나리오별 고유 케이스 ID로 정리했다. 아래 M 테스트는 `agent/tests/test_agent_integration.py`에 있다.

| 문서 케이스 | 자동 테스트 | 확인 범위 |
| --- | --- | --- |
| IT-01-C01 | test_M01_csv_to_dispatch_and_no_duplicate_send | CSV부터 결과·지도 데이터, 같은 요청 중복 접수 방지 |
| IT-02-C01 | test_M02_missing_date_continues_same_request_without_optional_vehicle_count | 같은 요청의 날짜 보완, 선택값 미지정 |
| IT-02-C02 | test_M03_ambiguous_address_stops_then_resumes_with_confirmed_correction | Mock 모호 주소 중단·보완 후 재개 |
| IT-03-C01 | test_M04_incompatible_vehicle_stops_before_dispatch | 부적합 차량 중단. 합계 적재량은 test_tools.py에서 별도 검사 |
| IT-04-C01 | test_M05_timeout_is_not_resent_and_secrets_are_masked | 접수 1회·오류 보존·마스킹. test_tools.py의 bounded polling 검사 포함 |
| IT-03-C02 | test_M06_partial_result_and_missing_eta_are_preserved | 부분 배차·ETA 누락. Vue agent-chat E2E에서 표시·지도 제외 확인 |
| IT-05-C01 | test_M07_key_request_is_blocked_before_model_or_tools | 모델·Tool 전 입력 차단. 마스킹 검사는 가짜 키 사용 |
| IT-05-C02 | test_M08_forbidden_tool_args_stop_before_execution | endpoint·header·appKey·runtime_context 등 직접 인자 주입 차단 |

실제 LLM + 합성 Mock으로 3개 지점·6건·4대 결과와 날짜 재질문을 확인했다. 실제 TMAP·TMS·Vue 검증은 은평 상온 주문 1건, GENERAL01, 2026-09-12 ETA 06:25와 점선·마커 표시다. 실행 내역은 [Agent 안내](agent-integration.md)의 실연동 기록을 따른다. 4.2의 8개 문장을 실제 API에서 모두 통과했다는 뜻은 아니다.

## 남은 확인과 MVP 범위

- 전체 40건 실배차, 냉장·냉동(TMS 유형 02)의 전용 차량 구분, 소수 부피의 TMS 예약값 대조는 남아 있다. 실제 시연은 별도 CSV와 TMS 등록 데이터를 맞춰 수행했다.
- vehicle_count는 가용 CSV의 앞 N대를 제한한다. 모든 품목을 운송할 최적 차량 조합을 선택하지 않는다. 전체 40건·4대 성공 예시는 현재 검증 실적으로 사용하지 않는다.
- 주소 보완은 현재 요청 State에 적용한다. TMS 마스터 주소·좌표를 자동 수정하지 않으므로 실제 배차 전 담당자가 일치를 확인해야 한다.
- priority는 보관하지만 TMS 옵션은 고정이다. 긴급도별 최적화·실제 도로 경로는 검증하지 않았다.
- 키·인젝션 정규식은 지정 패턴만 처리한다. 응답 전체 PII 제거, 모든 우회 표현 차단, 현재 로컬 시연 서버의 차단 로그 영구 저장은 확인하지 않았다.
- Session은 메모리 전용이다. 재시작·새 대화 간 배차 중복 방지, 인증·기사 권한, 장기 Store, 재배차는 MVP 밖이다.

남은 통합 검증은 #20에서 추적한다. #21의 완료는 현재 문서와 실행 계약의 일치를 뜻하며 위 기능의 구현 완료를 뜻하지 않는다.

## 이번 대조의 검사 결과

Python 187개, Vue 단위 53개, 브라우저 14개, Ruff·ESLint·빌드·설계 계약 대조를 통과했다. 브라우저의 별도 offline 서버 통합 1개는 제외했으며 Python의 실제 로컬 HTTP 테스트는 통과했다. 이번 대조에서는 외부 배차를 추가 실행하지 않았다. DOCX 21쪽을 렌더링해 검토했다.

## 최종 제출 보완

README에 새 환경의 설치·키 설정·CSV 날짜 생성·TMS 등록·Vue 실행 순서를 정리했다. `manual-tests.md`는 4.2 원문과 현재 날짜용 입력을 구분한다. 9월 11일~18일 주문 320건·차량 5대·센터·권역의 등록값 327건은 새 등록 도구로 재조회 대조했다. 이는 전체 주문의 실배차 성공을 뜻하지 않는다.

등록 도구의 읽기 대조·기존 값 충돌·추가 후 재조회·재실행·통신 실패 검사를 포함해 Python 191개가 통과했다. 고정 날짜 Mock 서버의 실제 HTTP 연결로 날짜 재질문 후 주문 6건·차량 4대·미배정 0건을 확인했다. 실제 배차는 추가 호출하지 않았다.

Vue 단위 53개·lint·빌드와 브라우저 15개도 통과했다. 브라우저 검사는 사용 중인 실제 서버를 유지하기 위해 임시 프록시의 별도 포트에서 수행했으며, 고정 날짜 Mock 서버로의 재질문·배차 결과 수신 1개를 포함한다. 최종 DOCX 21쪽을 렌더링해 확인했다.
