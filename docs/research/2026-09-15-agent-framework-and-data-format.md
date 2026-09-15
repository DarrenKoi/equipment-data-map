# 에이전트 프레임워크와 데이터 형식 조사 — 2026-09-15

기준 commit은 `17c66c9`다. 질문은 "이런 일에 에이전트를 어떻게 만드는 것이 최선인가,
`langchain` `create_agent` 같은 라이브러리를 써야 하는가, 나중에 팀원에게 서비스할 때
사람이 읽는(llm-wiki·Obsidian식) 데이터 형식은 무엇이 최선인가"이며, 이후 세 가지가
추가됐다: (A) 워크플로형 에이전트 구성, (B) Markdown 파일을 코드에 연결하는 법,
(C) `create_agent` 자체의 판정, (D) 위키를 prior로 쓰는 반복 정제 루프.
1차 출처(공식 문서, GitHub 소스, 명세, 논문)만 근거로 삼았고 확인하지 못한 항목은
`[미검증]`으로 표시했다. 저장소 쪽 근거는 `docs/architecture/equipment-data-map.md`
(이하 스펙)와 `spike.py`다.

## 결론/권고

1. **지금(장비 데이터 파싱)은 프레임워크 없이 간다.** 스펙 §4.6은 LLM에게 필드 하나씩
   짧은 평문을 묻고 코드가 검증·조립하며, LLM에 도구를 주지 않는다고 못 박는다. 이것은
   Anthropic이 말하는 "predefined code paths"의 **workflow**이지 "LLM이 스스로 도구
   사용을 결정하는" agent가 아니다[1]. 두 회사의 1차 지침 모두 "가장 단순한 해법에서
   시작하고 필요할 때만 복잡도를 올려라"[1], "결정론적 해법으로 충분하면 그것을 써라"[2]고
   말한다. 이 일에서 `create_agent`가 주는 것(도구 호출 루프, 미들웨어, 구조화 출력
   전략)은 스펙이 금지하거나 파일로 이미 정한 것과 겹친다(§2, §C).
2. **HTTP 클라이언트는 `requests` 하나로 충분하다.** proxy 전송이 이미 `requests`를
   요구하고 `spike.py`가 그것으로 `/v1/chat/completions`를 부른다. `openai` 공식
   클라이언트조차 `httpx2`·`pydantic`·`jiter` 등 6개 의존을 끌고 온다[15]. 사내 미러에
   올릴 wheel 수를 늘릴 이유가 없다.
3. **워크플로 형태(A)는 "plain Python + `work/llm.sqlite` + `audit.jsonl`"이 스펙과
   접착이 가장 적다.** LangGraph `StateGraph`는 같은 것을 표현할 수 있지만, interrupt
   재개 시 노드를 처음부터 재실행하고[23] 체크포인트가 자체 `SqliteSaver`(별도 패키지,
   `ormsgpack` Rust 확장 포함)[24][25]에 들어가므로, 스펙의 `audit.jsonl`이 단일 진실
   원천이라는 규칙(§5.1)과 저장소가 둘로 갈라진다. `create_agent`는 워크플로 DSL이
   아니라 "모델이 도구를 루프에서 부르는" 고정 그래프이고, 미들웨어 훅은 그 루프의
   전후에만 걸린다[22][26].
4. **Markdown↔코드 경계(B)는 "md는 구조화 데이터에서 렌더링한 사람용 뷰"로 고정한다.**
   스펙 §3이 이미 `data-map/`의 canonical JSON을 기준으로, `wiki/`를 파생물로 정했다.
   에이전트 지시용 md는 네 도구가 모두 읽는 Agent Skills 표준(`SKILL.md`)과
   `AGENTS.md`/`CLAUDE.md`로 연결하고[28]–[34], 코드가 md를 **파싱해서 결정을 내리는
   경로는 만들지 않는다**. 예외는 §6의 `review/` 사람 주석 파일 하나다.
5. **`create_agent`(C)는 "나중, 팀원용 대화 서비스"에서만 후보다.** 정확한 시그니처와
   반환형은 §C에 있다. 의존 트리는 약 25개 패키지, 그중 6개 이상이 컴파일 확장이며
   `langchain-core`가 `langsmith`(관측 SaaS 클라이언트)를 필수로 끌고 온다[11]–[14].
   모델이 도구 호출을 못 하면 오류 없이 조용히 평문 응답으로 끝난다(§C).
6. **사람이 읽는 형식은 Obsidian 호환 Markdown + 평탄한 YAML frontmatter, 파일명은
   `family_id` 해시로 고정, 사람용 이름은 `aliases`와 H1에 둔다(§6).** Observed와
   Inferred는 H2 절로 분리하고, frontmatter에서도 `inferred_` 접두사와 `confidence`로
   구분한다. 근거 SHA-256은 표로 본문에 둔다. **두 번째 사본(JSON)은 불가피하며 JSON이
   진실 원천이다**; 페이지 frontmatter의 `source_hash`가 두 사본의 동기화 검사기다.
7. **팀원 서비스 경로(LATER)는 Skill Market의 스킬이 1순위, MCP는 선택 어댑터다.**
   Codex·Claude Code·OpenCode·pi 네 도구가 모두 Agent Skills 표준을 읽지만[28]–[31],
   pi는 MCP를 의도적으로 지원하지 않는다[31]. MCP 서버는 `mcp` 패키지 하나가 `starlette`,
   `uvicorn`, `pyjwt[crypto]` 등을 요구한다[36].
8. **반복 정제(D)는 스펙의 `confidence`·`unresolved`·budget으로 이미 표현 가능한
   "pool-based 불확실성 샘플링"이다[45].** pass N+1은 pass N의 `file-families.json`을
   prior로 읽고 저신뢰·무표본·무관계 파일군을 다음 표본 대상으로 고르며, 수렴 신호가
   멈추거나 총 budget이 끝나면 `NEXT: STOP`으로 끝낸다. 위키 전체를 LLM에 넣지 않고
   index + 해당 파일군 페이지 + 용어집만 넣으며, prior의 Inferred는 "이전 추정"
   라벨을 붙여 데이터 경계 안에 둔다. 여러 pass를 한 계획 승인으로 묶을지는 사용자
   결정이다(§D.3).

---

## Codex 토론 결과 (2026-09-15, 3라운드)

위 결론을 Codex(gpt-5.6-sol → gpt-6-astra)에게 스펙·`spike.py` 기준으로 공격하게 하고
반박·양보를 거친 결과다. 아래가 위 결론보다 우선한다.

### 합의 (위 결론을 고친 것)

1. **프레임워크 배제 이유를 좁힌다.** "`create_agent`가 6단계를 담을 수 없다"는 거짓이다.
   담을 수는 있지만 스펙 §4.6이 LLM에 도구를 주지 않고 필드별 평문 호출만 하므로 **얻는
   이점이 없다**가 정확한 이유다. NOW는 plain Python + `requests` + `work/llm.sqlite` +
   `audit.jsonl`로 간다는 결론 자체는 유지.
2. **수렴은 `NEXT: STOP`이 아니다.** 스펙 L392에서 exit 20 = 실행 중단 = `NEXT: STOP`이다.
   pass가 정상 종료하면 **exit 0 + `NEXT: equipment-map status --rollout <ID>`**, 결과
   승인은 기존 절차. 종료 사유는 `no-eligible-work` / `max-passes` / `budget` 세 가지로
   `audit.jsonl`에 남기고, 첫 번째만 "작업상 수렴"이며 정확도 달성을 뜻하지 않는다.
3. **prior는 `file-families.json` 하나가 아니라 `data-map/` 전체다**(§3 L57). 선택의 1순위
   신호인 미완료 frontier는 `coverage.json`에 있다.
4. **선택 규칙은 결정론적 신호만 쓴다.** `confidence`는 LLM 자기평가라 정확도 지표가 아니다
   (§4.6 L243). 순서: 미완료 frontier → 표본 없는 적격 파일군, 동률은 정규화 경로·family ID
   순. deny·active-candidate·시도 소진은 제외. "uncertainty sampling"이라는 이름은
   버리고 "미완료 작업 이어가기"로 부른다.
5. **pass 루프는 `stage 3 next` 한 호출 안에서 돈다.** 새 서브커맨드도, pass마다 호출을
   끊는 프로토콜도 없다. stage 4는 발행만 한다.
6. **승인은 한 번.** `rollout.json`에 `max_passes`(양의 정수, 기본 1)만 추가하고 기존
   다운로드·목록·LLM 요청·시간 상한은 전체 pass 누적. `plan.json`에 `max_passes`와
   `selection_rule_version`을 넣어 승인 hash에 묶고, §6에 "승인된 규칙이 같은 scope 안에서
   고른 대상은 계획의 파생 결과"라고 명시. 범위·규칙·상한 변경은 재승인.
7. **prior Inferred 전달은 허용하되 좁게.** 같은 파일군과 검증된 관계로 직접 연결된 파일군의
   `category`·`description`만, `prior_inferred` 블록에 `family_id`·`pass_id`·값·provenance로
   넣고 `prior_max_bytes`로 제한. 프롬프트에 "이전 추정이며 틀릴 수 있다, 현재 Observed로
   유지·수정·unknown을 판단하라"를 명시. 이전 추정은 evidence로 인용 불가, 결과는 항상
   `inferred`. prior packet hash를 캐시 키에 넣되 현재·연결 파일군의 Observed 입력이 같으면
   재호출하지 않는다(prior 변경만으로 반복 호출 금지). 이는 §4.6 입력 목록(L229–235)의
   **스펙 변경**이며 §7 시나리오가 따라야 한다.
