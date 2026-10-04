---
name: meeting-notes
description: 명시적으로 제공된 회의 기록을 정리한다.
argument-hint: "[회의 기록 파일]"
disable-model-invocation: true
---

입력 파일: $ARGUMENTS

파일을 읽고 회의록을 만든다. 원문에 없는 사실은 만들지 않는다.

학습자 작업:
- templates/meeting.md를 읽고 해당 양식으로 작성한다.
- 결정·논의·할 일을 구분하고, 각 항목의 근거를 기록한다.
- 담당자·기한이 없으면 미정으로 남긴다.
- 결과를 artifacts/meeting-notes.md에 작성한다.
