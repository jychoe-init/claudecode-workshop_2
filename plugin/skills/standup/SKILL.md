---
name: standup
description: 최근 커밋과 사용자가 제공한 계획을 스탠드업으로 정리하고, 실습 수신기에 명시적으로 적재한다. 설정된 경우 Stop HTTP 훅이 알림을 전송한다.
argument-hint: "[오늘 계획; 없으면 미정으로 남김]"
disable-model-invocation: true
---

# Standup → 알림

사용자 계획: $ARGUMENTS

1. `git log --since="1 day ago" --format="%h %s"`로 실제 커밋을 확인한다. Git을 사용할 수 없으면 그 한계를 표시한다.
2. `artifacts/standup.md`에 `### 어제`, `### 오늘`, `### 확인 필요` 세 부분을 작성한다.
3. 커밋이 없다는 사실을 업무가 없었다는 뜻으로 바꾸지 않는다.
   제공되지 않은 오늘 계획은 ‘미정’, 확인하지 못한 블로커는 ‘미확인’으로 쓴다.
4. 원문과 사용자 계획을 대조한다. 일반 대화나 prompt-coach의 개선문을 이 결과로 사용하지 않는다.
5. 다음 명령으로 이 결과만 현재 요청에 적재한다.

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/stage.py" artifacts/standup.md
```

6. 적재 결과를 보고한다. ‘적재됨’과 Slack 도착은 다르다. 전송 상태는 수신기의 `/outbox` 또는 실행 기록에서 확인한다.

전송은 S1 환경에서 활성화한 Stop HTTP Hook이 담당한다. 수신기가 없거나 요청 식별자가 없으면 실패를 보고하고 임의로 Slack 주소를 찾거나 다른 경로로 보내지 않는다.
