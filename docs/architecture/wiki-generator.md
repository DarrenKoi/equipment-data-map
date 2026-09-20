# Wiki 생성기와 폴더 추가 조사

> 전체 구조와 목표 개선 루프는 [통합 아키텍처](equipment-data-map.md)를 따른다. 이 문서는 현재 오프라인 구현의 사용법이며, 사전 생애주기·의미 검토·iteration 보고서 등 신규 목표 기능은 아직 포함하지 않는다.

> 2026-09-19 · 구현된 범위: 오프라인 검토용 Wiki와 SQLite 조사 이력. 실제 FTP 수집, LLM 호출, 승인 상태 전환, graph 생성은 포함하지 않는다. [전체 개선안](equipment-data-parser-performance-proposal.md)의 첫 구현 단위다.

## 어떻게 쓰는가

엔지니어가 **“`/Data/Logs`를 더 자세히 조사해줘”**라고 요청하면 office LLM은 폴더 조사 요청을 기록하고 `plan`을 읽는다. 이 요청은 해당 폴더와 모든 알려진 하위 파일에 적용된다. 이전에 분석했던 표본도 새 요청 이후의 재해석 대상으로 열린다. 아직 발견하지 못한 파일은 추측하지 않고 `frontier`와 inventory 미완료로 남긴다.

1. `suggest`: 조사할 폴더·파일, 질문, 요청자, iteration을 기록한다.
2. `plan`: 현재 표본은 `interpret`, 추가 표본이 필요한 파일은 `review-sampling`, 보호 대상은 `blocked`로 구분한다.
3. office 실행기가 기존 승인·budget·샘플 정책 안에서 조사한다. 제출한 정확한 표본 집합을 `submitted`, 검증까지 마친 처리 결과를 `finished`로 기록한다. 실패·불명 상태는 완료로 세지 않는다.
4. 실행기는 새 extract·검증된 해석을 반영한 map projection과 manifest를 만든다. 생성기는 이 최신 입력으로 **새 출력 폴더**의 모든 `index.md`를 갱신한다. 원래 map과 이전 Wiki는 수정하지 않는다.

기존에 표본이 있는 파일군의 다른 파일을 요청하면 `family-capped`로 표시한다. 이 요청 자체가 표본 상한이나 선정 규칙을 바꾸지는 않는다. 엔지니어의 정책·프로필 검토가 필요하다. 보호 대상은 요청 중요도가 높아도 자동 접근하지 않는다. 생성기는 이름 필터를 중복 적용하지 않고 수집기가 엔지니어 예외까지 반영한 per-file `status`를 따른다. 기본 제외와 `temperature.csv` 같은 오탐 예외는 승인된 수집 정책에서 처리해야 한다. 조사 제안 자체로 status를 바꾸면 안 된다.

## 합성 데이터로 바로 실행

```sh
python -m tools.wiki_demo --output ./wiki-demo
```

새 폴더에 검증 가능한 `map/`, 조사 원장, `iteration-1/`, `iteration-2/`를 만든다. `iteration-2/wiki/index.md`부터 열면 된다. 표본과 성공 이벤트 모두 합성이며 FTP·LLM 호출이 없다. `wiki-demo`가 이미 있으면 다른 새 이름을 지정한다. 실제 의미 보충은 office 실행기가 검증한 해석을 새 map에 넣어야 한다.

## 실행 명령

저장소 루트에서 Python 3.11 이상으로 실행한다. 런타임은 표준 라이브러리만 사용한다. 아래 경로는 합성 예시이며 기존 office 파일 형식이 자동으로 호환된다는 뜻은 아니다.

```sh
python -m wiki_review.publish ./review-input --output ./reviews/iteration-1 --journal ./reviews/exploration.sqlite --iteration 1
python -m wiki_review.exploration --journal ./reviews/exploration.sqlite suggest ./review-input --path /Data/Logs --reason "로그 필드와 오류 조건을 더 자세히 조사" --actor engineer --iteration 2
python -m wiki_review.exploration --journal ./reviews/exploration.sqlite plan ./review-input
python -m wiki_review.exploration --journal ./reviews/exploration.sqlite read-page ./reviews/iteration-1 --page Data/Logs/index.md --actor qwen
```

office LLM에 주는 요청 예시:

> `/Data/Logs`를 더 자세히 조사해줘. 위 suggest 명령으로 질문을 남기고 plan의 requested 항목을 검토해. Wiki는 read-page로 읽어. 보호 파일은 건드리지 말고 추가 수집이 필요하면 현재 승인과 표본 규칙 안에서 가능한지 확인해. 각 해석 호출의 실제 입력 표본을 submitted로 기록하고, 결과 검증 후 finished를 남겨. 근거가 확인된 결과를 새 map projection으로 내보낸 뒤 iteration-2 Wiki를 생성해. 추측은 Inferred에만 넣어.

