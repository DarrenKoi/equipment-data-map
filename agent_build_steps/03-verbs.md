# 3. 동사로 쪼개기

키우는 성질: **경계 + 관측** · office 데이터: 필요 (letter 00 결과)

## 왜

`spike.py` 는 통짜다. 걷기·샘플링·LLM 호출·markdown 쓰기가 한 while 루프
안에 있다. 사람이 돌릴 때는 이게 장점이다 — 한 번 치면 끝난다.

agent 가 돌리려면 쪼개야 한다. 이유는 "모듈화가 좋아서" 가 아니라 셋이다:

- **모델에게 줄 선택지가 있어야 한다.** 통짜 스크립트에 모델이 할 수 있는
  선택은 "돌린다/안 돌린다" 뿐이다. 그건 agent 가 아니라 cron 이다.
- **비싼 것과 싼 것을 분리해야 한다.** 걷기는 싸고, 다운로드는 비싸고, LLM 은
  제일 비싸다. 지금은 하나가 실패하면 셋 다 다시 한다.
- **사람이 중간에 볼 지점이 생긴다.** 걷기만 돌려보고 범위가 맞는지 본 뒤에
  다운로드를 시작하는 게, 200MB 예산을 잘못 쓰고 나서 아는 것보다 낫다.

## 개념

**동사 설계의 규칙: 각 동사는 파일을 읽고 파일을 쓴다. 서로를 호출하지 않는다.**

```
walk      roots        -> inventory.jsonl   (경로, 크기, mtime)
sample    inventory    -> samples/          (내려받은 head)
describe  samples      -> describe.jsonl    (LLM 응답 원문)
emit      describe     -> out/*.md          (사람이 읽을 결과)
```

동사끼리 메모리로 값을 주고받지 않고 **중간 파일로만 이어진다.** 대가는
디스크 왕복이지만, 얻는 게 크다: 아무 동사나 따로 돌릴 수 있고, 실패한
동사만 다시 돌릴 수 있고, 각 단계의 중간 결과를 사람이 열어볼 수 있다.
이게 `CLAUDE.md` 의 "One CLI, thin skills" 가 말하는 구조다 — 분기와 상태는
동사 안에, 모델은 어떤 동사를 부를지만 고른다.

동사를 몇 개로 할지는 **office run 이 정한다.** 실제 서버가 SIZE 를 지원하지
않아 걷기가 못 쓰게 나오면 walk 를 둘로 쪼개야 할 수도 있고, 파일이 전부
같은 포맷이면 sample 과 describe 를 합치는 게 맞을 수도 있다. letter 00 을
돌리기 전에 이 단계를 설계하지 마라.

## 실습

`equipment-map` 을 만들되 프레임워크 없이. `argparse` 서브파서 넷이면 된다.
`spike.py` 를 지우지 말고 **옆에 둔 채로** 옮긴다 — 둘의 출력이 같은지가
리팩터링의 유일한 검증이다.

```
python -m equipment_map walk     equipment.toml
python -m equipment_map sample   equipment.toml
python -m equipment_map describe equipment.toml
python -m equipment_map emit     equipment.toml
```

각 동사는 마지막 줄에 JSON 한 줄(한 일의 개수 + 판정 boolean)을 찍고,
`audit.jsonl` 에 append 한다. 2단계에서 만든 ledger 를 그대로 쓴다.

**같은지 확인**: fake 트리에서 `spike.py` 를 돌린 `out/` 과 동사 넷을 순서대로
돌린 `out/` 을 `diff -r` 한다. LLM 응답 문구만 다르고 나머지는 같아야 한다.

**한 동사만 돌려보기**: `walk` 만 돌리고 `inventory.jsonl` 을 열어라. 여기서
"범위가 잘못됐다" 를 알아채는 것이, 이 단계가 주는 실질적 이득이다.

## 통과 기준

동사 넷을 순서대로 돌린 결과가 `spike.py` 한 번 돌린 결과와 `diff -r` 상
LLM 문구 외에 같고, `sample` 을 건너뛰고 `describe` 를 돌리면 "선행 산출물
없음" 으로 깨끗이 실패한다.

## 이 단계에서 배워 갈 것

agent 에게 주는 도구는 **동사이고, 동사는 파일 경계를 갖는다.** 도구가
서로를 호출하기 시작하면 모델의 선택은 의미를 잃고 디버깅도 불가능해진다.
