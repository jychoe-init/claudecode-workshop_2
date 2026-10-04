# M-OPUS5 — 증상에 맞는 조정만

확인일: 2026-10-04
근거: https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
확인할 섹션: Response length and verbosity; Task scope and over-verification.

- 답변 분량이 문제라면 원하는 분량을 프롬프트로 명시한다. effort 설정을 단순한 길이 설정으로 취급하지 않는다.
- 기준 없는 재검증·무조건적인 교차 검증 지시는 불필요한 검증을 늘리는지 확인해 줄인다. 실제 테스트·릴리스 조건·상태 변경 전 확인은 원래 작업의 요구와 구분해 보존한다.
- 기존에 잘 작동하는 요청을 모델 이름이 바뀌었다는 이유만으로 전면 재작성하지 않는다.
- 이 카드는 Fable·Sonnet의 삭제 규칙으로 일반화하지 않는다.
