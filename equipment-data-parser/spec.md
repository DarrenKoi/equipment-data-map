# Equipment Data Map spec (snapshot)

Copied from `docs/architecture/equipment-data-map.md` so this folder is self-contained. If the two differ, the `docs/` version wins; refresh this copy.

# Equipment Data Map 통합 아키텍처

> 2026-09-21 통합 기준. 저장소 목적, 에이전트/해석 LLM의 역할, 수집·발행, 성능 개선, 반복 검증과 장비 용어 사전을 이 문서에서 정의한다. `docs/architecture/`의 다른 문서는 배경 또는 구현 사용 안내이며, 설계가 다르면 이 문서가 우선한다. `equipment-data-parser/spec.md`는 이 본문의 배포용 스냅샷이다.
>
> **적용 상태:** 기존 절은 현행 실행 계약이다. **목표 계약**으로 표시한 절은 통합 설계로 채택하되, 11장의 구현·계약 전환 검증 전에는 현행 letter 실행에 적용하지 않는다. 문서상 계약과 실제 구현 완료는 다르다. 이 checkout에서 확인한 오프라인 Wiki/조사 원장의 범위도 11장에 따로 명시한다.

읽는 순서: 전체 구조·역할은 3장, 수집·해석·사전·개선 루프는 4장, 승인과 재개는 5장, 안전장치는 6장, 검증과 완료 판정은 7·10장, rollout 단계별 운영은 8장, 배포 및 전환은 9·11장이다.

## 1. 목표

FAB 장비의 FTP 파일 구조를 읽기 전용으로 탐색하고, 반복되는 파일을 묶어 최소한의 대표 샘플만 분석하여 **장비 데이터 지도**를 만든다.

장비 데이터 지도는 다음 질문에 답해야 한다.

- 어떤 경로에 어떤 성격의 파일이 있는가?
- 파일명, 디렉터리, 생성 시각에는 어떤 규칙이 있는가?
- 파일 안에는 어떤 필드와 데이터가 있으며 무엇에 쓰이는가?
- 같은 형식의 파일은 얼마나 자주, 얼마나 많이 생성되는가?
- 각 파일군은 로그, FDC, 설정, 측정 결과, recipe, 유지보수 또는 기준 정보 중 무엇이며 시간에 따라 어떻게 변하는가?
- 해석하지 못한 파일과 그 이유는 무엇인가?
- 운영, 장애 분석, Wiki에서 어떤 근거 파일을 찾아야 하는가?
- 서로 다른 파일군이 어떤 경로·명명 규칙·필드·식별자·참조로 연결되며, 그 연결은 어디까지 관측되었는가?

원본 파일과 분석 결과는 회사망 밖으로 반출하지 않는다. 목표는 전체 파일 백업이 아니라 대표 표본으로 장비 저장소를 이해하는 것이다. 첫 실행은 근거가 붙은 초안이며, 질문과 추가 관측을 통해 지도를 교정한다. 개선 대상은 지도·용어 정의·검토된 추출 규칙이며 모델 가중치나 운영 중인 코드를 스스로 바꾸는 학습 루프가 아니다.

## 2. 핵심 원칙

1. **읽기 전용:** 장비에서 생성, 수정, 삭제, 이름 변경을 수행하지 않는다.
2. **목록 우선:** 전체 파일을 복제하지 않고 메타데이터 목록부터 수집한다.
3. **규칙 우선, LLM은 대표 샘플만:** 경로·파일명 규칙·확장자 메타데이터로 먼저 묶고, 모호한 분류와 의미 해석에만 로컬 LLM을 사용한다.
4. **근거 보존:** 모든 해석에는 장비, 경로, 샘플, 추출 방식과 신뢰도를 남긴다.
5. **재개 가능:** 중단되어도 체크포인트부터 다시 시작한다.
6. **부하 제한:** 장비별 동시 연결 수, 초당 요청 수, 다운로드 용량과 실행 시간을 제한한다.
7. **모르는 것은 모른다고 기록:** 암호화·손상·독점 형식 파일도 누락하지 않고 `unreadable` 상태로 지도에 남긴다.
8. **새 근거로 교정:** 이전 추론과 용어 후보는 검증할 가설이다. 같은 답의 반복, 높은 confidence, 처리 성공을 정확도 증명으로 삼지 않는다.
9. **코드는 한 번 배포, 운영은 반복:** 수집·안전·추출·검증·문서 조립은 검증된 CLI가 맡고, LLM은 제한된 해석과 조사 제안을 맡는다. 정상 운영 중 코드 재생성을 요구하지 않는 배포 구조를 목표로 한다.

## 3. 전체 흐름

```text
장비 FTP
    |
    v
[1. Inventory] -- 경로, 크기, 시각 등 메타데이터만 수집
    |
    v
[2. Grouping] -- 경로/파일명 규칙/확장자로 파일군 생성
    |
    +-- [목표: heavy/medium/light 후보 선정·검증]
    |
    v
[3. Sampling] -- 파일군별 소수 대표 파일만 장비와 같은 폴더 구조로 회사 PC에 저장
    |
    v
[4. Extraction] -- 텍스트, 표, 설정, 로그, 바이너리 메타데이터 추출
    |
    v
[5. Local LLM] <-- 버전 고정 용어 사전 + 현재 표본 근거
    |                파일 의미, 필드, 생성 주기, 운영 용도 추론
    |
    v
[6. Data Map] -- 구조화된 canonical JSON 생성
    |              |
    v              v
  Wiki          Graph JSONL
    |
    v
[목표: 검토 — 미해결 질문·충돌·별도 표본 검증]
    |
    +-- 목적 충족 / 추가 작업 없음 / 한도·승인 대기 → 종료 사유 기록
    |
    +-- 추가 근거·사전 교정 → 허용 작업과 승인 확인 → 다음 iteration
         (기존 결과 보존, 수집은 같은 download guard 사용)
```

`data-map/` 디렉터리를 기준 데이터 세트로 삼고 Wiki와 graph는 그 안의 구조화 데이터에서 만든 파생 산출물로 취급한다. 서로 다른 결과를 별도로 관리하지 않는다.

### 3.1 단계와 반복의 구분

파이프라인 단계, rollout 단계, pass와 iteration을 구분한다.

- 위 흐름의 6단계는 한 번의 분석 실행 안에서 반복되는 **런타임 파이프라인**이다.
- 8장의 5단계는 장비, 현장 또는 버전별로 담당 운영자가 수행하고 승인하는 **rollout 단계**다.
- **pass**는 같은 수집 scope와 누적 budget 안에서 미탐색 frontier·표본 없는 파일군을 처리하는 내부 반복이다(4.4.1절).
- **iteration**은 지도 초안의 질문을 검토하고 추가 근거·사전 교정을 반영한 새 검토 결과를 만드는 외부 반복이다(4.8절). 하나의 iteration은 여러 pass를 포함할 수 있으며, 검토 사본만 새로 생성했다고 새 관측이나 정확도 개선이 생기지는 않는다.

Skill Market에 배포할 단계별 스킬은 rollout 5단계에 대응한다. 런타임 파이프라인은 스킬에 분산하지 않고 단일 CLI가 실행한다. iteration 번호는 rollout 단계·scope·승인 상태를 대신하지 않는다.

### 3.2 초기 spike

letter 00의 `spike.py`(FTP → 선택적 LLM → Markdown, 장비 하나)는 반복된 실장비 실행으로 목적을 마쳤고 2026-09-22에 저장소에서 제거했다. 현행 순서는 letter 01부터 시작하며, 사무실 PC에 남은 `equipment.toml`과 `out/`은 실행 순서와 무관한 이력이다.

### 3.3 역할과 신뢰 경계

| 주체 | 입력과 책임 | 넘지 않는 경계 |
|---|---|---|
| 엔지니어 | 목적·범위·budget 설정, 계획/결과 승인, 의미·용어 검토 | 처리 성공을 의미 정확성으로 간주하지 않음 |
| 운영 에이전트 | 읽기 전용 실행 지침, 집계 상태, 허용된 고정 CLI 명령 | 장비 원본·추출 내용을 대화에 싣지 않고 승인·잠금 해제·코드 변경을 대신하지 않음 |
| 단일 CLI | inventory, 선택 검사(목표 계약, 4.3.1절), 다운로드, 추출, 요청 예약, 검증, 체크포인트, 발행 | 안전·상태 판단을 모델에 위임하지 않음 |
| 내부 해석 LLM | 제한된 파일군 근거 패킷과 관련 용어, 짧은 의미 응답 | 도구·장비 접근·추가 다운로드·자기 승인 없음 |
| 사내 검토자/검토 LLM (목표 계약, 4.8절) | `rollouts/` 밖의 허용된 Wiki 사본과 질문 | 검토 사본 열람 권한을 원본 열람·수집 권한으로 확대하지 않음 |

운영 에이전트와 내부 해석 LLM은 같은 승인 모델을 쓰더라도 역할과 입력을 분리한다. Wiki를 읽는 검토 세션 역시 현행 운영 에이전트의 원본 접근 제한을 해제하지 않는다. 외부 유지관리자는 합성 fixture와 반출 가능한 집계·문제 요약으로 문서와 코드를 정비한다.

### 3.4 문서·상태·산출물의 책임

- **실행 지침:** `equipment-data-parser/index.md`와 해당 letter, 릴리스된 `SKILL.md`는 읽는 순서·허용 명령·체크포인트를 안내한다. 실행 에이전트가 이 지침을 스스로 고치지 않는다.
- **상태:** 승인 전이는 `audit.jsonl`, 작업 재개는 CLI의 SQLite/체크포인트, 추가 질문·검토 이력은 별도 조사 원장(목표 계약, 4.8절)에 둔다. 대화 기록이나 Markdown의 완료 체크가 이를 대체하지 않는다.
- **기준 지식:** `data-map/`의 관측·추론·근거가 지도 원본이다. 승인된 용어 사전은 버전 고정된 해석 입력이며, 목표 계약에서는 사용한 사전 사본과 hash를 지도에 보존한다(4.6.1절).
- **읽기용 문서:** Wiki, 사전 Markdown과 iteration 검토 보고서는 기준 데이터와 원장에서 생성한다. Markdown 편집을 지도의 사실 수정으로 역수입하지 않는다.

정상 흐름은 `승인된 계획 → CLI → 내부 해석 → 검증된 map → Wiki/Graph → 질문·검토 → 다음 승인된 작업`이다. 별도의 agent별 메모리·reflection 파일을 늘리지 않고 기존 조사 원장을 확장한다.

## 4. 모듈 구조

### 4.1 Source

전송 방식의 차이를 숨기는 실제 seam이다. 현재 adapter는 FTP 하나뿐이고, 그
interface는 프로토콜을 하나 더 붙일 수 있는 모양으로 남겨 둔다 — SMB는 필요해질
때 같은 interface 뒤에 추가한다. 지금 없는 프로토콜을 위해 미리 짓지 않는다.

- 디렉터리 목록 조회
- 파일 크기 조회
- 크기 상한을 전송 계층에 요구하지 않고 가능한 대표 파일을 통째로 다운로드
- 연결 종료

쓰기 동작은 interface에 포함하지 않는다.

FTP adapter는 사내 `ftp_handler` 라이브러리 위에 올린다. 전송 방식은 호출부의
선택이 아니라 기계의 속성이다. **운영 기계는 Windows 엔지니어 PC이고 FTP egress가
막혀 있으므로 HTTP proxy가 기본 경로다.** Linux 호스트의 직접 연결은 개발·시험용
보조 경로이며, 어떤 기능도 그쪽에서만 동작해서는 안 된다. 두 전송 방식은 같은
`FtpFleetDownloader` 표면을 제공하며 `ftp_handler.fleet_downloader()` 가 그
기계에 맞는 쪽을 고른다.

메타데이터 수집은 `size_dirs` 를 쓴다. fleet 목록(`list_dirs`)은 경로만 나르지만
`size_dirs` 는 경로·크기·UTC 수정 시각을 한 연결에서 함께 돌려주며, 두 전송 방식
모두에서 그렇다. 수정 시각은 `MDTM` 에서 오고 RFC 3659가 GMT로 고정하므로 서버
지역 시간을 추측할 필요가 없다. `MDTM` 이 없는 장비 서버는 수정 시각이 `None` 이
되며, 이는 실패가 아니라 미상으로 기록한다.

외부 접근을 방화벽으로 통제하는 사내 전용망에서 실행한다. FTP proxy와
내부 LLM endpoint는 운영·시험 환경 모두 `http://`를 사용한다. HTTPS/TLS를
실행 선행조건으로 요구하거나 URL을 자동 승격하지 않는다. 이 정책은 HTTP
endpoint에 적용하며 장비 쪽 FTP 프로토콜은 그대로 사용한다.

proxy의 위치는 배포 사실이므로 소스 트리에 두지 않는다. `FTP_PROXY_URL`,
선택 사항인 `FTP_PROXY_TOKEN`과 전송 방식 강제용 `FTP_TRANSPORT`는 기계별
`.env`에서 읽고 실제 환경 변수가 우선한다. 운영 proxy는 신뢰하는 단일 사용자용이라
token 없이 배포하며, token은 proxy가 인증을 켠 배포에서만 설정한다. 이 값이 맞는지는 사람이 아니라 `preflight`가
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
- 수정 시각의 출처(`MDTM`, 서버가 지원하지 않으면 `none`)와 원본 표기
- UTC로 정규화한 수정 시각과 정규화 가능 여부
- 확장자
- inventory pass 식별자, 탐색 시각과 성공/실패 상태
- collection scope, pass, 정규화 경로, 원본 크기·수정 시각·상태로 만든 결정론적 `observation_id`
- 반복 inventory에서 관측한 상태(`single-pass`, `new`, `changed`, `unchanged`, `missing`)

장비의 파일 목록이 매우 크면 디렉터리 단위 체크포인트를 남긴다. Sampling 이후에는 파일군 단위로 체크포인트를 남긴다.

`changed`와 `unchanged`는 두 pass에서 관측한 크기와 수정 시각의 비교 결과일 뿐이다. 내용 변경, append/overwrite 방식 또는 영구적인 static 파일임을 증명하지 않는다. 내부 event 시각, 파일 수정 시각과 inventory 관측 시각을 서로 다른 필드로 보존한다.

### 4.3 Grouping

LLM 호출 전에, 내용을 받지 않고 inventory 메타데이터만으로 파일군을 만든다.

- 날짜, 시각, lot, wafer, recipe, sequence처럼 변하는 파일명 부분을 프로필 규칙으로 정규화한다.
- **패턴 파일군:** 상위 디렉터리·정규화한 파일명·확장자가 같은 파일이 2개 이상이면 한 파일군이다. 같은 형식으로 반복 생성되어 시간 순서로 이어지거나 서로 관련된 것으로 추정되는 파일 집합이다.
- **느슨한 묶음(`loose`):** 이름 규칙을 공유하는 다른 파일이 없는 파일은 상위 디렉터리와 확장자가 같은 것끼리 한 묶음으로 둔다. 같은 생성 규칙이나 내부 포맷을 주장하지 않는다.

