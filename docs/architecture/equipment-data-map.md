# Equipment Data Map 아키텍처

## 1. 목표

FAB 장비의 FTP/SMB 파일 구조를 읽기 전용으로 탐색하고, 반복되는 파일을 묶어 최소한의 대표 샘플만 분석하여 **장비 데이터 지도**를 만든다.

장비 데이터 지도는 다음 질문에 답해야 한다.

- 어떤 경로에 어떤 성격의 파일이 있는가?
- 파일명, 디렉터리, 생성 시각에는 어떤 규칙이 있는가?
- 파일 안에는 어떤 필드와 데이터가 있으며 무엇에 쓰이는가?
- 같은 형식의 파일은 얼마나 자주, 얼마나 많이 생성되는가?
- 해석하지 못한 파일과 그 이유는 무엇인가?
- 운영, 장애 분석, Wiki, RAG에서 어떤 근거 파일을 찾아야 하는가?

원본 파일과 분석 결과는 회사망 밖으로 반출하지 않는다.

## 2. 핵심 원칙

1. **읽기 전용:** 장비에서 생성, 수정, 삭제, 이름 변경을 수행하지 않는다.
2. **목록 우선:** 전체 파일을 복제하지 않고 메타데이터 목록부터 수집한다.
3. **규칙 우선, LLM은 대표 샘플만:** 경로·파일명·확장자·크기·헤더로 먼저 묶고, 모호한 분류와 의미 해석에만 로컬 LLM을 사용한다.
4. **근거 보존:** 모든 해석에는 장비, 경로, 샘플, 추출 방식과 신뢰도를 남긴다.
5. **재개 가능:** 중단되어도 체크포인트부터 다시 시작한다.
6. **부하 제한:** 장비별 동시 연결 수, 초당 요청 수, 다운로드 용량과 실행 시간을 제한한다.
7. **모르는 것은 모른다고 기록:** 암호화·손상·독점 형식 파일도 누락하지 않고 `unreadable` 상태로 지도에 남긴다.

## 3. 전체 흐름

```text
장비 FTP/SMB
    |
    v
[1. Inventory] -- 경로, 크기, 시각 등 메타데이터만 수집
    |
    v
[2. Grouping] -- 경로/파일명/확장자/크기/헤더로 파일군 생성
    |
    v
[3. Sampling] -- 파일군별 소수 대표 파일만 회사 PC에 저장
    |
    v
[4. Extraction] -- 텍스트, 표, 설정, 로그, 바이너리 메타데이터 추출
    |
    v
[5. Local LLM] -- 파일 의미, 필드, 생성 주기, 운영 용도 추론
    |
    v
[6. Data Map] -- 구조화된 JSON + 사람이 읽는 Markdown 생성
    |                         |
    v                         v
  Wiki                       RAG
```

`data-map/` 디렉터리를 기준 데이터 세트로 삼고 Wiki와 RAG 문서는 그 안의 구조화 데이터에서 만든 파생 산출물로 취급한다. 서로 다른 결과를 별도로 관리하지 않는다.

### 3.1 두 종류의 단계

이 문서에는 서로 다른 두 단계 축이 있다.

- 위 흐름의 6단계는 한 번의 분석 실행 안에서 반복되는 **런타임 파이프라인**이다.
- 8장의 5단계는 장비, 현장 또는 버전별로 담당 운영자가 수행하고 승인하는 **rollout 단계**다.

Skill Market에 배포할 단계별 스킬은 rollout 5단계에 대응한다. 런타임 파이프라인은 스킬에 분산하지 않고 단일 CLI가 실행한다.

## 4. 모듈 구조

### 4.1 Source

FTP와 SMB의 차이를 숨기는 실제 seam이다. 두 adapter는 동일한 읽기 전용 interface를 제공한다.

- 디렉터리 목록 조회
- 파일 크기 조회
- 크기 상한을 전송 계층에 요구하지 않고 가능한 대표 파일을 통째로 다운로드
- 연결 종료

쓰기 동작은 interface에 포함하지 않는다.

FTP adapter는 사내 `ftp_handler` 라이브러리 위에 올린다. 전송 방식은 호출부의
선택이 아니라 기계의 속성이다. Windows 엔지니어 PC는 FTP egress가 막혀 있어
HTTP proxy를 거치고, Linux 호스트는 장비에 직접 붙는다. 두 전송 방식은 같은
`FtpFleetDownloader` 표면을 제공하며 `ftp_handler.fleet_downloader()` 가 그
기계에 맞는 쪽을 고른다.

외부 접근을 방화벽으로 통제하는 사내 전용망에서 실행한다. FTP proxy와
내부 LLM endpoint는 운영·시험 환경 모두 `http://`를 사용한다. HTTPS/TLS를
실행 선행조건으로 요구하거나 URL을 자동 승격하지 않는다. 이 정책은 HTTP
endpoint에 적용하며 장비 쪽 FTP/SMB 프로토콜은 그대로 사용한다.

proxy의 위치는 배포 사실이므로 소스 트리에 두지 않는다. `FTP_PROXY_URL`,
`FTP_PROXY_TOKEN`과 전송 방식 강제용 `FTP_TRANSPORT`는 기계별 `.env`에서 읽고
실제 환경 변수가 우선한다. 이 값이 맞는지는 사람이 아니라 `preflight`가
확인하며, 확인 전에는 어떤 단계도 장비에 접속하지 않는다.

부분 범위 읽기는 interface에 넣지 않는다. `ftp_handler`의 일반 다운로드로
대표 파일 전체를 받는다. 이 라이브러리는 전송 중 파일 크기를 제한하지 않으며,
이를 우회하는 별도 downloader나 upstream 크기 제한 기능을 선행조건으로 만들지 않는다.
조회 크기가 없거나 파일별 참고 크기를 넘어도 승인된 대표 파일은 다운로드를
시도할 수 있다. 크기 조회는 추정·기록용이며 파일별 크기 때문에 제외하지 않는다.
실제 받은 바이트와 추정 초과를 기록하고 성공한 전체 파일을 evidence로 보존한다.
다운로드 실패는 메타데이터와 실패 사유로 남긴다. 추출기의 입력·출력 제한은 별개다.

### 4.2 Inventory

파일 내용을 내려받지 않고 다음 메타데이터를 로컬 카탈로그에 저장한다.

