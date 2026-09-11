# Badaro · 물류 워크스페이스

Vue 3 + TypeScript + Vite로 구현한 센터·차량·배송지 관리와 배차 흐름을 시연하는 프론트엔드입니다. 저장소를 clone한 폴더가 프로젝트 루트입니다.

## 실행

Node.js 22.12 이상(또는 Vite가 지원하는 최신 LTS)이 필요합니다. 이 프로젝트는 Node.js 26.7 환경에서 검증했습니다.

```sh
npm install
npm run dev
```

브라우저에서 http://127.0.0.1:5173 을 엽니다. 메인에서 바다로 로고를 누르면 바다가 양옆으로 갈라지며 줌 인한 뒤 8단계 배송 준비 화면으로 이동합니다. API 키 없이 센터·주문·차량을 선택하고 목업 배차를 실행할 수 있습니다.

## 메인 페이지와 라우터

- `/`: 물 표면 사진, 일렁이는 바다로 로고, 뛰어오르는 작은 물고기를 표시합니다. 로고가 진입 링크입니다.
- `/workspace`: 센터 선택부터 차량별 배송 상세까지 이어지는 8단계 배송 준비
- `/workspace/centers`: 기존 센터 조회·검색·상세 화면
- `/workspace/vehicles`: 차량·센터·권역·교차금지선 관리
- `/workspace/orders`: 배송지 관리
- `/workspace/dispatch`: `/workspace`로 이동하는 기존 주소 호환 경로
- `/workspace/api`: 24개 API의 필드·공식 예제·목업 실행
- `/workspace/flow`: 동작 흐름
- `/workspace/history`: 실행 기록

Vue Router로 URL, 뒤로가기, 직접 접속을 지원합니다. 정적 배포 서버에서는 `/workspace` 하위 경로를 `index.html`로 반환하는 SPA fallback 설정이 필요합니다.

`src/asset`의 물 표면 JPG를 배경으로 사용하며 SVG `feTurbulence`와 `feDisplacementMap`, CSS 이동으로 일렁임을 만듭니다. 시스템의 모션 감소 설정을 켜면 배경과 글자 애니메이션을 멈춥니다. 메인의 글꼴 설정은 `SSRO_WaterDrop_OTF_Regular.otf`를 유지하며, 나머지 화면·입력·버튼·연결 설정은 `src/asset/JayeonSans (1)/web/woff2`의 JayeonSans를 전역 적용합니다. 폰트는 로컬 `@font-face`로 불러옵니다.

## 구현 범위

- 센터명·주소·센터 ID 검색, 지역 필터, 센터 상세 보기
- API의 위도·경도를 활용한 선택 가능한 위치 개략도 (배경은 실제 지도 아님)
- 입력 → 조회 → 응답 검증 → 필터링 → 표시의 단계별 상태·로그
- 정상 / 빈 목록 / HTTP 401 / 타임아웃 / 손상된 응답 테스트
- 요청 미리보기, 원본 응답 JSON, 필터 적용 결과 JSON 다운로드
- 현재 세션의 최근 30개 실행 기록
- 모바일 대응, 키보드 센터 선택 및 연결 설정 다이얼로그
- 동일 출처 프록시를 통한 실제 API 호출 어댑터

현재 화면에서는 입력 검증, API 응답 처리, 오류 복구를 시연할 수 있습니다. 검색·검증·목업 배차는 TypeScript로 실행됩니다. LLM/LangChain 에이전트, 자연어 분석, 실제 TMS 배차, 지도 SDK, 백엔드 연결은 개발 예정입니다.

## 배송 준비 순서

1. 출발 센터 선택
2. 오늘 배송할 주문 등록/선택
3. 운행 가능한 차량 선택
4. 배차 조건 설정
5. 요청 전 선택 정보 확인 및 배차 요청
6. 계산 중 — 요청 키를 발급받아 결과 조회
7. 배차 결과 및 미배차 사유 확인
8. 차량별 배송 순서·예상시간·경로 확인

센터·주문·차량을 선택하지 않으면 다음 단계로 이동할 수 없습니다. 주문은 2단계 안에서 등록할 수 있고, 운행 제외 차량은 선택할 수 없습니다. 입력한 선택은 이전 단계 및 보조 메뉴 이동 후에도 유지됩니다. 선택 데이터가 삭제되거나 차량이 운행 제외로 변경되면 선택에서 제거하며, 이미 받은 결과는 초기화해 다시 요청하도록 안내합니다. 계산 중에는 중복 요청과 단계 이동을 막고, 실패 시 선택을 유지한 채 요청 확인 단계로 돌아옵니다.

선택한 센터의 좌표가 목업 배차 출발·복귀 계산에 반영됩니다. 공식 `/allocation` 필드에는 센터 ID가 없어, `centerId`는 API 요청 JSON이 아닌 별도의 목업 실행 정보로 전달하고 실행 기록에도 구분해 남깁니다. 실제 API 연결 시 센터 선택과의 대응 방식은 별도 확인이 필요합니다.

## 확장 목업

차량 6대·배송지 8곳·권역 3개·교차금지선 1개를 추가했습니다. 차량/배송지/권역은 단건 및 일괄 등록, 센터/교차금지선은 단건 등록을 지원하며 수정·삭제는 명세의 지원 범위를 따릅니다. API 탐색의 24개 실행 예제는 동일한 데이터를 사용합니다.

배차는 `allocation → mappingKey → allocationData`로 진행합니다. 차량 적재량(ton)과 배송 무게(kg)를 환산하고 차종·권역·적재 한도·투입 여부·교차금지선을 검사합니다. 결과에서 배송 순서, 예상 시간, 직선 경로, 미배차 이유를 확인할 수 있습니다. 데이터 변경은 현재 탭의 메모리에만 보관합니다.

