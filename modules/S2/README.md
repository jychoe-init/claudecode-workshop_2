# S2. 사내 API를 MCP 도구로 제공

실제 stdio MCP 호출이 별도 HTTP API와 서버 상태 변경으로 연결되는 것을 확인합니다.

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
.venv/bin/python lab.py init S2 --root workspaces/s2 --stage starter
.venv/bin/python lab.py run --workspace workspaces/s2
```

`cca` 환경이면 `run`에 `--command cca`를 추가합니다. S6 계측은 `--otel`도 추가합니다.
실습 파일은 `workspaces/s2/.superlab/plugin/`에 있습니다. 참가자가 수정하는 위치: **.superlab/plugin/runtime/mcp_entry.py의 request_leave 도구**.

현재 파일을 덮어쓰지 않고 완성본·복구본을 새 디렉터리에 만듭니다.

```bash
.venv/bin/python lab.py init S2 --root workspaces/s2-complete --stage complete
```

## Claude 입력창

```text
내 실습용 잔여 휴가를 조회해 주세요.
```

## 직접 해볼 것
1. 서버를 시작하고 S2 시작본을 만듭니다. 시작본은 조회 도구 하나만 제공합니다.
2. 프로젝트 MCP 서버 연결 승인과 개별 도구 실행 승인을 구분합니다.
3. 조회 결과를 lab.py inspect balance로 대조합니다.
4. 완성본 mcp_server.py를 참고해 request_leave(start_date, days, request_key)를 추가하고 새 세션에서 서버를 다시 연결합니다.
5. 날짜와 일수를 명시해 신청하고 한 번은 거절, 한 번은 허용합니다. 요청 기록을 각각 대조합니다.

## 확인하기

```text
.venv/bin/python lab.py inspect balance
.venv/bin/python lab.py inspect requests
```

## 완료 기준

- [ ] 조회값이 서버 API와 같습니다.
- [ ] 거절 시 신청 기록이 없습니다.
- [ ] 허용 후 신청 ID와 pending 상태가 기록됩니다.

## 관찰의 한계와 주의

- MCP 호출 허용은 실제 휴가의 승인과 다릅니다. 이 API는 pending 신청만 만들며 승인 기능이 없습니다.
- 실습용 demo-user에게 12일이 있고 pending 신청은 가용 일수를 예약합니다. 실제 회사 정책이 아닙니다.
- 인증 토큰은 local-training-only인 로컬 교육용 값입니다. 실제 사내 API에서는 서버 측 인증·업무 권한을 별도로 적용해야 합니다.
