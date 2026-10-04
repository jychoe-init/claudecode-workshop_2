#!/usr/bin/env python3
from pathlib import Path
import json
import sys

for ancestor in Path(__file__).resolve().parents:
    choices = [ancestor / "runtime", ancestor / ".superlab/plugin/runtime"]
    runtime = next((p for p in choices if (p / "workshop_lab").is_dir()), None)
    if runtime:
        sys.path.insert(0, str(runtime))
        break
else:
    raise SystemExit("Initialize a superlab workspace first.")

from workshop_lab.cli import stage_standup

try:
    row = stage_standup(Path.cwd(), sys.argv[1])
    print(json.dumps({"outbox_id": row["id"], "state": row["state"]}))
except Exception as exc:
    print(f"Not staged: {exc}", file=sys.stderr)
    raise SystemExit(1)