- 장비 식별자와 프로토콜
- 전체 경로
- 파일 크기와 수정 시각
- 수정 시각의 출처(`LIST`, `MDTM`, `SMB`)와 원본 표기
- UTC로 정규화한 수정 시각과 정규화 가능 여부
- 확장자
- 탐색 시각과 성공/실패 상태

장비의 파일 목록이 매우 크면 디렉터리 단위 체크포인트를 남긴다. Sampling 이후에는 파일군 단위로 체크포인트를 남긴다.

### 4.3 Grouping

LLM 호출 전에 파일군을 만든다.

- 날짜, 시각, lot, wafer, recipe, sequence처럼 변하는 파일명 부분 정규화
- 상위 디렉터리와 확장자
- 파일 크기 구간
- 사전 파일군마다 제한된 대표 파일을 통째로 받아 앞부분 바이트로 판정한 형식 signature

하나의 파일군은 “같은 생성 규칙과 내부 포맷을 가진 것으로 추정되는 파일 집합”이다. 그룹 규칙과 예외 파일을 함께 기록해 잘못 묶인 결과를 추적할 수 있게 한다. 형식 판정용 다운로드는 경로·확장자·크기로 만든 사전 파일군마다 계획에 정한 최대 파일 수와 요청 수를 넘지 않으며, 파일별 크기만으로 후보를 제외하지 않는다. 접근 제한·표본 수 소진·다운로드 실패로 표본이 없으면 signature 없이 경로·확장자·크기만으로 묶고 그 사유를 기록한다.

### 4.4 Sampling

기본적으로 파일군마다 다음 대표본만 선택한다.

- 가장 오래된 파일 1개
- 가장 최신 파일 1개
- 크기가 중앙값에 가까운 파일 1개
- 크기 또는 헤더가 크게 다른 예외 파일 최대 2개

동일한 파일은 다운로드한 바이트의 SHA-256으로 중복 제거한다. 받은 표본은 언제나 파일 전체이며, budget을 넘어 받지 않은 파일은 표본이 아니라 메타데이터 전용 항목으로 사유와 함께 기록한다. 파일군의 형식이 일관되지 않으면 샘플 수를 제한 범위 안에서 늘리고, 일관되면 추가 다운로드를 멈춘다.

엔지니어는 rollout 설정에 허용 루트, 실시간 데이터 후보 경로와 샘플 다운로드 allow/deny 패턴을 입력한다. deny 대상은 내용을 다운로드하지 않고 메타데이터만 기록한다. 단일 inventory에서 최신 파일이 확인되면 `active_candidate`로만 표시한다. 주기 갱신은 기존 파일들의 시각 간격 또는 두 번 이상 inventory의 변화를 근거로 확인하며, 근거가 부족하면 주기를 `unknown`으로 둔다.

실행마다 다음 budget을 설정한다.

- 장비별 최대 다운로드 파일 수
- 파일별 참고 바이트 (`max_file_bytes`: 초과 기록용이며 다운로드 거부 조건이 아님)
- 전체 목표 바이트 (완료된 전송의 실제 사용량이 도달하면 다음 다운로드부터 중단)
- 최대 실행 시간
- 최대 동시 연결 수
- 초당 최대 요청 수
- 최대 목록 항목 수와 디렉터리 깊이
- 사전 파일군별 헤더 읽기 파일 수와 전체 헤더 요청 수

모든 내용 다운로드는 Grouping의 signature 조회와 Sampling 모두 같은 `download_guard`를 거친다. 사전 파일군을 메타데이터로 먼저 만들고 최신·실시간·변경 중 후보를 표시한 후에만 signature 후보를 고른다. 허용 루트, allow/deny, `active_candidate`, 남은 전체 목표 바이트·파일 수·요청·시간 budget을 전송 전에 검사한다. 파일별 크기는 참고값으로 기록하며 다운로드 허용 조건으로 사용하지 않는다. 헤더용 전체 파일도 전체 다운로드 budget에 포함하고, 이미 받은 동일 입력은 Sampling에서 재사용한다. 후보가 없으면 signature 없이 메타데이터와 생략 사유를 남긴다. 두 번의 목록이 같다는 사실만으로 최신·실시간 후보가 쓰기 완료됐다고 판단하지 않는다. 안정성을 확인할 근거가 없으면 내용을 받지 않는다.

direct와 proxy의 바이트 budget은 best-effort다. 전송 중 성장한 파일이나 크기를
몰랐던 파일 때문에 실제 전송량이 파일별 참고값 또는 전체 목표를 넘을 수 있다.
크기 제한을 흉내 내거나 파일을 잘라내지 않는다. 성공한 전체 파일과 실제 크기,
추정 초과 여부를 보존하고 전체 목표에 도달했으면 다음 전송을 시작하지 않는다.
전송 시도와 알려진 추정량을 먼저 기록하고 완료 후 실제 사용량으로 갱신한다.
중단되어 실제 사용량을 알 수 없는 전송은 `usage-unknown`으로 남겨 엔지니어가
작업 종료와 사용량을 확인하기 전 새 전송을 시작하지 않는다. 재개로 사용량을
초기화하지 않으며 네트워크 바이트의 엄격한 상한을 보장했다고 보고하지 않는다.

초당 요청 수는 누적 요청 수 상한이 아니라 전송 속도다. 남은 시간 안에서
다음 요청을 기다리며, 대기 시간이 남은 시간을 넘으면 중단한다. 메타데이터
호출과 재연결도 같은 속도 제한을 적용한다. 접근 시간대는 시작할 때뿐 아니라
매 장비 요청과 전송 중에도 확인하며, 종료 시각 이후 작업이 계속되지 않게 한다.
다운로드 파일 수는 전송 시도 기준이고 내용 hash 중복 제거는 사용량을 환급하지 않는다.

### 4.5 Extraction

먼저 결정론적인 도구로 내용을 추출한다.

- 일반 텍스트와 로그: 인코딩 판별 후 제한된 구간 읽기
- CSV/TSV: 열 이름, 자료형 추정, 일부 행
- JSON/XML/INI: 키 구조와 일부 값
- 압축 파일: 목록만 확인하고 허용된 크기 안에서만 내부 표본 추출
- 이미지: 크기, 포맷 등 메타데이터
- 알 수 없는 바이너리: magic bytes, 문자열 조각, entropy 등 안전한 특징

