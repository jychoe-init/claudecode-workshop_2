# 공용 실습 API

대상: 계정 **135808921005**, 리전 **ap-northeast-2**.
상태: 템플릿을 생성·검증할 수 있으며 실제 배포는 검토 후 별도로 수행합니다.
실제 Slack이나 실제 회사 시스템은 포함하지 않습니다.

## 구성과 공유 계약

- API Gateway HTTP API → Lambda → DynamoDB.
- S3 + CloudFront는 공개 API 안내 문서용입니다.
- 로컬 서버와 Lambda가 `workshop_core/api.py`의 동일한 업무 계약을 사용합니다.
- 등록한 토큰의 해시만 서버에 저장하고 각 토큰에 별도 가상 계정을 연결합니다.
- 계정별 신청은 revision 조건부 갱신으로 동시에 잔여 일수를 초과하지 않게 합니다.
- 제한은 토큰당 분당 60회입니다. 응답·요청 본문·토큰을 애플리케이션 로그에 기록하지 않습니다.
- 모델 사용량은 이 인프라 비용과 별도입니다.

## 먼저 준비할 검토 자료

```bash
.venv/bin/python infra/build_template.py
aws sts get-caller-identity --profile isengard-admin --region ap-northeast-2
aws cloudformation validate-template --profile isengard-admin --region ap-northeast-2 --template-body file://.local/cloudformation.json
```

생성된 템플릿은 코드가 읽을 수 있는 형태로 포함된 단일 스택입니다.
IAM 권한은 해당 테이블과 해당 함수 로그에 한정합니다.
validate-template 성공은 실제 배포·API 작동의 증거가 아닙니다.

## 검토와 배포 확인 후 실행

```bash
aws cloudformation deploy --profile isengard-admin --region ap-northeast-2 --stack-name claudecode-workshop-2 --template-file .local/cloudformation.json --capabilities CAPABILITY_IAM
aws cloudformation describe-stacks --profile isengard-admin --region ap-northeast-2 --stack-name claudecode-workshop-2
```

출력의 ApiBase, TableName, DocsBucket, DocsUrl을 기록합니다.
문서는 공개 가능한 index.html과 API 안내만 DocsBucket에 업로드합니다.
원본 강사용 교안, 참가자 자료, 토큰 CSV, 실제 실행 로그는 업로드하지 않습니다.

토큰 발급도 계정 확인과 배포 완료 후 실행합니다.

```bash
.venv/bin/python -m pip install -r infra/requirements.txt
.venv/bin/python infra/issue_tokens.py --profile isengard-admin --count 80 --out .local/tokens.csv
```

CSV는 화면에 토큰을 출력하지 않고 접근 권한 600으로 새로 만듭니다.
같은 경로를 덮어쓰지 않습니다. 발급 도중 실패하면 이미 발급된 행은 보존되므로 파일을 확인하세요.
다시 발급할 때는 새 파일과 새 배치를 사용합니다.

## 실제 API 확인

전용 검증 계정으로 다음을 확인한 뒤 참가자에게 배포합니다.

- `/health`, 내 정보·정책·잔여 일수 조회.
- 상신 201 → 같은 키 재요청 200 → 신청 ID·키 재조회.
- 다른 토큰에서 신청 ID가 보이지 않음.
- 미등록 토큰 401, 입력 오류 400, 중복·부족 409, 제한 초과 429.
- 동시 신청이 가용 일수를 초과하지 않음.
- 코드·출력·로그에 토큰 값이 없음.

## 비용과 종료

호출량, Lambda 실행 시간, DynamoDB 요청 단위·저장량, 로그, S3·CloudFront 사용량이 비용에 영향을 줍니다.
무료 구간이나 계정 크레딧을 전제로 계산하지 않습니다. 모델 호출 비용은 포함하지 않습니다.
코드 검증 보고서의 조회일·단가·가정으로 검토하며 실제 청구액과 구분합니다.

스택은 삭제 지시까지 유지합니다. 삭제 승인 후 DocsBucket의 공개 안내 파일만 먼저 비우고
`aws cloudformation delete-stack`을 실행합니다. DynamoDB 가상 신청과 등록 토큰도 함께 삭제됩니다.
토큰 CSV는 별도로 보관 여부를 결정하며 자동 삭제하지 않습니다.
