---
name: pr-desc
description: 스테이징된 변경을 읽고 PR 설명 초안을 작성한다.
argument-hint: "[추가 설명]"
disable-model-invocation: true
---

추가 설명: $ARGUMENTS
!`python3 "${CLAUDE_SKILL_DIR}/scripts/diff.py"`

변경 내용과 이유를 정리한다. 입력이 없거나 실패하면 내용을 만들어내지 않는다.

학습자 작업: 실제 검사 결과와 미확인 사항을 구분하는 출력 기준을 추가한다.
review-checklist의 description과 호출 조건을 확인하고 관련 요청에서 실제 호출되는지 관찰한다.
