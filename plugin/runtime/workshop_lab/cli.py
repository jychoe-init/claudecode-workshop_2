from __future__ import annotations

import argparse
import json
import os
import secrets
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .server import LabServer
from .store import Store, canonical

KIT = Path(__file__).resolve().parents[3]
PLUGIN = Path(__file__).resolve().parents[2]
MODULE_SKILLS = {
    "S1": ["standup", "prompt-coach"], "S2": [], "S3": ["pr-desc", "review-checklist"],
    "S4": ["meeting-notes", "weekly-report"], "S5": [],
    "S6": ["pr-desc", "review-checklist", "meeting-notes", "prompt-coach"],
    "S7": ["prompt-coach"], "ALL": ["standup", "pr-desc", "review-checklist",
                                  "meeting-notes", "weekly-report", "prompt-coach"],
}


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + "." + secrets.token_hex(4) + ".tmp")
    temp.write_text(canonical(value) + "\n", encoding="utf-8")
    os.replace(temp, path)


def post(config, path, value):
    req = urllib.request.Request(config["api_url"] + path,
        data=canonical(value).encode(), headers={"Content-Type": "application/json",
        "X-Superlab-Token": config["token"]}, method="POST")
    with urllib.request.urlopen(req, timeout=8) as response:
        return json.load(response)


def config_at(workspace):
    workspace = Path(workspace).resolve()
    return workspace, json.loads((workspace / ".superlab/config.json").read_text())


def initialize(root, module, stage, api_url, token):
    parts = urllib.parse.urlsplit(api_url)
    if (parts.scheme != "http" or parts.hostname not in {"127.0.0.1", "localhost"}
            or parts.username or parts.password or parts.query or parts.fragment
            or parts.path not in {"", "/"}):
        raise ValueError("The kit connects only to a localhost lab API base URL.")
    root = Path(root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("Destination must be empty. Choose a new directory; existing work is never overwritten.")
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(KIT / "fixtures/project", root, dirs_exist_ok=True)
    shutil.copytree(KIT / "fixtures/documents", root / "inputs")
    shutil.copytree(PLUGIN / "runtime", root / ".superlab/plugin/runtime")
    shutil.copytree(PLUGIN / ".claude-plugin", root / ".superlab/plugin/.claude-plugin")
    for name in MODULE_SKILLS[module]:
        dest = root / ".superlab/plugin/skills" / name
        shutil.copytree(PLUGIN / "skills" / name, dest)
        starter = KIT / "starters" / module / name / "SKILL.md"
        if stage == "starter" and starter.exists():
            shutil.copyfile(starter, dest / "SKILL.md")
    (root / ".claude").mkdir(exist_ok=True)
    config = {"module": module, "stage": stage, "api_url": api_url.rstrip("/"),
              "token": token, "workspace": str(root), "kit_version": "1.0.0"}
    atomic_json(root / ".superlab/config.json", config)
    os.chmod(root / ".superlab/config.json", 0o600)
    entry = root / ".superlab/plugin/runtime/hook_entry.py"
    command = shlex.join([sys.executable, str(entry)])
    settings = {
        "permissions": {"deny": ["Read(.env*)", "Edit(src/users.js)"]},
        "env": {"SUPERLAB_API_URL": api_url.rstrip("/"), "SUPERLAB_TOKEN": token},
        "statusLine": {"type": "command", "command": command + " status"},
    }
    if module in {"S1", "ALL"}:
        settings["hooks"] = {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": command + " record-prompt"}]}],
            "Stop": [{"hooks": [{"type": "http", "url": api_url.rstrip("/") + "/hooks/stop",
                      "headers": {"X-Superlab-Token": "${SUPERLAB_TOKEN}"},
                      "allowedEnvVars": ["SUPERLAB_TOKEN"], "timeout": 10}]}],
        }
    if module in {"S2", "S5", "ALL"}:
        if module == "S2" and stage == "starter":
            shutil.copyfile(KIT / "starters/S2/mcp_entry.py",
                            root / ".superlab/plugin/runtime/mcp_entry.py")
        atomic_json(root / ".mcp.json", {"mcpServers": {"hr": {
            "command": sys.executable,
            "args": [str(root / ".superlab/plugin/runtime/mcp_entry.py")],
            "env": {"SUPERLAB_API_URL": api_url.rstrip("/"), "SUPERLAB_TOKEN": token},
        }}})
        if module != "S5":
            settings["permissions"]["allow"] = ["mcp__hr__get_leave_balance"]
            settings["permissions"]["ask"] = ["mcp__hr__request_leave"]
    atomic_json(root / ".claude/settings.json", settings)
    for name, permissions in {
        "read-only": {"allow": ["mcp__hr__get_leave_balance"],
                      "deny": ["mcp__hr__request_leave", "Edit", "Write", "Bash"]},
        "assisted": {"allow": ["mcp__hr__get_leave_balance"],
                     "ask": ["mcp__hr__request_leave", "Edit(**)"]},
        "lab-automation": {"allow": ["mcp__hr__get_leave_balance", "mcp__hr__request_leave"],
                           "deny": ["Edit(src/users.js)"]},
    }.items():
        atomic_json(root / ".superlab/profiles" / f"{name}.json", {"permissions": permissions})
    (root / ".gitignore").write_text(".superlab/\n.env*\n.claude/settings.local.json\nartifacts/\n")
    (root / ".env.lab").write_text("FAKE_TOKEN=not-a-real-secret\n")
    (root / "artifacts").mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "src", "test.js", "package.json", "README.md",
                    "CLAUDE.md", "inputs", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Workshop",
                    "-c", "user.email=workshop@example.invalid", "commit", "-qm", "lab: baseline"], check=True)
    if module in {"S3", "ALL"}:
        with (root / "src/userService.js").open("a") as f:
            f.write('\nexport function getUserLabel(id) {\n  return getUser(id)?.name ?? "unknown";\n}\n')
        subprocess.run(["git", "-C", str(root), "add", "src/userService.js"], check=True)
    return {"workspace": str(root), "module": module, "stage": stage,
            "next": shlex.join([sys.executable, str(KIT / "lab.py"), "run", "--workspace", str(root)]),
            "launcher_hint": "Add --command cca if cca is your configured Claude Code launcher."}


