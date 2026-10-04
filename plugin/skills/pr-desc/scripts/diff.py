#!/usr/bin/env python3
"""Fixed command, no user-supplied shell interpolation."""
import json
import subprocess

try:
    r = subprocess.run(["git", "diff", "--cached", "--no-ext-diff", "--no-color", "--"],
                       capture_output=True, text=True, timeout=10)
    if r.returncode:
        result = {"status": "error", "detail": r.stderr[:1000], "scope": "staged changes"}
    elif not r.stdout.strip():
        result = {"status": "empty", "scope": "staged changes"}
    else:
        result = {"status": "ok", "scope": "staged changes", "truncated": len(r.stdout) > 50000,
                  "diff": r.stdout[:50000]}
except (OSError, subprocess.TimeoutExpired) as exc:
    result = {"status": "error", "detail": str(exc), "scope": "staged changes"}
print(json.dumps(result, ensure_ascii=False))