호출 추적은 실행기에 다음 두 지점을 연결한다. `request-id`는 호출마다 유일해야 한다. 반복한 같은 제출 기록은 중복 삽입하지 않으며, 같은 ID의 다른 입력이나 terminal 결과 변경은 거부한다.

```sh
python -m wiki_review.exploration --journal ./reviews/exploration.sqlite submitted ./review-input --request-id request-2 --path /Data/Logs/run.csv --actor qwen --iteration 2
# The existing office worker sends the bounded request and validates its result here.
python -m wiki_review.exploration --journal ./reviews/exploration.sqlite finished --scope scope-a --request-id request-2 --outcome succeeded
# Export the updated verified map projection to review-input before publishing.
python -m wiki_review.publish ./review-input --output ./reviews/iteration-2 --journal ./reviews/exploration.sqlite --iteration 2
```

`--path`는 실제 호출에 포함한 표본만큼 반복한다. 이 도구는 호출 패킹·8 worker·토큰 budget을 구현하지 않는다. Wiki 생성에는 LLM 호출이 없다. Python에서 `DataMap`, `publish`, `Journal`을 import해 subprocess 없이 같은 API를 사용할 수 있다.

## 사람과 LLM이 읽는 결과

```text
reviews/
  exploration.sqlite            # iteration 공통 조사 원장
  iteration-1/
    manifest.json               # 검토 사본 파일 hash, 원본 index hash
    next-actions.json           # 검토 항목, 요청, 기록된 Wiki 열람
    wiki/index.md
    wiki/Data/index.md
    wiki/Data/Logs/index.md
  iteration-2/                  # 보충된 최신 지도, 이전 결과 보존
```

각 `index.md`는 폴더 개요 → 하위 폴더 설명 → 대표 파일의 형식·필드·부분 관측 여부 → Observed/Fields/Inferred/Evidence/Relationships/Unresolved → 접근 기록과 추가 조사 순서다. 자식 설명을 읽고 하위 페이지로 이동하며, 부모로 돌아갈 수 있다. 의미 요약은 이미 검증한 claim만 재사용한다. 근거 없는 폴더 용도는 확정하지 않는다. 원본 표본을 활성 링크로 만들지 않는다.

`manifest.json`은 사본 무결성 검사용이며 **엔지니어 승인 증명은 아니다**. 모든 출력은 `approval_verified: false`로 표시한다. 현재 구현은 stage 4의 전체 publisher가 아니며 graph나 승인 manifest를 대체하지 않는다. Obsidian은 이 외부 검토 사본을 열 수 있지만, 페이지를 편집하면 `read-page`의 hash 검사가 실패한다. 원본 map에서 새 사본을 생성한다.

## 접근 기록이 뜻하는 것

| 기록 | 확인할 수 있는 것 | 확인할 수 없는 것 |
|---|---|---|
| `page-read` | wrapper가 검증된 Wiki 페이지 바이트를 반환했다 | 다른 파일 도구로 직접 읽은 접근, LLM의 이해 |
| `submitted` | 호출자가 해당 scope·경로·observation·sample/extract hash를 입력으로 보고했다 | 서버가 실제로 받았는지, 전체 원본을 읽었는지 |
| `finished: succeeded` | 호출자가 해당 요청의 성공을 보고했다 | 해석 정답, 장비 전체 조사 완료 |
| `suggestion` | 특정 파일/폴더에 추가 질문이 있다 | 보호 규칙 예외 승인, 다운로드 권한 |

완료를 옮겨 붙이지 않도록 scope·원격 경로·sample/extract hash·observation을 맞춘다. 같은 바이트의 다른 경로는 다른 파일이다. 새 질문 **이후에 제출되고 성공한** 요청만 그 질문의 완료로 인정한다. 진행 중이던 이전 요청이 늦게 끝나도 새 질문은 남는다. extract가 바뀌거나 scope가 바뀌면 과거 성공을 자동 재사용하지 않는다. 이로 인해 다른 scope로 넘어간 질문을 자동 이관하지 않으며 엔지니어가 새 scope에서 다시 요청해야 한다.

폴더 요청은 하위 파일에 모두 적용하고 미탐색 frontier를 함께 표시한다. 해석할 표본이나 미탐색 frontier가 남으면 `pending`이다. 표본을 모두 처리해도 보호·미수집 파일이 남으면 `review-required`와 `residual`의 사유별 개수를 표시한다. 완료한 표본을 계속 재호출하지 않으며 잔여 파일을 모두 읽었다고 표시하지도 않는다. 잔여 항목이 없는 조사만 `addressed`다. 목록이 갱신되면 같은 scope의 폴더 요청에 새로 발견된 파일도 포함한다. 다음 조사 항목은 **검토 목록**으로만 출력하며 운영 pass scheduler의 우선순위·승인·누적 budget을 변경하지 않는다.

## 입력 계약: wiki-map-v1

