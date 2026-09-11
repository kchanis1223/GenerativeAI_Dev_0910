# 협업 규칙

팀별 작업 경로, 검토 절차, 문서 작성 기준을 정리한다.

## 1. 브랜치

- `main` 에는 직접 push 하지 않는다. PR로만 들어간다.
- 작업 브랜치 이름: `feat/영역-내용` 또는 `fix/영역-내용`
  예) `feat/tools-geocode`, `feat/mw-retry`, `fix/agent-import`
- 이슈 하나 = 브랜치 하나 = PR 하나. 머지되면 브랜치는 지운다.

## 2. 폴더 소유

프론트(Vue)는 저장소 루트의 `src/`, 에이전트(Python)는 `agent/` 아래에 둔다. 담당 폴더에서 작업한다. 다른 담당자의 파일을 수정해야 하면 대상 파일과 사유를 PR 본문에 적어 요청한다.

| 폴더                                                                                                                                      | 담당   |
| ----------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `src/`, `tests/`, `public/`, `index.html`, vite·eslint 설정 (프론트)                                                                      | 가니 |
| `agent/badaro/schemas/`, `agent/prompts/`                                                                                                 | 이준형 |
| `agent/badaro/tools/`, `agent/data/`, `docs/tms-api.md`, `docs/api/`                                                                      | 권유나 |
| `agent/badaro/middleware/`, `agent/badaro/guardrails/`                                                                                    | 윤소영 |
| `agent/tests/`                                                                                                                            | 가니 |
| `agent/badaro/agent.py`, `agent/requirements.txt`, `agent/pyproject.toml`, `agent/.env.example`, `README.md`, `docs/`(설계서), `.github/` | 김동찬 |

공용 파일(`agent.py`, `requirements.txt`, `pyproject.toml`, `.env.example`, `README.md`)에 추가할 내용은 PR 본문에 대상 위치와 함께 요청한다.

## 3. 작업 순서

```bash
git switch main && git pull
git switch -c feat/tools-geocode      # 이슈 하나당 하나
# ... 작업, 커밋 ...
git pull --rebase origin main         # PR 올리기 직전에 꼭
git push -u origin feat/tools-geocode
```

GitHub에서 PR을 만든다. 리뷰어 1명의 검토와 CI 통과 후 **Squash and merge**한다.

## 4. 커밋 메시지

`영역: 무엇을 (왜)` 한 줄. 이슈 번호가 있으면 뒤에 `#12`.

```
tools: geocode 결과 캐시 추가 (같은 주소 반복 호출 줄이려고) #8
schemas: priority 를 Literal 로 고정 (설계서 2.4) #5
```

다른 팀원이 변경 배경을 확인할 수 있도록 사유를 적는다.

## 5. PR

- PR은 한 작업 단위로 작성한다. 변경이 300줄을 넘으면 PR을 나눈다.
- PR 템플릿의 변경 내용·변경 이유·확인한 결과를 작성한다.
- 설계와 다르게 구현했으면 PR에 적고, `docs/` 설계서의 **문서 변경 이력** 표에도 한 줄 추가한다.
- 리뷰 요청은 30분 이내에 확인한다. 바로 검토할 수 없으면 예상 시간을 공유한다.

## 6. 하지 말 것

- `.env`, API 키 커밋. `.env.example` 에 키 이름만.
- 노트북 출력 셀 포함 커밋. 노트북은 `notebooks/자기이름/` 에만, 출력 지우고.
- 불필요한 실제 TMS 배차 요청(`/allocation`). 프로젝트에서 사용하는 한도는 **하루 20건**이다. 실호출은 권유나·김동찬만, 나머지는 `USE_MOCK=1` 또는 프론트 목업.
- `main` 직접 push, `git push --force`.

## 7. 충돌 났을 때

```bash
git pull --rebase origin main
# 충돌 파일 고치기 → git add <파일> → git rebase --continue
```

충돌을 해결하기 어려우면 해당 파일과 충돌 내용을 담당자에게 공유한다.

## 8. 문구 작성

문서·화면·이슈·PR은 실제 작업과 결과를 설명한다. 과장된 홍보 문구, 상투적인 도입과 요약, 불필요한 영문·수식어를 줄인다.

- 주체와 행동을 적는다. 기능 설명은 입력·처리·출력, 오류 안내는 원인·다음 행동을 중심으로 쓴다.
- 제안, 미정, 개발 중, 검증 완료를 구분한다. 완료 여부와 수치는 확인한 근거가 있을 때만 쓴다.
- API명·필드명·기술 용어·테스트 입력의 뜻은 유지한다. 사용자 발화와 팀원 댓글을 문체 수정 목적으로 바꾸지 않는다.
- 문맥에 맞는 짧은 문장을 쓴다. 같은 내용을 도입·본문·결론에서 반복하지 않는다.

| 수정 전                       | 수정 후                                        |
| ----------------------------- | ---------------------------------------------- |
| 물류의 흐름을 더 가볍게       | 센터·차량·배송지·배차 관리                     |
| 조회 과정을 한눈에 확인하세요 | 현재 탭에서 실행한 조회 결과와 오류 기록입니다 |
| 이것만 지키면 충돌 안 납니다  | 팀별 작업 경로와 검토 절차를 따릅니다          |

자동화 도구에도 같은 기준을 적용한다. 저장소의 `AGENTS.md`에 작업 지침을 둔다.
