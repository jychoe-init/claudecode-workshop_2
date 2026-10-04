---
name: standup
description: 커밋과 사용자의 계획을 근거로 스탠드업 초안을 작성한다.
argument-hint: "[오늘 계획]"
disable-model-invocation: true
---

사용자 계획: $ARGUMENTS

최근 커밋을 확인하고 artifacts/standup.md에 어제 / 오늘 / 확인 필요를 작성한다.
근거 없는 계획·진행 상태·블로커를 만들지 않는다.

학습자 작업: 결과를 확인한 뒤에만 scripts/stage.py로 적재하는 단계를 추가한다.
단순 초안 생성, 전송 대기 등록, 실제 전송 성공을 구분해서 보고한다.