def hook(action, data, cwd=None):
    workspace = Path(cwd or data.get("cwd") or os.getcwd()).resolve()
    workspace, config = config_at(workspace)
    if action == "record-prompt":
        if data.get("hook_event_name") != "UserPromptSubmit" or not data.get("session_id") or not data.get("prompt_id"):
            raise ValueError("Expected UserPromptSubmit with session_id and prompt_id")
        # Deliberately do not save the user's prompt text.
        atomic_json(workspace / ".superlab/active.json",
                    {k: data[k] for k in ("session_id", "prompt_id")})
        return {}
    if action == "status":
        try:
            post(config, "/status", data)
        except (OSError, ValueError):
            pass
        ctx = (data.get("context_window") or {}).get("used_percentage")
        cost = (data.get("cost") or {}).get("total_cost_usd")
        return f"ctx {ctx if ctx is not None else '?'}% | session estimate ${cost if cost is not None else '?'}"
    raise ValueError("Unknown hook action")


def stage_standup(workspace, source):
    root, config = config_at(workspace)
    path = (root / source).resolve()
    artifact_root = (root / "artifacts").resolve()
    if not artifact_root.is_relative_to(root):
        raise ValueError("The artifacts directory must remain inside the workspace")
    if not path.is_relative_to(artifact_root) or not path.is_file():
        raise ValueError("Only a regular result file under this workspace's artifacts/ may be staged")
    active = json.loads((root / ".superlab/active.json").read_text())
    text = path.read_text()
    if not all(x in text for x in ("### 어제", "### 오늘", "### 확인 필요")):
        raise ValueError("Standup must include 어제, 오늘, 확인 필요 sections")
    return post(config, "/outbox", {**active, "text": text})


def cli_env(config, enable_otel=False):
    env = os.environ.copy()
    env.update(SUPERLAB_TOKEN=config["token"], SUPERLAB_API_URL=config["api_url"])
    if enable_otel:
        env.update(CLAUDE_CODE_ENABLE_TELEMETRY="1", OTEL_LOGS_EXPORTER="otlp",
                   OTEL_METRICS_EXPORTER="none", OTEL_LOGS_EXPORT_INTERVAL="1000",
                   OTEL_EXPORTER_OTLP_LOGS_PROTOCOL="http/protobuf",
                   OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=config["api_url"] + "/v1/logs",
                   OTEL_EXPORTER_OTLP_LOGS_HEADERS="X-Superlab-Token=" + config["token"],
                   OTEL_LOG_USER_PROMPTS="false",
                   OTEL_RESOURCE_ATTRIBUTES="module.id=" + config["module"])
    return env


