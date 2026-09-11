# 1. 경계를 테스트로 못 박기

키우는 성질: **경계** · office 데이터: 불필요

## 왜

`spike.py` 의 `inside()` 와 `denied()` 는 지금 **주장** 이다. 코드를 읽으면
맞는 것 같지만, 누가 리팩터링하다 `normpath` 한 번 빼먹으면 `/log/../etc` 가
통과한다. 그리고 그 사실은 실장비에서 처음 드러난다.

agent 로 가는 순간 이게 더 중요해진다. 사람이 돌릴 때는 사람이 명령을 보지만,
모델이 돌릴 때는 아무도 안 본다. **경계는 "모델이 시키지 않을 것" 이 아니라
"시켜도 안 되는 것" 이어야 한다.**

## 개념

harness 의 경계에는 두 층이 있다.

- **정책(policy)** — 무엇이 허용되는가. `roots`, `deny`, `budget`. 데이터다.
- **집행(enforcement)** — 그 정책이 우회 불가능한가. 코드고, **테스트로만
  증명된다.**

둘을 섞으면(= 호출부마다 if 로 막으면) 호출부 하나 빠뜨리는 순간 구멍이 난다.
집행은 wire 로 나가는 **단 하나의 길목** 에 두고, 그 길목을 테스트한다.
`spike.py` 는 이미 그렇게 돼 있다 — `dl.size_dirs` / `dl.download` 를 부르기
전에 `inside()`·`denied()` 를 통과해야 한다.

## 실습

`tests/test_spike_boundaries.py` 를 새로 쓴다. fake FTP 를 띄울 필요 없다 —
`spike.py` 의 판정 함수만 떼어 부르면 된다. 그러려면 `main()` 안의
`inside`/`denied` 를 모듈 최상위 함수로 끌어올려야 한다 (roots 를 인자로 받게).
이게 이 단계의 유일한 리팩터링이다.

막아야 할 것 최소 4개:

1. `/log/../etc/passwd` — 정규화 후에도 roots 밖
2. `/logs` — `/log` 의 접두사이지 하위가 아님 (`startswith` 버그의 고전)
3. `deny = ["*.bak"]` 일 때 `/log/a/b.bak`
4. `max_download_bytes` 를 1바이트 넘기는 파일이 `wanted` 에 안 들어감

3·4번은 fake 트리가 있어야 정직하다. `tests/test_spike_fake.py` 에 트리를
하나 더 심어서 확인해도 된다.

```
python tests/test_spike_boundaries.py
uv run --python 3.11 --with pyftpdlib --with flask --with requests \
    python tests/test_spike_fake.py
```

**의도적으로 깨보기** (이게 실습의 핵심이다): `inside()` 의 `normpath` 를
지우고 테스트를 돌려라. 1번이 빨갛게 떠야 한다. 안 뜨면 테스트가 경계를
검사하는 게 아니라 구현을 따라 쓴 것이다. 다시 써라.

## 통과 기준

`python tests/test_spike_boundaries.py` 가 0 으로 끝나고, `inside()` 안의
`normpath` 를 지우면 실패한다.

## 이 단계에서 배워 갈 것

경계 테스트는 "된다" 를 확인하는 게 아니라 **"안 된다" 를 확인한다.** 다른
프로젝트에서도 agent 에 도구를 줄 때 먼저 쓸 테스트는 언제나 거부 테스트다.
