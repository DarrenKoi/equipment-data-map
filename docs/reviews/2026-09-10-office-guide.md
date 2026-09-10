# Office LLM 실행 지침 검토 — 2026-09-10

기준 commit은 `8fb7668`이다. architecture, office 계약과 20개 letter,
문제 보고 양식, FTP 실제 API 및 기존 transport 테스트를 읽었다. 독립 검토는
상태·승인 계약과 에이전트 지침·전송 API의 두 축으로 수행했다.
이 변경은 Markdown 지침 보강이며 office letter 실행이나 CLI 구현이 아니다.

## 현재 판정

**실장비 실행 준비: REQUEST-CHANGES.** CLI, 추출 테스트, portable skill suite는
아직 없고 `progress.md`에도 완료 기록이 없다. 지침의 테스트 명령은 앞으로
구현할 산출물의 완료 조건이다. 현재 실행 가능한 검사는 transport 선택 5개뿐이다.
문서 수정으로 실제 전송 안전성이나 작은 모델의 정확성을 검증했다고 볼 수 없다.

## 계약·명세 축

| 심각도 | 기존 문제와 영향 | 지침 수정 |
|---|---|---|
| P1 | manifest 파일만 비교하면 실제 evidence 변조를 승인할 수 있음 | 실제 파일 집합과 bytes를 재검증하고 완료된 현재 epoch만 결과 승인 |
| P1 | stage/epoch 구속, 과거·미래 요청, init/승인 동시성 불명확 | 명시적 전이표, 공통 잠금과 복구 예외, terminal complete 정의 |
| P1 | 시작 때만 시간대 검사하여 종료 후에도 장비 접근 가능 | 매 요청 및 전송 중 deadline 검사, 중단 뒤 worker 종료 증거 요구 |
| P1 | parser·압축·LLM 입력의 상한과 실패 결과가 추상적 | 버전 1의 유한 상수, 출력 형식, 초과 사유와 시나리오 명시 |
| P2 | fake→real 전환과 장비 하나 규칙이 충돌 | harness provenance와 stage-3 실제 장비 정체성을 구분 |
| P2 | confidence가 높으면 의미 추론을 RAG fact로 오인 가능 | 관측과 추론을 분리하고 confidence/evidence를 개별 claim에 결합 |
| P2 | random bytes를 encrypted로 분류 | 암호화 형식 근거가 없으면 unsupported로 보존 |

원칙은 architecture §4–5에 반영했고, 구체적 자료형·예시는
`equipment-data-parser/implementation-reference.md`에서 해당 letter에 연결했다.
`spec.md`는 기존 snapshot 방식대로 architecture 본문과 동일하게 갱신한다.

## 에이전트 지침·전송 축

| 심각도 | 기존 문제와 영향 | 지침 수정 |
|---|---|---|
| P1 | fleet API의 mtime 누락과 timeout 후 worker 잔존 | metadata/실행 수명은 별도 검증; 크기 cap 부재는 수용하고 일반 다운로드와 실제 사용량 기록 |
| P1 | Windows에서 회사 proxy에 localhost를 보내면 원격 proxy의 localhost를 가리킴 | 같은 PC의 fake proxy + fake FTP로 검증하고 운영 설정과 프로세스 분리 |
| P1 | curl 예시는 .env를 shell에 로드하지 않으며 token을 argv로 전달 | agent가 secret을 읽지 않는 CLI 검사 구현과 engineer 실행으로 변경 |
| P2 | 인증 없는 proxy도 올바른 token 요청에 200을 반환할 수 있음 | 무인증 401 및 인증 200을 모두 검사하고 사내 HTTP 사용 및 redirect 제한 |
| P2 | rate limit을 요청 수 budget처럼 소진시킴 | 요청 pacing과 누적 count/time budget을 구분 |
| P2 | 공유 DTO import 금지와 DTO 사용 요구가 충돌 | downloader 선택만 factory로 제한, 공유 자료형 import 명시 |
| P2 | 테스트가 전역 requests mock을 설치하여 이후 HTTP 검증을 가릴 수 있음 | letter 01에 기존 테스트 격리 수정과 합동 실행 조건 추가 |
| P2 | 확정 행 4개 집계만으로 네 도구 검증을 판정 | 서로 다른 도구별 현재 release 결과와 증거 hash 확인 |
| P2 | 커밋하는 progress/problem에 오류 원문·모델 설정이 들어갈 수 있음 | sanitized code만 기록, 상세 결과는 회사 내부 untracked 파일 |
| P2 | next 반복 및 지난 rollout의 done 재사용으로 정지/재개가 모호 | status 기반 resume, 새 rollout marker, no-progress loop 종료 |

## 아직 필요한 외부 작업

1. **FTP upstream 유지보수자:** 상세 metadata, bounded listing, 요청 pacing,
   실제 cancellation/worker 종료 및 capability 계약을
   구현·검증하고 이 저장소에 검토된 버전을 다시 반영해야 한다.
   파일 크기 cap은 선행조건이 아니며, 초과·크기 미상 파일도 일반 다운로드를
   시도하고 실제 사용량을 기록하도록 사용자 정책을 반영했다.
2. **Proxy 운영자:** 해당 버전을 배포하고 사내 HTTP/auth 및 기능을 회사 환경에서
   확인해야 한다. HTTP는 사용자 지정 운영 정책이다. vendor 예시의 placeholder
   host와 no-auth 설정은 실제 host 및 비어 있지 않은 token으로 대체한다.
3. **Engineer:** keystore, 접근 승인, 읽기 전용 계정, ACL/보존, root/budget/window,
   profile/glossary와 실제 모델·도구 설정을 입력·확인해야 한다.
4. **Office 개발 에이전트:** letter 01–15로 CLI와 테스트를 구현하고 실패 지점에서
   멈춰야 한다. 기록되지 않은 사이트 사실이나 라이브러리 기능을 발명하지 않는다.
5. **네 도구 검증:** 동일 최소 모델 프로필과 suite 버전에서 실측한 transcript,
   audit, 재개·오류 시나리오 결과 및 사람의 의미 정확성 검토가 필요하다.

## 이번 변경의 검증 결과

- PASS: Markdown 로컬 링크와 참조 대상, 20개 letter 목록, snapshot 본문 일치.
- PASS: shell loop bash 구문 및 무변경·승인 대기·완료·이미 완료·도구 실패의 5개 종료 모의 실행.
- PASS: 기존 `python3 tests/test_ftp_transport.py`의 5개 검사. 이것은 platform/env 분기
  검증이며 회사 proxy, FTP/SMB 보안, extraction 또는 모델 정확도 검증이 아니다.
- PASS: `git diff --check`, 변경 파일은 Markdown뿐.
- vendor, runtime 코드, progress ledger, 현장 데이터 변경 없음.
- 두 독립 검토자 모두 지적했던 문서 충돌의 수정에 APPROVE. 실장비 준비 승인과는 별개다.

새 office 세션은 `equipment-data-parser/index.md`, engineer는
`equipment-data-parser/engineer-guide.md`에서 시작한다. 전체 문서를 한 번에
모델 context에 넣지 말고 current letter가 연결하는 reference 절만 읽는다.
