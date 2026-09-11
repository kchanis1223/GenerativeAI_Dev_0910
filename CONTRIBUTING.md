# 협업 규칙

하루짜리 프로젝트라 규칙은 최소한만. 이것만 지키면 충돌 안 납니다.

## 1. 브랜치

- `main` 에는 직접 push 하지 않는다. PR로만 들어간다.
- 작업 브랜치 이름: `feat/영역-내용` 또는 `fix/영역-내용`
  예) `feat/tools-geocode`, `feat/mw-retry`, `fix/agent-import`
- 이슈 하나 = 브랜치 하나 = PR 하나. 머지되면 브랜치는 지운다.

## 2. 폴더 소유

프론트(Vue)는 repo 루트의 `src/`, 에이전트(Python)는 `agent/` 아래에 둔다. 자기 폴더만 고친다. 남의 폴더를 고쳐야 하면 PR 본문에 적어서 요청한다.

| 폴더 | 담당 |
|---|---|
| `src/`, `tests/`, `public/`, `index.html`, vite·eslint 설정 (프론트) | 김강휘 |
| `agent/badaro/schemas/`, `agent/prompts/` | 이준형 |
| `agent/badaro/tools/`, `agent/data/`, `docs/tms-api.md`, `docs/api/` | 권유나 |
| `agent/badaro/middleware/`, `agent/badaro/guardrails/` | 윤소영 |
| `agent/tests/` | 김강휘 |
| `agent/badaro/agent.py`, `agent/requirements.txt`, `agent/pyproject.toml`, `agent/.env.example`, `README.md`, `docs/`(설계서), `.github/` | 김동찬 |

공용 파일(`agent.py`, `requirements.txt`, `pyproject.toml`, `.env.example`, `README.md`)에 뭔가 추가해야 하면 직접 고치지 말고 PR 본문에 "이 줄 추가해 주세요"로 남긴다.

## 3. 작업 순서

```bash
git switch main && git pull
git switch -c feat/tools-geocode      # 이슈 하나당 하나
# ... 작업, 커밋 ...
git pull --rebase origin main         # PR 올리기 직전에 꼭
git push -u origin feat/tools-geocode
```

그다음 GitHub에서 PR. 리뷰어 1명 + CI 초록이면 **Squash and merge**.

## 4. 커밋 메시지

`영역: 무엇을 (왜)` 한 줄. 이슈 번호가 있으면 뒤에 `#12`.

```
tools: geocode 결과 캐시 추가 (같은 주소 반복 호출 줄이려고) #8
schemas: priority 를 Literal 로 고정 (설계서 2.4) #5
```

"왜"가 없으면 나중에 아무도 이유를 모릅니다. 짧아도 꼭 적습니다.

## 5. PR

- 작게, 자주. 한 PR이 300줄 넘으면 쪼갠다.
- 템플릿 세 칸(무엇을 / 왜 / 확인한 것)만 채우면 된다.
- 설계와 다르게 구현했으면 PR에 적고, `docs/` 설계서의 **문서 변경 이력** 표에도 한 줄 추가한다.
- 리뷰 요청 받으면 30분 안에 본다. 막히면 바로 채팅.

## 6. 하지 말 것

- `.env`, API 키 커밋. `.env.example` 에 키 이름만.
- 노트북 출력 셀 포함 커밋. 노트북은 `notebooks/자기이름/` 에만, 출력 지우고.
- 실제 TMS 배차 요청(`/allocation`) 남발 — **하루 20건 한도**. 실호출은 권유나·김동찬만, 나머지는 `USE_MOCK=1` 또는 프론트 목업.
- `main` 직접 push, `git push --force`.

## 7. 충돌 났을 때

```bash
git pull --rebase origin main
# 충돌 파일 고치기 → git add <파일> → git rebase --continue
```

무슨 충돌인지 모르겠으면 건드리지 말고 파일명을 채팅에 올린다. 5분이면 같이 풉니다.
