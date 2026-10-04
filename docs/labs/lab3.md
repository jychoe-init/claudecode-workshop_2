# Lab 3 — 프롬프트 점검·공유

편성 초안 18분. 제공되는 prompt-coach를 활용하고, 저장 지시문과 공유 준비를 점검합니다.

Claude 입력창:

```text
/workshop:workshop-coach lab3
```

1. `inputs/original-prompt.txt`의 요청에서 좋은 결과의 기준을 정합니다.
2. `/workshop:prompt-coach`로 요청을 검토하고, 필요한 답을 제공해 개선문을 만듭니다.
3. 개선문을 `artifacts/improved-prompt.txt`로 저장하도록 요청한 뒤 실제 비교를 실행합니다.

```bash
python3 tools/compare.py --original inputs/original-prompt.txt --improved artifacts/improved-prompt.txt
```

비교는 두 개의 새 Claude 세션을 호출하며 모델 사용량이 발생합니다.
같은 입력 자료에서 읽기 전용 문서 업무를 비교합니다. 파일 수정·API 신청 비교용이 아닙니다.
두 실행은 같은 effort(기본 medium)를 사용하며 각각 3달러의 CLI 예산 상한을 둡니다.
`measurements/`의 원본·개선본 response.md와 usage.csv를 워크시트에 대조하세요.
캐시 사용량도 함께 표시하며, 코치 비용을 분리 측정하지 않았다면 미측정으로 남깁니다.

4. Claude에서 `/doctor prompt-audit inspection-target`을 실행하고 결함 하나를 선택해 수정합니다.
5. 용도·입력·주의사항 세 줄을 정한 뒤 README 작성을 요청합니다.
6. `.gitignore`, git diff, `python3 tools/check.py`를 확인하고 선택한 파일을 커밋합니다.

완료 기준:

- 실제 실행 결과와 사용량을 비교하고 지시문 결함 수정의 근거를 남겼다.
- 사용 안내와 공유 제외 항목을 확인한 커밋이 있다.
