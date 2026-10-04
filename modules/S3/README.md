# S3. PR 실행형·참조형 스킬 한 쌍

직접 호출하는 작업과 관련 요청에서 선택되는 지침을 구분합니다.

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
.venv/bin/python lab.py init S3 --root workspaces/s3 --stage starter
.venv/bin/python lab.py run --workspace workspaces/s3
```

`cca` 환경이면 `run`에 `--command cca`를 추가합니다. S6 계측은 `--otel`도 추가합니다.
실습 파일은 `workspaces/s3/.superlab/plugin/`에 있습니다. 참가자가 수정하는 위치: **pr-desc/SKILL.md와 review-checklist/SKILL.md**.

현재 파일을 덮어쓰지 않고 완성본·복구본을 새 디렉터리에 만듭니다.

```bash
.venv/bin/python lab.py init S3 --root workspaces/s3-complete --stage complete
```

## Claude 입력창

```text
/superlab:pr-desc 이번 변경을 팀이 검토할 수 있게 설명해 주세요.
```

## 직접 해볼 것
1. S3 시작본에는 작은 변경이 스테이징돼 있습니다. diff 범위는 git diff --cached입니다.
2. PR 초안을 생성하고 실제 변경과 대조합니다.
3. review-checklist의 description과 user-invocable 값을 읽고 팀 기준을 추가합니다.
4. 일반 요청으로 “이 변경을 우리 팀 기준으로 리뷰해 주세요”라고 입력합니다. 실제 스킬 호출을 관찰합니다.
5. 변경이 없는 경우와 입력 수집 오류를 구분하는 완성본을 확인합니다.

## 확인하기

```text
git -C workspaces/s3 diff --cached
```

## 완료 기준

- [ ] PR 본문이 실제 staged diff에 근거합니다.
- [ ] 참조형 스킬이 실제 호출됐는지 기록으로 확인합니다.
- [ ] 테스트를 실행하지 않았으면 완료로 체크하지 않습니다.

## 관찰의 한계와 주의

- 자동 호출 허용은 호출 보장이 아닙니다. 호출되지 않으면 description과 요청의 관계를 검토합니다.
- manual Skill 안에서 참조형을 강제로 호출했다면 자동 선택 실험으로 설명하지 않습니다.
