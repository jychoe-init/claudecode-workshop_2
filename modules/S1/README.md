# S1. 스탠드업 결과를 Slack으로 전달

HTTP Hook 이벤트와 외부 메시지 형식, 적재·전송·도착의 차이를 확인합니다.

## 공통 준비

저장소를 클론한 뒤 루트에서 실행합니다. Python 3.10 이상, Node.js, Git, 인증된 Claude Code가 필요합니다.

```bash
git clone https://github.com/jychoe-init/claudecode-workshop_2.git
cd claudecode-workshop_2
```

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python lab.py doctor
```

S1·S2·S5·S6은 별도 터미널에서 로컬 서버를 먼저 시작합니다.

```bash
.venv/bin/python lab.py serve --state .local/server
```

실제 Slack은 기본적으로 꺼져 있습니다. 강사 본인의 실습 채널을 검증할 때만 webhook을 환경변수에 설정한 뒤 `--slack-webhook-env 변수이름`을 명시합니다. URL을 코드·Skill·로그에 넣지 마세요.

## 시작본과 완성본

```bash
.venv/bin/python lab.py init S1 --root workspaces/s1 --stage starter
.venv/bin/python lab.py run --workspace workspaces/s1
```

`cca` 환경이면 `run`에 `--command cca`를 추가합니다. S6 계측은 `--otel`도 추가합니다.
실습 파일은 `workspaces/s1/.superlab/plugin/`에 있습니다. 참가자가 수정하는 위치: **standup/SKILL.md의 결과 확인·적재 단계**.

현재 파일을 덮어쓰지 않고 완성본·복구본을 새 디렉터리에 만듭니다.

```bash
.venv/bin/python lab.py init S1 --root workspaces/s1-complete --stage complete
```

## Claude 입력창

```text
/superlab:standup 오늘은 PR 검토와 실습 문서 갱신을 진행합니다.
```

## 직접 해볼 것
1. 로컬 서버를 먼저 시작하고 S1 시작본을 초기화합니다.
2. 스킬을 실행해 artifacts/standup.md를 확인합니다. 커밋이 없다는 것과 업무가 없다는 것은 다릅니다.
3. 완성본의 scripts/stage.py 호출 단계를 추가합니다. 현재 요청 식별자는 UserPromptSubmit 훅이 기록합니다.
4. 새 요청에서 다시 호출합니다. 결과가 적재되면 Stop HTTP 훅이 수신기에 전달합니다.
5. 일반 질문과 prompt-coach를 호출한 뒤에는 추가 메시지가 전송되지 않는지 확인합니다.

## 확인하기

```text
.venv/bin/python lab.py inspect outbox
.venv/bin/python lab.py inspect events
```

## 완료 기준

- [ ] outbox의 state와 mock_slack_received 기록이 연결됩니다.
- [ ] 같은 세션·요청의 결과가 중복 전송되지 않습니다.
- [ ] 적재와 외부 도착을 구분해 보고합니다.

## 관찰의 한계와 주의

- 기본값은 localhost mock입니다. 실제 Slack은 강사가 --slack-webhook-env로 명시적으로 켠 경우에만 전송합니다.
- Slack 응답을 받지 못한 timeout은 uncertain으로 남기고 자동 재전송하지 않습니다. 외부 서비스의 정확히 한 번 전송은 보장하지 않습니다.
- 127.0.0.1은 Claude Code가 실행되는 EC2/컨테이너/PC 자신입니다.
