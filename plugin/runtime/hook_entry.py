#!/usr/bin/env python3
import json
import sys
from workshop_lab.cli import hook

if __name__ == "__main__":
    try:
        result = hook(sys.argv[1], json.load(sys.stdin))
        if isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result))
    except Exception as exc:
        print(f"superlab hook: {type(exc).__name__}: {exc}", file=sys.stderr)
        # This diagnostic does not block the user's work.
        raise SystemExit(1)