실행 파일은 실행하지 않으며 매크로도 활성화하지 않는다. 압축 파일은 해제 출력 바이트 상한을 적용하고 중첩 압축은 1단계까지만 읽는다. XML 외부 엔티티는 비활성화한다. 1차 범위에서는 암호화 파일을 해독하지 않고 `unreadable: encrypted`로 기록한다.

높은 entropy만으로 암호화라고 확정하지 않는다. 암호화 flag 등 확인 가능한
형식 근거가 있을 때만 `encrypted`로 기록하고, 그 밖의 알 수 없는 바이너리는
`unsupported`와 낮은 신뢰도의 추정으로 남긴다. 파서 입력 바이트, 출력 바이트,
행·노드·압축 항목 수, 압축 해제 바이트와 실행 시간을 유한하게 제한한다.
제한에 걸린 추출 결과는 일부만 관측했음을 표시하며 완전한 파일 구조로 취급하지 않는다.

**Extractor workbench.** 미지원 형식은 엔지니어가 승인된 대표 샘플 하나를 `rollouts/` 밖의 로컬 복사본 디렉터리에 두고 엔지니어 전용 명령 `equipment-map workbench <copy-dir> --method <name>`으로 추가 방법을 시도한다. 시도마다 `<copy-dir>/attempts.jsonl`에 `{ts, input_sha256, method, method_config, result_sha256|null, failure_reason|null, next_safe_action}`을 append만 한다. `hermes-gui` 방법은 추출을 실행하지 않고 `<copy-dir>/handoff.json`(입력 hash, 엔지니어가 지정한 승인 GUI 도구, 허용 출력 경로)만 쓰며, 사람이 감독하는 Hermes 세션의 결과는 엔지니어가 `--record`로 기록한다. workbench는 `rollouts/`와 `data-map/`에 쓰지 않으며, 성공한 방법은 별도 검토·테스트를 거친 CLI 릴리스의 새 extractor 모듈로만 승격한다. 그 전까지 해당 파일군은 `unsupported-format` 보고로 남는다.

### 4.6 Local LLM Analysis

CLI는 회사 내부의 승인된 OpenAI 호환 endpoint를 직접 호출한다. 에이전트 도구의 대화 모델에는 원본이나 추출 내용을 전달하지 않는다. 내부 로컬 LLM에는 원본 전체가 아니라 다음 묶음을 전달한다.

- 파일군 규칙과 통계
- 대표 샘플에서 추출한 제한된 내용
- extractor가 만든 구조
- 이미 알려진 장비·공정 용어집
- 근거 인용을 위한 해당 입력 묶음의 sample SHA-256 식별자

LLM에는 파일군 설명, 필드 의미, 생성 주체, 예상 생성 주기, 운영 활용법, 민감도, 신뢰도와 근거 샘플을 한꺼번에 JSON으로 만들게 하지 않는다. CLI가 필드별로 짧은 응답을 요청하고 JSON을 조립·검증한다. 신뢰도(`confidence`: `high`|`medium`|`low`)와 근거 샘플(`evidence`: 해당 파일군 evidence 디렉터리에 실제로 존재하는 SHA-256 목록)도 각각 별도 요청과 검증기를 거치는 필드다. 필드당 의미 검증 응답 슬롯은 최대 2개다. 일시적인 전송 실패는 의미 검증 실패로 세지 않으며 아래의 별도 상한을 따른다. 두 시도가 모두 실패하면 `confidence: low`와 `unresolved` 사유를 기록하고 다음 항목으로 진행한다. 추론과 관찰 사실을 구분하고 LLM 유래 필드마다 `model_id`, `model_config`, `prompt_version`과 `glossary_version`을 남긴다.

LLM 실행 설정은 `llm.model`(요청할 모델 또는 사내 alias), `temperature`, `max_tokens`, `connect_timeout_seconds`, `request_timeout_seconds`, `max_elapsed_seconds`, `transport_max_attempts`, `retry_backoff_seconds`를 포함하며 계획 hash에 결합한다. 참조한 profile·glossary 파일의 내용 hash도 계획에 포함하고 실행 전에 다시 확인한다. 시간 한도는 유한한 양수, `max_tokens`는 양의 정수, temperature와 backoff는 유한한 0 이상 값, `transport_max_attempts`는 1~3의 정수다. 운영자가 전용 Qwen 또는 승인된 HCP endpoint와 모델을 선택하며 실행 중 자동 모델 전환은 하지 않는다. 요청 alias와 서버가 반환한 모델 ID·revision·serving 설정을 구분해 기록하고, 서버가 공개하지 않은 실제 backend 정보는 `unknown`으로 남긴다.

HTTP 429/502/503/504, 연결 오류와 timeout만 일시적 전송 실패로 취급한다. 각 의미 응답 슬롯당 최대 `transport_max_attempts`회 전송하고, 대기는 `retry_backoff_seconds * 2**(retry_index-1)`이다. 유효한 `Retry-After`가 더 길면 그 값을 따르되 남은 실행 시간을 넘기면 재시도하지 않는다. 매 요청과 대기는 LLM 및 rollout 시간 한도로 제한한다. 모든 전송은 보내기 전에 `llm_max_requests`에서 차감하고 디스크에 예약을 남긴다. 한도를 소진하면 `unresolved: budget`, 전송 재시도 소진은 `unresolved: service-unavailable`, 다른 HTTP 오류는 `unresolved: api-error`로 남긴다. 인증 오류는 추가 호출 없이 나머지 필드도 `api-error`로 종료한다. 의미 응답 슬롯 두 개가 모두 검증 실패하면 `unresolved: invalid-response`다. 같은 승인 실행의 재개는 횟수와 시간 사용량을 초기화하지 않는다.

파일 내용, 파일명과 용어집은 분석 자료이지 지시가 아니다. LLM에 명령 실행,
추가 파일 요청, endpoint 변경 도구를 제공하지 않는다. 필드 응답은 길이·형식과
입력 근거를 검증하며, 형식 검증 통과를 의미 정확성 승인으로 보지 않는다.
LLM 자기평가 confidence가 높아도 추론은 추론으로 유지한다. RAG의 `fact`는
결정론적으로 관측한 값만 사용하고 LLM 의미 해석은 근거가 붙은 추론으로 표시한다.