파일 크기 구간이나 앞부분 바이트 signature로 파일군을 나누지 않으며, 묶기 위해 내용을 받지 않는다. 패턴 파일군의 표본 중 추출 형식이 가장 흔한 형식과 다른 표본은 Data Map이 예외로 기록하고 파일군은 쪼개지 않는다. 그룹 규칙과 예외 표본을 함께 기록해 잘못 묶인 결과를 추적할 수 있게 한다. 받지 않은 구성원의 형식은 확인했다고 주장하지 않는다. 이름 규칙보다 넓게 파일군으로 엮는 일(형식·내용을 근거로 한 병합이나 분할)은 1차 범위에서 하지 않고, 전체 지도가 완성된 뒤 그 결과를 보고 진행한다.

폴더와 명명 관례는 사람이 만든 소프트웨어의 구조를 추정하는 단서다. 다만 같은 폴더나 비슷한 이름만으로 같은 용도·포맷이라고 확정하지 않는다. 파일군 생성과 파일군 사이의 연결은 구분한다. 서로 다른 형식의 설정·로그·측정 결과는 별도 파일군을 유지하면서 4.7.1절의 관계로 연결할 수 있다. 정규화 전 파일명과 치환 규칙을 보존하며 채널·장비 번호까지 임의로 지우지 않는다.

### 4.3.1 분석 대상 선정: heavy · medium · light — 목표 계약

Grouping 다음, 내용 다운로드·추출·해석 전에 대상을 줄인다. 현행 규칙 기반 Sampling을 대체하지 않고 그 앞에서 조사할 후보 집합을 제한한다. 선정에 쓰는 LLM은 도구 없는 내부 호출이며, 운영 에이전트에게 원본을 공개하는 경로가 아니다. 이 절은 11장의 선정 계약 전환 이후에만 활성화한다. `medium`과 `light`는 내부 LLM 설정이 필요하므로, LLM 없이 동작해야 하는 1단계는 항상 `heavy`다.

| 모드 | 대상과 결정 주체 | 완료 범위 |
|---|---|---|
| `heavy` | 공통 필터·보호 검사를 통과한 모든 파일군 | 모든 적격 파일군의 대표 표본 조사. 반복 파일 전수 다운로드가 아님 |
| `medium` | 내부 LLM이 포함·제외·보류와 이유를 제안하고 엔지니어가 확정 | 확정한 후보만 조사. 미확정 항목은 보류 |
| `light` | 사전 승인된 목적·정책 안에서 내부 LLM이 중요하다고 추정한 후보만 선정 | 선정 집합만 조사. 미선정 항목의 실제 중요도·내용은 미확인 |

순서는 `승인된 inventory 요약 → 공통 필터 → 모드별 후보 선정 → 선택 기록 고정 → 기존 대표본 선택`이다. 목록은 폴더·파일군·확장자·크기·시각으로 요약하고 미탐색 frontier를 표시한다. 내용을 먼저 읽어 중요도를 정하지 않는다. medium의 검토표는 포함/제외/보류 이유와 예상 표본 수·바이트를 보여 주며 미상 값은 추측하지 않는다.

공통 기본 content-deny는 대소문자를 무시해 각 경로 구성 요소의 `.` 시작 또는 `temp`, `tmp`, `lock` 포함을 검사한다. 디렉터리 매칭은 그 하위 내용에도 적용한다. `temperature.csv`, `attempt.log`, `clock.cfg` 같은 오탐이 있으므로 규칙별 매칭 사유를 보여 주고 엔지니어가 정확한 경로 예외를 설정한다. 예외는 해당 기본 이름 필터만 해제하며 명시적 deny·범위·실시간 보호·budget을 우회하지 않는다. LLM은 예외를 제안할 수만 있다. 목록 탐색까지 제외하는 경로는 content-deny와 별도로 기록하고 내부 개수를 추측하지 않는다.

선택 기록은 scope, inventory 입력 hash, 모드·목적·규칙 버전, 포함/제외/보류 대상과 이유, 결정 주체, 모델·prompt 버전, 엔지니어 확인을 담는다. 스크립트가 실재 경로·scope·보호 규칙·상한을 검증한 뒤 고정한다. 폴더 선택은 현재 알려진 하위 후보로 펼치고 개별 제외를 적용한다. 특정 파일 포함은 표본 상한을 우회하는 강제 다운로드가 아니다. 잘못된 응답·경로·미검토 항목은 보류하고 heavy로 자동 전환하지 않는다. 재개 시 검증된 선택을 재사용한다.

선정용 요청도 유한한 입력·요청 수·시간 상한을 가지며 해석과 같은 전체 LLM budget에서 차감한다. medium은 승인된 metadata inventory 뒤, 내용 수집 전에 검토 체크포인트에서 멈춘다. 엔지니어가 선택 결과 hash를 확인하기 전에는 내용 요청을 하지 않는다. light의 결과는 승인된 선택 정책의 파생 결과이며 허용 범위를 확대할 수 없다. 추가 pass에서 새로 발견한 대상도 같은 절차를 거치고 medium에서는 다시 검토한다.

모드·목적·필터·예외·상한·확정 절차는 승인 계획에 결합한다. 선정 계약의 세부 schema, medium 확인 전이와 재개 검사는 함께 릴리스해야 하며, 현행 `init`/`next`에 임의 키·명령을 만들어 적용하지 않는다. 미선정·보류·기본 필터·사용자 제외·보호·budget 부족은 coverage에서 분리한다. 반복 pass나 추가 조사 질문은 미선정 항목을 자동 포함하지 않는다. Publisher는 확정된 상태를 표시할 뿐 필터나 LLM 선정을 다시 수행하지 않는다.

### 4.4 Sampling

파일군마다 다음 대표본만 선택한다.

- 패턴 파일군: 수정 시각이 가장 늦은 적격 파일 3개와, 남은 적격 파일 중 무작위 2개. 최근 형식과 더 넓은 시기를 함께 본다.
- 느슨한 묶음: 적격 파일 중 무작위 최대 3개.

적격 파일은 deny 대상, `active_candidate`(최신·실시간·변경 중 후보)와 4.7절 로컬 이름 규칙에서 빠진 파일을 뺀 구성원이다. 최신 순서는 UTC로 정규화한 수정 시각을 쓰고 동률은 정규화 경로 순이다. 수정 시각을 모르는 파일은 최신 선택에서 빠지고 무작위 대상에는 남는다. 무작위는 collection scope·family ID·정규화 경로의 hash 순서로 고르는 결정론적 선택이라 재개와 고정 입력에서 같은 파일을 고른다. 5개와 3개는 상한이며 적격 파일이 적으면 그만큼만 받는다.

표본은 장비와 같은 경로로 `evidence/` 아래에 저장하며(4.7절) 내용 hash로 중복 제거하지 않는다. 다른 경로에 있는 같은 바이트는 각자의 표본이다. 같은 collection scope에서 이미 받은 표본은 다시 전송하지 않는다. 현재 scope의 sample record가 가리키고 다시 hash한 값이 기록과 같은 파일만 표본으로 쓰며, 기록과 맞지 않는 파일이 evidence 경로에 있으면 덮어쓰지 않고 exit 20으로 중단한다. 받은 표본은 언제나 파일 전체이며, budget을 넘어 받지 않은 파일은 표본이 아니라 메타데이터 전용 항목으로 사유와 함께 기록한다.

엔지니어는 rollout 설정에 허용 루트, 실시간 데이터 후보 경로와 샘플 다운로드 allow/deny 패턴을 입력한다. deny 대상은 내용을 다운로드하지 않고 메타데이터만 기록한다. 단일 inventory에서 최신 파일이 확인되면 `active_candidate`로만 표시한다. 주기 갱신은 기존 파일들의 시각 간격 또는 두 번 이상 inventory의 변화를 근거로 확인하며, 근거가 부족하면 주기를 `unknown`으로 둔다.

실행마다 다음 budget을 설정한다.

- 장비별 최대 다운로드 파일 수
- 파일별 참고 바이트 (`max_file_bytes`: 초과 기록용이며 다운로드 거부 조건이 아님)
- 전체 목표 바이트 (완료된 전송의 실제 사용량이 도달하면 다음 다운로드부터 중단)
- 최대 실행 시간
- 최대 동시 연결 수
- 초당 최대 요청 수
- 최대 목록 항목 수와 디렉터리 깊이

#### 4.4.1 반복 pass

`rollout.json`의 `max_passes`(양의 정수, 기본 1)는 한 `next` 호출 안에서 같은 collection scope의 미완료 작업을 몇 번까지 다시 도는지의 상한이다. pass 1은 위 파이프라인 그대로다. pass N+1은 직전 pass가 남긴 `data-map/` 전체를 prior로 읽고 다음 순서로 대상을 고른다.

1. `coverage.json`의 미완료 frontier — 미탐색 디렉터리의 inventory를 이어간다.
2. 표본이 없는 적격 파일군 — Sampling, Extraction, LLM 해석을 이어간다. deny 대상, `active_candidate`, 전송 시도를 소진한 파일군, `usage-unknown` 전송이 걸린 파일군은 적격이 아니다.

동률은 정규화 경로, family ID 순이다. LLM 자기평가 `confidence`는 선택에 쓰지 않는다. 선택 규칙 버전(`selection_rule_version`)은 CLI 버전에 고정하고 계획에 기록한다.

`max_passes`는 budget을 쪼개지 않는다. 위의 모든 budget과 4.6절의 `llm_max_requests`는 pass를 넘어 누적 소진되며 별도 pass budget은 없다. 루프는 다음 중 먼저 오는 사유로 끝나고 사유를 `coverage.json`과 감사 기록에 남긴다.

- `no-eligible-work`: 1·2의 대상이 남지 않음. 작업상 수렴이며 정확도 달성을 뜻하지 않는다.
- `max-passes`: 대상은 남았지만 pass 상한 도달.
- `budget`: 어느 budget이든 먼저 소진.

세 사유 모두 5.2절의 정상 종료(`completed: true`, exit 0)다. pass 경계마다 감사 기록에 `pass-start`/`pass-end`(pass 번호, prior manifest hash, 선택 목록 hash, 종료 사유)를 남기고, 선택 목록과 prior snapshot은 scope 체크포인트에 보존해 재개 시 검증한다. 재개는 pass 번호와 budget 사용량을 초기화하지 않는다. pass 반복으로 허용 루트·allow/deny·budget을 넓히지 않는다.

모든 내용 다운로드는 Sampling의 `download_guard` 하나를 거친다. 파일군을 메타데이터로 먼저 만들고 최신·실시간·변경 중 후보를 표시한 후에만 표본을 고른다. 허용 루트, allow/deny, `active_candidate`, 남은 전체 목표 바이트·파일 수·요청·시간 budget을 전송 전에 검사한다. 검사를 통과한 파일을 `max_connections`개까지 한 묶음으로 `ftp_handler`에 넘겨 동시에 받으며, 묶음의 파일마다 전송 전 예약과 전송 후 실사용량 기록은 파일 하나일 때와 같다. 전체 목표 도달은 다음 묶음을 막지, 진행 중인 묶음을 끊지 않는다. 파일별 크기는 참고값으로 기록하며 다운로드 허용 조건으로 사용하지 않는다. 후보가 없으면 메타데이터와 생략 사유를 남긴다. 두 번의 목록이 같다는 사실만으로 최신·실시간 후보가 쓰기 완료됐다고 판단하지 않는다. 안정성을 확인할 근거가 없으면 내용을 받지 않는다.

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
다운로드 파일 수는 전송 시도 기준이다.

### 4.5 Extraction

먼저 결정론적인 도구로 내용을 추출한다.

- 일반 텍스트와 로그: 인코딩 판별 후 제한된 구간 읽기. 줄 단위 `key = value`·`key: value` 파일과 로그 줄 안의 `name=value` 쌍은 필드 이름과 값으로 추출
- CSV/TSV: 열 이름 전체, 자료형 추정, 일부 행
- JSON/XML/INI: 키 구조와 일부 값
- 압축 파일: 목록만 확인하고 허용된 크기 안에서만 내부 표본 추출
- 이미지: 크기, 포맷 등 메타데이터
- 알 수 없는 바이너리: magic bytes, 문자열 조각, entropy 등 안전한 특징

텍스트 인코딩은 BOM, UTF-8, CP949 순서로 엄격하게 판별하고 사용한 인코딩을 기록한다. 셋 모두 실패하면 `unsupported`다. 한국어 장비가 쓰는 CP949·EUC-KR 파일에서도 필드 이름을 잃지 않기 위해서다.

지원 형식의 extractor는 출력 한도 안에서 다음 공통 descriptor도 만든다.

- 원본 필드 경로·이름, 관측 자료형, 헤더에 명시된 단위와 schema/version 문자열
- 내부 event/measurement/snapshot 시각 필드, 원본 표기, timezone 또는 clock basis, 관측한 시작·종료 시각
- 장비·module/chamber·channel/sensor·recipe·lot·wafer·run·site 식별자 필드와 값의 근거 위치
- 파일에 명시된 상태·severity·alarm code·quality flag·spec limit·pass/fail과 그 근거 위치
- 행·record 수, null/invalid 수와 표본 범위
- 필드마다 값 종류(정수·실수·문자열·null·invalid)별 개수. 숫자 값이 하나라도 있으면 최대 소수 자릿수, 표본별 min/max와 집계한 숫자 값의 개수
- 필드마다 서로 다른 예시 값 최대 3개
- 파일 참조, component/parameter 계층과 제한된 key/value 또는 단계 구조

이 descriptor는 파일에 실제로 적힌 구조와 값만 `observed`로 기록한다. 이름만 보고 단위·의미·producer·인과관계·pass/fail을 만들지 않는다. min/max는 category와 관계없이 숫자 값이 있는 모든 필드에서 입력 상한 안의 모든 숫자 값으로 계산하며, 표본이 보여 준 범위일 뿐 허용 범위가 아니다. 평균·분포 같은 다른 통계는 만들지 않는다. 로그 전체 event, FDC 전체 시계열과 측정 전체 행을 지도나 Wiki로 복제하지 않는다. 설정 snapshot의 diff는 같은 파일군에서 schema가 호환되는 승인 표본 사이에서만 key 추가·삭제·변경을 제한된 결과로 계산한다.

실행 파일은 실행하지 않으며 매크로도 활성화하지 않는다. 압축 파일은 해제 출력 바이트 상한을 적용하고 중첩 압축은 1단계까지만 읽는다. XML은 entity 선언이나 내부 DTD subset이 있으면 거부하고, 내부 subset이 없는 `<!DOCTYPE root>` 같은 선언만 있는 문서는 외부 DTD를 읽지 않고 파싱한다. 1차 범위에서는 암호화 파일을 해독하지 않고 `unreadable: encrypted`로 기록한다.

높은 entropy만으로 암호화라고 확정하지 않는다. 암호화 flag 등 확인 가능한
형식 근거가 있을 때만 `encrypted`로 기록하고, 그 밖의 알 수 없는 바이너리는
`unsupported`와 낮은 신뢰도의 추정으로 남긴다. 파서 입력 바이트, 출력 바이트,
행·노드·압축 항목 수, 압축 해제 바이트와 실행 시간을 유한하게 제한한다.
제한에 걸린 추출 결과는 일부만 관측했음을 표시하며 완전한 파일 구조로 취급하지 않는다.
입력 상한보다 큰 줄 단위 파일(텍스트·로그, CSV/TSV, key/value 텍스트)은 상한 안의 완전한 줄까지 읽어
일부 관측으로 기록하므로 헤더와 필드 이름은 남는다. JSON·XML처럼 앞부분만으로 구조를 읽을 수 없는 형식은
`too-large`로 기록한다.

