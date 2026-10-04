from __future__ import annotations

import argparse
import getpass
import json
import os
from pathlib import Path
import shutil
import sys
import re
import subprocess

from .local_api import LabServer, LocalStore
from .api import token_hash
from .workspace import LABS, configure, initialize, run, launcher


def main(argv=None):
    parser = argparse.ArgumentParser(description="Ch4: repeat work, API automation, prompt inspection and sharing")
    commands = parser.add_subparsers(dest="action", required=True)
    p = commands.add_parser("init")
    p.add_argument("lab", choices=LABS)
    p.add_argument("--root", required=True)
    p.add_argument("--api-base", default="http://127.0.0.1:8787")
    p = commands.add_parser("configure", help="Register a token without putting it in a model prompt")
    p.add_argument("--workspace", required=True)
    p.add_argument("--api-base")
    p.add_argument("--token-env", help="Read token from this environment variable, never from a command argument")
    p.add_argument("--local-demo", action="store_true")
    p = commands.add_parser("run")
    p.add_argument("--workspace", required=True)
    p.add_argument("--command", default="claude")
    p.add_argument("extra", nargs=argparse.REMAINDER)
    p = commands.add_parser("serve")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--state", default=".local/api")
    p = commands.add_parser("check")
    p.add_argument("--workspace", required=True)
    p = commands.add_parser("doctor")
    p.add_argument("--command", default="claude")
    args = parser.parse_args(argv)
    try:
        if args.action == "init":
            result = initialize(args.root, args.lab, args.api_base)
        elif args.action == "configure":
            if args.local_demo and args.token_env:
                raise ValueError("Choose local-demo or token-env")
            token = "local-training-only" if args.local_demo else (
                os.environ.get(args.token_env) if args.token_env else getpass.getpass("실습 토큰 (화면에 표시하지 않음): "))
            result = configure(args.workspace, token, args.api_base)
        elif args.action == "run":
            extra = args.extra[1:] if args.extra[:1] == ["--"] else args.extra
            return run(args.workspace, args.command, extra)
        elif args.action == "serve":
            store = LocalStore(Path(args.state) / "api.sqlite3")
            if not store.authenticate(token_hash("local-training-only")):
                store.register("local-training-only", "local-participant")
            server = LabServer(("127.0.0.1", args.port), store)
            print(json.dumps({"api_base": server.base_url, "mode": "local-fictional",
                              "token_configuration": "workshop.py configure --local-demo"}, ensure_ascii=False), flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        elif args.action == "check":
            from .checks import inspect_workspace
            result = inspect_workspace(Path(args.workspace).resolve())
        else:
            probe = subprocess.run(launcher(args.command, ["--version"]), capture_output=True, text=True, timeout=20)
            match = re.search(r"\b(\d+)\.(\d+)\.(\d+)", probe.stdout)
            version = tuple(map(int, match.groups())) if match else None
            ready = bool(probe.returncode == 0 and version and version >= (2, 1, 283) and shutil.which("git"))
            result = {"python": sys.version.split()[0], "git": shutil.which("git"),
                      "claude": shutil.which("claude"), "minimum_claude_code": "2.1.283",
                      "launcher": args.command, "observed_version": probe.stdout.strip(),
                      "ready": ready, "authentication_checked": False,
                      "note": "Claude 입력창의 /status에서 모델·인증·작업 폴더를 확인하세요."}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if args.action == "doctor" and not result["ready"] else 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print("Workshop error: " + str(exc), file=sys.stderr)
        return 2
