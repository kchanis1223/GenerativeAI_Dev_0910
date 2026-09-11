# 본사 배차 Agent 실행

v2의 본사 물류 운영자 요청을 처리한다. 점주 탭, 기사 대화, 재배차, 파일 업로드, 별도 분류 모델, 장기 Store, LLM의 결과 재작성은 등록하지 않는다.

## 설치와 키 없는 시연

Python 3.11 이상에서 저장소의 `agent/`로 이동한다.

```sh
python -m pip install -r requirements.txt
USE_MOCK=1 MODEL_MODE=offline python -m badaro.agent '2026-09-11 마포 서대문 은평 배차해줘'
USE_MOCK=1 MODEL_MODE=offline python -m badaro.agent
```

두 번째 명령은 대화형이다. `마포 서대문 은평 배차해줘`를 입력하면 배송일을 묻는다. `2026-09-11`로 답하면 같은 요청으로 이어간다. 생략한 차량 수는 오류로 처리하지 않는다. 출발 시각을 따로 입력하지 않으면 현재 센터의 시연 시작 시각인 06:00을 사용한다.

`offline`은 날짜·지점·차량 수 예시를 읽는 대체 모델이다. 자유로운 자연어 이해를 검증하는 모드가 아니다. 시간·제외 조건 등 지원하지 않는 입력은 처리하지 않으며 자유 입력 검증에는 아래 OpenAI 모드를 사용한다.

## 실행 모드

| MODEL_MODE | USE_MOCK | 동작 |
|---|---|---|
| offline | 1 | 외부 호출 없이 시연용 입력 해석과 LangChain Tool 흐름 실행 |
| openai | 1 | 같은 OpenAI 모델로 조건 추출·Tool 선택, 배차는 합성 Mock |
| openai | 0 | OpenAI와 실제 TMAP·TMS Tool 호출 |

OpenAI 모드는 서버에 `OPENAI_API_KEY`와 사용 가능한 `MAIN_MODEL`을 설정해야 한다. 모델명은 임의로 확정하지 않는다. `USE_MOCK`는 TMAP·TMS 전환이며 OpenAI 요금 발생 여부를 결정하지 않는다. `MODEL_MODE=offline`만 모든 외부 모델 호출을 생략한다.

실제 모드는 `TMAP_APP_KEY`가 필요하며, 담당자가 마스터 등록값과 현재 요청 데이터의 일치를 확인한 뒤 `TMS_MASTER_VERIFIED=1`로 실행한다. 기본값 0에서는 실제 배차를 중단한다. 이 설정은 검증을 자동 수행하지 않는다. 실제 호출과 한도 확인은 #19에서 진행한다.

설정은 시작 시 읽는다. 실행 중 모드나 키를 바꾸려면 서버를 재시작한다. 조회 오류는 초회 이후 최대 3회 재시도하고 배차는 자동 재전송하지 않는다. `MAX_TOOL_ITERATIONS`는 **조건 추출을 포함한 요청별 모델 호출 수**로, 최대 6이다. SDK의 숨은 재시도는 끈다. TMS 폴링 횟수와 통신 재시도 횟수는 별도 제한이다.

## 시연 데이터의 출처와 범위

- 원본 `agent/data/`는 변경하지 않는다. 설치 패키지에는 동일한 CSV를 포함하고 사본 일치를 테스트한다.
- `agent/badaro/runtime/demo.json`은 **합성 시연 응답**이다. CENTER-NR, 2026-09-11 06:00, S01·S02·S03 주문 6건, 기존 가용 차량 5대 요청에만 대응한다. 반환 경로는 4대에 배정된다.
- 좌표는 기존 CSV에서 가져왔다. 실제 TMAP 응답이나 TMS 최적화 결과라고 표시하지 않는다. ETA·거리·소요시간은 제공하지 않으며 생성하지 않는다.
- 다른 요청은 응답을 조작해 맞추지 않고 저장 응답 없음으로 중단한다. 실제 시연용 응답 확보와 대조는 #19에 남아 있다.
- PR #40의 B-02 실응답 재생 어댑터는 그대로 유지한다. 이번 합성 시연 데이터와 출처가 다르다.

## 로컬 API와 Vue 연결 계약

```sh
USE_MOCK=1 MODEL_MODE=offline python -m badaro.server --port 8000
```

서버는 `127.0.0.1`에만 바인딩한다. 운영 인증 서버가 아니라 로컬 시연용이다. Vue 개발 서버의 `http://localhost:5173`과 `http://127.0.0.1:5173`만 CORS를 허용한다. 기존 Vue 화면에 버튼과 결과 표시를 연결하는 작업은 #15에 남아 있다.

`GET /health`는 상태와 실행 모드를 반환한다. `POST /api/chat`은 다음 JSON을 받는다. 클라이언트는 모델·키·역할·runtime_context·실행 모드를 지정할 수 없다.

```json
{"message":"마포 서대문 은평 배차해줘"}
```

응답의 `thread_id`를 사용해 재질문에 답한다.

```json
{"message":"2026-09-11","thread_id":"서버가 발급한 UUID"}
```

응답 필드는 `thread_id`, `request_id`, `mode`, `status`, `message`, `questions`, `request`, `result`, `error`, `model_calls`다. Python 타입은 `AgentReply`다.

- `needs_clarification`: questions를 보여주고 같은 thread_id로 답한다.
- `completed`: result의 status·routes·unassigned_orders를 직접 표시한다. completed는 요청 처리 종료를 뜻하며, result.status가 partial 또는 failed일 수도 있다.
- `blocked`·`error`: message와 error를 표시하고 자동으로 새 배차를 실행하지 않는다.
- result의 ETA가 null이면 미제공으로 표시한다. mode가 offline 또는 llm_mock이면 합성 Mock임을 표시한다.

새 배차는 thread_id 없이 시작한다. 완료된 thread_id로 재전송하면 저장한 응답만 반환한다. 세션은 서버 메모리에만 보관하며 재시작하면 사라진다. 없는 thread_id를 새 배차로 바꾸지 않고 missing_context 오류를 반환한다.

## 검증과 구현 참고

`cd agent && python -m pytest`로 기존 테스트와 M01~M08 통합 테스트, 실제 로컬 HTTP 테스트, 저장소 밖 wheel 설치 테스트를 실행한다. 테스트는 실제 LLM·TMS를 호출하지 않는다. 모델 호출 상한, 요청 분리, 모호한 주소 보완, 배차 중복 실행 방지와 금지 Tool 인자를 포함한다.

[LangChain ToolRuntime·Command](https://docs.langchain.com/oss/python/langchain/tools)로 서버 State를 주입한다. [미들웨어 종료 분기](https://docs.langchain.com/oss/python/langchain/middleware/custom)로 오류와 호출 상한에서 멈춘다. 조건 추출은 [OpenAI 구조화 출력의 strict 규칙](https://developers.openai.com/api/docs/guides/function-calling#strict-mode)을 사용하는 동일 모델에서 처리한다.
