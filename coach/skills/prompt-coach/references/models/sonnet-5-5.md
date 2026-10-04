# M-SONNET55 — 실제 검사와 작업 범위

확인일: 2026-10-04
근거: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5
섹션: Steer initiative and scope; Verification on coding tasks; Tool use in chat and knowledge work; Reasoning tasks with JSON output.

- 작업을 일찍 멈추거나 요청하지 않은 일을 추가하는 증상이 있다면, 완료 범위와 필요한 멈춤 조건을 명시한다.
- 특히 낮은 effort에서 검사 없이 완료를 보고하는 증상이 있으면 실제 테스트·빌드·실행 확인을 요구한다. Opus 5의 일반적인 검증 축소 권고를 가져와 필요한 검사를 지우지 않는다.
- 바뀔 수 있는 사실을 훈련 지식만으로 답한다면 사용할 수 있는 조회 도구와 필요한 확인 대상을 명시한다.
- JSON 문법 준수와 내용의 정확성은 다르다. 추론 설정·구조화된 출력·결과 검증을 구분한다.
