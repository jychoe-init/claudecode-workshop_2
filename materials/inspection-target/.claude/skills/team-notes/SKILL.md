---
name: team-notes
description: 지정한 회의 기록을 팀 검토용 결정·할 일·확인 필요 표로 정리한다.
argument-hint: "[회의 기록 파일 경로]"
disable-model-invocation: true
---

입력: $ARGUMENTS

원문 파일과 이 스킬의 `templates/report.md`를 읽고 결과를 작성한다.
원문 근거를 표시하며 외부 작업을 실행하지 않는다.
프로젝트의 CLAUDE.md와 reporting 규칙을 함께 적용한다.
출력 경로를 지정하면 그 경로를 사용하고, 없으면 대화에 결과를 보여준다.