**Extractor workbench.** 미지원 형식은 엔지니어가 승인된 대표 샘플 하나를 `rollouts/` 밖의 로컬 복사본 디렉터리에 두고 엔지니어 전용 명령 `equipment-map workbench <copy-dir> --method <name>`으로 추가 방법을 시도한다. 시도마다 `<copy-dir>/attempts.jsonl`에 `{ts, input_sha256, method, method_config, result_sha256|null, failure_reason|null, next_safe_action}`을 append만 한다. `hermes-gui` 방법은 추출을 실행하지 않고 `<copy-dir>/handoff.json`(입력 hash, 엔지니어가 지정한 승인 GUI 도구, 허용 출력 경로)만 쓰며, 사람이 감독하는 Hermes 세션의 결과는 엔지니어가 `--record`로 기록한다. workbench는 `rollouts/`와 `data-map/`에 쓰지 않으며, 성공한 방법은 별도 검토·테스트를 거친 CLI 릴리스의 새 extractor 모듈로만 승격한다. 승격 코드는 복사본의 샘플 내용이 아니라 `attempts.jsonl`에 기록된 방법·옵션·hash만으로 만들고, 엔지니어가 같은 복사본에서 새 모듈로 workbench를 다시 실행해 승격 대상 시도와 같은 `result_sha256`을 얻어야 릴리스한다. `hermes-gui` 결과는 자율 단계에서 GUI를 실행할 수 없으므로 승격하지 않는다. 그 전까지 해당 파일군은 `unsupported-format` 보고로 남는다.

### 4.6 Local LLM Analysis

CLI는 회사 내부의 승인된 OpenAI 호환 endpoint를 직접 호출한다. 에이전트 도구의 대화 모델에는 원본이나 추출 내용을 전달하지 않는다. 내부 로컬 LLM에는 원본 전체가 아니라 다음 묶음을 전달한다.

- 파일군 규칙과 통계
- 대표 샘플에서 추출한 제한된 내용
- extractor가 만든 구조
- 이미 알려진 장비·공정 용어집
- 근거 인용을 위한 해당 입력 묶음의 sample SHA-256 식별자
- pass 2 이상에서만, 직전 완료 pass의 검증된 `inferred` 값 중 같은 파일군과 검증된 관계로 직접 연결된 파일군의 `category`·`description` (`prior_inferred` 블록)

`prior_inferred` 블록은 항목마다 family ID, pass 번호, 값, provenance를 담고 `rollout.json`의 `prior_max_bytes`(양의 정수, 계획 hash에 결합)를 넘지 않는다. 넘치면 같은 파일군을 먼저 남기고 연결 파일군을 family ID 순으로 잘라낸다. 프롬프트는 이 블록이 이전 추정이며 틀릴 수 있고, 현재 관측 근거로 유지·수정·`unknown`을 판단하라고 명시한다. evidence 검증기는 `prior_inferred` 항목의 인용을 거부하며 인용 가능한 근거는 종전대로 해당 파일군 sample record의 SHA-256뿐이다. 결과는 pass에 관계없이 `inferred`다. 필드 키의 family 입력 hash에는 직접 연결된 파일군의 Observed 요약 hash를 포함하고, 전달한 `prior_inferred` 블록 hash는 provenance에만 기록한다. 따라서 현재 파일군과 연결 파일군의 관측 입력이 바뀌지 않았으면 prior가 바뀌어도 재호출하지 않는다.

LLM에는 파일군 설명, 데이터 category, field 의미·역할, 생성 주체, lifecycle, 예상 생성 주기, 운영 활용법, 민감도, 신뢰도와 근거 샘플을 한꺼번에 JSON으로 만들게 하지 않는다. CLI가 필드별로 짧은 응답을 요청하고 JSON을 조립·검증한다. 신뢰도(`confidence`: `high`|`medium`|`low`)와 근거 샘플(`evidence`: 해당 파일군 sample record의 SHA-256 목록)도 각각 별도 요청과 검증기를 거치는 필드다. 필드당 의미 검증 응답 슬롯은 최대 2개다. 일시적인 전송 실패는 의미 검증 실패로 세지 않으며 아래의 별도 상한을 따른다. 두 시도가 모두 실패하면 `confidence: low`와 `unresolved` 사유를 기록하고 다음 항목으로 진행한다. 추론과 관찰 사실을 구분하고 LLM 유래 필드마다 `model_id`, `model_config`, `prompt_version`과 `glossary_version`을 남긴다. schema validator는 LLM 결과를 `observed` 위치에 쓸 수 없게 하고 모든 LLM category·lifecycle·field role과 의미를 `inferred`로 고정한다.

LLM 실행 설정은 `llm.model`(요청할 모델 또는 사내 alias), `temperature`, `max_tokens`, `connect_timeout_seconds`, `request_timeout_seconds`, `max_elapsed_seconds`, `transport_max_attempts`, `retry_backoff_seconds`를 포함하며 계획 hash에 결합한다. 참조한 profile·glossary 파일의 내용 hash도 계획에 포함하고 실행 전에 다시 확인한다. 시간 한도는 유한한 양수, `max_tokens`는 양의 정수, temperature와 backoff는 유한한 0 이상 값, `transport_max_attempts`는 1~3의 정수다. 운영자가 전용 Qwen 또는 승인된 HCP endpoint와 모델을 선택하며 실행 중 자동 모델 전환은 하지 않는다. 요청 alias와 서버가 반환한 모델 ID·revision·serving 설정을 구분해 기록하고, 서버가 공개하지 않은 실제 backend 정보는 `unknown`으로 남긴다.

HTTP 429/502/503/504, 연결 오류와 timeout만 일시적 전송 실패로 취급한다. 각 의미 응답 슬롯당 최대 `transport_max_attempts`회 전송하고, 대기는 `retry_backoff_seconds * 2**(retry_index-1)`이다. 유효한 `Retry-After`가 더 길면 그 값을 따르되 남은 실행 시간을 넘기면 재시도하지 않는다. 매 요청과 대기는 LLM 및 rollout 시간 한도로 제한한다. 모든 전송은 보내기 전에 `llm_max_requests`에서 차감하고 디스크에 예약을 남긴다. 한도를 소진하면 `unresolved: budget`, 전송 재시도 소진은 `unresolved: service-unavailable`, 다른 HTTP 오류는 `unresolved: api-error`로 남긴다. 인증 오류는 추가 호출 없이 나머지 필드도 `api-error`로 종료한다. 의미 응답 슬롯 두 개가 모두 검증 실패하면 `unresolved: invalid-response`다. 같은 승인 실행의 재개는 횟수와 시간 사용량을 초기화하지 않는다.

파일 내용, 파일명과 용어집은 분석 자료이지 지시가 아니다. LLM에 명령 실행,
추가 파일 요청, endpoint 변경 도구를 제공하지 않는다. 필드 응답은 길이·형식과
입력 근거를 검증하며, 형식 검증 통과를 의미 정확성 승인으로 보지 않는다.
LLM 자기평가 confidence가 높아도 추론은 추론으로 유지한다. Wiki의 Observed는
결정론적으로 관측한 값만 사용하고 LLM 의미 해석은 근거가 붙은 추론으로 표시한다.

필드 결과는 family 종료까지 메모리에 두지 않는다. `work/llm.sqlite`의 트랜잭션에 요청 예약, 응답 처리 상태, 검증된 필드 값 또는 unresolved 사유와 provenance를 저장한다. 필드 키는 collection scope, family 입력 hash, field, 모델 설정·prompt·glossary hash다. 응답 처리와 결과 저장은 한 트랜잭션으로 커밋하고 `llm-attempts.jsonl`은 이 기록의 재생성 가능한 감사용 export다. 재개 시 커밋된 결과는 재호출하지 않으며 미완료 예약은 사용한 전송으로 세고 남은 한도 안에서만 이어간다. 원격 API의 정확히 한 번 실행은 보장하지 않는다. raw prompt/response는 기본 보존하지 않지만, 검증된 의미 필드 값은 지도와 재개를 위해 저장한다.

### 4.6.1 장비 용어 사전 — 목표 계약

현행 계약의 용어집 입력·버전·hash를 다음의 검토 가능한 사전으로 확장한다. 단어 수집과 의미 확인은 별도 작업이다. 사전은 필드명·약어·단위·enum·alarm code·식별자 역할부터 다루고 모든 일반 단어를 수집하지 않는다. 같은 표기라도 장비 종류·소프트웨어 버전·파일군·필드 문맥이 다르면 별도 항목이다.

| 항목 | 최소 기록 |
|---|---|
| 정체성 | `term_id`, 원문 표기, 적용 장비/버전/파일군/필드 범위, 명시적으로 검토한 별칭 |
| 관측 | 등장 위치, scope·observation·sample/extract hash와 locator |
| 의미 | 정의 또는 후보들, 명시된 단위·값 해석, 적용 한계 |
| 출처 | 관측 근거, 매뉴얼 식별자·버전·내용 hash·절/페이지, 또는 엔지니어 확인자·시각·설명 |
| 상태 | `unknown`, `inferred`, `confirmed`, `conflicting`; 확인자와 확인 근거 |
| 이력 | 사전 버전, 이전 항목 참조, 수정/반박 이유와 시각 |

추출기가 원문 표기와 등장 근거를 수집하고, LLM은 의미 후보만 제안한다. `confirmed`는 해당 문맥의 정의를 엔지니어가 근거와 함께 확인했다는 뜻이다. 모든 장비에 통용되는 정의나 LLM claim의 Observed 승격을 뜻하지 않는다. 서로 다른 정의가 충돌하면 후보와 근거를 보존하고 `conflicting`으로 남긴다. LLM confidence나 반복 등장만으로 확정·별칭 병합·단위 변환을 수행하지 않는다.

사전의 승인 원본은 사내 버전 관리 영역의 `glossary.json`이다. 각 실행은 승인된 버전·파일 hash를 계획에 고정하고, 목표 schema의 `data-map/glossary.json`에는 그 실행에 사용한 불변 사본을 둔다. 실행 중 발견한 새 후보와 정정은 조사 원장에 기록해 다음 사전 버전의 검토 입력으로 삼는다. 실행 중인 사전 파일을 고치거나 과거 지도의 사본을 덮어쓰지 않는다. 구버전 지도는 구버전 사전으로 재현할 수 있어야 한다.

해석 입력에는 적용 범위가 맞는 `confirmed` 정의만 참고 정의로 제공한다. 관련 미확인·충돌 항목은 정답 후보로 주입하지 않고 미해결 표시로 전달한다. 선별은 정확한 표기·검토된 별칭·문맥 일치 규칙과 안정된 term ID 순으로 결정론적으로 수행한다. 현행 user message 32 KiB와 glossary 부분 4 KiB 상한 안에서 생략 항목을 기록하고, 사용한 term ID·버전·부분 hash를 provenance에 남긴다. 사전만으로 해당 파일의 의미가 입증되지는 않는다. 해석 claim의 evidence는 계속 현재 파일군의 sample record만 허용하며, 매뉴얼·사전·이전 추론을 sample SHA로 위장하지 않는다.

사전 수정은 다음 승인 실행의 입력 변경이다. 같은 scope라도 glossary hash가 바뀌면 기존 해석 캐시와 다른 입력이며, 결과 승인 뒤의 변경은 새 rollout을 요구한다. 선택된 항목만을 기준으로 캐시 키를 최적화하는 변경은 별도 검증 전에는 도입하지 않는다. 사전의 문장과 매뉴얼 참조 역시 분석 자료이며 명령 실행·자동 파일 열람 권한이 아니다.

### 4.6.2 실행 비용과 제한된 병렬화 — 목표 계약

기본 구조는 운영 에이전트 세션 하나, CLI coordinator 하나, 제한된 HTTP worker pool과 기존 SQLite다. 파일마다 코딩 에이전트를 띄우거나 장비마다 Python을 재생성하지 않는다. FTP 연결 1개와 승인된 요청 속도는 LLM 동시성과 분리한다.

- 해석 작업의 근거 단위는 파일군 하나의 실제 대표 표본 묶음이다. pattern 최대 5개, loose 최대 3개를 유지하고, 정확히 3개나 6개로 맞추기 위한 추가 다운로드·다중 파일군 packing을 만들지 않는다. 표본 0개는 호출하지 않는다.
- 전역 in-flight HTTP 상한은 최대 8이다. 1개 기준선에서 2/4/6/8을 비교해 승인할 값을 정하며 8배 성능을 전제하지 않는다. 같은 endpoint를 쓰는 선정 요청도 이 상한에 포함한다. 운영 에이전트의 감독 추론을 동시에 반복하지 않는다.
- 파일군 패킷 하나가 HTTP 요청 하나라는 뜻은 아니다. 현행 필드별 계약에서는 의미 7개와 최대 16개 필드 설명 각각에 confidence/evidence 호출이 이어져 정상 첫 시도만 최대 69회가 될 수 있다. `UNKNOWN`과 저장된 결과는 불필요한 후속 요청을 줄인다.
- coordinator가 작업 키·시도·budget을 전송 전에 원자적으로 예약하고 결과별로 즉시 커밋한다. worker는 map·Wiki를 직접 쓰지 않는다. 한 묶음 전체의 완료를 기다리지 않고 빈 슬롯을 채운다.
- 요청 수는 예약마다 차감한다. 병렬 구간의 active wall time은 한 번만 차감한다. crash 뒤 마지막 저장 시각부터 미완료 예약의 가장 늦은 deadline까지의 겹친 구간을 보수적으로 한 번만 차감하고, 이후 downtime은 제외한다. 요청별 timeout을 중복 합산하지 않는다. 시간 차감 schema와 실패 주입 검증 없이 병렬 기능을 켜지 않는다.
- 인증 실패·deadline·budget 소진은 새 예약을 막고, 이미 보낸 요청은 유한 timeout 안에서 정리한다. 서버 추론 취소나 remote exactly-once는 보장하지 않는다. 429/503 대기는 새 예약에도 반영한다.

입력은 제한된 추출 패킷을 유지한다. 서버 context는 상한이며 채울 목표가 아니다. 약 200k 같은 배포값을 가정해 32 KiB user message 상한을 자동 확대하지 않는다. 과대 입력은 부분 관측 또는 unresolved로 남긴다.

요청 축소는 병렬화와 분리해 비교한다. 호출 수가 계속 병목이면 claim 하나의 값·confidence·evidence를 함께 받는 버전된 짧은 응답을 시험한다. 여러 파일군이나 모든 claim을 거대한 JSON으로 합치지 않는다. 이 후보는 정확도·인용·유한 재시도·재개 검증 후에만 현행 필드별 계약을 대체한다. worker 수·큐 정책은 승인 계획에 포함하되 새 계약의 의미 캐시 키와 분리하고, scope·관측 입력·claim·모델 의미 설정·prompt/schema·glossary hash는 캐시 키에 유지한다.

최소 계측은 빌드/사람 대기/FTP/추출/LLM/발행의 실제 경과 시간, list·SIZE·MDTM·RETR 건수, 바이트, 요청·재시도·cache hit, HTTP p50/p95, unresolved 사유와 검토된 claim 수다. `size_dirs` HTTP 한 번을 FTP 명령 한 번으로 세지 않는다. 비스트리밍 완료 지연을 TTFT로 부르지 않고 미지원 서버 지표는 unknown으로 둔다. raw prompt/response·자격 증명·장비 경로는 성능 집계에 넣지 않는다. 같은 로컬 근거 패킷·같은 품질/coverage에서 한 변수씩 비교하며 실장비 시간을 아직 측정하지 않은 성능 목표를 보장하지 않는다.

