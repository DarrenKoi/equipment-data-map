# 통합 아키텍처 문서 리뷰·수정, `wiki_review` 개명, office refresh 안내

- 일시: 2026-09-21 05:44–19:23 KST
- 상태: 완료 (커밋 `b262fde` push 완료, office refresh 완료, 에이전트 재실행은 사용자 몫)
- 스킬: 없음 (문서 리뷰와 짧은 diff라 프로세스 스킬을 쓰지 않음)

## 1. 요약

`docs/architecture/equipment-data-map.md`의 통합본(목표 계약 절 추가, +251줄)을 리뷰해 6개 항목과 서식 문제를 찾았고, 사용자 승인 후 전부 고쳐 `b262fde`로 커밋·push했다. 가장 큰 발견은 미추적 `equipment_map/publish.py`가 letter 12의 산출물 경로와 충돌한다는 것이어서 패키지를 `wiki_review/`로 개명했다. 이후 office refresh에서 나온 "changed letters already marked done: 02 12"의 원인(미반영이던 `8fab382`)을 설명하고 재실행 절차를 안내했다.

## 2. 진행 사항

**리뷰 (읽기만)**
- 문서 896줄 전체를 3회에 나눠 읽고, 의심 지점을 저장소에서 대조했다.
  - `spec.md`는 4줄 헤더 외 본문과 byte-identical.
  - 32 KiB / 4 KiB 상한은 `implementation-reference.md:681`과 일치.
  - `suggest/plan/submitted/finished`, `addressed`, `page-read`, `approval_verified: false`는 `exploration.py` 실제 동작과 일치.
  - §4.6.2의 "최대 69회" = (의미 7 + 필드 16) × (값·confidence·evidence 3) 산술 확인.
- `index.md:300`이 "letter가 지목한 절 범위를 통째로 출력"하게 하므로, letter가 읽는 절(§4.7.3 ← letter 12) 안의 표시 없는 목표 계약 문단이 실행 지시로 읽힐 위험을 확인했다. §7.1은 별도 `###` 절이라 letter 10의 "§7 bullet마다 테스트" 범위에 안 섞인다.
- `12-publish.md:18`이 `equipment_map/publish.py`를 실행 에이전트 산출물로 지정하고, §5의 `code_hash`가 그 패키지의 모든 `.py`를 덮는 것을 확인 → 미추적 `equipment_map/`을 커밋하면 실행 폴더의 stage 4 발행기를 덮어쓰고 기준 rollout 채택이 전부 무효가 된다.
- scope ID에 epoch이 들어가므로(§5.1) 사전만 바꾼 3단계 `init`도 장비 재수집을 유발한다는 것을 §4.8 iteration 루프와 연결해 지적했다(지난 성능 제안 리뷰의 redo-cost 문제와 같은 뿌리).

**수정**
- `sed`로 `.publish` / `.exploration` / `.review-v1` 접미 패턴만 골라 개명했다. 같은 문서에 "letter가 만드는 `equipment_map` CLI"와 "오프라인 도구" 두 의미가 섞여 있어 패키지 이름 전체 치환은 쓰지 않았다(§5의 `code_hash` 문장, letter들은 그대로).
- 아키텍처 문서 치환은 Python 스크립트로 하되 치환마다 `count == 1` assert를 걸었다. `spec.md`는 헤더 4줄 + 본문으로 재생성.
- 검증: `tests/test_wiki_generator.py` 17개 통과, `python -m tools.wiki_demo` 정상. `tests/test_ftp_transport.py`는 이 Mac 셸에 `python` 명령이 없어 못 돌렸다(`ftp_handler/`는 미수정).

**office 안내**
- refresh 출력 "02 12"의 원인 추적: `git diff 8fab382 b262fde -- 'equipment-data-parser/[0-9]*.md'`가 비어 있음 → 오늘 커밋은 letter 0개 변경. 02·12는 9/19의 `8fab382`가 바꿨고 office에 미반영 상태였다.
- 02(기준 rollout 채택, `code_hash`, 테스트 성공 1·거부 4)와 12(`REPORT.md`의 `adopted <기준 ID>`)의 재작업 규모를 diff로 확인해 전달.
- ledger가 append-only이고 awk 검사가 letter별 마지막 `done` 줄만 본다는 점, one-shot 프롬프트와 루프(`index.md` "One-shot sessions")를 안내.

## 3. 수정 내용

| 경로 | 구분 | 내용 |
|---|---|---|
| `docs/architecture/equipment-data-map.md` | 수정 | 아래 "결정 사항"의 1–6과 서식 |
| `equipment-data-parser/spec.md` | 수정 | 본문에서 재생성 |
| `wiki_review/publish.py`, `wiki_review/exploration.py` | 신규(개명) | 구 `equipment_map/`. import와 `generated_by: "wiki_review.review-v1"` 갱신 |
| `tests/test_wiki_generator.py`, `tools/wiki_demo.py` | 신규 | import 경로를 `wiki_review`로 |
| `docs/architecture/wiki-generator.{md,html}` | 신규 | 명령 예시의 모듈 이름 갱신 |
| `docs/architecture/equipment-data-parser-performance-proposal.{md,html}` | 신규 | `equipment_map.publish` 언급만 갱신 |
| `docs/architecture/equipment-data-parser-llm-behavior.md`, `repository-purpose.md` | 수정 | 세션 전부터 있던 사용자 수정분을 같은 커밋에 포함 |
| `CLAUDE.md` | 수정 | Repo status에 spike가 retired임을 표기 |

