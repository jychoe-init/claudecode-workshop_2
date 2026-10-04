# Lab 3 — 프롬프트·저장 지시문 점검과 공유

목표: prompt-coach를 활용해 요청을 개선하고 실제 결과·사용량을 비교한 뒤 공유 가능한 안내를 만든다.
prompt-coach 자체를 새로 만드는 랩이 아니다.

1. `inputs/original-prompt.txt`의 업무에서 좋은 결과의 기준을 참가자가 정하게 한다.
2. `/workshop:prompt-coach`를 사용해 공식·모델별·팀 기준에 따라 검토한다.
   개선본을 사용할 대상 모델을 참가자가 지정하면 해당 모델 카드도 읽는다. 실행 중인 코치 모델과 혼동하지 않는다.
   참가자가 답한 정보만 반영해 개선문을 `artifacts/improved-prompt.txt`로 저장한다.
   원문의 업무를 코치 검토 중 실행하지 않는다.
3. 비교 실행 요청을 받으면 아래 제공 도구를 실행한다.

```bash
python3 tools/compare.py --original inputs/original-prompt.txt --improved artifacts/improved-prompt.txt
```

두 개의 독립된 읽기 전용 Claude 세션에서 같은 입력 자료로 원본·개선본을 실행한다.
도구는 진행 중 수십 초 이상 걸릴 수 있다. 요청이 끝나기 전에 실패나 성공을 꾸며내지 않는다.
`measurements/comparison.json`, 두 response.md와 usage.csv를 참가자 기준으로 비교한다.
comparable=false이면 동일 조건의 비교로 설명하지 않는다. 캐시 값과 오류도 함께 본다.
코치 비용이 따로 측정되지 않았다면 미측정이라고 표시한다. 응답 글자 수로 비용을 추정하지 않는다.

4. `/doctor prompt-audit inspection-target`으로 저장 지시문을 검토한다.
   지원되는 도구의 실제 출력과 해당 파일을 함께 읽는다. 명령을 실행하지 않았으면 실행했다고 하지 않는다.
   참가자가 고칠 결함을 선택하면 수정 요청을 받아 고치고 변경 이유를 설명한다.
   inspection-target에는 독립적으로 가져갈 수 있는 team-notes 스킬과 양식도 포함돼 있다.
5. 참가자가 용도·입력·주의사항 세 줄을 정한다. 요청받으면 README 나머지를 작성한다.
6. `tools/check.py`, `.gitignore`, git diff를 확인한다. 개인 입력·측정·토큰을 커밋 대상에 넣지 않는다.
   참가자의 커밋 요청이 있으면 해당 파일만 커밋한다. push는 추가하지 않는다.

완료 증거: 원본/개선본의 실제 출력·사용량 비교와 참가자 관찰, 지시문 수정 diff, 사용 안내와 커밋.