### 4.7 Data Map

```text
data-map/
  index.json              # 데이터 세트 버전과 구성 파일 hash
  equipment.json          # 장비와 접속 범위
  file-families.json      # 파일군, 규칙, 통계, 해석
  paths.json              # 디렉터리 구조 요약
  unreadable.json         # 암호화/미지원/오류 파일군
  coverage.json           # 목록/로컬 이름/표본/의미 해석 완료 범위
  extracts.jsonl          # 표본마다 추출 결과 record 한 줄
  metadata-evidence.jsonl # 파일군마다 관측 메타데이터 근거 record 한 줄
  evidence/<장비 경로>    # 받은 대표 샘플 원본
  wiki/<장비 경로>        # 폴더마다 index.md, 사람과 LLM이 읽는 Obsidian 호환 Markdown
  graph/                  # graph DB import용 nodes/edges JSONL
```

JSON 파일은 사람이 읽을 수 있게 들여쓰기해 쓰고, JSONL 파일은 한 줄에 record 하나다. 계획 hash와 family·observation·claim·graph ID 같은 payload hash는 메모리에서 만든 compact canonical JSON으로 계산하므로 들여쓰기의 영향을 받지 않는다. extract와 metadata evidence의 SHA-256도 `extracts.jsonl`·`metadata-evidence.jsonl`에서 해당 record 한 줄의 payload hash다. 그래서 뒤 pass가 record를 더해 파일을 다시 써도 앞선 인용은 그대로 유효하다. 표본과 manifest 항목 같은 파일 hash는 디스크의 원시 바이트로 계산해 공백 하나의 변경도 드러낸다. 같은 입력은 언제나 같은 바이트를 쓴다.

`evidence/`와 `wiki/`는 장비의 폴더 구조를 그대로 따른다. `<장비 경로>`는 source의 정규화한 절대 경로에서 앞의 `/`를 빼고 구성 요소마다 아래 로컬 이름 규칙을 적용한 것이며 허용 루트 기준 상대 경로가 아니다. 그래서 허용 루트가 여럿이거나 겹쳐도 원격 파일 하나는 로컬 경로 하나를 가진다. 사람이 여는 파일·폴더 이름에는 ID나 hash를 쓰지 않는다. hash는 record, manifest, graph ID와 `work/history/<scope 앞 12자>/`에만 둔다. 인용 검증은 표본이면 파일 바이트를, extract·metadata evidence면 해당 record를 다시 hash해 전체 값과 대조한다.

로컬 이름은 Windows에서 쓸 수 있고 원격 이름마다 하나로 정해진다. Windows가 금지한 문자, `%`, 제어 문자와 이름 끝의 `.`·공백은 `%XX`로 쓰고, 예약 이름 `index.md`와 Windows 장치 이름(`NUL.txt` 등)은 첫 글자도 `%XX`로 쓴다. `%`도 항상 바꾸므로 서로 다른 원격 이름이 같은 로컬 이름이 되지 않는다. Windows 파일 시스템은 대소문자를 구별하지 않으므로, 이미 배정한 로컬 경로와 casefold해 같아지는 경로는 하위 전체와 함께 `case-collision`으로 로컬 지도에서 빼고, 배정한 이름은 같은 scope 안에서 바꾸지 않는다.

Windows MAX_PATH(260자) 안에 들도록 CLI가 `rollouts/<rollout-id>/` 아래에 쓰는 모든 경로는 그 디렉터리 기준 120자 이하이고, `data-map/`을 `work/history/<scope 앞 12자>/`로 바꾼 경로도 이 상한을 지킨다. 이를 넘는 파일과 폴더(하위 전체 포함)는 `path-too-long`으로 로컬 지도에서 뺀다. 뺀 항목은 표본으로 고르지 않지만 inventory와 grouping에는 원격 경로로 남고, 가장 가까운 표현 가능한 상위 폴더의 `index.md`와 `coverage.json`에 사유와 함께 기록한다.

원본 자격 증명, 전체 원본 파일, LLM 비밀 설정은 저장소에 넣지 않는다. 검증된 의미 필드 값은 지도와 재개용으로 보존한다. raw LLM prompt/response는 기본적으로 보존하지 않고 model·prompt·입력·출력 hash만 기록한다. 별도 보존이 승인된 경우에만 접근 제어된 로컬 위치를 사용하고 `data-map/`에는 위치 식별자와 hash만 남긴다.

내용을 받지 못한 파일군도 출력한다. `metadata-evidence.jsonl`에 파일군마다 source scope, 경로, 크기, 시각, 관측 출처, 생략 사유를 담은 record를 기록하고 그 record의 SHA-256을 `evidence_kind: metadata`로 인용한다. 대표 샘플이 없으면 LLM 내용 해석을 호출하지 않고 `unresolved: no-sample`로 둔다. Wiki에는 관측한 메타데이터만 사실로 등록하며 내부 필드·용도에 대한 근거로 사용하지 않는다. 샘플이 있는 해석은 기존 sample SHA를 인용한다.

완료와 해석 품질은 별도로 보고한다. `coverage.json`에는 허용 루트별 inventory 완료 여부와 미탐색 frontier 수, 로컬 지도 완료 여부와 사유별 제외 수, 발견한 파일·파일군 수, 표본이 있는 파일군 수와 없는 사유별 수, resolved/unresolved 의미 필드 수와 사유별 수를 남긴다. 알려지지 않은 전체 파일 수를 추측해 coverage 백분율을 만들지 않는다. budget으로 inventory가 끝나지 않았으면 `inventory_complete: false`다. 정상 종료는 승인된 실행의 종료이지 장비 전체 이해나 모든 해석 성공의 증명이 아니다. 이 coverage를 결과 검토표에 포함한다.

### 4.7.1 파일군 사이의 관계

Extraction이 끝난 뒤 현재 collection scope의 inventory와 이미 승인 범위 안에서 받은 대표 샘플의 추출 결과로 관계를 만든다. 별도 그래프 DB나 LLM 호출 없이 `file-families.json`의 각 파일군에 `features`, `relationships`, `relationship_coverage`를 추가한다. 관계 발견을 이유로 다운로드·탐색 범위를 넓히거나 참조 파일을 자동으로 열지 않는다. 표본을 받지 못한 파일군은 메타데이터 관계와 다른 표본이 명시적으로 참조한 도착점만 될 수 있으며, 자신의 미관측 내용을 근거로 관계를 만들지 않는다.

초기 관계 유형은 다음으로 제한한다. 구조·주제 유사성은 탐색 단서이며 업무상 연관성을 확정하지 않는다.

| `type` | 관측 조건 | 해석의 한계 |
|---|---|---|
| `same_directory` | 정규화한 직접 상위 경로가 같음 | 공통 최상위 루트만으로 연결하지 않음 |
| `similar_name` | 기존 프로필 규칙으로 정규화한 파일명 stem이 같음 | 확장자·포맷이 달라도 파일군은 합치지 않음 |
| `shared_field` | 추출한 필드 이름이 같음 | 같은 값·자료형·의미라는 뜻은 아님 |
| `shared_keyword` | 추출 텍스트의 유효 키워드가 겹침 | 주제 유사성 단서만 제공 |
| `shared_identifier` | 명시된 식별자 필드의 이름과 문자열 값이 모두 같음 | 같은 run이나 인과관계임을 확정하지 않음 |
| `references_file` | 샘플에 명시된 경로가 현재 inventory의 파일 하나로 해석됨 | 참조 문자열의 존재를 증명하며 실제 사용을 증명하지 않음 |

`features`에는 키워드, 필드 이름, 식별자, 파일 참조를 종류별로 보존한다. 추출은 결정론적으로 수행하며 규칙 버전을 기록한다. 키워드는 Unicode 문자·숫자 토큰을 casefold하고 3자 미만·숫자만인 토큰과 버전된 불용어(`data`, `status`, `file`, `log` 포함)를 제외한다. 같은 키워드가 추출 표본이 있는 파일군의 절반을 초과해 나타나면 키워드 관계 생성에서 제외한다. 이 빈도는 관측한 표본에 대한 값이며 장비 전체의 빈도가 아니다.

식별자는 파서가 필드와 값을 연결할 수 있는 경우만 추출한다. 초기 필드 이름은 대소문자와 `_`, `-`를 정규화한 `lotid`, `waferid`, `recipeid`, `runid`로 제한한다. 값은 앞뒤 공백만 제거하고 대소문자와 선행 0을 보존하며 빈 값·일반 숫자 조각은 매칭하지 않는다. `run_id=0042`는 유효하지만 본문에 단독으로 나온 `0042`는 식별자가 아니다. 약어·동의어·새 식별자 종류는 검토된 규칙 버전에서만 확장하며 LLM이 임의로 합치지 않는다. 동일 값이 다른 장비·시간대에서 재사용될 수 있으므로 값 일치 자체만 관측 사실로 남긴다.

파일 참조는 추출기가 위치와 함께 보존한 명시적 경로 문자열만 사용한다. 상대 경로는 원본 샘플의 디렉터리 기준으로 정규화하고 기존 source 경로·허용 범위 규칙을 적용한다. basename만으로 여러 후보가 생기거나 대상이 미탐색·범위 밖이면 `features`에 `unresolved`와 사유를 남기고 임의의 대상 관계를 만들지 않는다. URL이나 파일 속 지시문을 실행하지 않는다.

관계 한 건은 `target_family_id`, `type`, `matched_value`, `rule_version`, `observed_vs_inferred: observed`, `support_scope`와 `evidence`를 가진다. `support_scope`는 경로·이름 관계에 `metadata`, 내용 관계에 `samples`다. 내용 일치 관계는 양쪽의 원본 경로, sample SHA-256, extract SHA-256, 추출 결과 내 위치를 인용한다. 명시적 파일 참조는 출발 표본의 위치와 도착 파일의 metadata evidence를 인용한다. 경로·이름 관계에 참여하는 파일군도 metadata evidence를 생성하며, 근거가 현재 map에 없거나 위치에서 해당 값을 확인할 수 없으면 관계를 거부한다. 같은 바이트가 여러 경로에 있어도 출처 경로를 구분한다.

같은 source/target family ID·type·matched_value의 근거는 한 관계로 합친다. 대칭 관계는 family ID가 작은 쪽에 한 번만 저장하고 Wiki에서 양방향으로 탐색한다. `references_file`은 참조하는 쪽에 저장한다. 파일군 내부의 관계는 초기 범위에서 생략한다. 대표 샘플의 연결을 파일군 전체 구성원에 적용하지 않으며 업무 의미 설명은 기존 LLM 해석의 `inferred`로만 표시한다. 예를 들어 같은 recipe ID 관측은 사실이지만 “이 설정으로 이 측정을 수행했다”는 별도 근거가 필요한 추론이다. 높은 confidence나 연결 수로 추론을 Wiki의 Observed로 승격하지 않는다.

초기 규칙 버전은 표본당 최대 100개 feature와 관계당 최대 5쌍의 근거를 보존하고, 파일군당 연결 참여 수 20개 및 지도 전체 관계 10,000개에서 멈춘다. feature는 파일 참조·식별자·필드·키워드 순서에서 정규화 값·근거 위치 순으로 정렬해 선택한다. 후보는 `references_file`, `shared_identifier`, `similar_name`, `same_directory`, `shared_field`, `shared_keyword` 순으로 생성하고 같은 유형은 source/target family ID·매칭 값 순으로 처리한다. 키별 역색인으로 후보를 순차 생성하고 모든 파일 쌍을 메모리에 펼치지 않는다. 처리 중에도 rollout 시간 상한을 지킨다. 제한값과 규칙 버전은 CLI 버전에 고정하며 재개 시 바꾸지 않는다.

`relationship_coverage`는 사용한 표본 수, feature·관계·근거 잘림 여부, 미해결 참조 수와 사유, 중단 사유(`no-sample`, `partial-extraction`, `feature-limit`, `evidence-limit`, `family-limit`, `map-limit`, `deadline`)를 기록한다. 한도 때문에 보지 못한 후보 수는 추측하지 않는다. 관계가 없다는 사실은 무관함의 증명이 아니다. Wiki는 관계 유형·일치 값·표본 범위·근거·잘림 상태를 함께 표시하고 기존 반출 제한을 따른다.

### 4.7.2 장비 데이터 category와 시간 profile

`file-families.json`의 각 파일군은 `data_profile`을 가진다. `data_profile`은 `category`, `temporal`, `schema`와 `domain`으로 나누며 각 값은 4.7절 field record와 같이 `observed_vs_inferred`, typed evidence, producer와 version, confidence, `unresolved`를 가진다. extractor가 만든 구조는 `observed`, LLM의 category·역할·용도 해석은 항상 `inferred`다. 근거가 없으면 값 대신 `unknown` 또는 `unresolved`를 저장한다.

초기 `category` enum은 다음으로 고정한다. category는 파일군의 속성이지 별도 class hierarchy가 아니다.

| category | 지도에 남길 최소 정보 |
|---|---|
| `event_log` | event 시각 범위, level/severity, code/state/component 필드, 제한된 유형별 count |
| `alarm` | alarm code, severity, 발생·해제·ack 상태와 시각 필드 |
| `fdc_timeseries` | channel/tag, 단위, 자료형, sample interval, 시각 범위, row/null/invalid 수, 표본별 min/max |
| `measurement_result` | lot/wafer/run/recipe/site 식별자, 측정 시각, metric, 단위, method, 좌표, 명시된 limit·quality·pass/fail |
| `hardware_configuration` | component 계층, parameter, 명시된 setpoint/readback, snapshot/version/effective 시각, 제한된 표본 diff |
| `recipe_program` | recipe ID/version, 순서가 있는 step, parameter·단위와 명시적 파일 참조 |
| `software_firmware` | component, product/version/build와 적용 또는 관측 시각 |
| `maintenance_calibration` | 대상 component, 작업·절차·교정 parameter, limit와 기록된 결과·시각 |
| `reference_lookup` | title, schema/version, lookup key/value 구조와 effective 시각 |
| `unknown` | 관측한 format·schema와 미해결 사유만 보존 |

`temporal`은 서로 다른 시간 의미를 섞지 않는다. source 내부 시각, source가 제공한 file mtime, inventory `observed_at`, snapshot/reference의 명시적 validity를 각각 원본 값·UTC 정규화 값·timezone/clock basis와 함께 기록한다. timezone이나 clock 출처가 없으면 추측하지 않는다.

반복 inventory의 `change_state`는 `single-pass`, `new`, `changed`, `unchanged`, `missing` 중 하나와 비교한 observation ID를 가진다. 의미상 `lifecycle`은 `append-series`, `rolling-or-rotating`, `replaced-snapshot`, `immutable-per-run`, `static-reference`, `unknown` 중 하나다. path 또는 두 번의 동일 목록만으로 lifecycle을 확정하지 않으며 LLM 판단도 `inferred`다. 최소 3개의 정규화 가능한 member 시각처럼 간격 근거가 있을 때만 관측 gap과 추정 cadence를 기록하고, 그보다 적으면 `unknown`이다. 1차 버전은 기대 cadence가 없는 gap record를 만들지 않는다.