8. **Wiki 최초 버전은 작게.** `index.md`(scope, coverage, 파일군 링크, 미해결·생략 사유) +
   `families/<family_id>.md`(제목, Observed, Inferred, Evidence, Relationships, Unresolved).
   표준 상대 링크. frontmatter는 **3키만**: `family_id`, `pass_id`, `generated_by`. 표시·추적용이며
   무결성은 기존 manifest의 파일 hash가 담당하고 frontmatter를 신뢰하지 않는다. `[[wikilink]]`,
   `aliases`, `tags`, `source_hash`, `inferred_*` 키는 Obsidian 소비자가 실제로 생기면 추가.
9. **Skills는 팀원에게 데이터를 서비스하지 않는다.** 스킬은 운영 절차 배포 수단(§3.1, §5),
   팀원 열람은 생성된 Wiki, 질의 요구가 실제로 생기면 그때 RAG 검색 어댑터/MCP/챗.

### 사용자 결정 (2026-09-15 09:55)

- **Wiki 페이지에 장비 디렉터리 경로를 노출한다.** 파일군 페이지의 Observed 절에 정규화
  경로를 그대로 쓴다. stdout에는 여전히 경로를 내지 않는다(불변조건은 stdout 규칙이지
  로컬 파일 규칙이 아니다).
- **사내 LLM은 GLM-5.3, Qwen3.8 계열, OpenAI 호환 endpoint.** 두 모델 모두 도구 호출은
  서빙 측 parser 플래그에 달려 있으므로(§1.3), 도구·구조화 출력을 요구하지 않는 스펙
  설계가 그대로 맞다. `llm.model`은 사내 alias로 두고 서버가 돌려주는 실제 모델 ID를
  따로 기록한다(스펙 §4.6).

### `max_passes`와 budget이 함께 움직이는 방식

스펙 §4.4는 실행마다 다운로드 파일 수, 전체 목표 바이트, 최대 실행 시간, 목록 항목 수와
깊이, 헤더 요청 수를 정하고 §4.6·§8은 LLM 요청 수(`llm_max_requests`)를 더한다. 이것이
"budget"이며 모두 `rollout.json`에 있고 계획 hash에 묶인다.

`max_passes`는 이 budget을 **쪼개지 않는다**. 한 승인 안에서 같은 scope의 미완료 작업을
몇 번까지 다시 돌지의 상한일 뿐이고, 모든 budget은 pass를 넘어 누적 소진된다. 그래서
루프는 세 조건 중 먼저 오는 것으로 끝난다.

| 종료 사유 | 뜻 | 다음 행동 |
|---|---|---|
| `no-eligible-work` | frontier도 표본 없는 적격 파일군도 남지 않음 | 결과 승인으로 진행 |
| `max-passes` | 적격 대상은 남았지만 pass 상한 도달 | 결과 승인 또는 `max_passes` 올려 재승인 |
| `budget` | 어느 budget이든 먼저 소진 | 결과 승인 또는 budget 올려 재승인 |

**기본값 1**인 이유: 기본값이 1이면 기존 단일 pass 동작과 완전히 같아서 스펙 개정이
기존 rollout을 바꾸지 않고, 여러 pass는 엔지니어가 명시적으로 켜야 한다. 값을 올릴 때의
기준은 pass 하나가 소비하는 양이다. pass 1은 inventory와 첫 표본이라 가장 크고, pass 2
이후는 frontier 잔여분과 무표본 파일군만 다루므로 작아진다. 따라서 `max_passes`를 2~3으로
두고 전체 목표 바이트·`llm_max_requests`·실행 시간을 pass 1 예상치의 1.5~2배로 잡으면
budget이 상한 역할을 하고 `max_passes`는 무한 루프 방지 장치가 된다. 정확도 목표로
`max_passes`를 정하지 않는다. 수렴 신호는 "할 일이 없다"이지 "맞다"가 아니기 때문이다.

### 남은 이견·검증 과제

- 7의 울타리로도 "틀린 이전 설명에 끌리는 현상"은 막지 못한다(Codex, 유지). §7에 의도적으로
  틀린 prior와 반대 Observed를 넣는 시나리오를 추가하고, 라벨 안정화를 정확도 증명으로
  취급하지 않는다.
- §7 추가 시나리오: pass 경계 강제 종료 후 재개 시 중복 요청·예산 초기화 없음, 적격 대상 소진
  종료, prior 변경 시 캐시 갱신, 범위 밖 인용·자료 속 지시 거부.

### 스펙 개정이 필요한 것 (두 가지뿐)

- pass 승인·종료 계약(§4.4, §5, §5.1, §5.2, §6): 6·2·5항.
- prior 입력 계약(§4.6): 7항.

나머지(canonical 전체, Markdown 파생 원칙, 프레임워크 배제)는 이미 스펙에 있어 개정 불필요.

두 개정은 2026-09-15에 스펙 §4.4.1(신설)·§4.6과 이를 참조하는 §5·§5.1·§5.2·§6·§7·§8에 반영했고 `equipment-data-parser/spec.md`를 다시 떴다.

---

## 1. 에이전트 아키텍처 비교

### 1.1 기준: workflow와 agent의 구분

Anthropic: "Workflows are systems where LLMs and tools are orchestrated through
predefined code paths." / "Agents are systems where LLMs dynamically direct their own
processes and tool usage"[1]. 같은 글은 "We suggest that developers start by using LLM
APIs directly: many patterns can be implemented in a few lines of code"와, 프레임워크가
"extra layers of abstraction that can obscure the underlying prompts and responses,
making them harder to debug"를 만든다고 적는다[1].

OpenAI 가이드는 agent를 "systems that independently accomplish tasks on your behalf"로
정의하고, "Before committing to building an agent, validate that your use case can meet
these criteria clearly. Otherwise, a deterministic solution may suffice."라고 쓴다[2].
또 "Our general recommendation is to maximize a single agent's capabilities first"와,
guardrail로 "Rules-based protections: Simple deterministic measures (blocklists, input
length limits, regex filters)"를 권한다[2].

스펙의 6단계 파이프라인(§3)은 코드가 순서를 정하고 LLM은 §4.6에서 "필드별로 짧은
응답"만 준다. 이 저장소가 만드는 것은 두 정의 모두에서 **workflow**다. "에이전트"는
바깥쪽, 즉 스킬을 읽고 CLI를 부르는 Claude Code/Codex 세션이며 그것은 이미 있다.

### 1.2 후보별 사실표

| 후보 | 직접 의존(필수) | 컴파일 확장 포함 | Python | 도구 호출 없는 모델 | 구조화 출력 | 재개/체크포인트 | 출처 |
|---|---|---|---|---|---|---|---|
| (a) plain Python + `requests`/`urllib` | 0 (requests는 proxy가 이미 요구) | 없음 | 3.11 (stdlib `tomllib`) | 필요 없음 — 평문 필드 + 검증기 | 코드가 검증. vLLM/Ollama는 `response_format`으로 JSON-schema 제약도 제공[19][20] | `work/llm.sqlite` + `audit.jsonl`(스펙 §4.6, §5.1) | 스펙 |
| (b) `langchain` `create_agent` | `langchain-core`, `langgraph`, `pydantic` + endpoint용 `langchain-openai`(`openai`, `tiktoken`, `certifi`) | `pydantic-core`(Rust)[40], `xxhash`(C)[39], `ormsgpack`(Rust)[41], `orjson`, `jiter`, `uuid-utils`, `zstandard`, `tiktoken` | ≥3.10[13] | `bind_tools`만 호출; 서버가 tool parser 없으면 모델이 평문 답 → 루프 종료(오류 없음) | `ToolStrategy`(도구 호출 필요) / `ProviderStrategy`(네이티브 필요); prompted 폴백 없음[8] | LangGraph checkpointer, `SqliteSaver`는 별도 패키지[24][25] | [3][4][5][11][12] |
| (c) LangGraph 직접 | `langchain-core`(→`langsmith` 등), `langgraph-checkpoint`(`ormsgpack`), `langgraph-sdk`, `langgraph-prebuilt`, `xxhash`, `pydantic` | 위와 같음 | ≥3.10 | 그래프 자체는 모델 무관 | 직접 구현 | `SqliteSaver`, `thread_id`, `interrupt`/`Command(resume=)`[23][24] | [6][21][23] |
| (d) Pydantic AI (`pydantic-ai-slim[openai]`) | `anyio`, `griffelib`, `httpx2`, `pydantic`, `pydantic-graph`, `opentelemetry-api`, `typing-inspection`, `genai-prices` + `openai`, `tiktoken` | `pydantic-core`, `jiter`, `tiktoken` | — | `PromptedOutput`이 "models without native tool calling or structured output support"용 폴백[17] | Tool/Native/Prompted 세 모드 + `@output_validator` 재시도[17] | 자체 graph; 파일 체크포인트는 확인 못 함 `[미검증]` | [16][17] |
| (e) OpenAI Agents SDK | `openai`, `pydantic`, `griffelib`, `requests`, `websockets`, **`mcp`**, `httpx2`, `pyjwt`, `python-multipart`, `starlette`, `urllib3` | 다수 | ≥3.10 | 문서: "providers that don't support structured JSON outputs will occasionally produce invalid JSON"; `set_default_openai_api("chat_completions")` 필요[18] | `output_type` (provider 의존) | 세션 객체; 파일 체크포인트 `[미검증]` | [18][38] |
| (f) `openai` 공식 클라이언트만 | `httpx2`, `pydantic`, `typing-extensions`, `anyio`, `sniffio`, `jiter` | `pydantic-core`, `jiter` | ≥3.10 | 해당 없음(클라이언트) | 없음 | 없음 | [15] |

