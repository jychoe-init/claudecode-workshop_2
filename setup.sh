#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null
command -v git >/dev/null
python3 -c 'import sys; assert sys.version_info >= (3,10), "Python 3.10 이상이 필요합니다."'
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
workshop_launcher="${CLAUDE_LAUNCHER:-claude}"
.venv/bin/python workshop.py doctor --command "$workshop_launcher"
printf '\nClaude의 /status에서 인증·모델·작업 폴더를 확인하세요.\n'
printf '다음: .venv/bin/python workshop.py init lab1 --root workspaces/lab1\n'