식별자는 목적에 따라 구분한다. `family_id`는 현재 collection scope의 파일군 규칙을 식별하고, `observation_id`는 pass에서 본 source file 상태를 식별한다. sample record와 metadata-evidence record는 자신이 인용하는 `observation_id`를 포함한다. 다운로드한 전체 표본의 SHA-256과 bounded extract의 SHA-256은 서로 바꾸어 쓰지 않는다. 의미 claim은 family, field, 값, provenance의 canonical hash로 `claim_id`를 만들며 모든 ID는 현재 scope와 typed evidence로 역추적할 수 있어야 한다.

### 4.7.3 Graph와 Wiki 파생 형식

graph DB 제품을 기준 데이터로 삼지 않는다. 4단계 publish는 승인된 현재 `data-map/`에서 UTF-8/LF, 한 줄 한 canonical JSON record인 `graph/nodes.jsonl`과 `graph/edges.jsonl`을 결정론적으로 생성한다. node type은 초기에는 `equipment`, `path`, `file_family`, `field`, `claim`만 사용한다. `path` node는 `paths.json`의 디렉터리 요약이며 inventory의 모든 파일을 graph node로 복제하지 않는다. edge는 `contains_path`, `contains_family`, `has_field`, `supports_claim`과 4.7.1절의 관계 type을 사용한다.

모든 node와 edge는 stable ID, collection scope, type, `observed_vs_inferred`, typed evidence, producer/rule/extractor/model version, confidence, temporal/validity 범위, sensitivity, `unresolved`를 해당할 때 포함한다. graph node ID는 4.7.2절의 기존 ID를 재사용하거나 고정 입력의 canonical JSON hash로 만든다: `file_family:<family_id>`, `claim:<claim_id>`, `equipment:<sha256([scope,equipment_id])>`, `path:<sha256([scope,normalized_directory_path])>`, `field:<sha256([scope,family_id,exact_field_path])>`. hash 입력 배열은 이 순서의 UTF-8 compact JSON이고 SHA-256은 소문자 hex다. edge ID는 `edge:<sha256([type,source_id,target_id,matched_value,rule_version])>`이며 같은 canonical encoding을 쓴다. LLM claim과 `supports_claim`은 `inferred`이고 관측 node 또는 evidence를 인용해야 한다. shared identifier, 가까운 시각 또는 파일 참조만으로 `produced`, `caused`, `used_recipe` 같은 인과 edge를 만들지 않는다. JSON-LD, RDF, GraphML과 특정 graph DB loader는 실제 consumer가 정해진 뒤 이 두 파일에서 만드는 별도 adapter다.

Wiki는 사람과 LLM이 함께 읽는 Obsidian 호환 Markdown이며 장비의 폴더 구조를 그대로 따른다. 4단계 publish는 승인된 현재 `data-map/`에서 inventory한 폴더와 그 상위 폴더마다 `wiki/<장비 경로>/index.md`를 결정론적으로 생성한다. `wiki/index.md`는 원격 `/`의 페이지이며 맨 앞에 scope, 허용 루트와 coverage 요약을 둔다. 각 `index.md`는 그 폴더의 직접 하위 폴더와 그 폴더에 있는 파일군만 설명하고, 더 깊은 항목은 하위 폴더의 `index.md`에 맡긴다. 사람과 LLM은 `wiki/index.md`부터 폴더 링크를 따라 내려가며 찾는다. 허용 루트 밖의 상위 폴더 페이지는 하위 폴더 링크만 두고 inventory하지 않았다고 표시한다. 파일군은 폴더를 넘지 않으므로 파일군 페이지를 따로 만들지 않는다. 폴더 `index.md` 안에 파일군마다 Observed, Fields, Inferred, Evidence, Relationships, Unresolved 절을 두고 LLM 유래 값은 Inferred 절에만 둔다. 링크는 다른 `index.md`로 가는 표준 상대 Markdown 링크뿐이며, 링크 대상은 로컬 이름을 한 번 더 URL percent-encoding한 경로다. 표본 원본은 링크하지 않고 evidence 경로를 글자로 적는다. frontmatter는 따옴표로 감싼 평탄한 YAML 세 키(`path_id`, `pass_id`, `generated_by`)이며 표시용이고, 무결성은 manifest의 파일 hash가 맡는다. `path_id`는 그 폴더의 graph `path` node ID다.

Fields 절은 필드마다 관측 자료형, 단위, 표본 범위의 min/max, null/invalid 수와 예시 값을 보여 준다. 예시 값은 extract 결과에서만 가져오며 필드당 서로 다른 값 최대 3개를 값마다 40자로 잘라 가져온 표본의 파일 이름과 함께 표시한다. 필드 이름에 `pass`, `pwd`, `secret`, `token`, `key`, `credential`이 들어 있으면(대소문자 무시) 예시 값과 범위를 모두 `(masked)`로 바꾸고, 그 값은 관계의 일치 값을 포함해 Wiki 어디에도 쓰지 않는다. 이름 기반 가리기는 최소 장치일 뿐이므로 4단계 검토에서 예시 값을 확인한다. 예시는 필드 값 하나씩이며 원문 log line, FDC/측정 row, 파일 전체와 임의의 발췌는 Wiki에 넣지 않는다.

Wiki는 이후 LLM이 파일 도구나 Obsidian CLI로 읽는 입력이다. 데이터 유래 문자열(경로, 파일군 규칙, 필드 이름, 예시 값, 일치 값)은 항상 inline code span 안에 쓰고 표 안의 `|`는 이스케이프해, `[[`, `#`, `%%`, `$`, `==`, HTML 태그가 링크·태그·주석·수식으로 렌더링되지 않고 글자 그대로 보이게 한다. 이 처리는 렌더링만 막을 뿐 LLM이 값 속 문장을 따르는 것까지 막지는 못한다. 그래서 Wiki를 읽는 LLM 세션은 Wiki 전체를 신뢰할 수 없는 데이터로 다루며, Wiki 안의 문장은 명령 실행, 장비 접근이나 파일 변경의 근거가 되지 않는다. 외부 이미지와 링크는 넣지 않는다. 모든 Observed·Inferred 항목과 관계는 현재 map의 `observation_id`, sample 또는 metadata evidence SHA, 필요하면 extract SHA와 field/row/byte locator를 인용한다. citation이 없거나 현재 scope에서 해석되지 않는 항목, LLM 의미를 Observed로 표시한 항목, 근거에 없는 인과 주장은 발행을 거부한다.

각 폴더 페이지는 파일 목록에 앞서 관측 형식·주요 필드·표본 범위를 이용한 개요와 직접 하위 폴더의 짧은 설명을 제공한다. 대표 파일마다 내용 요약과 부분 관측 여부를 표시하고, 의미 설명은 기존 검증된 Inferred claim만 재사용한다. Wiki 생성을 위해 새 LLM 해석 호출을 만들지 않는다.

Obsidian은 vault로 연 폴더에 `.obsidian/` 설정 폴더를 만들고 편집을 즉시 저장한다. `data-map/` 안에서 파일이 추가·변경되면 결과 승인이 거부되므로(5.2절) 엔지니어와 LLM은 `wiki/`를 `rollouts/` 밖으로 복사한 사본을 vault로 연다. vault에는 생성한 Markdown만 있고 장비 원본이 없으므로, 장비 파일 속 Markdown이나 HTML이 노트로 렌더링되지 않는다. 원본은 `index.md`에 적힌 evidence 경로에서 따로 연다. 사본은 승인 대상이 아니다. 완료된 `stage 4 next`는 no-op이므로 재호출을 재발행으로 취급하지 않는다. 새 검토 사본은 검증된 map에서 별도로 생성하고, 승인 후 지도 보충은 새 rollout으로 수행한다(4.8절). Wiki와 graph는 언제든 canonical map에서 재생성할 수 있는 파생물이며, 질의용 검색 adapter는 실제 요구가 생기면 canonical map에서 따로 만든다.

### 4.8 질문과 근거를 통한 개선 iteration — 목표 계약

목표 루프는 `초안 → 미해결 질문 → 추가 근거/사전 검토 → 반증·교정 → 비교 검증 → 새 iteration 발행`이다. 첫 실행은 목록과 대표 표본으로 구조·용어 후보를 만드는 데 적합하다. 반복 횟수 자체가 정확도를 보장하지 않으며 같은 입력에 같은 질문을 반복해 답변이 안정됐다는 사실을 개선으로 세지 않는다.

#### 4.8.1 질문·처리·의미 검증을 구분한다

검토 사본의 추가 조사 이력은 승인 map 밖의 별도 원장에 보관한다. 파일뿐 아니라 폴더 전체에 질문을 등록할 수 있으며, 폴더 요청은 알려진 모든 하위 파일과 미탐색 frontier를 포함한다. Wiki 열람, 호출자가 보고한 표본 제출, 처리 성공/실패/불명, 엔지니어·LLM의 추가 질문을 구분한다. Wiki를 열었다는 기록은 파일 해석 완료로 보지 않는다. 현재 scope·원격 경로·observation·sample/extract hash에 맞고 새 질문 이후에 제출되어 성공한 요청만 그 질문의 처리 완료로 표시한다. 처리 성공은 의미 정확성이나 전체 장비 coverage를 증명하지 않는다. 다음 iteration은 보충된 검증 map에서 새 사본을 생성한다. 추가 조사 요청은 수집 권한·보호 예외·새 budget이 아니며, 4.4.1절 운영 pass 순서와 샘플 선정 규칙을 자동 변경하지 않는다. 미수집·보호·미탐색 항목은 이유와 검토 필요 상태를 남긴다.

현재 오프라인 구현의 입력 projection과 명령은 `docs/architecture/wiki-generator.md`에 정리했다. 구현 범위는 11장을 따르고, 이 절의 나머지는 그 위에 얹는 목표 iteration 계약이다. 이 검토 도구는 4단계 전체 publish와 graph·승인 전이를 대신하지 않는다.

기존 `exploration.sqlite`의 `suggest → plan → submitted → finished` 흐름을 재사용한다. 별도 reflection/memory 파일을 진실 원천으로 추가하지 않는다. 목표 확장에서는 질문마다 다음 정보를 append-only 이벤트로 보존한다.

| 정보 | 내용 |
|---|---|
| 질문 | 고유 ID, 대상 scope·경로·파일군·필드, 현재 claim/term, 요청자·시각·목적 |
| 검증 계획 | 의심/충돌 이유, 필요한 근거, 유지·수정·반박을 판정할 기준 |
| 처리 근거 | 입력 map/사전 hash, 실제 제출한 observation·sample/extract hash, 요청 ID, 처리 성공/실패/불명 |
| 의미 검토 | `supported`, `corrected`, `refuted`, `unresolved` 중 판정, 검토자·시각·근거, 이전/새 claim·term 참조 |
| 다음 행동 | 남은 한계, 추가 관측/엔지니어 확인/사전 수정/extractor 릴리스 중 필요한 작업 |

LLM은 후보 질문을 만들 수 있고 엔지니어는 목적상 중요한 질문과 판정 기준을 정한다. 처리 성공은 작업 상태이며 의미 검토 통과가 아니다. 기존 도구의 `addressed`도 미처리 잔여 대상이 없다는 뜻으로만 읽는다. `page-read`는 페이지 바이트 반환, `submitted`와 `finished`는 호출자가 보고한 처리 기록이지 서버 수신·LLM 이해·정답 증명이 아니다.

예를 들어 `SV`라는 필드가 있다는 사실은 Observed다. 그 뜻이 설정값이라는 해석은 가설이다. 같은 문맥의 명시적 설정 설명이나 승인된 매뉴얼 정의를 확인해 사전을 교정한 뒤, 표본에서 그 적용이 맞는지 다시 검토한다. 반대 근거가 나오면 기존 claim을 참조해 수정·반박하며 과거 결과를 지우지 않는다. 정의 확인만으로 해당 값의 실제 제어 역할이나 인과관계까지 확정하지 않는다.

#### 4.8.2 다음 작업과 기존 승인 계약의 연결

| 필요한 작업 | 실행 경로와 경계 |
|---|---|
| Wiki 재생성·열람 | 같은 검증 map에서 새 외부 사본 생성. FTP/LLM 호출 없이 가능하며 지식 개선으로 세지 않음 |
| 기존 근거의 의미 재검토 | 사내 검토자가 허용된 사본과 근거를 검토하고 원장에 판정. 자동 재해석 runner는 아래 목표 계약 전환 후 사용 |
| 추가 inventory·표본 | 현행 pass의 적격 대상이면 같은 승인·누적 budget 안에서 처리. 기존 표본 상한, 미선정, 보호 상태는 질문으로 해제되지 않음 |
| 범위·사전·선정 정책 변경 | 현재 단계에서 허용한 `init`과 재승인만 사용. 결과 승인된 단계는 다시 열지 않으며 새 rollout 필요 |
| 미지원 extractor 개선 | 승인된 로컬 복사본의 workbench → 검토·시험 → 새 CLI 릴리스. 운영 중 즉석 코드 수정 금지 |

새 질문만으로 현행 LLM 캐시를 무효화하거나 4.4.1절의 pass 순서를 바꾸지 않는다. 질문 중심 자동 재해석은 목표 확장이며, 릴리스 전에 질문 ID/내용 hash·판정 기준·실제 근거·사전·모델/prompt 버전을 작업 키와 승인 입력에 결합하고 유한한 요청/시간 상한을 정의한다. 같은 작업의 완료 결과는 재사용하고, 재질문을 무제한 새 작업으로 발급하지 않는다. 그 전에는 현행 오프라인 도구가 요청을 기록하더라도 실제 해석 호출을 수행했다고 표시할 수 없다.

승인된 map은 불변이다. 새 결과는 별도 검토용 map projection과 iteration 사본으로 작성하며, 검토 사본 manifest는 운영 결과 승인 증명이 아니다. 정식 지도에 반영할 때는 해당 결과를 생산할 수 있는 승인된 CLI 실행과 결과 검토를 거친다. 현재 완료된 rollout의 `stage 3/4 next`를 반복 호출해 수정할 수 없다. collection scope에는 epoch이 들어가므로(5.1절) 사전만 바꾼 3단계 `init`이나 새 rollout도 inventory와 표본을 장비에서 다시 받는다. 그래서 평소 iteration은 `reviews/`의 검토 projection에서 돌리고, 정식 지도 반영은 재수집 비용과 장비 부하(원칙 6)를 치르는 드문 사건으로 계획한다. 같은 근거를 재사용하는 정식 재해석 경로는 이 문서에 없으며, 필요해지면 별도 계약으로 검토한다.

다른 scope로 넘어가면 과거 성공·표본·해석을 새 scope에 자동 채택하지 않는다. 질문의 의도와 이전 결과 참조만 엔지니어가 새 대상에 연결하고, 새 scope의 근거로 다시 검증한다. 사전의 일반화 가능한 정의도 적용 장비·버전·문맥 검토 없이 옮기지 않는다. 시간 변화 검증은 간격을 둔 승인 관측으로 수행하며 두 scope의 관측 비교를 scope 내부 캐시 재사용과 혼동하지 않는다.

#### 4.8.3 Markdown 산출물과 재개

목표 구조는 아래와 같다. `glossary.json`, `glossary.md`, iteration의 `REPORT.md`와 의미 검토 이벤트는 신규 목표이며 현재 오프라인 생성기가 이미 만드는 파일은 아니다.