필드 결과는 family 종료까지 메모리에 두지 않는다. `work/llm.sqlite`의 트랜잭션에 요청 예약, 응답 처리 상태, 검증된 필드 값 또는 unresolved 사유와 provenance를 저장한다. 필드 키는 collection scope, family 입력 hash, field, 모델 설정·prompt·glossary hash다. 응답 처리와 결과 저장은 한 트랜잭션으로 커밋하고 `llm-attempts.jsonl`은 이 기록의 재생성 가능한 감사용 export다. 재개 시 커밋된 결과는 재호출하지 않으며 미완료 예약은 사용한 전송으로 세고 남은 한도 안에서만 이어간다. 원격 API의 정확히 한 번 실행은 보장하지 않는다. raw prompt/response는 기본 보존하지 않지만, 검증된 의미 필드 값은 지도와 재개를 위해 저장한다.

### 4.7 Data Map

```text
data-map/
  index.json              # 데이터 세트 버전과 구성 파일 hash
  equipment.json          # 장비와 접속 범위
  file-families.json      # 파일군, 규칙, 통계, 해석
  paths.json              # 디렉터리 구조 요약
  unreadable.json         # 암호화/미지원/오류 파일군
  coverage.json           # 목록/표본/의미 해석 완료 범위
  metadata-evidence/      # 표본 없는 파일군의 관측 메타데이터 근거
  evidence/               # 허용된 대표 샘플과 추출 결과
  wiki/                   # 사람이 읽는 Markdown
  rag/                    # 근거 경로가 포함된 RAG 문서
```

원본 자격 증명, 전체 원본 파일, LLM 비밀 설정은 저장소에 넣지 않는다. 검증된 의미 필드 값은 지도와 재개용으로 보존한다. raw LLM prompt/response는 기본적으로 보존하지 않고 model·prompt·입력·출력 hash만 기록한다. 별도 보존이 승인된 경우에만 접근 제어된 로컬 위치를 사용하고 `data-map/`에는 위치 식별자와 hash만 남긴다.

내용을 받지 못한 파일군도 출력한다. `data-map/metadata-evidence/<family-key-sha256>.json`에 source scope, 경로, 크기, 시각, 관측 출처, 생략 사유를 기록하고 이 파일의 SHA-256을 `evidence_kind: metadata`로 인용한다. 대표 샘플이 없으면 LLM 내용 해석을 호출하지 않고 `unresolved: no-sample`로 둔다. Wiki와 RAG에는 관측한 메타데이터만 사실로 등록하며 내부 필드·용도에 대한 근거로 사용하지 않는다. 샘플이 있는 해석은 기존 sample SHA를 인용한다.

완료와 해석 품질은 별도로 보고한다. `coverage.json`에는 허용 루트별 inventory 완료 여부와 미탐색 frontier 수, 발견한 파일·파일군 수, 표본이 있는 파일군 수와 없는 사유별 수, resolved/unresolved 의미 필드 수와 사유별 수를 남긴다. 알려지지 않은 전체 파일 수를 추측해 coverage 백분율을 만들지 않는다. budget으로 inventory가 끝나지 않았으면 `inventory_complete: false`다. 정상 종료는 승인된 실행의 종료이지 장비 전체 이해나 모든 해석 성공의 증명이 아니다. 이 coverage를 결과 검토표에 포함한다.

## 5. 실행 방식

### 방식 A: 로컬 LLM이 Markdown workflow 수행

변경이 빠르지만 모델 성능에 따라 수집 품질과 재현성이 달라질 수 있다. 탐색적 조사와 예외 파일 해석에 적합하다.

### 방식 B: 이 저장소의 코드를 회사에서 실행

결과가 재현 가능하고 테스트하기 쉽다. 대신 회사 환경의 실행 결과를 외부 개발 환경에서 직접 확인할 수 없다.

### 권장: 혼합 방식

수집, 그룹화, 샘플링, 검증, 산출물 생성은 코드로 고정한다. 회사 내부 로컬 LLM은 의미 해석만 담당하고, 스킬은 실행 절차와 상태 전달에만 사용한다.

회사의 실행 코드는 단일 `equipment-map` CLI로 제공한다. 각 스킬은 다른 스킬을 호출하거나 상태를 판단하지 않고 CLI의 고정 subcommand만 실행한다.

스킬은 Codex, Claude Code, OpenCode 또는 pi가 회사 내부의 승인된 모델 endpoint로 설정된 환경에서만 실행한다. 외부 모델을 사용하는 세션에서는 장비 연결과 rollout 실행을 시작하지 않는다.

```text
equipment-map init --rollout <ID>
equipment-map preflight --stage <N> --contract <VERSION>
equipment-map stage <N> plan --rollout <ID>
equipment-map stage <N> next --rollout <ID>
equipment-map status --rollout <ID>
```

`init`은 엔지니어가 직접 실행하는 대화형 명령이다. 다음을 `rollout.json`에 저장한다.

- 장비 식별자, 프로토콜, 접속 정보(host, port, SMB share)
- 허용 루트, 실시간 데이터 후보 경로, 샘플 allow/deny 패턴
- 4.4절의 모든 budget과 LLM 요청 수 budget
- 자격 증명 별칭, 장비 접근 허용 시간대(`always` 또는 UTC 구간)
- 장비 프로필 이름(`profile`)
- LLM endpoint URL, 키 별칭, 용어집 경로와 버전 및 4.6절의 모델·생성·timeout·재시도 설정(2단계 `plan`부터 필수)
- prompt/response 보존 위치 식별자(선택, `rollouts/` 밖의 접근 제어된 경로)
- 5단계에서 등록할 다음 프로필 이름(`next_profile`, 5단계 `plan`부터 필수)

`plan`은 이 파일만 입력으로 사용하며 모델이 장비 경로와 budget을 command flag로 만들 수 없게 한다. 각 단계의 `plan`은 그 단계에 필요한 필드가 없으면 거부한다.

하나의 rollout ID는 1단계부터 5단계까지 유지한다. 단계 경계에서 설정을 바꿔야 하면(1단계 가짜 트리에서 3단계 실장비로 전환, LLM endpoint 추가, 5단계 프로필 등록) 엔지니어가 같은 ID로 `init`을 다시 실행한다. 재설정은 `.lock`이 없을 때만 허용되며 이전·새 `rollout.json`의 hash를 `init` 감사 기록에 남긴다.

