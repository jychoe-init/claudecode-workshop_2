# S5. 운영 프로필 3종과 실제 권한

프로필 이름, 설정 스코프, 병합 결과와 실제 행동을 구분합니다.

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
.venv/bin/python lab.py init S5 --root workspaces/s5 --stage starter
.venv/bin/python lab.py run --workspace workspaces/s5
```

`cca` 환경이면 `run`에 `--command cca`를 추가합니다. S6 계측은 `--otel`도 추가합니다.
실습 파일은 `workspaces/s5/.superlab/plugin/`에 있습니다. 참가자가 수정하는 위치: **.superlab/profiles/read-only.json, assisted.json, lab-automation.json**.

현재 파일을 덮어쓰지 않고 완성본·복구본을 새 디렉터리에 만듭니다.

```bash
.venv/bin/python lab.py init S5 --root workspaces/s5-complete --stage complete
```

## Claude 입력창

```text
실습 API에서 잔여 휴가를 조회한 뒤, 제가 지정한 날짜와 일수로 신청할 때 어떤 확인이 필요한지 설명해 주세요.
```

## 직접 해볼 것
1. 프로필별로 조회·신청·파일 수정의 기대 결과를 먼저 적습니다.
2. read-only 프로필로 새 세션을 시작해 조회와 신청을 요청합니다.
3. assisted 프로필로 시작해 같은 신청을 거절·허용해 봅니다.
4. lab-automation은 명시적인 실습용 신청 요청에 한해 별도의 도구 확인 없이 실행될 수 있는 프로필입니다. 실제 외부 API에는 사용하지 않습니다.
5. /permissions에서 출처와 적용 규칙을 확인하고, 실제 API 상태와 함께 기록합니다.

## 확인하기

```text
.venv/bin/python lab.py run --workspace workspaces/s5 --profile read-only
.venv/bin/python lab.py run --workspace workspaces/s5 --profile assisted
.venv/bin/python lab.py run --workspace workspaces/s5 --profile lab-automation
```

## 완료 기준

- [ ] read-only는 신청을 거부합니다.
- [ ] assisted는 신청 전 확인합니다.
- [ ] 자동화 프로필도 서버의 날짜·일수·가용량 검사를 통과해야 합니다.

## 관찰의 한계와 주의

- 세 파일 모두 --settings로 불러오면 CLI 설정입니다. 이름이 개인/팀/규제라고 scope가 바뀌지 않습니다.
- 기존 user/project/local의 deny·ask는 합쳐지고 managed 정책은 해제되지 않습니다.
- --dangerously-skip-permissions를 사용하면 이 비교 실습이 성립하지 않습니다. 실제 permissionMode를 확인합니다.