```text
사내 사전 영역/
  glossary.json                    # 승인된 버전 원본, 이전 버전 보존
rollouts/<rollout-id>/
  data-map/                        # 현재 scope의 지도·근거·사전 사본
  REPORT.md                        # 기존 반출 가능 집계만
reviews/<review-id>/                # 승인 map 밖, 회사 내부 전용
  exploration.sqlite               # 질문·작업·의미 검토·회차 이력
  iteration-001/
    manifest.json                  # 원본 map·사전·원장 이벤트 경계와 출력 hash
    next-actions.json              # 미해결 질문과 후속 검토 항목
    REPORT.md                      # 목적·변경·근거·검증·한계: 반출 금지
    glossary.md                    # 해당 사전 버전의 읽기용 표현
    wiki/<장비 경로>/index.md       # 폴더별 읽기용 지도
  iteration-002/                   # 새 결과, 이전 회차 덮어쓰기 금지
```

각 폴더 페이지는 개요 → 직접 하위 폴더 설명/링크 → 실제 대표 파일별 관측 요약 → 파일군별 Observed/Fields/Inferred/Evidence/Relationships/Unresolved 순이다. 부모는 자식의 상세를 복제하지 않는다. Unresolved에는 조사 원장의 질문 ID, 미확인 이유와 다음에 필요한 근거를 연결한다. 모든 설명은 기존 map에서 코드로 조립하고 문서 작성용 LLM 호출을 추가하지 않는다.

iteration `REPORT.md`는 입력/이전 회차 manifest, 목적과 판정 기준, 이번 추가 관측·수정·반박, 검사한 표본 수와 결과, 미해결/보호/미탐색 범위, 비용과 종료 사유를 원장에서 생성한다. 중요한 질문이 무엇으로 해결됐는지 보여 주며 전체 transcript를 복제하지 않는다. 근거·경로가 들어가는 이 내부 보고서는 기존 rollout `REPORT.md`의 반출 가능 요약과 별개다.

회차 시작 전에 입력 map·사전 hash, 질문 집합, 판정 기준, budget과 입력 원장 이벤트 경계를 고정한다. 해당 작업의 처리·검토 결과는 같은 회차에 append하고, 발행 시 결과 map hash와 최종 이벤트 경계를 manifest에 고정한다. 재개는 고정 입력과 처리 상태를 확인하고 완료 작업을 반복하지 않는다. 새 질문·정책 변경은 다음 회차 입력으로 다루며 과거 manifest가 가리키는 원장 구간을 바꾸지 않는다. 생성한 문서를 고쳐 답을 바꾸지 않고 기준 map/검토 기록을 수정한 새 회차로 발행한다.

#### 4.8.4 반복 횟수와 종료 조건

기본 운영 예는 1차 구조·용어 후보 발견, 2차 중요한 미해결/충돌 검증, 3차 교정에 사용하지 않은 표본과 엔지니어 검토다. 3회는 정확도 보장이나 고정 의무가 아니다. 승인된 대표 표본 안에서 검증용 표본을 분리하고, 독립 표본이 없으면 그 한계를 명시한다. 추가 수집이 필요하면 기존 보호·표본·승인 계약을 따른다.

전체 검토 계획에는 최대 iteration 수, 누적 요청·시간·수집 한도, 우선 질문과 판정 기준을 실행 전에 정한다. pass·재개·질문 추가로 budget을 초기화하지 않는다. 새 rollout으로 전환해도 외부 검토 원장은 누적 사용량을 보존하며 상한 확대는 엔지니어의 새 결정으로 기록한다. 이 누적값은 검토용 기록이지 guard가 아니다. 실행을 멈추는 상한은 각 rollout의 `rollout.json` budget뿐이며, 엔지니어가 누적값을 보고 새 rollout의 budget을 정한다. 무인 반복은 아래 중 먼저 만난 조건에서 끝난다.

- **목적 충족:** 사전에 정한 중요한 질문이 검토 근거로 해결됐고, 별도 검증 표본의 결과와 남은 한계를 엔지니어가 확인함.
- **추가 가능한 작업 없음:** 새 관측·검증 가능한 질문이 없거나 보호·미지원·외부 확인이 필요함. 정확도 달성으로 표시하지 않음.
- **한도 도달:** iteration·요청·시간·수집 budget 도달. 남은 질문과 종료 사유를 보존함.
- **승인 대기 또는 오류:** 범위/사전/정책 변경, 연결·무결성 오류. 자동 재승인·우회·무한 재실행 없음.

품질은 발견/선정/표본/해석 coverage, 근거 연결 유효성, 검토한 의미의 맞음/틀림/미해결 수, 수정·반박 수, 미해결 중요 질문 수로 나눠 보고한다. 검토하지 않은 항목을 정답으로 세지 않고 표본 수·선정 방식·목적을 함께 남긴다. 알려지지 않은 장비 전체 정확도나 coverage 백분율은 만들지 않는다. 표본에서 오류가 발견되지 않은 사실도 장비 전체 정확도의 증명은 아니다.

## 5. 실행 방식

### 단일 CLI와 역할이 제한된 LLM

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

- 장비 식별자, 프로토콜, 접속 정보(host, port)
- 허용 루트, 실시간 데이터 후보 경로, 샘플 allow/deny 패턴
- 4.4절의 모든 budget과 LLM 요청 수 budget
- `max_passes`(4.4.1절)와 `prior_max_bytes`(4.6절, 2단계 `plan`부터 필수)
- 자격 증명 별칭, 장비 접근 허용 시간대(`always` 또는 UTC 구간)
- 장비 프로필 이름(`profile`)
- LLM endpoint URL, 키 별칭, 용어집 경로와 버전 및 4.6절의 모델·생성·timeout·재시도 설정(2단계 `plan`부터 필수)
- prompt/response 보존 위치 식별자(선택, `rollouts/` 밖의 접근 제어된 경로)
- 5단계에서 등록할 다음 프로필 이름(`next_profile`, 5단계 `plan`부터 필수)

`init`은 엔지니어의 결정이 필요한 키만 묻고, 나머지는 아래 기본값을 `rollout.json`에 직접 쓴다. 기본값도 파일에 있는 값이므로 계획 hash에 똑같이 결합되고, 엔지니어는 파일을 고쳐 바꿀 수 있다. 재설정 `init`은 기존 값을 기본값으로 보여 준다. 기본값이 있는 질문은 Enter로 받아들인다.

| 묻는 키 | 단계 | 보여 주는 기본값 |
|---|---|---|
| `equipment_id`, `host`, `allowed_roots` | 1·3 | 없음 |
| `protocol` | 1·3 | `ftp` |
| `port` | 1·3 | 21 |
| `next_profile` | 5 | 없음 |

이 다섯 개(5단계는 하나) 밖의 키로 `init`이 "missing required value"나 "missing budget"을 내면 그것은 `init`의 결함이다.

`llm` 블록은 묻지 않는다. endpoint, 모델, 키 별칭, 용어집 경로는 proxy 위치와 같은 기계의 배포 사실이므로 `.env`의 `LLM_ENDPOINT`, `LLM_MODEL`, `LLM_KEY_ALIAS`, `LLM_GLOSSARY_PATH`에서 읽어 rollout을 만드는 `init`이 그대로 `rollout.json`에 복사한다(실제 환경 변수 우선). 네 값이 그때 비어 있었으면 2단계 `plan`이 거부하며, 엔지니어가 `.env`를 채우고 같은 ID로 `init`을 다시 실행한다. 2단계 전용 `init`은 그 경우와 `llm` 값을 바꿀 때만 필요하다.

| 기본값을 쓰는 키 | 기본값 |
|---|---|
| `realtime_candidates`, `allow_patterns`, `deny_patterns` | `[]` (allow가 비면 허용 루트 전체, deny는 4.4절 공통 content-deny에 추가되는 것) |
| `profile` | `generic` (CLI가 동봉하는 `profiles/generic.json`) |
| `budgets.max_download_files` | 200 |
| `budgets.max_total_bytes` | 524288000 (500 MiB) |
| `budgets.max_elapsed_seconds` | 7200 |
| `budgets.max_file_bytes` | 10485760 |
| `budgets.max_connections` | 6 (허용 범위 1–8, `ftp_handler`의 `max_concurrency`로 전달) |
| `budgets.requests_per_second` | 8 (연결 전체 합산) |
| `budgets.max_entries` | 100000 |
| `budgets.max_depth` | 8 |
| `budgets.llm_max_requests` | 2000 |
| `max_passes` | 1 |
| `credential_alias` | `equipment_id`와 같은 값 |
| `access_window` | `always` |
| `llm.endpoint`, `llm.model`, `llm.key_alias`, `llm.glossary_path` | `.env`의 값 |
| `llm.glossary_version` | 용어집 파일 내용 SHA-256의 앞 12자리 |
| `llm.temperature` | 0 |
| `llm.max_tokens` | 512 |
| `llm.connect_timeout_seconds`, `llm.request_timeout_seconds` | 10, 120 |
| `llm.max_elapsed_seconds` | 3600 |
| `llm.transport_max_attempts`, `llm.retry_backoff_seconds` | 3, 2 |
| `llm.prior_max_bytes` | 8192 |
| `llm.retention_location` | 없음 |

`plan`은 이 파일만 입력으로 사용하며 모델이 장비 경로와 budget을 command flag로 만들 수 없게 한다. 각 단계의 `plan`은 그 단계에 필요한 필드가 없으면 거부한다.

하나의 rollout ID는 1단계부터 5단계까지 유지한다. 단계 경계에서 설정을 바꿔야 하면(1단계 가짜 트리에서 3단계 실장비로 전환, LLM endpoint 추가, 5단계 프로필 등록) 엔지니어가 같은 ID로 `init`을 다시 실행한다. 재설정은 `.lock`이 없을 때만 허용되며 이전·새 `rollout.json`의 hash를 `init` 감사 기록에 남긴다.

새 rollout은 1·2단계를 **기준 rollout**에서 채택할 수 있다. 두 단계는 장비가 아니라 이 PC에 설치된 CLI 코드, 전송 경로와 LLM 설정을 가짜 트리로 검증하므로, 그것들이 그대로면 장비마다 반복하지 않는다. 엔지니어가 새 ID의 첫 `init`에서 기준 rollout ID를 입력하면 CLI는 다음을 모두 만족할 때만 채택한다.

- 기준 rollout이 1·2단계 결과 승인을 직접 가진다. 채택으로 얻은 단계는 기준이 되지 않는다.
- 두 결과 승인이 이 호스트에서 기록되었다.
- 두 승인이 가리키는 완료 `next-stop` 기록의 `code_hash`가 현재 CLI의 `code_hash`와 같다. `code_hash`는 설치된 `equipment_map` 패키지의 모든 `.py` 파일에 대한 정렬된 상대 경로와 바이트 hash의 canonical hash이며 모든 `next-stop` 기록에 남는다.

채택하면 기준 rollout의 2단계 승인 계획에서 `llm` 블록을 복사하고, 기준 ID와 두 결과 승인 기록의 hash, `code_hash`를 담은 `adopt` 감사 기록을 남긴 뒤 3단계 키를 묻는다. 현재 단계는 3단계이고, `status`와 `REPORT.md`는 1·2단계를 기준 ID와 함께 `adopted`로 표시한다. 3단계 계획은 `adopt` 기록을 입력으로 결합하므로 계획 승인이 채택도 확인한다. 조건이 하나라도 어긋나면 `init`은 어긋난 조건을 출력하고 아무것도 쓰지 않은 채 exit 20으로 끝나며, 엔지니어는 기준 없이 1단계부터 시작한다. 첫 rollout과 CLI 코드가 바뀐 뒤의 첫 rollout은 이렇게 1·2단계를 수행해 다음 rollout의 기준이 된다.

`init`이 바꿀 수 있는 키는 현재 단계가 정한다. `init`은 그 키만 묻고 나머지 값은 그대로 둔다. `plan`은 바꿀 수 없는 키가 기준 계획과 다르면 exit 20으로 거부하며, 손으로 고친 `rollout.json`도 같은 검사를 받는다. 2·4·5단계의 기준 계획은 직전 단계의 마지막 계획 승인 기록이고, 3단계 장비 정체성의 기준은 3단계 첫 `next-start`가 실행한 계획이다.

| 현재 단계 | `init`이 바꿀 수 있는 키 | 그 밖의 변경 |
|---|---|---|
| 1 | `next_profile`을 뺀 모든 키 | 검사 없음. 새 epoch이 새 collection scope를 연다 |
| 2 | `llm`, `budgets.llm_max_requests` | 2단계 `plan` exit 20 |
| 3 | `next_profile`을 뺀 모든 키. 장비 정체성(`equipment_id`, `protocol`, `host`, `port`)은 3단계 첫 `next-start` 전까지만 | 그 뒤 정체성 변경은 3단계 `plan` exit 20, 새 rollout 필요 |
| 4 | 없음 | `init` exit 20 |
| 5 | `next_profile` | 5단계 `plan` exit 20 |

현재 단계는 결과 승인되거나 채택된 가장 높은 단계의 다음 단계다. 각 `init` 기록은 현재 단계의 새 **epoch**을 연다. `status`는 현재 단계의 `plan`, `approve-plan`, `next-*` 기록 중 최신 `init`보다 앞선 것을 stale로 보고 무시하므로, 재설정 뒤에는 그 단계의 `plan`, 계획 승인, `next`를 다시 거친다. 결과 승인된 단계는 어떤 `init`으로도 무효가 되지 않는다. 승인된 범위를 넓히려면 새 rollout을 시작한다.

실행 전 계획 승인과 실행 후 결과 승인은 엔지니어가 직접 수행한다. 승인·결과 승인·stale lock 해제 명령은 어떤 `SKILL.md`에도 넣지 않고 CLI의 다음 명령으로도 출력하지 않는다. 비대화형 stdin에서는 거부하며 OS 사용자, 호스트, UTC 시각, 계획 hash 또는 결과 manifest hash를 감사 기록에 남긴다. 이는 전자서명이 아니라 운영자 자기확인임을 명시한다.

엔지니어 전용 명령은 `equipment-map operator approve-plan`, `equipment-map operator approve-result`, `equipment-map operator unlock`과 4.5절의 `equipment-map workbench`다. 이 명령은 LLM에 대한 보안 경계가 아니라 사람의 운영 절차다. 스킬이 대신 호출하면 시나리오 검증 실패로 처리한다.

`next`는 현재 rollout 단계가 완료되거나 budget·오류·승인 대기 조건으로 중단될 때까지 실행한다. 4.4.1절의 pass 반복은 이 한 호출 안에서 끝나며 pass마다 호출을 끊는 별도 프로토콜은 없다. 완료된 단계에서 다시 호출하면 작업 없이 성공하고 현재 결과 승인 상태만 출력한다. 다음 rollout 단계의 `plan`은 이전 단계 결과 승인이 없으면 거부한다. 1·2단계의 결과 승인은 채택으로 대신할 수 있다.

CLI 종료 코드와 마지막 출력 행은 고정한다.

```text
0   완료 또는 안전한 no-op       NEXT: <허용된 다음 CLI 명령>
10  운영자 승인 대기             NEXT: WAIT-APPROVAL
20  실행 중단                    NEXT: STOP
30  설치·계약 preflight 실패     NEXT: INSTALL-OR-UPGRADE
```