현재 단계는 결과 승인된 가장 높은 단계의 다음 단계다. 각 `init` 기록은 현재 단계의 새 **epoch**을 연다. `status`는 현재 단계의 `plan`, `approve-plan`, `next-*` 기록 중 최신 `init`보다 앞선 것을 stale로 보고 무시하므로, 재설정 뒤에는 그 단계의 `plan`, 계획 승인, `next`를 다시 거친다. 결과 승인된 단계는 어떤 `init`으로도 무효가 되지 않는다. 승인된 범위를 넓히려면 새 rollout을 시작한다.

실행 전 계획 승인과 실행 후 결과 승인은 엔지니어가 직접 수행한다. 승인·결과 승인·stale lock 해제 명령은 어떤 `SKILL.md`에도 넣지 않고 CLI의 다음 명령으로도 출력하지 않는다. 비대화형 stdin에서는 거부하며 OS 사용자, 호스트, UTC 시각, 계획 hash 또는 결과 manifest hash를 감사 기록에 남긴다. 이는 전자서명이 아니라 운영자 자기확인임을 명시한다.

엔지니어 전용 명령은 `equipment-map operator approve-plan`, `equipment-map operator approve-result`, `equipment-map operator unlock`과 4.5절의 `equipment-map workbench`다. 이 명령은 LLM에 대한 보안 경계가 아니라 사람의 운영 절차다. 스킬이 대신 호출하면 시나리오 검증 실패로 처리한다.

`next`는 현재 rollout 단계가 완료되거나 budget·오류·승인 대기 조건으로 중단될 때까지 실행한다. 완료된 단계에서 다시 호출하면 작업 없이 성공하고 현재 결과 승인 상태만 출력한다. 다음 rollout 단계의 `plan`은 이전 단계 결과 승인이 없으면 거부한다.

CLI 종료 코드와 마지막 출력 행은 고정한다.

```text
0   완료 또는 안전한 no-op       NEXT: <허용된 다음 CLI 명령>
10  운영자 승인 대기             NEXT: WAIT-APPROVAL
20  실행 중단                    NEXT: STOP
30  설치·계약 preflight 실패     NEXT: INSTALL-OR-UPGRADE
```

stdout에는 rollout ID, 단계, 집계 건수, hash, 상태와 로컬 결과 경로만 출력한다. `status`는 `REPORT.md`의 존재 여부와 SHA-256도 한 줄로 출력한다. 샘플 내용, 장비 경로, 파일명, 자격 증명, LLM 입력·출력은 파일에만 기록하며 출력하지 않는다. 대화 세션이나 특정 LLM이 이전 상태를 기억한다고 가정하지 않는다. `preflight`는 CLI가 없거나 스킬이 요구한 계약 버전을 지원하지 않으면 실행을 거부하고 설치 또는 갱신 안내만 출력한다. `preflight`는 이 기계가 사용할 전송 방식도 함께 확인한다. 선택된 방식과 그 근거(platform 추정 또는 `FTP_TRANSPORT`)를 출력하고, proxy면 세 번 호출한다. health endpoint는 도달 여부만 증명하므로 목록 route에 빈 대상으로 인증 없이 요청해 401인지 확인한 다음, 설정한 token으로 요청해 200인지 확인한다. 인증 없는 요청의 401은 기대 결과이고 token을 보낸 요청의 401은 실패다. 인증 없는 요청이 성공하거나 도달하지 못해도 exit 30으로 멈춘다. 설정된 사내 `http://` URL과 비어 있지 않은 token을 먼저 확인하고 redirect를 거부한다. 운영 proxy와 loopback fixture 모두 HTTP를 사용하며 HTTPS/TLS를 요구하지 않는다. 빈 대상이므로 장비에는 접속하지 않는다. 이 확인은 장비에 접속하지 않으므로 계획 승인을 필요로 하지 않으며, 장비 접속을 대신 증명하지도 않는다. stdout에는 전송 방식 이름과 도달 여부만 출력하고 proxy URL, host와 token은 출력하지 않는다.

초기 검증은 한 엔지니어의 PC와 로컬 rollout 디렉터리에서 수행한다. Skill Market 배포 후에도 rollout 하나는 한 엔지니어가 자기 PC에서 1~5단계를 끝까지 수행한다. 다른 엔지니어는 자기 장비와 별도 rollout ID로 독립 실행한다.

회사망 밖으로 전달할 수 있는 상태 요약은 rollout ID, 단계 번호, 성공·생략·실패 건수와 CLI·계약 버전으로 제한한다. 장비 식별자, 경로, 파일명, 파일군명, 오류 원문, 분석 내용, 모델 ID와 serving 설정은 포함하지 않는다. 이 요약은 4단계 `next`가 `rollouts/<rollout-id>/REPORT.md`로 생성하며 사람이나 스킬이 직접 쓰지 않는다. 모델 ID와 설정은 `data-map/`의 LLM 유래 필드에만 남는다.

### 5.1 Rollout 상태

상태의 기준은 채팅 기록이 아니라 rollout 작업 디렉터리다.

한 rollout ID는 정확히 장비 하나를 다룬다. `init` 재실행은 같은 장비의 단계 경계 설정 변경에만 쓰며, 다른 장비는 승인 계보를 섞지 않기 위해 새 rollout ID로 1단계부터 시작한다.

rollout ID는 장비 이름, host와 IP를 포함하지 않는 불투명한 식별자다. stdout이 rollout 디렉터리 경로를 출력하므로 ID에 장비 식별자를 넣으면 반출 금지 항목이 경로로 노출된다.

```text
rollouts/<rollout-id>/
  rollout.json            # 엔지니어가 입력한 대상, 경로, budget과 시간대
  plan.json               # 정규화된 실행 계획과 hash
  audit.jsonl             # 승인 포함 append-only 상태 원장
  result-manifest.json    # data-map/ 파일의 정렬된 상대 경로와 SHA-256
  data-map/               # 구조화 결과와 허용된 evidence
  REPORT.md               # 4단계 next가 생성하는 반출 가능 요약, manifest에서 제외
  .lock                   # 실행 중에만 존재, manifest에서 제외
```

