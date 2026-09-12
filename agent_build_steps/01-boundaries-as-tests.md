# 1. 경계를 테스트로 못 박기

키우는 성질: **경계** · office 데이터: 불필요

## 왜

`spike.py` 의 경계는 `tests/test_spike_boundaries.py`로 검증한다.
리팩터링 중 검사가 빠져도 실제 장비에 닿기 전에 실패하도록 유지해야 한다.

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
`spike.py`는 `list_dirs`로 먼저 목록을 받은 뒤 경로를 정규화·검사하고,
고정 경로만 `size_dirs`에 넘긴다. 다운로드 직전에도 같은 정책을 적용한다.
목록을 직접 `size_dirs`로 확장하면 제외 경로에도 SIZE/MDTM이 전송될 수 있다.

## 실습

기존 `tests/test_spike_boundaries.py`를 실행하고 가짜 목록에 예외 입력을 더한다.
가짜 FTP 서버 없이 `main()`을 실행하고 외부 전송 응답만 대체한다.
함수를 떼어 단독 검사하는 것보다 실제 LIST·SIZE·다운로드 요청 기록에서
금지 경로가 없는지 확인하는 것이 이 단계의 목적이다.

막아야 할 것 최소 4개:

1. `/log/../etc/passwd` — 정규화 후에도 roots 밖
2. `/logs` — `/log` 의 접두사이지 하위가 아님 (`startswith` 버그의 고전)
3. `deny = ["*.bak"]` 일 때 `/log/a/b.bak`
4. 전체 목표 바이트에 도달·초과한 전송 이후 다음 다운로드가 시작되지 않음

조회 크기는 참고값이다. 남은 목표보다 큰 파일도 통째로 받을 수 있으며
완료 후 실제 바이트로 다음 전송을 결정한다. 실패 전송은 부분 사용량을
모르므로 이후 전송을 멈춘다. `tests/test_spike_fake.py`는 실제 FTP 명령도 기록한다.

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