기존 canonical map의 파일명과 근거 개념을 사용하는 **명시적 projection**이다. office 구현이 다른 스키마라면 그 환경에서 adapter가 아래 구조로 내보내야 한다. 이를 위해 office LLM이 매번 Python을 새로 작성할 필요는 없지만, 아직 확인하지 못한 office 구현의 adapter를 여기서 완성했다고 할 수는 없다. export 결과를 기존 승인 map과 분리한다.

| 파일 | 필수 구조 |
|---|---|
| `index.json` | `schema_version: "wiki-map-v1"`, `files: {상대 경로: 원시 바이트 SHA256}`. 아래 JSON/JSONL과 모든 참조 표본 포함. 자기 자신 제외 |
| `equipment.json` | 같은 `schema_version`, 문자열 `scope`, `pass_id`, 허용 절대 경로 배열 `roots` |
| `paths.json` | 배열. 각 항목은 `source_path`, `local_path`, `status: ancestor/inventoried/frontier`. `/`와 모든 상위 폴더 포함 |
| `file-families.json` | 배열. `family_id`, `scope`, `directory`, `rule`, `kind`, `member_count`, `samples`, `metadata_evidence`, `interpretations`, `relationships: []`, `unresolved` |
| `coverage.json` | 원본 coverage 정보. 적어도 `inventory_complete`, `stop_reasons`를 유지 |
| `metadata-evidence.jsonl` | 파일군마다 `scope`, `family_id`, `entries` 배열. 각 entry는 `source_path`, `observation_id`, `size`, `status: eligible/denied/active_candidate/unreadable/unknown`. 해당 파일군의 알려진 파일 상태를 누락 없이 projection에 담는다 |
| `extracts.jsonl` | 표본마다 `scope`, `source_path`, `observation_id`, `sample_sha256`, `method`, `encoding`, `truncated`, `fields` 배열 |
| `evidence/<매핑 경로>` | 검증할 대표 표본 원본. Wiki 내용에 원문을 복사하지 않는다 |

`sample` 구조:

```json
{"source_path":"/Data/Logs/run.csv","local_path":"evidence/Data/Logs/run.csv","sha256":"<raw SHA256>","observation_id":"logs-1","extract_sha256":"<extract payload SHA256>"}
```

`fields`의 각 항목은 `name`, `type_counts`(예: `{"float":2}`), `unit`, `min`, `max`, `examples`다. 예시는 최대 3개·값당 40자로 표시한다. 민감한 필드의 범위와 예시는 `(masked)`로 바꾸며, 동일 문자열이 해석에 나타나도 Wiki에서 가린다. 자유 텍스트는 가리되 경로·hash·observation·locator 같은 근거 식별자는 보존한다. 이는 최소 필터이며 엔지니어의 민감정보 검토를 대체하지 않는다.

`interpretations`의 각 항목은 `claim_id`, `value`, `observed_vs_inferred: "inferred"`, `confidence`, `evidence` 배열이다. 이 projection은 **검증된 의미 해석의 전달 형식**이며 생성기가 의미의 진실성이나 인과성을 자동 판정하지 않는다. citation은 다음 형식이고 `/fields/N` 또는 그 필드의 `name/type_counts/unit/min/max/examples` locator를 지원한다.

```json
{"evidence_kind":"sample","source_path":"/Data/Logs/run.csv","sha256":"<raw SHA256>","observation_id":"logs-1","extract_sha256":"<extract payload SHA256>","locator":"/fields/0"}
```

record payload SHA는 `json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')`의 SHA256이다. JSONL 개행은 payload hash에 포함하지 않는다. `metadata_evidence`는 해당 metadata record의 payload SHA다. 현재 projection은 field locator만 지원하고, 관계 record가 있으면 조용히 누락하지 않고 거부한다. 운영 map에 관계·다른 locator가 있으면 해당 adapter/publisher 확장이 먼저 필요하다.

로컬 경로는 canonical 4.7절의 전체 원격 경로 percent-encoding을 따른다. 대소문자 충돌, 상위 폴더 누락, traversal, symlink/junction, scope/hash/observation 불일치를 거부한다. projection의 폴더 매핑은 80자, 표본 매핑은 85자 이하로 제한한다. 더 긴 원격 항목의 생략 정보는 원본 coverage에 유지한다. 출력은 새 폴더만 허용하고 원본 map 및 원장과 겹칠 수 없다. 전체 index hash를 엔지니어의 승인 hash와 비교하는 기능은 아직 없다.

## 확인한 범위

```sh
python -m pytest -q tests/test_wiki_generator.py
```

합성 표본으로 설명 우선 탐색, 인코딩된 링크, 결정론적 재생성, 원본 불변, metadata-only, 민감값 가리기, 잘못된 근거/경로 거부, 접근과 해석 구분, 실패·재시도·scope/extract 변경, 폴더 추가 요청과 보호 대상 보존을 검사한다. 실제 office 스키마, Windows 실행, pi/Qwen 연동, 장비 성능은 별도 검증이 필요하다.