Windows용 wheel: `xxhash`, `ormsgpack`, `pydantic-core`는 `cp311-win_amd64` wheel을
PyPI에 올린다[39][40][41]. 나머지 컴파일 패키지도 wheel이 있을 가능성이 높지만
개별 확인은 하지 않았다 `[미검증]`. 사내 미러에 wheel이 있는지는 사무실에서만 알 수
있다.

### 1.3 도구 호출과 Qwen serving

- vLLM: 자동 도구 호출은 `--enable-auto-tool-choice`("mandatory")와 `--tool-call-parser`
  가 필요하고 Qwen2.5/QwQ는 `hermes`, Qwen3-Coder는 `qwen3_xml` parser다. parser를
  켜지 않으면 "Tool calling becomes unavailable entirely"[19].
- Qwen 공식 문서: "It is not guaranteed that the model generation will always follow
  the protocol even with proper prompting or templates"[42].
- Ollama OpenAI 호환: chat completions에서 "Tools" 지원, "Tool choice"는 미지원[20].
- 결론: 도구 호출 가능 여부는 **서빙 운영자의 플래그**이고, `rollout.json`이 기록하는
  `llm.model`/serving 설정의 일부다(스펙 §4.6). 스펙의 설계는 도구 호출도 구조화
  출력도 요구하지 않으므로 어느 serving 설정에서든 돌아간다. 이것이 (a)의 가장 큰
  실용적 장점이다.

### 1.4 락인

(b)(c)는 `langchain-core` 메시지 타입과 LangGraph 상태 스키마에 결과가 묶인다. (a)는
HTTP 요청·응답 dict와 SQLite 행뿐이다. LangChain은 v1에서 `create_react_agent`를
`create_agent`로 대체하고 레거시를 `langchain-classic`으로 옮겼다[9][10]; 다음 major에서
같은 일이 다시 일어나지 않는다는 보장은 문서에 없다.

## 2. 저장소 불변조건과의 적합성

| 스펙 불변조건 | plain Python | `create_agent` | LangGraph | 판정 |
|---|---|---|---|---|
| 한 CLI, 얇은 스킬(§9) | CLI 안 함수 | CLI 안에서 그래프 컴파일 | 동일 | 셋 다 가능; 프레임워크는 CLI 내부 세부일 뿐 스킬에서 보이지 않음 |
| stdout은 건수·hash만(§5) | 직접 제어 | 스트리밍 콜백 끄면 가능 | 동일 | 동일 |
| `audit.jsonl`이 단일 상태 원천(§5.1) | 그대로 | checkpointer가 **두 번째 상태 저장소** 추가 | 동일 | 프레임워크 사용 시 둘 중 하나를 파생물로 선언해야 함 |
| 필드별 짧은 요청 + 검증기(§4.6) | 함수 하나 | 도구 없는 `create_agent`는 "모델 1회 호출"과 같음; 검증기는 `after_model` 훅[26] | 노드 함수 | 프레임워크가 더해 주는 것 없음 |
| LLM에 도구 없음(§4.6) | 자연스럽다 | `tools=None`이면 `bind()`만 호출[4] — 즉 도구 루프 자체를 쓰지 않는다 | 해당 없음 | `create_agent`의 존재 이유가 사라짐 |
| 승인 게이트, exit 10/`WAIT-APPROVAL` | `sys.exit(10)` | `interrupt()` + 재개 시 노드 재실행[23] | 동일 | 스펙은 프로세스 종료 후 사람 승인 → 새 프로세스; 그래프 재개 의미론과 다름 |
| observed/inferred 분리 | schema validator | 동일 코드 필요 | 동일 | 동일 |

**NOW 권고:** (a). `spike.py`의 `ask_llm()`을 필드별 함수로 쪼개고 `work/llm.sqlite`
트랜잭션에 넣는 것이 다음 단계다(`agent_build_steps/04`). 프레임워크는 스펙이 파일로
정한 것을 객체로 한 번 더 만든다.

**LATER 권고(팀원 서비스):**

- **1순위 — Skill Market 스킬.** Agent Skills 표준은 `SKILL.md`에 `name`·`description`만
  필수이고, "Metadata (~100 tokens)" → "Instructions" → "Resources" 순으로 점진 로드한다[27].
  Claude Code[28], Codex(`.agents/skills`, `~/.agents/skills`)[29], OpenCode
  (`.opencode/skills`, Claude 호환 경로)[30], pi(`~/.pi/agent/skills`, `.agents/skills`)[31]
  모두 읽는다. 스펙 §9의 6개 스킬 구조가 이미 이 형식이다.
- **2순위 — MCP 서버(선택).** MCP는 JSON-RPC 2.0 위에 Resources/Prompts/Tools를 제공하는
  프로토콜이고 spec 2025-06-18이 현행이다[35]. Claude Code(`claude mcp add`, stdio/http)[32],
  Codex(`config.toml [mcp_servers]`, STDIO/Streamable HTTP)[33], OpenCode(`opencode.json`
  `mcp`, local/remote)[34]는 지원하지만 **pi는 "No MCP. Build CLI tools with READMEs
  (see Skills), or build an extension that adds MCP support."**[31]. MCP 서버를 만들면
  `equipment-map` 읽기 전용 질의(`status`, wiki 검색)를 도구로 노출할 수 있지만, 스펙
  §5의 "stdout에는 경로·파일명 없음" 규칙을 MCP 응답에도 그대로 적용해야 하며, MCP
  spec 자체가 "Tools represent arbitrary code execution and must be treated with
  appropriate caution"이라고 쓴다[35]. OpenCode는 "MCP servers add to your context"라고
  경고한다[34].
- **3순위 — 대화 서비스.** 팀원이 "이 장비의 recipe 파일은 어디 있나"를 묻는 챗이라면
  `rag/chunks.jsonl`(스펙 §4.7.3)을 색인하는 검색 도구 하나를 가진 단일 에이전트가
  맞고, 이때 비로소 `create_agent`나 Pydantic AI가 도구 루프를 대신 돌려 주는 가치가
  생긴다(§C.4). 그 전까지는 위키 폴더를 Obsidian/사내 위키로 여는 것이 서비스다.

## 3. (A) 워크플로형 에이전트 구성

### 3.1 LangGraph `StateGraph`

- 정의: `StateGraph(State)` → `add_node` → `add_edge(START, ...)` → `compile()`; "nodes do
  the work, edges tell what to do next"[21]. 상태 키마다 reducer가 있고 "If no reducer
  function is explicitly specified then it is assumed that all updates to that key
  should override it"[21]. 조건부 분기는 `add_conditional_edges(node, routing_fn)`,
  상태 갱신과 이동을 한 번에 하려면 `Command(update=..., goto=...)`[21].
- 루프: "By composing Nodes and Edges, you can create complex, looping workflows";
  종료는 `END`; "The recursion limit sets the maximum number of super-steps ... Once the
  limit is reached, LangGraph will raise `GraphRecursionError`"이고 "Starting in
  version 1.0.6, the default recursion limit is set to 1000 steps"[21].
- 체크포인트: `InMemorySaver`, `SqliteSaver`, `PostgresSaver`; `thread_id`를
  `config={"configurable": {"thread_id": ...}}`로 준다[24]. `SqliteSaver`는
  `langgraph-checkpoint-sqlite`(의존: `langgraph-checkpoint`, `aiosqlite`, `sqlite-vec`)
  이며 `from langgraph.checkpoint.sqlite import SqliteSaver` /
  `SqliteSaver.from_conn_string(path)`[25].
- 승인 게이트: `interrupt()`는 "saves the current graph state and waits for you to
  resume execution with input"; 재개는 `Command(resume=...)`; **"the runtime restarts
  the entire node from the beginning—it does not resume from the exact line where
  `interrupt` was called"**이므로 "any code that ran before the `interrupt` will execute
  again"[23]. 정적 게이트는 `compile(interrupt_before=[...], interrupt_after=[...])`[23].

### 3.2 `create_agent` + 미들웨어

- `create_agent`는 내부에서 `StateGraph`를 만들고 `graph.compile(checkpointer=...,
  store=...)`로 `CompiledStateGraph`를 반환한다[4]. 그래프 모양은 고정(model → tools →
  model …)이고, 사용자는 미들웨어 훅으로 그 앞뒤에 끼어든다.
- 훅: `before_agent`, `before_model`, `after_model`, `after_agent`(노드형),
  `wrap_model_call`, `wrap_tool_call`(래핑형); 데코레이터 `@before_model` 등; 조기 종료는
  `{"jump_to": "end"}` 반환[26].