stdout에는 rollout ID, 단계, 집계 건수, hash, 상태와 로컬 결과 경로만 출력한다. `status`는 `REPORT.md`의 존재 여부와 SHA-256도 한 줄로 출력한다. 샘플 내용, 장비 경로, 파일명, 자격 증명, LLM 입력·출력은 파일에만 기록하며 출력하지 않는다. 대화 세션이나 특정 LLM이 이전 상태를 기억한다고 가정하지 않는다. `preflight`는 CLI가 없거나 스킬이 요구한 계약 버전을 지원하지 않으면 실행을 거부하고 설치 또는 갱신 안내만 출력한다. `preflight`는 이 기계가 사용할 전송 방식도 함께 확인한다. 선택된 방식과 그 근거(platform 추정 또는 `FTP_TRANSPORT`)를 출력하고, proxy면 health endpoint를 호출한 뒤 목록 route에도 빈 대상으로 요청한다. health endpoint는 도달 여부만 증명하기 때문이다. token이 비어 있으면 인증 없는 요청이 200이어야 한다. token이 설정되어 있으면 인증 없는 요청이 401인지 확인한 다음, 설정한 token으로 요청해 200인지 확인한다. 이때 인증 없는 요청의 401은 기대 결과이고 token을 보낸 요청의 401은 실패다. token을 설정했는데 인증 없는 요청이 성공하면 설정과 배포가 어긋난 것이므로 exit 30으로 멈추며, 도달하지 못해도 exit 30으로 멈춘다. 설정된 사내 `http://` URL을 먼저 확인하고 redirect를 거부한다. 운영 proxy와 loopback fixture 모두 HTTP를 사용하며 HTTPS/TLS를 요구하지 않는다. 빈 대상이므로 장비에는 접속하지 않는다. 이 확인은 장비에 접속하지 않으므로 계획 승인을 필요로 하지 않으며, 장비 접속을 대신 증명하지도 않는다. stdout에는 전송 방식 이름과 도달 여부만 출력하고 proxy URL, host와 token은 출력하지 않는다.

초기 검증은 한 엔지니어의 PC와 로컬 rollout 디렉터리에서 수행한다. Skill Market 배포 후에도 rollout 하나는 한 엔지니어가 자기 PC에서 1~5단계를 끝까지 수행한다. 다른 엔지니어는 자기 장비와 별도 rollout ID로 독립 실행한다.

회사망 밖으로 전달할 수 있는 상태 요약은 rollout ID, 단계 번호, 성공·생략·실패 건수와 CLI·계약 버전으로 제한한다. 장비 식별자, 경로, 파일명, 파일군명, 오류 원문, 분석 내용, 모델 ID와 serving 설정은 포함하지 않는다. 이 요약은 4단계 `next`가 `rollouts/<rollout-id>/REPORT.md`로 생성하며 사람이나 스킬이 직접 쓰지 않는다. 모델 ID와 설정은 `data-map/`의 LLM 유래 필드에만 남는다.

### 5.1 Rollout 상태

상태의 기준은 채팅 기록이 아니라 rollout 작업 디렉터리다.

한 rollout ID는 정확히 장비 하나를 다룬다. `init` 재실행은 같은 장비의 단계 경계 설정 변경에만 쓰며, 다른 장비는 승인 계보를 섞지 않기 위해 새 rollout ID로 시작한다. 5장의 기준 rollout 채택은 장비가 아니라 설치된 CLI와 LLM 설정에 대한 가짜 트리 검증만 가져오므로 장비 승인 계보를 섞지 않는다.

rollout ID는 장비 이름, host와 IP를 포함하지 않는 불투명한 식별자이며 `[a-z0-9][a-z0-9-]{0,31}`에 맞아야 한다. stdout이 rollout 디렉터리 경로를 출력하므로 ID에 장비 식별자를 넣으면 반출 금지 항목이 경로로 노출된다.

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

collection scope는 수집 단계(1 또는 3), 그 단계가 현재 단계일 때 기록된 최신 `init`의 epoch(rollout을 만든 `init`은 1단계 것, 채택한 rollout에서는 3단계 것), 정규화된 source 설정 hash로 식별하며 scope ID는 이 세 값 배열의 canonical hash다. source 설정 hash는 `equipment_id`·`protocol`·`host`·`port`·`allowed_roots`·`realtime_candidates`·`allow_patterns`·`deny_patterns`·`profile` 이름과 profile 파일 내용 hash로 만든다. 따라서 2·4·5단계의 `init`은 수집 scope를 바꾸지 않는다. inventory의 디렉터리 및 pass, grouping, sampling, extraction 체크포인트와 4.4.1절의 pass 선택 목록·prior snapshot은 모두 이 scope에 속한다. 1·3단계의 새 수집이나 재설정은 새 scope를 사용하며 이전 가짜 장비나 이전 scope의 완료 표시·샘플·해석을 재사용하지 않는다. 2·4·5단계는 수집하지 않고 직전 단계의 결과 승인 기록이 가리키는 scope와 manifest hash를 계획에 입력으로 결합한다(2단계는 1단계, 4단계는 3단계, 5단계는 4단계의 결과 승인). 새 scope의 첫 `next`는 이전 scope의 `data-map/`을 `work/history/<scope 앞 12자>/`로 옮긴 뒤 새 지도를 시작하고, 새 지도에는 현재 scope 자료만 포함한다. 이 전환은 중단 후에도 재개 가능해야 한다. 이전 감사·승인 기록은 보존한다. 단순 프로세스 재시작은 scope나 budget을 새로 만들지 않는다.

### 5.2 상태 전이와 결과 무결성

`plan`과 `next`는 현재 단계 및 최신 epoch의 일치 여부를 검사한다. 승인된
과거 단계의 `next`는 쓰기 없는 no-op만 허용하고 미래 단계 실행은 거부한다.
완료된 단계의 결과 승인 대기는 `status`로 확인하며 `next`를 반복 호출하지 않는다.
5단계 결과 승인 뒤에는 terminal complete이고 `init` 재설정도 거부한다.
1·2단계의 가짜 source에서 3단계의 장비 하나로 바꾸는 것은 허용하되,
3단계 첫 `next-start` 뒤 장비 정체성을 바꾸는 재설정은 새 rollout을 요구한다(5장의 단계별 `init` 표).

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

목록·표본 budget 소진과 4.4.1절의 `max-passes`·`no-eligible-work` 종료는 부분 coverage와 생략 사유를 파일에 확정한 뒤
`completed: true`, exit 0으로 끝낼 수 있다. 연결·무결성·잠금·시간대 오류는
`completed: false`, exit 20이며 결과 승인을 허용하지 않는다. LLM의 유한 실패는
4.6절의 unresolved 기록으로 확정한다. 시간 상한 도달 뒤 장비/API 요청은
없으며 이미 관측한 로컬 상태를 안전하게 저장하는 마무리만 수행한다.

## 6. 안전장치

- 장비와 허용 루트 경로를 allowlist로 제한
- 읽기 전용 계정 사용
- 기본 동시 연결 수 6, 최대 8 (`budgets.max_connections`)
- 명시적인 다운로드/시간 budget 없이는 실행 거부
- 정규화된 실행 계획의 hash에 승인을 결합하고 실행 직전에 다시 대조
- 승인 후 계획, 대상, 경로 또는 budget이 바뀌면 재승인 요구
- 승인된 선택 규칙이 같은 collection scope 안에서 고른 pass 대상은 계획의 파생 결과이며 재승인 대상이 아님; 허용 루트, `max_passes`, `prior_max_bytes`, 선택 규칙 버전 변경은 재승인 요구
- rollout별 lock에 호스트, PID와 시각을 기록해 동시 실행 차단
- stale lock은 자동 삭제하지 않고 상태를 보여준 뒤 엔지니어의 대화형 해제 요구
- 경로 이탈 방지
- 자격 증명은 OS의 승인된 비밀 저장소에서 별칭으로 조회
- 샘플과 LLM prompt/response 접근 권한 및 보존 기간 설정
- 파일별 성공, 생략, 실패 사유를 audit log에 기록
- 장비 연결 실패 시 자동 재시도 폭주 없이 중단
- 승인 기록에 OS 사용자, 호스트, UTC 시각과 계획·결과 hash를 남기고 전자서명이 아닌 운영자 자기확인임을 표시

## 7. 검증 전략

실장비 연결 전에 회사 PC에서 작은 가짜 FTP 트리를 사용해 다음을 검증한다.

- 쓰기 동작이 존재하지 않는지
- 이름이 반복되는 파일이 같은 패턴 파일군으로 묶이고, 이름 규칙을 공유하지 않는 파일은 디렉터리·확장자별 느슨한 묶음이 되며, 묶는 동안 내용 요청이 0건인지
- 패턴 파일군은 최신 적격 3개와 결정론적 무작위 2개, 느슨한 묶음은 무작위 최대 3개를 고르고 재실행해도 같은 파일을 고르는지
- 패턴 파일군에서 추출 형식이 다른 표본이 예외로 기록되는지
- 전체 목표 바이트에 도달한 다운로드 완료 후 다음 전송을 시작하지 않는지
- 참고 크기 초과·크기 미상 파일도 다운로드를 시도하고 성공한 전체 파일과 실제 사용량을 보존하는지
- FTP 전송 방식이 기계에 따라 선택되는지 (Windows → proxy, 그 외 → direct)
- 잘못된 `FTP_PROXY_URL`이나 proxy 배포와 맞지 않는 token 설정으로 `preflight`가 exit 30으로 멈추고 장비 접속을 시도하지 않는지
- 중단 후 체크포인트부터 재개되는지
- 암호화·손상 파일이 누락되지 않고 `unreadable`로 남는지
- 고정된 시각과 같은 가짜 입력의 LLM 미사용 경로에서 `data-map/`의 구조화 파일이 바이트 단위로 동일한지
- 반복 inventory의 observation ID와 new/changed/unchanged/missing 상태가 결정론적이며 unchanged를 static으로 승격하지 않는지
- 로그·alarm·FDC·측정·설정·recipe·software/firmware·유지보수/교정·reference fixture에서 제한된 observed descriptor만 만들고 전체 event/row나 의미를 복제하지 않는지
- CP949 텍스트, 섹션 없는 `key = value` 파일, 로그 줄 안의 `name=value`, 입력 상한을 넘는 CSV, 128열을 넘는 표에서 필드 이름을 잃지 않고, 숫자 필드의 자료형·min/max·null/invalid 수를 미리보기 행이 아니라 파싱한 모든 값에서 계산하는지
- 승인된 계획 hash와 실행 직전 계획 hash가 다르면 중단하는지
- 같은 rollout의 동시 실행과 무단 stale lock 해제가 차단되는지
- 이전 단계를 승인하지 않고 다음 rollout 단계에 진입할 수 없는지
- 실행 결과 승인 없이 다음 rollout 단계에 진입할 수 없는지
- CLI가 없거나 계약 버전이 맞지 않을 때 스킬이 실행을 계속하지 않는지

추가 필수 시나리오: sample 경로에서 보호 파일 내용 요청 0건, 단계별 `init` 표 밖의 키 변경과 3단계 실행 뒤 장비 정체성 변경의 거부, 원격 이름의 금지 문자·`%`·예약 이름·장치 이름 변환, 대소문자 충돌과 120자 경로 상한에 걸린 항목의 로컬 조회·다운로드 전 제외, 기록과 맞지 않는 evidence 파일을 덮어쓰지 않는 중단, 같은 scope 재개에서 이미 받은 표본의 재전송 없음, 전송 중 성장 파일의 전체 다운로드와 실제 초과량 기록, 동일 rollout의 fake→real 전환과 재설정 후 stale 자료 배제, metadata-only 지도 발행, 요청 예약·응답 수신·결과 커밋 경계에서 종료 후 재개, 429/503/timeout 뒤 회복과 영구 장애의 유한 종료, 요청·시간 budget의 재개 보존, 불완전 inventory와 의미 해석 coverage의 구분, 기준 rollout 채택이 다른 호스트·다른 `code_hash`·채택으로 얻은 단계·2단계 결과 승인이 없는 기준을 거부하고 채택한 rollout이 3단계에서 시작하며 `status`와 `REPORT.md`에 기준 ID를 드러내는지를 검증한다.

pass 반복은 다음을 검증한다. pass 경계에서 강제 종료한 뒤 재개해도 중복 전송·중복 LLM 요청이 없고 pass 번호와 budget이 초기화되지 않는지, 적격 대상 소진이 `no-eligible-work`로 끝나고 `max_passes`·budget 도달이 각각의 사유로 끝나는지, 세 종료 모두 `completed: true`·exit 0이고 `NEXT: STOP`이 아닌지, `confidence` 값을 바꿔도 선택 순서가 변하지 않는지, 연결 파일군의 Observed가 바뀌면 재호출하고 prior만 바뀌면 재호출하지 않는지, `prior_inferred` 항목을 evidence로 인용한 응답이 거부되는지, 그리고 의도적으로 틀린 prior와 반대되는 Observed를 넣었을 때 결과가 `inferred`로 남고 관측 fact가 바뀌지 않는지다. 라벨이 pass 사이에 안정됐다는 사실을 정확도 증명으로 보고하지 않는다.

추가로 결과 파일 추가·삭제·변조, 완료 전 결과 승인, 과거·미래 단계 호출,
남의 lock 해제 방지, 실행 중 시간대 종료, parser/압축 해제 상한, 파일 속 지시문,
높은 confidence의 추론이 Wiki의 Observed로 승격되지 않는 경우도 검증한다.

Wiki와 Graph 발행은 고정 입력에서 `wiki/`, `nodes.jsonl`, `edges.jsonl`이 바이트 단위로 동일한지, 모든 링크·endpoint와 typed citation이 현재 scope의 근거로 해석되는지, raw log/FDC/측정 row와 근거 없는 인과관계가 없는지, LLM 유래 값이 Observed나 observed graph field로 들어가지 않는지 검증한다. `[[`, `#`, `%%`, `$`, `|`, backtick이 든 경로·필드 이름·값이 글자 그대로 표시되는지, 이름에 비밀정보를 나타내는 문자열이 든 필드의 예시 값과 범위가 가려지는지, `wiki/`의 폴더 구조가 로컬 이름 규칙을 적용한 장비 폴더 구조와 같고 각 `index.md`가 직접 하위 항목만 설명하는지도 확인한다.

LLM 설명의 정확성은 사람이 대표 파일과 근거를 함께 검토한다. 근거 없는 추론은 Wiki의 Observed로 등록하지 않는다.

파일군 관계는 합성 설정·로그·측정 파일로 검증한다. 다른 폴더의 동일 recipe ID 연결, 같은 폴더지만 다른 포맷인 파일군 유지, 일반 키워드와 필드가 다른 동일 숫자의 오연결 방지, 반복 사용된 run ID를 실제 동일 run으로 단정하지 않음, 범위 밖·다중 후보 참조의 unresolved 유지, metadata-only 파일군의 미관측 내용 매칭 금지와 명시적 참조 도착점 허용, 잘못된 근거 hash·위치 거부를 포함한다. 관계·feature·근거 상한과 deadline, 재개 후 중복 없음, 고정 입력의 결정론적 출력, 샘플 관계의 전체 파일군 확대 금지, 관계 생성 중 추가 source 요청 0건도 확인한다.