def main(argv=None):
    parser = argparse.ArgumentParser(description="S1–S7 local workshop kit")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("init", help="Create a NEW module workspace, never overwrite")
    p.add_argument("module", choices=MODULE_SKILLS)
    p.add_argument("--root", required=True)
    p.add_argument("--stage", choices=["starter", "complete"], default="complete")
    p.add_argument("--url", default="http://127.0.0.1:8765")
    p.add_argument("--token", default=os.environ.get("SUPERLAB_TOKEN", "local-training-only"))
    p = commands.add_parser("serve", help="Run local mock HR API, relay, and OTLP collector")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--state", default=".superlab-server")
    p.add_argument("--token", default=os.environ.get("SUPERLAB_TOKEN", "local-training-only"))
    p.add_argument("--slack-webhook-env", help="Explicit opt-in to external delivery; value is never printed")
    p = commands.add_parser("stage-standup", help="Arm THIS standup result for the current prompt's Stop event")
    p.add_argument("file")
    p.add_argument("--workspace", default=".")
    p = commands.add_parser("export", help="Export observed telemetry; does not invent missing usage")
    p.add_argument("--state", default=".superlab-server")
    p.add_argument("--out", required=True)
    p = commands.add_parser("inspect", help="Read local backend state; does not change it")
    p.add_argument("what", choices=["balance", "requests", "outbox", "events"])
    p.add_argument("--url", default="http://127.0.0.1:8765")
    p.add_argument("--token", default=os.environ.get("SUPERLAB_TOKEN", "local-training-only"))
    p = commands.add_parser("run", help="Launch configured Claude Code in an initialized workspace")
    p.add_argument("--workspace", default=".")
    p.add_argument("--command", dest="launcher", default="claude", help="Executable or shell alias; e.g. cca")
    p.add_argument("--profile", choices=["read-only", "assisted", "lab-automation"])
    p.add_argument("--otel", action="store_true")
    p.add_argument("claude_args", nargs=argparse.REMAINDER)
    commands.add_parser("doctor", help="Show local dependency readiness, no model calls")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            print(canonical(initialize(args.root, args.module, args.stage, args.url, args.token)))
        elif args.command == "serve":
            url = None
            if args.slack_webhook_env:
                url = os.environ.get(args.slack_webhook_env)
                parts = urllib.parse.urlsplit(url or "")
                if (parts.scheme != "https" or parts.hostname not in {"hooks.slack.com", "hooks.slack-gov.com"}
                        or not parts.path.startswith("/services/")):
                    raise ValueError("Explicit Slack mode requires a valid webhook in the named environment variable")
            server = LabServer(("127.0.0.1", args.port), Store(Path(args.state) / "lab.sqlite3"), args.token, url)
            print(canonical({"server": server.base_url, "delivery": "slack" if url else "local_mock",
                             "state": str(Path(args.state).resolve())}), flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        elif args.command == "stage-standup":
            result = stage_standup(args.workspace, args.file)
            print(canonical({"outbox_id": result["id"], "state": result["state"]}))
        elif args.command == "export":
            print(canonical(Store(Path(args.state) / "lab.sqlite3").export(args.out)))
        elif args.command == "inspect":
            path = {"balance": "/api/hr/balance", "requests": "/api/hr/requests",
                    "outbox": "/outbox", "events": "/events"}[args.what]
            req = urllib.request.Request(args.url.rstrip("/") + path,
                                         headers={"X-Superlab-Token": args.token})
            with urllib.request.urlopen(req, timeout=5) as response:
                print(json.dumps(json.load(response), ensure_ascii=False, indent=2))
        elif args.command == "run":
            root, config = config_at(args.workspace)
            extra = args.claude_args
            if extra and extra[0] == "--":
                extra = extra[1:]
            extra = ["--plugin-dir", str(root / ".superlab/plugin")] + extra
            if args.profile:
                extra = ["--settings", str(root / ".superlab/profiles" / (args.profile + ".json"))] + extra
            # No interpolation of prompt text: argv is shell-quoted as code, aliases resolved by user's shell.
            executable = shutil.which(args.launcher)
            if executable:
                launch = [executable, *extra]
            else:
                command = shlex.join([args.launcher, *extra])
                shell = os.environ.get("SHELL") or shutil.which("zsh") or "/bin/bash"
                launch = [shell, "-ic", command]
            return subprocess.call(launch, cwd=root, env=cli_env(config, args.otel))
        elif args.command == "doctor":
            import importlib.metadata
            info = {"python": sys.version.split()[0], "node": shutil.which("node"),
                    "git": shutil.which("git"), "claude": shutil.which("claude")}
            for dependency in ("mcp", "opentelemetry-proto"):
                try:
                    info[dependency] = importlib.metadata.version(dependency)
                except importlib.metadata.PackageNotFoundError:
                    info[dependency] = "missing"
            print(canonical(info))
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