- 구조화 출력: `response_format`에 스키마를 주면 `AutoStrategy` → 네이티브 지원이면
  `ProviderStrategy`, 아니면 `ToolStrategy`("works with all models that support tool
  calling")[8]. 도구 호출도 네이티브도 없는 모델용 폴백은 문서에 없다.
- **워크플로를 `create_agent`로 표현할 수 있는가:** 6단계 파이프라인 중 LLM이 개입하는
  것은 5단계 하나이고 나머지는 FTP·해시·정규식이다. `create_agent`에는 "Inventory 노드
  → Grouping 노드"를 넣을 자리가 없다; 그런 단계는 미들웨어 `before_agent`에 밀어
  넣거나 그래프 바깥에서 순서대로 호출해야 한다. 즉 워크플로는 LangGraph(또는 plain
  Python)가 필요하고 `create_agent`는 그 안의 한 노드 후보일 뿐이다. 그 한 노드마저
  도구가 없으므로 `bind()` 한 번 호출과 같다[4].

### 3.3 Anthropic 패턴 ↔ 스펙 6단계

| 스펙 단계 | 패턴[1] | 비고 |
|---|---|---|
| 1 Inventory, 2 Grouping | 없음(결정론) | LLM 호출 없음 |
| 3 Sampling | 없음(결정론, budget) | |
| 4 Extraction | 없음(결정론) | |
| 5 Local LLM | **prompt chaining**(필드별 순차 요청 + 코드 검증 "gate") | 스펙 §4.6 |
| 5의 category enum | **routing**의 축소형 — 코드가 enum 검증 | vLLM `guided_choice`로 강제 가능[19] |
| 5의 파일군 병렬 | **parallelization**(sectioning) | 동시성은 budget에 묶임 |
| 6 Data Map + 파생 | 없음(결정론) | |
| D의 pass 반복 | **evaluator-optimizer**의 변형 — 평가자는 LLM이 아니라 `confidence`/coverage 계산 코드 | §D |

orchestrator-workers("subtasks aren't pre-defined, but determined by the orchestrator")[1]
는 이 일에 해당하지 않는다. 스펙은 다음 표본을 LLM이 아니라 budget과 규칙이 고르게
한다(§4.4, §4.7.1 "관계 발견을 이유로 다운로드·탐색 범위를 넓히지 않는다").

### 3.4 같은 파이프라인 세 가지 스케치

(1) LangGraph `StateGraph`

```python
class S(TypedDict):
    scope: str; families: list; pending_fields: list; approved: bool

g = StateGraph(S)
for name, fn in [("inventory", inventory), ("grouping", grouping),
                 ("sampling", sampling), ("extraction", extraction),
                 ("llm_field", llm_field), ("datamap", datamap)]:
    g.add_node(name, fn)
g.add_edge(START, "inventory"); g.add_edge("inventory", "grouping")
g.add_edge("grouping", "sampling"); g.add_edge("sampling", "extraction")
g.add_edge("extraction", "llm_field")
g.add_conditional_edges("llm_field", lambda s: "llm_field" if s["pending_fields"] else "datamap")
g.add_edge("datamap", END)
app = g.compile(checkpointer=SqliteSaver.from_conn_string("work/graph.sqlite"),
                interrupt_before=["sampling"])          # plan approval gate
app.invoke(init, config={"configurable": {"thread_id": rollout_id}})
# 승인 뒤 새 프로세스: app.invoke(Command(resume=True), config=same)
```

(2) `create_agent` + 미들웨어 — LLM 단계만 표현 가능

```python
@before_agent
def load_packet(state, runtime): ...        # 파일군 규칙·샘플 발췌·용어집 조립
@after_model
def validate(state, runtime):               # 길이·형식·evidence SHA 검증
    if not ok(state["messages"][-1]): return {"jump_to": "end"}
agent = create_agent(model=init_chat_model("qwen", model_provider="openai",
                     base_url=URL, api_key=KEY), tools=None,
                     system_prompt=PROMPT, middleware=[load_packet, validate])
# inventory/grouping/sampling/extraction/datamap는 그래프 밖에서 순서대로 호출
```

(3) plain Python (스펙 그대로)

```python
def run_stage(rollout):
    with Lock(rollout), Audit(rollout) as audit:
        scope = inventory(rollout, audit)         # 체크포인트: work/inventory/*
        fams  = grouping(scope)
        if not plan_approved(audit): return 10    # NEXT: WAIT-APPROVAL
        sampling(fams, rollout.budget, audit)     # 체크포인트: evidence/
        extraction(fams)
        with sqlite3.connect("work/llm.sqlite") as db:
            for fam in fams:
                for field in FIELDS:
                    if committed(db, fam, field): continue
                    reserve(db, fam, field)                     # 요청 예약
                    val = validate(field, ask(field, packet(fam)))
                    commit(db, fam, field, val or unresolved())  # 한 트랜잭션
        datamap(fams, db); manifest(rollout)
    return 0                                     # NEXT: <다음 명령>
```

**접착 비용 판정.** 스펙의 계약은 "프로세스가 exit 10으로 끝나고, 사람이 `operator
approve-plan`을 실행하고, 다음 `next`가 `audit.jsonl`을 읽어 이어간다"(§5, §5.2)이다.
(3)은 그 문장을 그대로 코드로 옮긴 것이다. (1)은 같은 것을 `interrupt_before` +
`thread_id`로 할 수 있지만, 승인 기록이 `audit.jsonl`이 아니라 checkpointer에도 생겨
"어느 쪽이 진실인가"를 정해야 하고, 재개 시 노드 재실행[23] 때문에 노드 안의 FTP
다운로드나 LLM 요청 예약이 멱등해야 한다 — 스펙은 이미 sqlite 예약으로 멱등을 만들지만
그건 (3)에서도 똑같이 필요한 코드다. (2)는 워크플로를 담지 못한다. 따라서 **A의 답은
(3)**이고, LangGraph는 나중에 D의 반복 루프가 "그래프로 그려야 설명이 되는" 수준으로
커질 때 다시 검토한다(§D.3).

## 4. (B) Markdown 파일을 코드에 연결하기

### 4.1 md가 에이전트 지시일 때

| 도구 | 상시 컨텍스트 | 온디맨드 스킬 | 근거 |
|---|---|---|---|
| Claude Code | `CLAUDE.md`(managed → `~/.claude` → `./CLAUDE.md` → `CLAUDE.local.md`, 상위 디렉터리 연결), `@path` import 최대 4단계, "Claude Code reads `CLAUDE.md`, not `AGENTS.md`" → `@AGENTS.md` import 권장 | `.claude/skills/<name>/SKILL.md`, Agent Skills 표준 + 자체 확장 필드 | [28][37] |
| Codex | `~/.codex/AGENTS.md`(또는 `AGENTS.override.md`) → repo root부터 cwd까지 연결, 합산 `project_doc_max_bytes` 32 KiB 기본 | `.agents/skills`, `~/.agents/skills`, `/etc/codex/skills` | [29][33b] |
| OpenCode | `AGENTS.md`(프로젝트·`~/.config/opencode`), 없으면 `CLAUDE.md` 폴백; `opencode.json` `instructions` | `.opencode/skills`, Claude 호환 경로 | [30][34b] |
| pi | `~/.pi/agent/AGENTS.md` + 상위 디렉터리 + cwd의 `AGENTS.md`/`CLAUDE.md`, `AGENTS.override.md` 우선 | `~/.pi/agent/skills`, `.pi/skills`, `.agents/skills` | [31] |

이 저장소는 이미 `CLAUDE.md`가 `@AGENTS.md`를 import한다 — Claude Code 문서가 권하는
바로 그 형태다[28]. 네 도구 모두 **파일을 읽어 프롬프트에 붙이는 것**이 전부이고,
"안전 판단"은 하지 않는다: Claude Code 문서는 "CLAUDE.md instructions shape Claude's
behavior but are not a hard enforcement layer"라고 명시한다[28]. 스펙의 "안전은 코드"
원칙과 같은 말이다.

LangChain 쪽에서 같은 md를 쓰려면 `create_agent(system_prompt=Path("SKILL.md")
.read_text())`처럼 문자열로 넣는 것이 전부다(`system_prompt: str | SystemMessage |
None`)[4]. SKILL.md의 frontmatter·점진 로드(metadata → body → resources)를 해석하는
1차 기능은 LangChain/LangGraph 문서에서 찾지 못했다 `[미검증]`; LangChain Hub는 조사
범위에서 확인하지 않았다 `[미검증]`.

### 4.2 md가 데이터일 때 — 파싱 선택지

| 방법 | 의존 | 비고 |
|---|---|---|
| stdlib: `---`로 분할 + `tomllib` | 0 | TOML frontmatter만 파싱 가능(3.11+, 쓰기는 미지원)[44]; **Obsidian은 YAML만 읽는다**[46] |
| `python-frontmatter` | PyYAML(YAML 1.1 구현, `safe_load` 필수)[43] | YAML/JSON/TOML 핸들러, `load/loads/dumps`[47] |
| `markdown-it-py` | 없음(Python ≥3.10); frontmatter는 `mdit-py-plugins`[48] | CommonMark 준수 파서 |
| `mistune` | 없음(Python ≥3.8)[49] | frontmatter 플러그인 여부 `[미검증]` |
| LangChain `ObsidianLoader` | `langchain-community` | 정규식으로 frontmatter `^---\n(.*?)\n---\n`, 태그, Dataview `[k:: v]`/`(k:: v)` 추출[50] |
| LangChain `MarkdownHeaderTextSplitter` | `langchain-text-splitters` | 헤더별로 쪼개고 헤더 값을 metadata에 넣음[51] |

CommonMark 0.31.2는 frontmatter도 `[[wikilink]]`도 정의하지 않는다[52] — 둘 다
Obsidian/Foam/Logseq 확장이다.

### 4.3 경계 판정

**md는 구조화 데이터에서 렌더링한 사람용 뷰다.** 이유:

1. 스펙 §3·§4.7.3이 `data-map/*.json`을 canonical으로, `wiki/`를 "언제든 canonical
   map에서 재생성할 수 있는 파생물"로 이미 정했다.
2. YAML 파싱은 stdlib에 없고, PyYAML은 YAML 1.1이며 `load`는 "as powerful as
   `pickle.load`"라 `safe_load`만 써야 한다[43]. 데이터 유래 문자열(파일명·샘플 발췌)이
   frontmatter에 들어가는 파일을 코드가 다시 읽어 결정을 내리면, 스펙 llm-behavior §4.3
   의 "데이터가 지시가 되는 경로"가 하나 더 생긴다.
3. Karpathy의 패턴도 raw(불변) → wiki(LLM 소유) → schema(규약) 세 층을 분리한다[53].
   이 저장소에서는 evidence가 raw, canonical JSON이 "컴파일된 지식", wiki가 렌더링이다.
   LLM이 wiki를 직접 쓰는 Karpathy식과 달리 스펙은 LLM이 파일에 쓰지 못하게 하므로
   (llm-behavior §1), wiki를 LLM 소유로 두지 않는다.

코드가 md를 **읽는** 유일한 경로는 §6.5의 `review/<family_id>.md`(사람 주석)이며, 그
파일은 frontmatter 없이 본문만 `data-map/`에 첨부 문자열로 실린다.

## 5. (C) `create_agent` 판정

### 5.1 사실

- 시그니처(`libs/langchain_v1/langchain/agents/factory.py`, master, langchain 1.4.0):
  `create_agent(model: str | BaseChatModel, tools=None, *, system_prompt=None,
  middleware=(), response_format=None, state_schema=None, context_schema=None,
  checkpointer=None, store=None, interrupt_before=None, interrupt_after=None,
  debug=False, name=None, cache=None, transformers=None) -> CompiledStateGraph`[4].
- 내부: `from langgraph.graph.state import StateGraph`; 도구가 있으면
  `request.model.bind_tools(final_tools, tool_choice=...)`, 없으면
  `request.model.bind(**request.model_settings)`; 마지막에
  `graph.compile(checkpointer=checkpointer, store=store, ...)`[4].
- OpenAI 호환 endpoint: `init_chat_model(model=..., model_provider="openai",
  base_url=..., api_key=...)`[7]; `langchain-openai` 1.6.2가 `openai>=2.45.0`,
  `tiktoken`, `certifi`를 요구[12].
- 의존 트리(필수만): `langchain` → `langchain-core`, `langgraph`, `pydantic`[11];
  `langchain-core` → `langsmith`, `httpx`, `tenacity`, `jsonpatch`, `PyYAML`,
  `typing-extensions`, `packaging`, `pydantic`, `uuid-utils`, `langchain-protocol`[13];
  `langsmith` → `requests`, `orjson`, `requests-toolbelt`, `zstandard`, `uuid-utils`,
  `xxhash`, `websockets`, `anyio`, `distro`, …[14]; `langgraph` → `langgraph-checkpoint`
  (`ormsgpack`), `langgraph-sdk`(`httpx`, `orjson`, `websockets`), `langgraph-prebuilt`,
  `xxhash`[6][25b][25c]. 대략 25개 이상, 컴파일 확장은 최소 `pydantic-core`, `xxhash`,
  `ormsgpack`, `orjson`, `jiter`, `uuid-utils`, `zstandard`, `tiktoken`.
- Python: `requires-python = ">=3.10.0,<4.0.0"`[11b]; 마이그레이션 문서 "All LangChain
  packages now require Python 3.10 or higher"[10].
- API 변천: v1에서 `create_react_agent` → `create_agent`, 레거시 체인·기능은
  `langchain-classic`[9][10]. `AgentExecutor`/`initialize_agent`의 현재 상태는 문서에서
  명시된 문장을 찾지 못했다 `[미검증]`.
- 도구 호출 없는 모델: 문서는 "agents are described as 'a model calling tools in a
  loop'"이고 명시적 요구 문장은 없다[3]. 코드상 `bind_tools`는 요청에 `tools`를 실어
  보낼 뿐이므로, vLLM이 parser 없이 뜨면[19] 모델은 평문을 돌려주고 루프는 도구 호출
  없음으로 정상 종료한다 — **실패가 아니라 조용한 저하**다.
- 구조화 출력: `ToolStrategy`는 도구 호출 필요, `ProviderStrategy`는 네이티브 필요[8].
  Pydantic AI의 `PromptedOutput` 같은 프롬프트 폴백은 없다[17].

### 5.2 이 일에서 사는 것과 죽는 것

| `create_agent`가 주는 것 | 이 일(NOW)에서 | 팀원 챗(LATER)에서 |
|---|---|---|
| 도구 호출 루프 | 스펙이 LLM에 도구를 주지 않음 → 사용 안 함 | 검색 도구 1–2개면 유용 |
| 미들웨어 훅 | 필드 검증기는 함수 한 줄 | 요청 제한·PII 등 내장 미들웨어 유용 |
| `response_format` | 스펙은 평문 필드 → 불필요; 서빙이 parser 없으면 동작 안 함 | 제공자에 따라 |
| checkpointer | `work/llm.sqlite`와 중복 | 대화 스레드 기억에 유용 |
| 모델 추상화 | endpoint 하나, 실행 중 모델 전환 금지(§4.6) | 여러 사내 모델 비교 시 유용 |

**판정:** NOW는 dead weight. `agent_build_steps/README.md`의 "agent 프레임워크를 미리
도입하지 않는다"가 맞다. LATER의 대화 서비스에서 "모델이 검색 도구를 골라 부르는"
요구가 실제로 생기면 그때 `create_agent`(또는 더 가벼운 Pydantic AI slim)를 검토한다.
그 시점의 판단 기준: (1) 사내 미러에 위 wheel들이 있는가, (2) serving에 tool parser가
켜져 있는가[19], (3) `langsmith` 필수 의존이 사내 보안 검토를 통과하는가(네트워크
전송은 키가 없으면 하지 않지만 코드가 포함된다 — 실제 전송 조건은 `[미검증]`).

## 6. 사람이 읽는 데이터 형식

### 6.1 1차 출처 요약

- Obsidian properties: "Properties are stored in YAML format at the top of the file";
  타입은 Text/List/Number/Checkbox/Date/Date & time; 기본 속성 `tags`, `aliases`,
  `cssclasses`; "Internal links in text properties must be surrounded with quotes";
  중첩 YAML은 "we recommend using the source mode"[46].
- 링크: `[[Note]]`, `[[Note#Heading]]`, `[[Note^id]]`, `[[Note|Custom name]]`,
  Markdown 링크 `[text](Note.md)`; "Obsidian can automatically update internal links in
  your vault when you rename a file"[54]. 별칭은 `aliases` 리스트이고 링크는
  `[[Artificial Intelligence|AI]]` 형태로 만들어져 "compatibility with other applications
  supporting the Wikilink format"를 유지한다[55]. 태그는 `#a/b` 중첩, 공백 불가,
  frontmatter `tags` 리스트[56].
- Bases: "a core plugin that lets you create database-like views of your notes";
  `.base` 파일 또는 코드블록; "all the data in Obsidian Bases stored in your local
  Markdown files and their properties"; Table/Cards/List/Kanban/Map 뷰, formulas[57].
  1.9.0 early access(2025-05-21 changelog)에서 도입[58].
- Dataview: "All YAML Frontmatter fields will be automatically available as Dataview
  fields"; 인라인 `Key:: Value`, 리스트 안은 `[key:: value]`, `(key:: value)`는 키 숨김[59].
- Karpathy LLM wiki(gist, 2026-04-04): raw sources "The LLM reads from them but never
  modifies them. This is your source of truth." / wiki "The LLM owns this layer
  entirely" / schema "tells the LLM how the wiki is structured"; `index.md`는 "a
  catalog of everything in the wiki—each page listed with a link, a one-line summary",
  `log.md`는 "append-only record"; "Obsidian's graph view is the best way to see the
  shape of your wiki"[53].
- Foam: `[[double bracket]]`; "When the same filename exists in multiple locations,
  `[[todo]]` is ambiguous. Foam resolves it alphabetically (deterministic), and shows a
  warning diagnostic"[60]. Logseq: "Page properties are defined by putting them into
  the first block of the page (frontmatter)" — `key:: value` 문법이며 YAML frontmatter
  지원은 공식 문서에서 확인 못 함 `[미검증]`[61].
- 기계 쪽: SQLite는 "works particularly well as a replacement for these ad hoc data
  files"이지만 네트워크 파일시스템에서 여러 컴퓨터가 동시에 쓰는 것은 피하라[62];
  Parquet은 "column-oriented data file format designed for efficient data storage and
  retrieval"[63]; JSON-LD 1.1은 "a JSON-based format to serialize Linked Data",
  W3C Recommendation 2020-07-16[64]. 스펙 §4.7.3은 JSON-LD/RDF/GraphML을 "실제
  consumer가 정해진 뒤" 어댑터로 두므로 여기서는 채택하지 않는다. Parquet은 분석
  워크로드용이며 이 지도는 행 수가 작고 사람이 diff해야 하므로 JSON을 유지한다.

### 6.2 설계 원칙

1. **JSON이 진실, md는 뷰.** 두 사본은 불가피하다(스펙 §3). 동기화 검사는 md
   frontmatter의 `source_hash`(해당 파일군의 canonical JSON record SHA-256)와
   `index.json`의 hash 비교로 한다. 불일치면 `status`가 "wiki stale"을 세어 보고한다.
2. **frontmatter는 평탄한 YAML만.** 중첩 없음(Obsidian 제약)[46], 값은 문자열·숫자·
   불리언·문자열 리스트. Bases/Dataview가 그대로 컬럼으로 읽는다[57][59].
3. **파일명은 `family_id`**(스펙 §4.7.2의 안정 ID). 사람용 제목은 H1과 `aliases`.
   파일군 규칙이 바뀌면 새 ID·새 파일이고 옛 파일은 삭제된다 — Obsidian의 rename 링크
   갱신[54]에 기대지 않는다. 모든 링크는 CLI가 매 publish마다 다시 쓰므로 깨진 링크가
   남지 않는다.
4. **Observed/Inferred는 두 번 표시.** 본문은 `## Observed`/`## Inferred` H2로, frontmatter
   는 `inferred_` 접두사 + `confidence`로. `observed_vs_inferred: inferred`를 인라인
   Dataview 필드로도 남겨 검색 가능하게 한다.
5. **근거는 표.** SHA-256 앞 12자 + 전체 해시를 코드 스팬으로. 위키 페이지는 evidence
   파일을 링크하지 않는다(evidence는 반출 통제 대상, 스펙 §5.1).
6. **데이터 유래 문자열은 이스케이프.** 파일명·필드명 속 `[[`, `#`, `::`, `---`는
   코드 스팬으로 감싸고 frontmatter 값은 항상 따옴표(llm-behavior §4.3).
7. **생성물임을 표시.** `generated: true`, `generator: equipment-map <ver>`, 그리고
   사람이 고칠 곳은 `review/`뿐임을 페이지 하단에 한 줄로 적는다.

### 6.3 디렉터리 배치

```text
rollouts/<id>/data-map/wiki/        # Obsidian에서 이 폴더를 vault로 연다
  index.md                          # 허브: 장비, coverage, 파일군 표, 미해석 목록
  equipment.md                      # 장비·범위·scope hash (경로는 정규화된 루트만)
  coverage.md                       # coverage.json 렌더링
  glossary.md                       # 용어집 버전 + 항목
  unreadable.md                     # unreadable.json 렌더링
  families/<family_id>.md           # 파일군마다 한 장
  paths/<path_id>.md                # paths.json의 디렉터리 요약 (선택)
  families.base                     # Obsidian ≥1.9 Bases 뷰 (선택, 텍스트 파일)
  review/<family_id>.md             # 사람 주석. CLI가 읽기만 하고 절대 덮어쓰지 않음
```

`review/`를 제외한 모든 파일은 publish가 통째로 다시 만들고 고아 파일을 지운다.
`review/`는 manifest에서 별도 항목으로 hash되어 결과 승인에 포함된다(스펙 §5.2의
manifest 규칙 확장 — 스펙 개정 필요, §7).

### 6.4 파일군 페이지 예시

```markdown
---
schema_version: 1
generated: true
generator: "equipment-map 0.3.0"
rollout: "r-7c1e"
scope: "s3-e2-9f0a"
family_id: "fam-3f9a1c7b2d40"
source_hash: "sha256:8d2f…c41e"
aliases:
  - "PM1 process log (daily csv)"
equipment: "eq-01"
directory: "/data/log/process"
name_rule: "PROC_{YYYYMMDD}.csv"
extensions: [".csv"]
member_count: 412
sample_count: 3
inventory_complete: true
inferred_category: "event_log"
inferred_category_confidence: "medium"
inferred_lifecycle: "append-series"
inferred_lifecycle_confidence: "low"
unresolved: ["operational_use: insufficient-evidence"]
relationship_count: 2
tags:
  - "eq/eq-01"
  - "category/event_log"
  - "confidence/medium"
  - "status/unconfirmed"
---

# PM1 process log (daily csv)

`fam-3f9a1c7b2d40` · rollout `r-7c1e` · [[index]] · [[coverage]]

## Observed

- 디렉터리 `/data/log/process`, 파일명 규칙 `PROC_{YYYYMMDD}.csv`, 412개, 크기 12 KB–2.1 MB.
- mtime 범위(UTC, MDTM) 2026-06-01 … 2026-09-10, 최소 간격 근거 3개 이상 → 관측 gap 24 h.
- 헤더 필드: `timestamp`, `step`, `chamber_pressure`, `rf_power`, `lot_id` (표본 3/3 동일).
- 식별자 관측: `lotid` 값 형식 `[A-Z]{2}\d{6}` (관측 사실, 의미 아님).

## Inferred

observed_vs_inferred:: inferred · model_id:: `qwen3-27b@rev-…` · prompt_version:: p3 · glossary_version:: g2

| field | value | confidence | evidence |
|---|---|---|---|
| category | event_log | medium | `sha256:1a…`, `sha256:7b…` |
| description | 공정 스텝별 챔버 압력·RF 파워 기록 | medium | `sha256:1a…` |
| lifecycle | append-series | low | (metadata) |
| operational_use | UNKNOWN — unresolved: insufficient-evidence | — | — |

LLM 유래 값은 검증을 통과해도 추론이다. 근거 없는 항목은 `UNKNOWN`으로 남긴다.

## Evidence

| kind | sha256 | observation_id | locator |
|---|---|---|---|
| sample | `1a5c…e90f` | obs-2026-09-10-0412 | header row 1 |
| sample | `7b03…2ad1` | obs-2026-09-10-0388 | rows 1–20 |
| metadata | `c9e2…77b0` | obs-2026-09-10-* | listing |

## Relationships

| type | target | matched_value | support_scope | evidence |
|---|---|---|---|---|
| shared_identifier | [[fam-a10c5e…\|PM1 measurement result]] | `lotid=AB123456` | samples | 2 pairs |
| same_directory | [[fam-77d0b2…\|PM1 alarm csv]] | `/data/log/process` | metadata | 1 pair |

relationship_coverage: samples_used 3, truncated no, unresolved_refs 0.

## Unresolved

- `operational_use`: insufficient-evidence (2 slots used).

---
생성 파일. 고칠 것은 [[review/fam-3f9a1c7b2d40]]에 쓴다.
```

### 6.5 허브 페이지 예시 (`index.md`)

```markdown
---
schema_version: 1
generated: true
rollout: "r-7c1e"
scope: "s3-e2-9f0a"
family_count: 37
families_with_sample: 29
families_no_sample: 8
unresolved_fields: 41
inventory_complete: true
tags: ["eq/eq-01", "hub"]
---

# eq-01 데이터 지도 (rollout r-7c1e)

[[equipment]] · [[coverage]] · [[glossary]] · [[unreadable]]

## 파일군

| family | category (inferred) | conf | members | samples | rel | status |
|---|---|---|---|---|---|---|
| [[families/fam-3f9a1c7b2d40\|PM1 process log]] | event_log | medium | 412 | 3 | 2 | unconfirmed |
| [[families/fam-a10c5e…\|PM1 measurement result]] | measurement_result | high | 1,980 | 5 | 4 | ok |
| [[families/fam-77d0b2…\|PM1 alarm csv]] | alarm | low | 96 | 0 | 1 | no-sample |

## 미해석 / 미표본
- 8개 파일군 no-sample: [[unreadable]] 참조.

## 리뷰 대기
- `review/` 주석이 있는 파일군: 2개.
```

Obsidian 1.9 이상이면 `families.base` 하나로 위 표를 frontmatter에서 직접 뷰로 만들
수 있다[57]; `index.md`의 표는 Obsidian이 없는 사내 위키 렌더러를 위한 정적 사본이다.

### 6.6 멱등 재생성과 링크 무결성

- 입력: `data-map/*.json` + 용어집 + `review/`. 출력: `wiki/` 전체. 같은 입력 → 바이트
  동일 출력(정렬 고정, 시각은 canonical의 값만). 이는 스펙 §4.7.3의 graph/RAG와 같은
  규칙이다.
- 링크는 `family_id`만 가리키므로 사람용 이름이 바뀌어도 링크는 그대로다. `aliases`가
  바뀌면 `[[id|표시명]]`의 표시명만 재생성된다[55].
- 고아 페이지: `families/` 아래 canonical에 없는 ID의 파일은 삭제한다. `review/`의
  고아는 삭제하지 않고 `index.md` "리뷰 대기"에 "대상 없음"으로 표시한다.
- Foam 같은 다른 뷰어는 파일명 충돌 시 알파벳순 해석[60]을 하므로 파일명은 vault 안에서
  유일해야 한다 — 해시 ID가 이를 보장한다.

## 7. (D) 반복 정제 루프

### 7.1 선행 사례

- **Evaluator-optimizer**: "one LLM call generates a response while another provides
  evaluation and feedback in a loop"; 조건은 "clear evaluation criteria, and when
  iterative refinement provides measurable value"[1]. 이 저장소의 평가자는 LLM이 아니라
  코드(`confidence` 분포, coverage, 관계 수)여야 한다 — 스펙 §4.6 "LLM 자기평가
  confidence가 높아도 추론은 추론".
- **Agents 절의 정지 조건**: "it's also common to include stopping conditions (such as
  a maximum number of iterations) to maintain control"[1].
- **Karpathy LLM wiki**: ingest는 "updates relevant entity and concept pages across
  the wiki, and appends an entry to the log", "noting when new data contradicts old
  claims"; lint는 "contradictions between pages, stale claims that newer sources have
  superseded, orphan pages with no inbound links, important concepts mentioned but
  lacking their own page, missing cross-references, data gaps"를 찾는다; 핵심은 "the
  knowledge is compiled once and then kept current"[53].
- **Reflexion**(arXiv 2303.11366): 에이전트가 "verbally reflect on task feedback
  signals, then maintain their own reflective text in an episodic memory buffer"[65].
  **Self-Refine**(arXiv 2303.17651): "the same LLMs provides feedback for its output
  and uses it to refine itself, iteratively"[66]. 두 논문 모두 **같은 모델이 자기 출력을
  평가**하는 구조이므로, 확증 드리프트 위험이 그 구조 자체에 있다. 이 저장소는 평가를
  코드에 두어 그 위험을 피한다.
- **LangGraph 순환 그래프**: 루프 + `END` + `recursion_limit`(기본 1000, 초과 시
  `GraphRecursionError`)[21].
- **능동 학습**: Settles, *Active Learning Literature Survey*, UW–Madison CS TR 1648
  (2010-01-26 갱신): "a machine learning algorithm can achieve greater accuracy with
  fewer training labels if it is allowed to choose the data from which it learns";
  pool-based sampling은 "a small set of labeled data L and a large pool of unlabeled
  data U ... instances are queried in a greedy fashion, according to an informativeness
  measure"[45]. 불확실성 샘플링(least confident / margin / entropy)은 같은 보고서 §3.1.

### 7.2 이 저장소에 대응

pool = inventory의 파일군(스펙 §4.3), label = 검증된 의미 필드, oracle = 내부 LLM +
표본 다운로드, 비용 = `max_download_bytes`·`llm_max_requests`·디렉터리 수. 불확실성
지표는 새로 만들 필요가 없다:

| 우선순위 | 선택 조건 (스펙 필드) | 근거 종류 |
|---|---|---|
| 1 | `inventory_complete: false`인 루트의 미탐색 frontier | coverage.json |
| 2 | `unresolved: no-sample` 파일군 | file-families.json |
| 3 | `confidence: low` 필드가 있는 파일군, `unresolved: invalid-response` | file-families.json |
| 4 | `relationships`가 0이고 표본이 있는 파일군 | file-families.json |
| 5 | `relationship_coverage`가 `feature-limit`/`evidence-limit`로 잘린 파일군 | file-families.json |
| 6 | 이전 pass와 `inferred_category`가 달라진 파일군(churn) | pass 간 diff |

pass N+1:

(a) prior 로드 — `data-map/file-families.json`(canonical)을 읽는다. **위키 md가 아니라
JSON**이다(§4.3). 위키는 사람이 보는 같은 정보다.
(b) 선택 — 위 표 순서로 pass budget(총 budget의 분할분)까지 채운다. 선택은 결정론이고
`plan.json`에 기록되어 hash에 묶인다.
(c) 실행 — 선택된 파일군만 Sampling → Extraction → LLM. Grouping은 새 inventory pass가
있을 때만 전체 재실행하고, `change_state`(`new`/`changed`/`unchanged`/`missing`,
스펙 §4.7.2)로 기존 파일군과 잇는다.
(d) 병합 — 필드 키가 (scope, family 입력 hash, field, 모델·prompt·glossary hash)이므로
(§4.6) 입력이 같으면 재호출하지 않고, 새 표본으로 입력 hash가 바뀐 필드만 다시 묻는다.
새 값은 `pass_id`와 `prior_source_hash`(이전 페이지의 `source_hash`)를 provenance에
더한다. **Observed는 절대 강등하지 않는다**: 관측은 observation_id를 가진 사실이고,
새 pass는 관측을 추가하거나 `missing`으로 표시할 뿐 지우지 않는다. Inferred는 최신
pass의 검증된 값으로 교체하되 이전 값과 confidence를 `history`에 남긴다.
(e) 수렴 — 코드가 계산한다: `low_confidence_families`, `no_sample_families`,
`category_churn`(이전 pass 대비 바뀐 수), `new_relationships`, `frontier_dirs`. 세 값이
연속 두 pass 동안 줄지 않으면 plateau. 총 budget 소진 또는 plateau면 `NEXT: STOP`.

**LLM에 prior를 주는 방식.** 전체 vault를 넣지 않는다. 패킷(§4.6)에 다음만 더한다:
`index.md`의 해당 파일군 행, 그 파일군 페이지의 `## Observed`, 관계로 연결된 파일군
페이지의 `## Observed` 요약, 용어집. **`## Inferred`는 "previous inference (not a
fact), confidence: X" 라벨을 붙인 데이터 블록으로만** 넣고, 시스템 지시에 "prior
inference는 근거가 아니며 evidence로 인용할 수 없다"를 추가한다. evidence 검증기는
이미 패킷에 실제로 든 SHA만 허용하므로(§4.6), prior 문장을 근거로 인용하면 거부된다.
컨텍스트 예산은 `max_tokens`와 별도로 `prior_max_bytes`를 `rollout.json`에 둔다.

**확증 드리프트.** 같은 모델이 자기 추정을 다시 읽으면 굳어진다(Self-Refine·Reflexion
구조의 본질[65][66]). 완화: (1) 평가자는 코드(위 지표), (2) Karpathy의 lint에 해당하는
결정론 검사 — 관계가 있는데 category가 서로 모순(예: `static-reference`인데
`append-series` 관계)인 쌍, 표본이 늘었는데 confidence가 오르지 않는 필드, 고아
파일군 — 을 `coverage.json`에 `lint` 절로 기록[53], (3) `category_churn`이 0인데
`low_confidence`가 줄지 않으면 "더 물어도 소용없음"으로 보고 그 필드를 사람 검토
(`review/`)로 넘긴다. 사람 검토 없이 pass만 늘려 confidence를 올리는 경로를 두지 않는다.

### 7.3 상태·CLI 계약·승인

| 상태 | 위치 | 이유 |
|---|---|---|
| pass 번호, 선택 목록, 수렴 지표 | `audit.jsonl`(`pass-start`, `pass-end` 행) + `plan.json` | 단일 상태 원천(§5.1) |
| 필드 값·provenance·history | `work/llm.sqlite` → `data-map/file-families.json` | §4.6 트랜잭션 규칙 |
| 이전 pass의 지도 | `work/history/<scope>/pass-<n>/` | 스펙 §5.1의 history 규칙 재사용 |
| 사람 주석 | `data-map/wiki/review/` | §6.3 |
| 위키 페이지 | `data-map/wiki/` | 파생물; pass마다 전체 재생성 |

CLI 경계: 새 subcommand를 만들지 않고 `stage 3 next`(또는 4)가 **한 pass = 한 호출**로
동작한다. 종료 코드는 그대로다: pass가 끝나고 더 할 일이 있으면 exit 0 + `NEXT:
equipment-map stage 3 next --rollout <id>`, 수렴·budget 소진이면 exit 0 + `NEXT: STOP`,
연결·잠금 오류는 exit 20. 스킬 표(§9)는 바뀌지 않는다 — 스킬은 `NEXT:`를 따라 다시
부를 뿐이다.

**사용자 결정(승인).** 스펙 §5는 실행 전 계획 승인을 계획 hash에 묶는다. 선택지:
(가) pass마다 `plan` → `approve-plan` → `next` — 안전하지만 사람이 pass 수만큼 승인;
(나) 한 계획에 `max_passes`와 총 budget을 넣고 승인 한 번, 각 pass의 선택 목록은
계획의 결정론 규칙에서 나오므로 hash 안에 포함된 것으로 본다. (나)는 스펙 §6 "승인
후 계획, 대상, 경로 또는 budget이 바뀌면 재승인"과 양립하려면 "pass별 선택은 계획의
파생"이라는 문장을 스펙에 추가해야 한다. 어느 쪽이든 `operator` 명령은 스킬에 들어가지
않는다.

### 7.4 두 스케치

plain Python:

```python
def refine_pass(rollout, audit, db):
    prior = load_families(rollout)                       # data-map/file-families.json
    targets = select_uncertain(prior, rollout.pass_budget)   # §7.2 표 순서, 결정론
    audit.append("pass-start", pass_id=..., targets=len(targets), plan_hash=...)
    for fam in targets:
        sample(fam, rollout.budget); extract(fam)
        for field in FIELDS:
            key = field_key(scope, fam.input_hash, field, cfg_hash)
            if committed(db, key): continue
            reserve(db, key); commit(db, key, validate(field, ask(field, packet(fam, prior))))
    merged = merge(prior, db, never_demote_observed=True)
    write_datamap(merged); render_wiki(merged); manifest(rollout)
    m = metrics(prior, merged)                           # low_conf, no_sample, churn, new_rel, frontier
    audit.append("pass-end", **m)
    return "STOP" if plateau(audit, m) or budget_exhausted(audit) else "NEXT"
```

LangGraph 순환 그래프:

```python
g = StateGraph(S)
g.add_node("select", select_uncertain); g.add_node("sample", sample)
g.add_node("extract", extract); g.add_node("llm", llm_fields)
g.add_node("merge", merge); g.add_node("metrics", metrics)
g.add_edge(START, "select"); g.add_edge("select", "sample")
g.add_edge("sample", "extract"); g.add_edge("extract", "llm"); g.add_edge("llm", "merge")
g.add_edge("merge", "metrics")
g.add_conditional_edges("metrics", lambda s: END if s["plateau"] or s["budget_gone"] else "select")
app = g.compile(checkpointer=SqliteSaver.from_conn_string("work/graph.sqlite"))
app.invoke(init, config={"configurable": {"thread_id": rollout_id}, "recursion_limit": 6 * max_passes})
```

**스펙이 고르는 쪽:** plain Python. 이유는 §3.4와 같고 하나가 더해진다 — 반복 루프의
"한 바퀴"가 곧 스펙의 "한 `next` 호출"이어야 승인·잠금·`REPORT.md` 규칙이 그대로
맞는데, LangGraph 그래프는 한 프로세스 안에서 여러 바퀴를 돌도록 만들어졌고
(`recursion_limit`), 바퀴마다 프로세스를 끝내려면 결국 그래프 바깥에 plain Python
루프를 또 써야 한다.

## 8. 위험과 열린 질문

1. **모델 serving 플래그는 외부 사실이다.** 도구 호출·구조화 출력은 vLLM의
   `--enable-auto-tool-choice --tool-call-parser`[19]나 Ollama 버전[20]에 달렸다. 스펙
   §4.6의 "서버가 반환한 모델 ID·serving 설정 기록"에 tool parser 유무를 추가할지 결정.
2. **`langsmith` 필수 의존.** `langchain-core`를 쓰면 관측 SaaS 클라이언트가 항상
   설치된다[13][14]. 사내 보안 검토 대상인지 확인 필요. 실제 전송 조건은 `[미검증]`.
3. **`review/`의 manifest 처리.** §6.3은 사람 주석 파일을 `data-map/` 안에 두어 결과
   승인에 포함시키는데, 스펙 §5.2는 `data-map/` 변조를 거부한다. "review/는 사람이
   쓰는 예외"를 스펙에 명시할지, `rollouts/<id>/review/`로 빼서 manifest 밖에 둘지 결정.
4. **다중 pass 승인 단위**(§7.3 가/나). 사용자 결정.
5. **위키 페이지에 넣을 경로.** §6.4 예시는 디렉터리 경로를 frontmatter에 넣었다.
   스펙 §5는 stdout만 제한하고 파일에는 경로를 허용하지만, 위키가 사내 위키 서버로
   복사되면 반출 범위가 넓어진다. `directory`를 페이지에서 뺄지 결정.
6. **Obsidian 의존도.** `[[wikilink]]`와 frontmatter는 CommonMark 밖이다[52]. 사내 위키
   렌더러가 wikilink를 지원하지 않으면 `[text](families/id.md)` Markdown 링크로
   전환해야 한다 — 생성기 옵션 하나로 두면 된다[54].
7. **MCP 도입 시 pi 미지원**[31]. 네 도구 지원이 §10 완료 기준이므로 MCP는 보조로만.
8. **PyYAML 부재.** 코드가 위키를 읽지 않는 한 YAML 파서는 필요 없다(쓰기는 문자열
   조립). `review/`를 읽을 때 frontmatter를 두지 않는 이유가 이것이다.
9. **Bases는 early access로 출발한 기능**[58]. 사내 Obsidian 버전이 1.9 미만이면
   `families.base`는 무시된다(텍스트 파일이므로 해가 없다).
10. **Logseq 호환**은 확인하지 못했다 `[미검증]`. `key:: value` 첫 블록 문법[61]과 YAML
    frontmatter를 동시에 만족시키는 파일은 만들지 않는다.

## 출처

[1] Anthropic, "Building effective agents" — https://www.anthropic.com/engineering/building-effective-agents
[2] OpenAI, "A practical guide to building agents" (PDF, pp. 4–16, 24–28) — https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf
[3] LangChain docs, Agents — https://docs.langchain.com/oss/python/langchain/agents
[4] langchain-ai/langchain, `libs/langchain_v1/langchain/agents/factory.py` (master, langchain 1.4.0) — https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/langchain/agents/factory.py
[5] LangChain docs, Models (`init_chat_model` + `base_url`) — https://docs.langchain.com/oss/python/langchain/models
[6] langchain-ai/langgraph, `libs/langgraph/pyproject.toml` (main, 1.2.11) — https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/pyproject.toml
[7] = [5]
[8] LangChain docs, Structured output — https://docs.langchain.com/oss/python/langchain/structured-output
[9] LangChain docs, v1 release notes — https://docs.langchain.com/oss/python/releases/langchain-v1
[10] LangChain docs, Migrate to v1 — https://docs.langchain.com/oss/python/migrate/langchain-v1
[11] langchain-ai/langchain, `libs/langchain_v1/pyproject.toml` (1.4.0) — https://github.com/langchain-ai/langchain/blob/master/libs/langchain_v1/pyproject.toml
[11b] 같은 파일, `requires-python = ">=3.10.0,<4.0.0"`
[12] langchain-ai/langchain, `libs/partners/openai/pyproject.toml` (1.6.2) — https://github.com/langchain-ai/langchain/blob/master/libs/partners/openai/pyproject.toml
[13] langchain-ai/langchain, `libs/core/pyproject.toml` (1.6.3) — https://github.com/langchain-ai/langchain/blob/master/libs/core/pyproject.toml
[14] langchain-ai/langsmith-sdk, `python/pyproject.toml` — https://github.com/langchain-ai/langsmith-sdk/blob/main/python/pyproject.toml
[15] openai/openai-python, `pyproject.toml` (3.14.0) — https://github.com/openai/openai-python/blob/main/pyproject.toml
[16] pydantic/pydantic-ai, `pydantic_ai_slim/pyproject.toml` — https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pyproject.toml ; OpenAI-compatible 설정 — https://pydantic.dev/docs/ai/models/openai/
[17] Pydantic AI docs, Output — https://pydantic.dev/docs/ai/core-concepts/output/
[18] OpenAI Agents SDK docs, Models — https://openai.github.io/openai-agents-python/models/
[19] vLLM docs, Tool Calling — https://docs.vllm.ai/en/latest/features/tool_calling.html ; Structured Outputs — https://docs.vllm.ai/en/latest/features/structured_outputs.html
[20] Ollama docs, OpenAI compatibility — https://docs.ollama.com/api/openai-compatibility ; Tool calling — https://docs.ollama.com/capabilities/tool-calling ; Structured outputs — https://docs.ollama.com/capabilities/structured-outputs
[21] LangGraph docs, Graph API — https://docs.langchain.com/oss/python/langgraph/graph-api
[22] LangChain docs, Middleware — https://docs.langchain.com/oss/python/langchain/middleware
[23] LangGraph docs, Interrupts — https://docs.langchain.com/oss/python/langgraph/interrupts
[24] LangGraph docs, Persistence — https://docs.langchain.com/oss/python/langgraph/persistence
[25] langchain-ai/langgraph, `libs/checkpoint-sqlite/pyproject.toml` (3.1.1) 및 README — https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-sqlite
[25b] langchain-ai/langgraph, `libs/checkpoint/pyproject.toml` (4.2.0) — https://github.com/langchain-ai/langgraph/blob/main/libs/checkpoint/pyproject.toml
[25c] langchain-ai/langgraph, `libs/sdk-py/pyproject.toml` — https://github.com/langchain-ai/langgraph/blob/main/libs/sdk-py/pyproject.toml
[26] LangChain docs, Custom middleware — https://docs.langchain.com/oss/python/langchain/middleware/custom
[27] Agent Skills specification — https://agentskills.io/specification
[28] Claude Code docs, Skills — https://code.claude.com/docs/en/skills ; Memory (CLAUDE.md) — https://code.claude.com/docs/en/memory
[29] Codex docs, Build skills — https://learn.chatgpt.com/docs/build-skills
[30] OpenCode docs, Skills — https://opencode.ai/docs/skills/
[31] badlogic/pi-mono, `packages/coding-agent/README.md` (main) — https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/README.md ; https://pi.dev/docs
[32] Claude Code docs, MCP — https://code.claude.com/docs/en/mcp
[33] Codex docs, MCP — https://learn.chatgpt.com/docs/extend/mcp?surface=cli
[33b] Codex docs, AGENTS.md — https://learn.chatgpt.com/docs/agent-configuration/agents-md
[34] OpenCode docs, MCP servers — https://opencode.ai/docs/mcp-servers/
[34b] OpenCode docs, Rules — https://opencode.ai/docs/rules/
[35] Model Context Protocol specification 2025-06-18 — https://modelcontextprotocol.io/specification/2025-06-18
[36] modelcontextprotocol/python-sdk, `pyproject.toml` — https://github.com/modelcontextprotocol/python-sdk/blob/main/pyproject.toml
[37] = [28] Memory
[38] openai/openai-agents-python, `pyproject.toml` (0.22.2) — https://github.com/openai/openai-agents-python/blob/main/pyproject.toml
[39] PyPI, xxhash — https://pypi.org/project/xxhash/
[40] PyPI, pydantic-core — https://pypi.org/project/pydantic-core/
[41] PyPI, ormsgpack — https://pypi.org/project/ormsgpack/
[42] Qwen docs, Function Calling — https://qwen.readthedocs.io/en/latest/framework/function_call.html
[43] PyYAML documentation — https://pyyaml.org/wiki/PyYAMLDocumentation
[44] Python 3.11 docs, `tomllib` — https://docs.python.org/3.11/library/tomllib.html
[45] B. Settles, "Active Learning Literature Survey", Computer Sciences Technical Report 1648, University of Wisconsin–Madison (updated 2010-01-26) — https://burrsettles.com/pub/settles.activelearning.pdf
[46] Obsidian Help, Properties — https://obsidian.md/help/properties
[47] PyPI, python-frontmatter — https://pypi.org/project/python-frontmatter/
[48] PyPI, markdown-it-py — https://pypi.org/project/markdown-it-py/
[49] PyPI, mistune — https://pypi.org/project/mistune/
[50] langchain-ai/langchain-community, `document_loaders/obsidian.py` — https://github.com/langchain-ai/langchain-community/blob/main/libs/community/langchain_community/document_loaders/obsidian.py
[51] LangChain docs, MarkdownHeaderTextSplitter — https://docs.langchain.com/oss/python/integrations/splitters/markdown_header_metadata_splitter
[52] CommonMark Spec 0.31.2 (2024-01-28) — https://spec.commonmark.org/0.31.2/
[53] A. Karpathy, "LLM Wiki" gist (2026-04-04) — https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
[54] Obsidian Help, Internal links — https://obsidian.md/help/links
[55] Obsidian Help, Aliases — https://obsidian.md/help/aliases
[56] Obsidian Help, Tags — https://obsidian.md/help/tags
[57] Obsidian Help, Bases — https://obsidian.md/help/bases
[58] Obsidian changelog 1.9.0 desktop early access (2025-05-21) — https://obsidian.md/changelog/2025-05-21-desktop-v1.9.0/
[59] Dataview docs, Adding metadata — https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/
[60] foambubble/foam, `docs/user/features/wikilinks.md` — https://github.com/foambubble/foam/blob/master/docs/user/features/wikilinks.md
[61] logseq/docs, `pages/Properties.md` — https://github.com/logseq/docs/blob/master/pages/Properties.md
[62] SQLite, "Appropriate Uses For SQLite" — https://www.sqlite.org/whentouse.html
[63] Apache Parquet, Overview — https://parquet.apache.org/docs/overview/
[64] W3C, JSON-LD 1.1 Recommendation (2020-07-16) — https://www.w3.org/TR/json-ld11/
[65] N. Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning", arXiv:2303.11366 — https://arxiv.org/abs/2303.11366
[66] A. Madaan et al., "Self-Refine: Iterative Refinement with Self-Feedback", arXiv:2303.17651 — https://arxiv.org/abs/2303.17651