스킬은 먼저 pi에서 같은 시나리오로 검증한다. Codex, Claude Code, OpenCode는 아직 범위 밖이고, 같은 시나리오와 같은 결과 시트로 뒤에 확장한다. 그 전에는 지원 도구로 표기하지 않는다. 초기 최소 모델 검증 프로필은 엔지니어의 전용 Qwen3.8-27B 배포로 삼고 정확한 served model ID와 설정을 기록한다. 크기 표기는 검증된 모델 식별자나 정확도 증명이 아니다. 문구 일치가 아니라 다음 관찰 가능한 결과를 확인한다.

- 올바른 CLI subcommand를 선택하는가?
- `plan` 이후 운영자 승인 없이 `next`가 성공하지 않는가?
- 실패 시 임의 우회 명령을 만들지 않고 CLI의 중단 이유를 전달하는가?
- LLM 의미 응답이 두 슬롯 모두 유효하지 않으면 `unresolved`로 남기며, 별도 전송 재시도와 전체 요청·시간 상한도 지키는가?
- audit의 CLI 호출 기록과 시나리오의 shell command 목록에 허용되지 않은 명령이 없는가?

### 7.1 통합 목표 계약의 추가 검증

11장의 확장을 배포할 때는 기존 시나리오에 다음을 더한다. 문서 검토와 오프라인 합성 시험 통과를 Windows/proxy·pi·사내 LLM·실장비 검증으로 대신하지 않는다.

- **선정:** heavy의 적격 파일군 coverage, medium 확정 전 내용 요청 0건, light의 검증된 후보만 처리, invalid 응답의 보류, 필터 오탐 예외가 명시적 deny를 해제하지 않음, 재개/추가 pass에서 미선정 항목을 몰래 포함하지 않음.
- **사전:** 같은 약어의 서로 다른 문맥을 분리, 틀린 정의와 반대 관측 시 unknown/충돌 유지, LLM 후보의 자동 확정 거부, 실행 중 사전 hash 변경 거부, 새 사전 버전의 기존 캐시 오사용 방지, 이전 사전 사본으로 결과 추적 가능.
- **iteration:** 처리 성공과 의미 검토를 분리, 질문 전에 제출한 작업을 새 질문 완료로 인정하지 않음, 새 근거로 claim 수정/반박 시 이전 참조 보존, 다른 scope의 성공을 이관하지 않음, 승인된 map·이전 Wiki 불변, 입력 고정과 중단 후 재개, 회차/누적 budget 종료.
- **정확도:** 교정에 쓰지 않은 표본의 판정과 분모 기록, 미해결·오류 표본 누락 금지, confidence·반복 답변·addressed 상태를 정확도 통과로 간주하지 않음.
- **병렬/성능:** in-flight 상한, 예약의 원자성, crash 시 겹친 시간 단일 차감, 재시도·인증 실패·deadline의 새 요청 중단, 완료 결과 재호출 0건, 같은 입력/coverage/품질에서의 비용 비교.
- **발행:** 원장 이벤트 경계·map/사전 hash가 고정된 입력의 결정론적 생성, glossary/질문 링크와 근거 검증, 내부 iteration 보고서와 반출 요약 분리, 생성 중 FTP·LLM 호출 0건.

## 8. Rollout 단계별 운영

다음 5단계는 3장의 런타임 파이프라인과 별개다. 3~5단계는 장비마다 새 rollout에서 반복한다. 1·2단계는 PC, CLI 코드 또는 LLM 설정이 바뀔 때 반복하고, 그대로면 5장의 기준 rollout 채택으로 대신한다. 한 엔지니어가 자기 PC에서 모든 단계를 수행한다. 각 단계에서 실행 전 계획과 실행 후 결과를 확인해야 다음 단계로 넘어간다. 승인 기록은 해당 단계의 정규화된 계획 hash 또는 결과 manifest hash를 포함한다.

### 1단계: 로컬 가짜 장비로 수집기 검증

설치된 CLI로 가짜 FTP의 목록 수집, 파일군 분류, 제한 샘플링과 `data-map/` 생성을 실행·검증한다. LLM 없이도 전체 흐름이 동작해야 한다.

실장비 주소와 자격 증명을 사용하지 않은 가짜 트리 결과만 승인 대상으로 삼는다.
Windows의 가짜 FTP 검증은 같은 PC의 가짜 proxy와 가짜 FTP를 함께 사용한다.
회사 운영 proxy에 `localhost`를 보내면 엔지니어 PC가 아니라 proxy 서버를
가리키므로 허용하지 않는다. 시험용 설정은 별도 프로세스 환경에만 적용한다.
FTP adapter를 direct·proxy 두 전송 방식 모두 build 시나리오로 검증하고 rollout 하나의 1단계는
선택한 protocol 하나만 사용한다.

### 2단계: 회사 로컬 LLM 연결

대표 샘플 분석 결과를 필드별로 받아 CLI가 구조화된 JSON으로 조립하고 검증한다. 한 종류의 측정 데이터와 한 종류의 로그 파일로 정확도를 확인한다.

### 3단계: 승인된 장비 1대에서 읽기 전용 시범 운영

엔지니어가 같은 rollout ID로 `init`을 다시 실행해 실장비 접속 정보, 좁은 허용 루트와 작은 budget을 입력한다. 실시간 데이터 후보 경로가 있으면 함께 입력한다. 장비 부하, 파일군 정확도, 샘플 대표성과 운영자 검토 결과를 기록한다. 접근 허용 시간대가 없으면 계획에 `always`를 명시해 승인 hash에 포함한다.

3단계 `next`는 1단계와 같은 파이프라인을 실장비에 실행한 뒤, 2단계와 같은 필드별 LLM 해석을 아직 해석이 없는 파일군에만 수행한다. LLM 호출은 `rollout.json`의 LLM 요청 수 budget으로 제한하며, budget에 걸려 해석하지 못한 파일군은 `unresolved: budget`으로 남긴다. `max_passes`가 1보다 크면 4.4.1절의 pass 반복이 같은 `next` 안에서 이어진다. 4단계는 모든 파일군에 해석 또는 `unresolved` 기록이 있어야 진행한다.

방화벽과 접속 승인은 스킬 외부의 선행조건이다. 스킬은 방화벽 변경이나 승인 시스템 조회를 시도하지 않는다. 연결되지 않으면 원인을 단정하거나 우회하지 않고 진단 결과를 남긴 후 중단한다.

### 4단계: Wiki와 Graph 생성

검토가 끝난 `data-map/`만 사용해 Wiki와 graph JSONL을 만든다. Wiki 항목에는 항상 장비 경로와 근거 종류·hash를 표시한다. 샘플이 없으면 4.7절의 metadata evidence만 인용하고 내부 내용은 미확인으로 남긴다. 4단계 `next`는 `wiki/`, `graph/`와 함께 `rollouts/<rollout-id>/REPORT.md`를 생성한다. 5단계 `next`는 5단계 건수를 포함한 `REPORT.md`를 임시 파일에 쓰고 원자적으로 교체한 뒤에 `next-stop`을 기록한다. 완료 기록과 오래된 보고서가 공존하지 않는다.

### 5단계: 장비 종류 확장

엔지니어가 새 장비 프로필 파일에 허용 경로, 파일명 규칙과 기존 extractor 매핑을 작성하고, 같은 rollout ID로 `init`을 다시 실행해 `next_profile`로 등록한다. 5단계 `plan`은 `next_profile`이 등록된 프로필 파일을 가리키고 현재 `profile`과 다를 때만 허용한다. 5단계 `next`는 그 프로필의 스키마와 extractor 매핑(기존 extractor 이름만 허용)을 검증하고, 현재 지도에서 `unsupported-format`으로 남은 파일군을 `data-map/extractor-requests.json`에 정리한 뒤 manifest를 다시 생성한다. 결과 승인으로 rollout이 끝나며, 새 장비는 이 프로필로 새 rollout을 시작한다. 5장의 채택 조건을 만족하면 1·2단계를 채택하고 3단계부터 수행한다. 새 extractor 코드가 필요하면 이 단계에서 즉석 생성하지 않고 4.5절의 별도 CLI 릴리스 절차로 넘긴다. 릴리스는 CLI 코드를 바꾸므로 그 뒤 첫 rollout은 1·2단계를 다시 수행한다. 한 장비의 예외를 공통 로직에 억지로 넣지 않는다.

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

- 가짜 FTP에서 direct·proxy 두 전송 방식이 동일한 형식의 inventory를 생성한다.
- 반복 파일 100개를 전체 복제하지 않고 대표 샘플 최대 5개(최신 적격 3개와 무작위 2개)로 요약한다.
- 텍스트, CSV, JSON, 알 수 없는 바이너리, 암호화 파일을 구분한다.
- 파일군마다 규칙, 통계, 설명, 신뢰도와 근거 경로가 기록된다.
- 파일군마다 category, schema descriptor와 시간 profile이 있고 반복 관측과 영구적인 static 판정을 혼동하지 않는다.
- 파일군 사이의 구조·내용 관계에 유형, 관측 범위와 검증 가능한 근거가 있으며 잘림·미해결 참조가 드러난다.
- 실행 budget과 읽기 전용 제약을 자동 검사한다.
- 검토된 지도에서 장비 폴더 구조를 따르고 Obsidian에서 읽히며 항목마다 근거를 추적할 수 있는 Markdown Wiki와 vendor-neutral graph JSONL을 생성한다.
- 필드마다 이름, 관측 자료형, 숫자 범위와 예시 값이 Wiki에 드러나고, 이름에 비밀정보를 나타내는 문자열이 든 필드의 값은 가려진다.
- 6개 스킬이 pi에서 같은 CLI 계약으로 동작한다. 나머지 세 도구는 같은 기준을 통과한 뒤에 지원 목록에 들어간다.
- 전용 Qwen3.8-27B 배포의 정확한 모델·serving 설정으로 실행한 기준 시나리오에서 승인 우회, 자유형 JSON 작성과 대화 상태 의존 없이 rollout을 재개한다.
- 한 엔지니어가 로컬 rollout 상태만으로 중단 후 1~5단계를 재개한다.

## 11. 구현 상태와 계약 전환

### 11.1 현재 확인한 범위

| 구성 | 이 checkout에서의 상태 | 의미 |
|---|---|---|
| 전체 rollout CLI·6개 배포 스킬 | 현행 letter가 구축·검증하도록 정의한 계약 | 설치된 완성 운영 제품으로 간주하지 않음. 회사 복사본의 구현 여부는 별도 확인 |
| `ftp_handler/` | 기존 코드 | 정식 rollout CLI나 재개 가능한 개선 루프의 완료 증거가 아님 |
| `wiki_review.publish`, `wiki_review.exploration` | 오프라인 Wiki 생성·SQLite 조사 원장 구현 | `wiki-map-v1` projection 입력, 새 폴더 발행, `approval_verified: false`; FTP·LLM·graph·운영 승인 전이 없음 |
| 파일 선정 모드·사전 생애주기·의미 검토 iteration | 이 문서의 목표 계약 | schema·validator·원장·실행기·지침 전환 필요 |
| 사전 제작 배포·최대 8개 HTTP 병렬·claim 응답 통합 | 목표 배포 구조와 검증할 최적화 | 실제 사내 지연/처리량 미측정; 응답 통합은 비교 검증 뒤 채택 |

현재 오프라인 projection은 field locator와 빈 관계 배열 등 제한된 입력만 지원한다. 운영 map의 모든 관계·locator·사전 확장을 이미 처리한다고 가정하지 않는다. 기존 명령·입력 상세는 `docs/architecture/wiki-generator.md`를 따른다. 목표 구조의 새 파일을 기존 `wiki-map-v1`에 임의로 추가해 호환된다고 표시하지 않는다.

### 11.2 적용 순서와 릴리스 게이트

1. **검증된 CLI를 고정 배포한다.** 이미 동작하는 사내 구현이 있으면 그 환경에서 재사용·패키징한다. 외부 유지관리 환경에서는 합성 fixture로 작성·시험한 코드만 반입한다. 정상 운영이 매번 편지 01–15의 코딩을 요구하지 않도록 설치 경로를 마련한다. 그 전까지 `index.md`의 현행 빌드 순서를 건너뛰거나 done 원장을 조작하지 않는다.
2. **지도·사전·질문 계약을 함께 구현한다.** 사전 snapshot/검토 이력, 질문과 의미 판정, 회차 입력/manifest·내부 보고서를 버전된 schema로 추가한다. 오프라인 원장을 재사용하고 승인된 map과 분리한다. 기존 지도·projection에는 명시적인 adapter/버전 검사를 적용한다.
3. **선정과 자동 재해석을 연결한다.** medium의 내용 수집 전 확인, light의 범위 제한, 질문별 작업 키·누적 budget·재개를 검증한다. 엔지니어 승인 경계를 지키며 새로운 모델 판단이 download guard를 우회하지 않게 한다.
4. **측정 뒤 병렬·호출 축소를 적용한다.** 동일한 로컬 패킷으로 기준선을 만들고 동시성을 비교한다. claim 응답 통합은 별도 품질 시험 뒤 채택한다. 실제 장비를 반복 수집해 성능 비교용 입력을 만들지 않는다.
5. **최소 모델·운영 환경에서 검증한다.** pi와 지정 Qwen 프로필, Windows/proxy, 승인된 좁은 장비 범위를 순서대로 검증한다. scope·코드·모델 변경 시 5장의 기준 rollout 채택 조건을 다시 검사한다.

각 릴리스는 이 문서와 `spec.md`뿐 아니라 `index.md`, implementation-reference, 해당 letter, schema/validator, 고정 CLI 명령, 시험을 함께 갱신한다. 선정은 Letters 06–07, LLM/사전/재개는 11, 발행은 12, 패키지/스킬/검증은 02·14–15와 운영 16–20을 대조한다. 새 스킬 명령·medium 확인 전이·자동 재해석 명령은 구현 계약 검토 전에 존재하는 명령처럼 문서에 넣지 않는다. 배포 역할을 바꿀 때 maintainer의 파일 소유권 규칙도 명시적으로 정비한다. 이 문서 통합만으로 현재 AGENTS의 쓰기 권한을 확대하지 않는다.

기존 실행에는 새 동시성·시간 차감·선정·사전 schema를 소급 적용하지 않는다. 현재 승인된 버전으로 마치거나 정식 중단하고, 새 계약 버전의 preflight·가짜 시험·계획 승인 뒤 시작한다. 10장의 현행 완료 기준에 더해, 목표 계약을 지원한다고 선언하려면 7.1절의 관련 시나리오도 통과해야 한다.

### 11.3 보조 문서의 위치

아키텍처의 원본은 이 문서 하나다. 아래 자료는 설명·운영 예시·진단 이력을 보존하며 별도 설계 결정의 원본으로 관리하지 않는다.

| 문서 | 남기는 역할 |
|---|---|
| `docs/architecture/repository-purpose.md` | 처음 읽는 사람을 위한 목적 요약 |
| `docs/architecture/equipment-data-parser-llm-behavior.md` | 현행 letter와 두 LLM 역할을 설명하는 안내 |
| `docs/architecture/equipment-data-parser-performance-proposal.md` 및 HTML | 병목 진단 근거·산술 예시·비교 실험 배경. 채택 방향은 4.3.1·4.6.2·11장으로 통합 |
| `docs/architecture/wiki-generator.md` 및 HTML | 현재 오프라인 구현의 사용법·projection 계약. 목표 iteration과 구별 |
| `equipment-data-parser/spec.md` | 실행 폴더만으로 읽을 수 있는 이 문서의 본문 스냅샷 |