rollout 단계·승인 상태의 진실 원천은 `audit.jsonl`이며 `status`는 이를 읽어 현재 단계를 계산한다. 별도 가변 `state.json`은 두지 않는다. `result-manifest.json`은 `data-map/`만 대상으로 하고 `/` 구분자의 정렬된 상대 경로와 원시 바이트 SHA-256을 기록한다. `data-map/`을 바꾸는 모든 단계의 `next`는 종료 직전에 이 파일을 다시 생성하며, 결과 승인은 그 시점의 manifest hash에 결합한다. 모든 기록 시각은 UTC ISO-8601 형식을 사용한다.

자격 증명, LLM 비밀 설정과 허용 범위를 넘는 원본 파일은 rollout 디렉터리에 넣지 않는다. 자격 증명은 `rollout.json`의 별칭으로만 참조하며 CLI가 OS의 승인된 비밀 저장소에서 직접 조회한다. command argument, 환경 변수와 stdout으로 전달하지 않는다. 민감한 대표 샘플을 포함해야 하면 회사 내부 접근 권한과 보존 기간이 적용되는 로컬 위치만 사용한다. Skill Market은 rollout 데이터를 배포하지 않는다.

collection scope는 수집 단계(1 또는 3), 그 단계의 최신 `init` epoch, 정규화된 source 설정 hash로 식별한다. source 설정에는 장비·protocol·host·port·share·root·pattern·profile 내용 hash가 포함된다. inventory의 디렉터리 및 pass, grouping, sampling, extraction 체크포인트는 모두 이 scope에 속한다. 새 stage 3 수집이나 stage 3 재설정은 새 scope를 사용하며 이전 가짜 장비나 이전 scope의 완료 표시·샘플·해석을 재사용하지 않는다. stage 2와 4는 명시적으로 승인된 이전 단계의 collection scope와 manifest를 입력으로 삼는다. 새 collection을 활성화할 때 이전 `data-map/`은 `work/history/<scope>/`에 보존하고 새 지도에는 현재 scope 자료만 포함한다. 이 전환은 중단 후에도 재개 가능해야 한다. 이전 감사·승인 기록은 보존한다. 단순 프로세스 재시작은 scope나 budget을 새로 만들지 않는다.

### 5.2 상태 전이와 결과 무결성

`plan`과 `next`는 현재 단계 및 최신 epoch의 일치 여부를 검사한다. 승인된
과거 단계의 `next`는 쓰기 없는 no-op만 허용하고 미래 단계 실행은 거부한다.
완료된 단계의 결과 승인 대기는 `status`로 확인하며 `next`를 반복 호출하지 않는다.
5단계 결과 승인 뒤에는 terminal complete이고 `init` 재설정도 거부한다.
1·2단계의 가짜 source에서 3단계의 장비 하나로 바꾸는 것은 허용하되,
3단계에서 정한 장비 정체성을 다른 장비로 바꾸는 재설정은 새 rollout을 요구한다.

계획·실행·설정·승인은 같은 rollout의 원자적 잠금으로 직렬화한다. stale lock을 제거하는 엔지니어 전용 unlock은 아래의 복구 절차를 사용하는 예외다. 잠금을
획득한 프로세스만 해제하며 충돌한 호출은 남의 잠금을 지우지 않는다.
프로세스 강제 종료 뒤 잠금은 엔지니어가 실행 중인 로컬·proxy 작업이 없음을
확인한 후 해제한다. 복구 호출끼리도 배타적으로 실행하고, 확인한 잠금의 정체성이 바뀌면 해제를 거부한다. 복구 이벤트를 내구성 있게 기록한 뒤 해당 잠금만 제거한다. 깨진 감사 행이나 불가능한 전이는 자동 보정하지 않고 중단한다.

`approve-result`는 현재 epoch의 `completed: true` 실행에만 허용한다.
승인 직전 실제 `data-map/`의 모든 파일 목록과 바이트 hash를 다시 계산해
manifest 및 마지막 완료 기록과 일치하는지 확인한다. 파일 추가·삭제·변조와
symlink/reparse point는 거부한다. 다음 단계의 계획과 첫 실행도 승인된 입력을
검증한다. 같은 단계 재개는 그 단계가 쓴 체크포인트를 검증하고, 변경 전의
상위 단계 manifest와 현재 작업 결과를 혼동하지 않는다.
`index.json`은 자신을 제외한 `data-map/` 파일을 hash하고 마지막에 작성한다.
외부 `result-manifest.json`은 `index.json`을 포함한다.

목록·표본 budget 소진은 부분 coverage와 생략 사유를 파일에 확정한 뒤
`completed: true`, exit 0으로 끝낼 수 있다. 연결·무결성·잠금·시간대 오류는
`completed: false`, exit 20이며 결과 승인을 허용하지 않는다. LLM의 유한 실패는
4.6절의 unresolved 기록으로 확정한다. 시간 상한 도달 뒤 장비/API 요청은
없으며 이미 관측한 로컬 상태를 안전하게 저장하는 마무리만 수행한다.

## 6. 안전장치

- 장비와 허용 루트 경로를 allowlist로 제한
- 읽기 전용 계정 사용
- 기본 동시 연결 수 1
- 명시적인 다운로드/시간 budget 없이는 실행 거부
- 정규화된 실행 계획의 hash에 승인을 결합하고 실행 직전에 다시 대조
- 승인 후 계획, 대상, 경로 또는 budget이 바뀌면 재승인 요구
- rollout별 lock에 호스트, PID와 시각을 기록해 동시 실행 차단
- stale lock은 자동 삭제하지 않고 상태를 보여준 뒤 엔지니어의 대화형 해제 요구
- 경로 이탈과 SMB symlink/reparse point 추적 방지
- 자격 증명은 OS의 승인된 비밀 저장소에서 별칭으로 조회
- 샘플과 LLM prompt/response 접근 권한 및 보존 기간 설정
- 파일별 성공, 생략, 실패 사유를 audit log에 기록
- 장비 연결 실패 시 자동 재시도 폭주 없이 중단
- 승인 기록에 OS 사용자, 호스트, UTC 시각과 계획·결과 hash를 남기고 전자서명이 아닌 운영자 자기확인임을 표시

## 7. 검증 전략

실장비 연결 전에 회사 PC에서 작은 가짜 FTP/SMB 트리를 사용해 다음을 검증한다.

