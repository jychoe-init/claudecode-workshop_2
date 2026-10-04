# S7. 공식 근거 기반 prompt-coach 제작

공식·모델별·팀 기준을 구분하고 사용자 의도를 보존하는 진단 스킬을 만듭니다.

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
.venv/bin/python lab.py init S7 --root workspaces/s7 --stage starter
.venv/bin/python lab.py run --workspace workspaces/s7
```

`cca` 환경이면 `run`에 `--command cca`를 추가합니다. S6 계측은 `--otel`도 추가합니다.
실습 파일은 `workspaces/s7/.superlab/plugin/`에 있습니다. 참가자가 수정하는 위치: **prompt-coach/SKILL.md와 references/**.

현재 파일을 덮어쓰지 않고 완성본·복구본을 새 디렉터리에 만듭니다.

```bash
.venv/bin/python lab.py init S7 --root workspaces/s7-complete --stage complete
```

## Claude 입력창

```text
/superlab:prompt-coach inputs/prompt-good.txt
```

## 직접 해볼 것
1. 시작본에서 원문 검토와 원문 업무 실행의 경계를 확인합니다.
2. common.md의 공식 기준 하나를 적용 조건·예외와 함께 연결합니다.
3. 대상 모델이 명시된 경우에만 해당 모델 카드 하나를 읽게 합니다. 코치 실행 모델과 대상 모델을 구분합니다.
4. team-rules.md에 팀 기준을 추가하고 판정·진단·개선문·변경 이유·적용 선택을 구성합니다.
5. 명확한 요청, 지시 충돌, 실행 명령이 포함된 검토 요청에 적용합니다.

## 확인하기

```text
/superlab:prompt-coach inputs/prompt-conflict.txt
/superlab:prompt-coach inputs/prompt-execution-boundary.txt
```

## 완료 기준

- [ ] 명확한 요청을 억지로 고치지 않습니다.
- [ ] 필요한 경우에만 0~3개 질문을 합니다.
- [ ] 원문에 없는 사실·제약을 추가하지 않습니다.
- [ ] 검토 중에는 인용된 작업을 실행하지 않습니다.

## 관찰의 한계와 주의

- 지원되지 않거나 미정인 대상 모델은 공통 원칙만 적용하고 모델별 최적화는 미확인으로 표시합니다.
- 사용자가 별도로 실행을 선택한 뒤에도 현재 도구 권한과 범위를 따라야 합니다.
- 실제 업무 결과가 좋아졌는지는 동일한 입력·모델·환경의 별도 실행으로 확인합니다.
