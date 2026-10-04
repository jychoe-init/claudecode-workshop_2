# 실습용 업무 API v1

모든 직원·잔여 휴가·신청은 가상 데이터입니다. 회사 규정이나 실제 휴가 승인 시스템이 아닙니다.
공용 API와 로컬 API는 같은 경로·검사·응답 구조를 사용합니다.

## 연결

`LAB_API_BASE` 또는 작업 공간 설정에 API 주소를 지정합니다.
실습 토큰은 터미널의 `workshop.py configure`로 등록합니다. Claude 프롬프트에 넣지 않습니다.
요청 인증은 `Authorization: Bearer <실습 토큰>`이며 제공 클라이언트가 처리합니다.
토큰별로 계정·잔여 일수·신청이 분리됩니다.

## 조회

| HTTP | 경로 | 응답에서 볼 것 |
|---|---|---|
| GET | `/v1/me` | participant_id, employee_id=self, 서버 기준일 as_of |
| GET | `/v1/leave/policy` | 신청 종류·최대 5 근무일·pending 예약 규칙 |
| GET | `/v1/leave` | annual_days, used_days, pending_days, available_days |
| GET | `/v1/leave/requests` | 본인 신청 목록 |
| GET | `/v1/leave/requests?request_key=...` | 같은 업무 요청의 처리 결과 |
| GET | `/v1/leave/requests/{id}` | 본인 신청 ID의 현재 상태 |

조회 예:

```bash
python3 tools/api.py get /v1/me
python3 tools/api.py get /v1/leave
```

클라이언트는 한 번의 HTTP 요청만 수행합니다. 어떤 순서로 조회하고 판단할지는 스킬에 구현합니다.

## 신청

`POST /v1/leave/requests`

| 필드 | 형식·의미 |
|---|---|
| start_date, end_date | YYYY-MM-DD. 서버 기준일 이후, 시작·끝 모두 평일 |
| leave_type | 실습에서는 annual |
| request_key | 같은 업무를 식별하는 8–80자의 영문·숫자·밑줄·하이픈 |
| note | 선택. 400자 이하 |

실습의 일수 계산은 월–금만 셉니다. 실제 공휴일 달력은 적용하지 않습니다.
서버는 최대 일수·가용 일수·기간 중복을 제출 시 다시 검사합니다.
각 계정은 처음 12일이며 pending 신청은 가용 일수를 예약합니다.

제출 전에 `python3 tools/api.py key`로 업무 키를 만들 수 있습니다.
참가자가 확정한 제출 내용을 JSON 파일로 저장한 뒤 클라이언트에 전달합니다.

```bash
python3 tools/api.py post /v1/leave/requests --json-file artifacts/submission.json
```

첫 성공은 201, 같은 키·같은 내용의 재요청은 200과 `created:false`입니다.
응답의 `request.id`로 다시 조회하세요. `status:pending`은 상신이며 승인·사용 완료가 아닙니다.

## 실패·응답 끊김

| 상태 | 의미 | 업무 흐름에서 판단할 것 |
|---|---|---|
| 400 | 필수 값·날짜·종류·한 번의 일수 제한 오류 | 내용을 확인하고 수정 여부 결정 |
| 401 | 미등록·잘못된 토큰 | 인증 준비 확인 |
| 404 | 본인 계정에서 찾을 수 없는 경로·신청 | ID와 경로 확인 |
| 409 | 잔여 일수 부족, 기간 중복, 같은 키의 내용 변경 | 원인을 설명하고 재제출 여부 결정 |
| 429 | 토큰당 분당 60회 제한 | Retry-After 이후 필요한 호출만 수행 |
| 응답 확인 불가 | 특히 POST는 처리됐을 수도 있음 | 보존한 request_key로 먼저 조회 |

POST는 클라이언트가 자동 재시도하지 않습니다. 같은 키로 조회했는데 기록이 없더라도
네트워크 상태와 사용자 요청을 확인하고 재제출을 결정하세요.
출력의 `http_status:0`은 HTTP 성공이 아니라 연결·응답 확인 실패입니다.