- 쓰기 동작이 존재하지 않는지
- 이름이 반복되는 파일이 같은 파일군으로 묶이는지
- 형식이 다른 예외 파일이 별도로 포착되는지
- 전체 목표 바이트에 도달한 다운로드 완료 후 다음 전송을 시작하지 않는지
- 참고 크기 초과·크기 미상 파일도 다운로드를 시도하고 성공한 전체 파일과 실제 사용량을 보존하는지
- FTP 전송 방식이 기계에 따라 선택되는지 (Windows → proxy, 그 외 → direct)
- 잘못된 `FTP_PROXY_URL`이나 token으로 `preflight`가 exit 30으로 멈추고 장비 접속을 시도하지 않는지
- 중단 후 체크포인트부터 재개되는지
- 암호화·손상 파일이 누락되지 않고 `unreadable`로 남는지
- 고정된 시각과 같은 가짜 입력의 LLM 미사용 경로에서 `data-map/`의 구조화 파일이 바이트 단위로 동일한지
- 승인된 계획 hash와 실행 직전 계획 hash가 다르면 중단하는지
- 같은 rollout의 동시 실행과 무단 stale lock 해제가 차단되는지
- 이전 단계를 승인하지 않고 다음 rollout 단계에 진입할 수 없는지
- 실행 결과 승인 없이 다음 rollout 단계에 진입할 수 없는지
- CLI가 없거나 계약 버전이 맞지 않을 때 스킬이 실행을 계속하지 않는지
- 가짜 SMB가 비표준 포트 또는 격리된 VM·컨테이너에서 검증되는지

추가 필수 시나리오: signature와 sample 경로 모두에서 보호 파일 내용 요청 0건, 전송 중 성장 파일의 전체 다운로드와 실제 초과량 기록, 동일 rollout의 fake→real 전환과 재설정 후 stale 자료 배제, metadata-only 지도 발행, 요청 예약·응답 수신·결과 커밋 경계에서 종료 후 재개, 429/503/timeout 뒤 회복과 영구 장애의 유한 종료, 요청·시간 budget의 재개 보존, 불완전 inventory와 의미 해석 coverage의 구분을 검증한다.

추가로 결과 파일 추가·삭제·변조, 완료 전 결과 승인, 과거·미래 단계 호출,
남의 lock 해제 방지, 실행 중 시간대 종료, parser/압축 해제 상한, 파일 속 지시문,
높은 confidence의 추론이 RAG fact로 승격되지 않는 경우도 검증한다.

LLM 설명의 정확성은 사람이 대표 파일과 근거를 함께 검토한다. 근거 없는 추론은 RAG의 확정 사실로 등록하지 않는다.

스킬은 Codex, Claude Code, OpenCode와 pi에서 각각 같은 시나리오로 검증한다. 초기 최소 모델 검증 프로필은 엔지니어의 전용 Qwen3.8-27B 배포로 삼고 정확한 served model ID와 설정을 기록한다. 크기 표기는 검증된 모델 식별자나 정확도 증명이 아니다. 문구 일치가 아니라 다음 관찰 가능한 결과를 확인한다.

- 올바른 CLI subcommand를 선택하는가?
- `plan` 이후 운영자 승인 없이 `next`가 성공하지 않는가?
- 실패 시 임의 우회 명령을 만들지 않고 CLI의 중단 이유를 전달하는가?
- LLM 의미 응답이 두 슬롯 모두 유효하지 않으면 `unresolved`로 남기며, 별도 전송 재시도와 전체 요청·시간 상한도 지키는가?
- audit의 CLI 호출 기록과 시나리오의 shell command 목록에 허용되지 않은 명령이 없는가?

## 8. Rollout 단계별 운영

다음 5단계는 3장의 런타임 파이프라인과 별개다. 장비, 현장 또는 CLI·스킬 버전별 rollout마다 반복하며, 한 엔지니어가 자기 PC에서 모든 단계를 수행한다. 각 단계에서 실행 전 계획과 실행 후 결과를 확인해야 다음 단계로 넘어간다. 승인 기록은 해당 단계의 정규화된 계획 hash 또는 결과 manifest hash를 포함한다.

### 1단계: 로컬 가짜 장비로 수집기 검증

설치된 CLI로 가짜 FTP/SMB의 목록 수집, 파일군 분류, 제한 샘플링과 `data-map/` 생성을 실행·검증한다. LLM 없이도 전체 흐름이 동작해야 한다.

실장비 주소와 자격 증명을 사용하지 않은 가짜 트리 결과만 승인 대상으로 삼는다.
Windows의 가짜 FTP 검증은 같은 PC의 가짜 proxy와 가짜 FTP를 함께 사용한다.
회사 운영 proxy에 `localhost`를 보내면 엔지니어 PC가 아니라 proxy 서버를
가리키므로 허용하지 않는다. 시험용 설정은 별도 프로세스 환경에만 적용한다.
FTP와 SMB adapter 모두 build 시나리오로 검증하고 rollout 하나의 1단계는
선택한 protocol 하나만 사용한다.

### 2단계: 회사 로컬 LLM 연결

대표 샘플 분석 결과를 필드별로 받아 CLI가 구조화된 JSON으로 조립하고 검증한다. 한 종류의 측정 데이터와 한 종류의 로그 파일로 정확도를 확인한다.

### 3단계: 승인된 장비 1대에서 읽기 전용 시범 운영

엔지니어가 같은 rollout ID로 `init`을 다시 실행해 실장비 접속 정보, 좁은 허용 루트와 작은 budget을 입력한다. 실시간 데이터 후보 경로가 있으면 함께 입력한다. 장비 부하, 파일군 정확도, 샘플 대표성과 운영자 검토 결과를 기록한다. 접근 허용 시간대가 없으면 계획에 `always`를 명시해 승인 hash에 포함한다.

3단계 `next`는 1단계와 같은 파이프라인을 실장비에 실행한 뒤, 2단계와 같은 필드별 LLM 해석을 아직 해석이 없는 파일군에만 수행한다. LLM 호출은 `rollout.json`의 LLM 요청 수 budget으로 제한하며, budget에 걸려 해석하지 못한 파일군은 `unresolved: budget`으로 남긴다. 4단계는 모든 파일군에 해석 또는 `unresolved` 기록이 있어야 진행한다.

방화벽과 접속 승인은 스킬 외부의 선행조건이다. 스킬은 방화벽 변경이나 승인 시스템 조회를 시도하지 않는다. 연결되지 않으면 원인을 단정하거나 우회하지 않고 진단 결과를 남긴 후 중단한다.

### 4단계: Wiki와 RAG 생성