문서 쪽 세부:
- §4.7.3의 조사 원장 문단과 `wiki-generator.md` 참조 문단 → §4.8.1 맨 앞으로 이동.
- §3 흐름도의 검토 단계, §3.3 "선택 검사"·"검토 LLM" 행, §3.4 "조사 원장"에 목표 계약 표시.
- §4.8.2: 사전만 바꿔도 재수집, 평소 iteration은 `reviews/` projection, 같은 근거 재사용 재해석 경로는 문서에 없음.
- §4.8.4: 원장의 누적 사용량은 기록이지 guard가 아님. 상한은 `rollout.json` budget뿐.
- §4.3.1: LLM 없이 도는 1단계는 항상 `heavy`.
- §3.2: spike 은퇴 명시, 절을 `spike.py` 동작 기록으로 자리매김.
- 서식: §3.1 목록 합침, §4.5 인코딩 문단을 목록 뒤로, 읽는 순서에 6·8장, §4.7 트리에서 목표 전용 `glossary.json` 제거.

## 4. 결정 사항과 근거

- **패키지 개명 `equipment_map/` → `wiki_review/`.** 근거: letter 12 산출물 경로 충돌, `code_hash` 무효화, AGENTS.md의 "실행 에이전트에 배정된 root-level output을 만들지 말 것". 기각한 대안: §11.2의 "소유권 규칙은 나중에 정비"에 맡기기 — 충돌은 커밋 순간 생기므로 미룰 수 없다.
- **목표 계약은 "표시"가 아니라 "위치"로 분리.** letter가 절을 통째로 읽으므로 §4.7.3 안에 두고 표시만 다는 것은 저사양 모델에 약하다. 문단을 §4.8로 옮겼다. §3의 개요 절들은 옮길 곳이 없어 인라인 표시로 처리.
- **3번(재수집 비용)·4번(누적 budget)은 설계 변경 없이 한계를 한 문장씩 명시.** 사용자가 "추천대로 전부 수정"으로 승인. 기각한 대안: glossary 변경을 새 scope에서 제외하는 규칙, 원장 누적값을 계획 hash에 결합하는 경로 — 둘 다 새 계약이 필요하고 지금 요구가 없다(YAGNI). 필요해지면 별도 계약으로.
- **`main`에 직접 커밋.** 기본 지침은 default 브랜치에서 브랜치를 먼저 만드는 것이지만, 이 저장소는 hub가 `main`만 pull하고 모든 커밋이 `main` 직행이다(메모리: office branch 금지).
- **세션 전부터 있던 수정분 두 파일을 같은 커밋에 포함.** 같은 통합 작업의 일부로 판단. 사용자에게 보고함.

## 5. 배운 것 / 주의점

- **"이번 커밋이 무엇을 바꿨나"와 "office에 무엇이 새로 들어왔나"는 다른 질문이다.** 나는 "재빌드될 letter 없음"이라고 단정했다가 틀렸다. `.remember/open-jobs.md`에 "Office sync of `8fab382`" 미결 항목이 이미 있었는데 읽지 않았다. office 영향 예측 전에 open-jobs와 마지막 office 반영 커밋을 확인할 것.
- refresh 스크립트의 "changed letters" 출력은 이번 복사의 바이트 차이 기준인 참고 정보이고, 최종 판정은 ledger의 `letter:` hash 검사다. 손 복사가 끼면 스크립트 출력은 실제보다 적게 나온다.
- 이 Mac 셸에는 `python`이 없다(`python3` 또는 `uv run`). README의 home check는 `python3`로 적혀 있고 office PC는 `python`을 쓴다.
- zsh에서 `grep --include=*.md`는 glob 확장 오류가 난다. 따옴표로 감쌀 것.

## 6. 다음 단계

- 사용자가 모델 폴더에서 one-shot 루프를 재실행 → 02·12 재작업 후 다음 letter. open-jobs에 따르면 08·14·15도 `done`이었다면 함께 재작업되고, **`engineer.toml.example`을 모델 폴더에 `engineer.toml`로 복사하는 단계가 남아 있다**(이번 대화에서 안내를 빠뜨림 — 사용자에게 별도로 알림).
- 08의 ledger 마지막 줄 상태는 미확인. `blocked`면 problem 요약을 받아 letter를 고친다.
- 에이전트가 `glossary.json`·조사 원장·선정 모드를 만들거나 `wiki_review/`를 건드리면 spec의 목표 계약 차단을 더 강하게.
- `.remember/now.md`에 남은 이전 세션 항목: `publish.py:244` 부근 마스킹이 비밀이 아닌 필드 값을 망가뜨린다는 결함 — 이번 세션에서 다루지 않았고 현재 상태 미확인(추정: 미해결).
- open-jobs의 "Office sync of `8fab382`" 항목은 refresh가 끝났으니 갱신 대상. 나머지 미결 목록은 `open-jobs.md` 참조.

## 7. 메모리 업데이트

- auto-memory에 `check-office-sync-before-predicting-redo.md`(feedback) 추가: office 재작업 예측 전에 open-jobs와 미반영 커밋을 확인할 것.
- auto-memory에 `wiki-review-package-name.md`(project) 추가: 오프라인 검토 도구는 `wiki_review/`, 이 저장소에 `equipment_map/`을 만들지 않는 이유.