[API별 명세·목업 정책·문서 예제의 차이](docs/tms-api.md)에 자세히 정리했습니다. 확장 API는 목업 전용입니다. 실제 최적화·도로 경로를 재현한 결과가 아닙니다.

## 실제 API 연결

참고: [SK TMS 센터 목록조회 명세](https://tms-skopenapi.readme.io/reference/센터-목록조회)

- 원본 API: `GET https://apis.openapi.sk.com/tms/centerList`
- 응답: `resultCode`, `resultCount`, `resultMessage`, `resultData`
- 센터: `centerId`, `centerName`, `address`, `latitude`, `longitude`, `seq`, `updateDate`
- 지역과 검색어는 명세의 요청 파라미터가 아니므로 응답을 받은 후 클라이언트에서 필터링합니다.

API 정보를 받으면 다음 부분을 연결하면 됩니다.

1. 서버에 `/api/tms/centerList` 같은 프록시 경로를 준비합니다.
2. 서버에서 앱 키를 주입해 원본 API를 호출하고 원본 JSON 응답을 반환합니다.
3. 앱의 **연결 설정 → 실제 API · 서버 프록시**에서 해당 경로를 적용하고 조회를 실행합니다.

현재 프록시 서버는 포함되어 있지 않습니다. 정적 페이지 서버에서 경로만 바꾸면 실제 연결이 되지는 않습니다. 프록시 장애 시 목업으로 자동 대체하지 않고 오류를 표시합니다. 실제 요청은 8초 후 중단하며, 자동 재시도 없이 사용자가 다시 실행할 수 있습니다.

문서에는 `appKey`가 query 파라미터와 header 보안 스키마 양쪽에 기재되어 있습니다. 제공받는 인증 방식으로 서버 구현 시 확정해야 합니다. 공개 문서의 샘플 키는 사용하지 않습니다. 앱 키를 `VITE_*` 환경 변수나 브라우저 저장소에 넣지 마세요. Vite의 공개 환경 변수는 브라우저 번들에 포함됩니다.

## 주요 파일

```text
src/App.vue                  RouterView
src/router/index.ts          메인·워크스페이스 라우트
src/views/LandingView.vue     Badaro 메인 페이지
src/views/WorkspaceView.vue   조회 화면과 실행 상태 관리
src/components/OceanTransition.vue 바다 분할·줌 전환
src/views/LogisticsView.vue    차량·배송지·배차·API 화면
src/components/TmsResources.vue 데이터 편집
src/views/DispatchWorkflowView.vue 8단계 배송 준비 화면
src/stores/dispatch-workflow.ts 선택·진행·계산·결과 세션 상태
src/components/DispatchRouteDetails.vue 차량별 배송 순서·시간·경로
src/components/TmsExplorer.vue API 예제 실행
src/stores/tms.ts             세션 데이터·API 로그
src/services/tms-mock.ts      CRUD·배차 목업 엔진
src/data/tms-api-catalog.json 24개 명세 필드·응답 예제
src/components/PageSteps.vue  카드 구간 이동 내비게이션
src/components/WaterSurface.vue 배경 사진과 일렁임 효과
src/components/CenterMap.vue  좌표 기반 위치 개략도
src/services/centers.ts       목업·실제 요청, 응답 검증, 필터링
src/data/centers.ts           명세 형태를 따른 예제 데이터 8건
src/types.ts                 API·실행 로그 타입
src/style.css                반응형 스타일
```

을지로센터는 API 문서 예제를 따르며 나머지는 가상의 시연용 데이터입니다. 실제 운영 현황을 뜻하지 않습니다. 최초 조회 시간은 실제 API 성능 수치가 아니라 목업 지연과 화면 단계 전환 시간을 합한 값입니다. 폰트는 외부 요청 없이 로컬 에셋으로 제공하며, 로딩 중에는 시스템 폰트로 표시합니다.

## 검증 명령

```sh
npm run lint
npm run format:check
npm run test
npm run build
npx playwright install chromium
npm run test:e2e
```

단위 테스트는 응답 검증·검색·프록시 실패·실제 요청 중단을, 브라우저 테스트는 조회·선택·오류 복구·JSON 출력·프록시 연결 UI·모바일을 검증합니다. 브라우저 테스트의 프록시 응답은 Playwright로 대체하며 SK API의 실제 인증·통신을 검증한 것은 아닙니다.

## 로고

바다로 로고의 투명 PNG는 `src/asset/badaro-logo.png`에 있습니다. 공통 `BadaroLogo.vue` 컴포넌트로 메인·헤더·푸터에 표시하며, `public/favicon.png`도 같은 이미지에서 만듭니다.

로고는 2042×690 RGBA PNG입니다. 청록색 로고와 내부 파도 무늬를 남기고 배경을 투명하게 처리했습니다. 추출 과정은 선택적 개발 도구인 `scripts/extract-logo.py`에 기록했습니다(Pillow·NumPy·SciPy 필요, 앱 실행에는 불필요).

메인의 물고기 효과는 `src/components/JumpingFish.vue`에서 SVG와 CSS로 구현합니다. 데스크톱 3마리·모바일 2마리가 시차를 두고 두 번씩 뛰어오르며 꼬리·물방울·착수 물결이 함께 움직입니다. 장식 요소는 클릭을 가로채지 않고, 모션 감소 설정에서는 숨기며 탭이 비활성화되면 일시 정지합니다.
