# Claude Code Super Lab Kit

S1–S7을 독립된 실습 공간에서 실행하는 교육 키트입니다. 시간 제한과 필수/선택 구분은 넣지 않았습니다.

**시작 화면:** `index.html`  · **검증 상태:** `validation/REPORT.md`

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

## 실행 흐름

1. 로컬 서버가 필요한 모듈은 서버를 시작합니다.
2. `lab.py init S7 --root workspaces/s7 --stage starter`로 새 시작본을 만듭니다.
3. `lab.py run --workspace workspaces/s7`로 시작합니다. `cca`는 `--command cca`를 추가합니다.
4. `/superlab:prompt-coach`처럼 접두사가 있는 명령을 사용합니다.
5. 완료 기준을 실제 파일·로그·서버 상태로 확인합니다.

모듈별 프로젝트의 자동 Skill 검색에 의존하지 않도록 실행기가 해당 모듈의 플러그인을 명시적으로 로드합니다. 단순히 다른 폴더에서 `claude`를 켰다면 같은 스킬이 로드되지 않을 수 있습니다.

## 모듈

- [S1: 스탠드업 결과를 Slack으로 전달](modules/S1/README.md)
- [S2: 사내 API를 MCP 도구로 제공](modules/S2/README.md)
- [S3: PR 실행형·참조형 스킬 한 쌍](modules/S3/README.md)
- [S4: 회의록·주간보고와 supporting file](modules/S4/README.md)
- [S5: 운영 프로필 3종과 실제 권한](modules/S5/README.md)
- [S6: 컨텍스트·토큰·비용 계측](modules/S6/README.md)
- [S7: 공식 근거 기반 prompt-coach 제작](modules/S7/README.md)

## 핵심 파일

- `plugin/skills/`: 완성된 6개 스킬과 supporting files
- `starters/`: 참가자가 보완할 시작본
- `plugin/runtime/`: MCP·HTTP API·전송·계측 실행 도구
- `fixtures/`: 가상 코드·회의록·업무 상태·프롬프트 입력
- `SOURCES.json`: 공식 문서 조회 시각·URL·해시
- `tests/`: 실제 로컬 HTTP·MCP·오류·중복 처리 검사
- `validation/`: 실제 확인한 범위와 남은 확인 사항

## 로컬 검사

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```

## 실제 Slack 모드

강사가 본인의 허용된 실습 채널 webhook을 안전한 환경변수로 설정한 후에만 서버를 실행합니다.

```bash
.venv/bin/python lab.py serve --state .local/live-slack --slack-webhook-env SUPERLAB_SLACK_WEBHOOK
```

실제 Slack은 이번 제작 자동 검증에서 호출하지 않습니다. 성공 여부는 해당 채널에서 요청 식별자와 함께 확인해야 합니다. 타임아웃 등 결과가 불확실한 전송은 자동 재시도하지 않습니다.

## 버전과 적용 범위

실제 사용한 Python·SDK·CLI와 시험 결과는 validation에 기록합니다. /skill-doctor 등 feature flag가 필요한 명령은 해당 환경에서 표시되는지 사전에 확인합니다. 프로필은 CLI 설정이며 managed 정책을 재현하거나 우회하지 않습니다.

생성된 `.superlab`에는 해당 실습의 런타임 경로와 로컬 테스트 토큰이 있습니다. 개인 인증이나 Slack 비밀값을 배포물에 넣지 않습니다. 한 모듈의 작업을 복구하려면 기존 디렉터리를 지우지 말고 새 경로에 다시 초기화합니다.
