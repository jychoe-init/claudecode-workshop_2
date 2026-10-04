# S4. 회의록·주간보고와 supporting file

원문 사실, 업무 상태, 출력 템플릿을 분리해 반복 업무에 적용합니다.

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
.venv/bin/python lab.py init S4 --root workspaces/s4 --stage starter
.venv/bin/python lab.py run --workspace workspaces/s4
```

`cca` 환경이면 `run`에 `--command cca`를 추가합니다. S6 계측은 `--otel`도 추가합니다.
실습 파일은 `workspaces/s4/.superlab/plugin/`에 있습니다. 참가자가 수정하는 위치: **meeting-notes 및 weekly-report의 SKILL.md와 templates/**.

현재 파일을 덮어쓰지 않고 완성본·복구본을 새 디렉터리에 만듭니다.

```bash
.venv/bin/python lab.py init S4 --root workspaces/s4-complete --stage complete
```

## Claude 입력창

```text
/superlab:meeting-notes inputs/meeting.txt
```

## 직접 해볼 것
1. 회의록 입력과 supporting template을 먼저 읽습니다.
2. 회의록 스킬을 실행하고 담당자·기한·근거가 원문과 맞는지 확인합니다.
3. 템플릿의 항목 하나를 변경하고 새 입력에도 같은 방식으로 적용되게 합니다.
4. 주간보고에는 inputs/tasks.csv와 명시적인 보고 기간을 전달합니다.
5. 기간 밖의 T05와 승인되지 않은 T04가 완료 업무로 잘못 분류되지 않았는지 확인합니다.

## 확인하기

```text
/superlab:weekly-report inputs/tasks.csv 2026-09-28..2026-10-04
```

## 완료 기준

- [ ] 미정 담당자와 기한을 만들어내지 않습니다.
- [ ] 논의·계획을 완료로 바꾸지 않습니다.
- [ ] 보고 기간 밖의 업무가 구분됩니다.

## 관찰의 한계와 주의

- argument-hint는 입력 안내이며 파일 존재·유효성을 검사하는 파서가 아닙니다.
- 기획·비개발 참가자도 Git 없이 원문·템플릿·결과를 대조할 수 있습니다.