검토가 끝난 `data-map/`만 사용해 Wiki와 RAG 문서를 만든다. 답변에는 항상 장비 경로와 근거 종류·hash를 표시한다. 샘플이 없으면 4.7절의 metadata evidence만 인용하고 내부 내용은 미확인으로 남긴다. 4단계 `next`는 `wiki/`, `rag/`와 함께 `rollouts/<rollout-id>/REPORT.md`를 생성한다. 5단계 `next`는 5단계 건수를 포함한 `REPORT.md`를 임시 파일에 쓰고 원자적으로 교체한 뒤에 `next-stop`을 기록한다. 완료 기록과 오래된 보고서가 공존하지 않는다.

### 5단계: 장비 종류 확장

엔지니어가 새 장비 프로필 파일에 허용 경로, 파일명 규칙과 기존 extractor 매핑을 작성하고, 같은 rollout ID로 `init`을 다시 실행해 `next_profile`로 등록한다. 5단계 `plan`은 `next_profile`이 등록된 프로필 파일을 가리키고 현재 `profile`과 다를 때만 허용한다. 5단계 `next`는 그 프로필의 스키마와 extractor 매핑(기존 extractor 이름만 허용)을 검증하고, 현재 지도에서 `unsupported-format`으로 남은 파일군을 `data-map/extractor-requests.json`에 정리한 뒤 manifest를 다시 생성한다. 결과 승인으로 rollout이 끝나며, 새 장비는 이 프로필로 새 rollout을 1단계부터 시작한다. 새 extractor 코드가 필요하면 이 단계에서 즉석 생성하지 않고 별도 CLI 릴리스 절차로 넘긴다. 한 장비의 예외를 공통 로직에 억지로 넣지 않는다.

## 9. Skill Market 배포 구조

공통 Agent Skills 형식의 단일 원본으로 다음 6개 스킬을 관리한다. Skill Market에는 6개 스킬과 공통 CLI를 하나의 버전된 suite로 배포하되 각 스킬은 개별 호출할 수 있다.

```text
equipment-map-suite/
  skills/
    equipment-map-run/SKILL.md
    equipment-map-stage1-harness/SKILL.md
    equipment-map-stage2-llm/SKILL.md
    equipment-map-stage3-pilot/SKILL.md
    equipment-map-stage4-publish/SKILL.md
    equipment-map-stage5-expand/SKILL.md
  runtime/
    equipment-map
  install/
    install.ps1
    install.sh
```

- `equipment-map-run`은 rollout 상태와 다음 담당 단계를 안내하는 기본 진입점이다.
- 단계별 스킬은 담당 역할, 선행조건, 고정 CLI 명령과 결과 판독법만 포함한다.
- 각 `SKILL.md`에는 분기, 상태 머신, JSON 조립 또는 다른 스킬 호출을 넣지 않는다.
- `equipment-map-common` 스킬은 만들지 않는다. 공통 로직은 단일 CLI에만 둔다.
- 공통 frontmatter에는 이식 가능한 `name`과 `description`만 필수로 사용한다. 플랫폼 전용 metadata는 공통 동작에 필요할 때만 설치 과정에서 추가한다.
- 5개 단계 description은 단계 번호, 담당 역할과 고유 작업을 명시해 서로 겹치지 않게 한다. `equipment-map-run`만 일반적인 요청을 받는 넓은 description을 사용한다.
- 각 스킬은 실행 전에 자신의 CLI 계약 버전을 `preflight`로 검사한다.
- 설치기는 도구별 discovery 경로에 스킬을 배치하고 공통 CLI를 사용자 PATH에 한 번 설치한다. Windows는 PowerShell 설치기, macOS/Linux는 shell 설치기를 사용한다.
- suite 버전과 CLI의 지원 계약 버전은 별도로 기록한다. 스킬은 `--contract <VERSION>`을 넘기고 CLI는 지원 목록에 없는 계약이면 중단한다.

스킬별 허용 명령은 다음과 같다.

| 스킬 | 허용된 CLI 호출 |
|---|---|
| `equipment-map-run` | `preflight`, `status` (`--rollout` 생략 시 로컬 목록) |
| `equipment-map-stage1-harness` | `preflight --stage 1`, `stage 1 plan`, `stage 1 next`, `status` |
| `equipment-map-stage2-llm` | `preflight --stage 2`, `stage 2 plan`, `stage 2 next`, `status` |
| `equipment-map-stage3-pilot` | `preflight --stage 3`, `stage 3 plan`, `stage 3 next`, `status` |
| `equipment-map-stage4-publish` | `preflight --stage 4`, `stage 4 plan`, `stage 4 next`, `status` |
| `equipment-map-stage5-expand` | `preflight --stage 5`, `stage 5 plan`, `stage 5 next`, `status` |

`init`, 실행 전 계획 승인, 실행 후 결과 승인과 stale lock 해제는 엔지니어 전용이며 어떤 스킬의 허용 명령에도 포함하지 않는다. 스킬에서 허용하는 유일한 분기는 `preflight` 실패 시 설치 안내를 전달하고 중단하는 것이다.

낮은 성능 모델에서도 스킬의 역할은 “정해진 명령 실행과 결과 전달”로 제한한다. 모델이 승인 여부, 다음 단계, budget 초과 또는 상태 무결성을 판단하게 하지 않는다.

## 10. 1차 완료 기준

- 가짜 FTP와 SMB에서 동일한 형식의 inventory가 생성된다.
- 반복 파일 100개를 전체 복제하지 않고 대표 샘플 3~5개로 요약한다.
- 텍스트, CSV, JSON, 알 수 없는 바이너리, 암호화 파일을 구분한다.
- 파일군마다 규칙, 통계, 설명, 신뢰도와 근거 경로가 기록된다.
- 실행 budget과 읽기 전용 제약을 자동 검사한다.
- 검토된 지도에서 Markdown Wiki와 근거 추적 가능한 RAG 문서를 생성한다.
- 6개 스킬이 네 지원 도구에서 같은 CLI 계약으로 동작한다.
- 전용 Qwen3.8-27B 배포의 정확한 모델·serving 설정으로 실행한 기준 시나리오에서 승인 우회, 자유형 JSON 작성과 대화 상태 의존 없이 rollout을 재개한다.
- 한 엔지니어가 로컬 rollout 상태만으로 중단 후 1~5단계를 재개한다.
