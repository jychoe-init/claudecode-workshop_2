# Claude Code Workshop — 세 가지 업무 실습

**Lab 1 반복업무 스킬 제작 → Lab 2 API 업무 자동화 → Lab 3 프롬프트 점검·공유**

각 랩은 독립된 작업 공간에서 시작합니다. 참가자가 기준을 정하고 Claude에게 제작·실행을 요청하며,
워크시트로 실제 결과를 확인합니다. 편성 초안은 20·20·18분이며 준비·마무리는 별도입니다.

## 준비

Python 3.10 이상, Git, 인증된 Claude Code 2.1.283 이상이 필요합니다.
아래 명령은 macOS/Linux/WSL 기준입니다. Windows 기본 셸에서는 가상환경 실행 파일 경로를 조정하세요.

```bash
git clone --branch ch4-three-labs-api https://github.com/jychoe-init/claudecode-workshop_2.git
cd claudecode-workshop_2
bash setup.sh
```

## 시작

```bash
.venv/bin/python workshop.py init lab1 --root workspaces/lab1
.venv/bin/python workshop.py run --workspace workspaces/lab1
```

Claude 입력창:

```text
/workshop:workshop-coach lab1
```

`lab2`, `lab3`도 같은 방식으로 각각 새 폴더에 만듭니다.
`cca`를 쓰는 환경은 `run`에 `--command cca`를 추가합니다.
준비 검사도 `cca`로 하려면 `CLAUDE_LAUNCHER=cca bash setup.sh`를 사용합니다.
Claude를 시작한 뒤 `/status`에서 모델·인증·작업 폴더를 확인하세요.
실행기는 제공 스킬과 학습자 플러그인을 명시적으로 로드합니다.
학습자 스킬 호출은 `/my-team:스킬이름`입니다. 새 파일을 만들었으면 실행기를 다시 시작하세요.
환경에 따라 스킬 파일 작성에 개별 승인 창이 나타납니다. 생성할 파일과 내용을 확인해 허용하세요.
코치는 거부된 작업을 다른 도구로 우회하지 않습니다.

| 랩 | 제공 자료 | 내가 만드는 것 |
|---|---|---|
| [lab1](docs/labs/lab1.md) | 회의록·주간보고 시작본, 입력 자료 | 팀 양식 스킬 또는 새 반복업무 스킬 |
| [lab2](docs/labs/lab2.md) | 가상 업무 API, 명세, HTTP 클라이언트 | 조회·판단·질문·상신·상태 확인 스킬 |
| [lab3](docs/labs/lab3.md) | prompt-coach, 비교 도구, 결함 있는 지시문 | 개선된 요청과 지시문, 공유 안내와 커밋 |

## Lab 2 API 준비

공용 API 주소와 실습 토큰이 제공되면:

```bash
.venv/bin/python workshop.py init lab2 --root workspaces/lab2 --api-base https://제공받은-API-주소
.venv/bin/python workshop.py configure --workspace workspaces/lab2
```

토큰은 터미널에서 숨겨 입력하며 `.env.local`에 저장됩니다. Claude에 붙여넣지 않습니다.

로컬 대체는 별도 터미널에서 시작합니다.

```bash
.venv/bin/python workshop.py serve --state .local/api
```

```bash
.venv/bin/python workshop.py init lab2 --root workspaces/lab2
.venv/bin/python workshop.py configure --workspace workspaces/lab2 --local-demo
.venv/bin/python workshop.py run --workspace workspaces/lab2
```

로컬 주소는 `http://127.0.0.1:8787`이며 가상 계정 하나를 사용합니다. 공용 API는 발급 토큰별로 분리됩니다.
실제 회사 시스템이나 Slack을 사용하지 않습니다.

## 점검·공유

생성된 작업 공간의 `worksheet.md`에 결정·예측·실행 결과·수정 이유를 남기세요.
코치의 “확인”과 제공 검사 도구는 실제 업무 품질을 자동 인증하지 않습니다.
`artifacts/`, `measurements/`, 토큰과 개인 설정은 Git에서 제외합니다.
강사용 검증 결과는 `validation/`, AWS 템플릿은 `infra/`에 둡니다.

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests -q
```
