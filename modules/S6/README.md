# S6. 컨텍스트·토큰·비용 계측

현재 컨텍스트, 요청별 사용량, 세션 추정 비용을 서로 다른 데이터로 읽습니다.

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
.venv/bin/python lab.py init S6 --root workspaces/s6 --stage starter
.venv/bin/python lab.py run --workspace workspaces/s6
```

`cca` 환경이면 `run`에 `--command cca`를 추가합니다. S6 계측은 `--otel`도 추가합니다.
실습 파일은 `workspaces/s6/.superlab/plugin/`에 있습니다. 참가자가 수정하는 위치: **계측 대상·비교 기준과 export된 CSV 해석**.

현재 파일을 덮어쓰지 않고 완성본·복구본을 새 디렉터리에 만듭니다.

```bash
.venv/bin/python lab.py init S6 --root workspaces/s6-complete --stage complete
```

## Claude 입력창

```text
/context all
```

## 직접 해볼 것
1. 서버를 시작하고 run에 --otel을 추가해 요청별 이벤트를 수집합니다.
2. /context all로 현재 점유를 확인합니다. /skill-doctor는 사용 가능한 환경에서만 실행합니다.
3. 스킬 등록과 본문 실제 호출 후의 변화를 구분합니다.
4. 같은 입력·모델에서 읽는 자료 범위만 바꾼 실험을 별도 세션으로 수행합니다.
5. CSV를 내보내고 품질·누락과 사용량을 함께 검토합니다.

## 확인하기

```text
.venv/bin/python lab.py export --state .local/server --out measurements
# api_requests.csv / status_snapshots.csv / sessions.csv / coverage.json
```

## 완료 기준

- [ ] 스냅샷을 누적 사용량처럼 합산하지 않습니다.
- [ ] agent 완료의 마지막 요청 토큰을 전체 실행 합계로 사용하지 않습니다.
- [ ] 데이터가 없으면 미측정으로 남깁니다.

## 관찰의 한계와 주의

- 기본 수집 프로토콜은 OTLP HTTP/protobuf입니다. /v1/logs 수신기는 JSON도 처리합니다.
- Stop에는 전체 사용량이 들어오지 않습니다. 상태줄과 OTel의 역할을 분리했습니다.
- 세션 추정비용과 실제 제공자 청구는 다릅니다. 코치 실행 비용과 이후 업무 비용도 분리합니다.
