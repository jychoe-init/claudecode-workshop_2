from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

KIT = Path(__file__).resolve().parents[1]
LABS = {"lab1": "반복업무 스킬 제작", "lab2": "API 업무 자동화", "lab3": "프롬프트 점검·공유"}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def launcher(command, args):
    executable = shutil.which(command)
    if executable:
        return [executable, *args]
    return [os.environ.get("SHELL") or "/bin/zsh", "-ic", shlex.join([command, *args])]


def tool_wrapper(module):
    return f'''#!/usr/bin/env python3
from pathlib import Path
import json, os, subprocess, sys
root = Path(__file__).resolve().parents[1]
config = json.loads((root / ".workshop/config.json").read_text())
if os.path.abspath(sys.executable) != os.path.abspath(config["python"]):
    raise SystemExit(subprocess.call([config["python"], __file__, *sys.argv[1:]], cwd=root))
os.chdir(root)
sys.path.insert(0, str(root / ".workshop/runtime"))
from workshop_core.{module} import main
raise SystemExit(main())
'''


def initialize(root, lab, api_base="http://127.0.0.1:8787"):
    if lab not in LABS:
        raise ValueError("Choose lab1, lab2 or lab3")
    root = Path(root).resolve()
    if root.exists() and any(root.iterdir()):
        raise ValueError("기존 작업을 덮어쓰지 않습니다. 빈 새 디렉터리를 선택하세요.")
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(KIT / "workshop_core", root / ".workshop/runtime/workshop_core",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    support = root / ".workshop/support-plugin"
    (support / "skills").mkdir(parents=True)
    shutil.copytree(KIT / "coach/skills/workshop-coach", support / "skills/workshop-coach")
    if lab == "lab3":
        shutil.copytree(KIT / "coach/skills/prompt-coach", support / "skills/prompt-coach")
    write_json(support / ".claude-plugin/plugin.json", {
        "name": "workshop", "version": "2.0.0", "description": "Workshop guidance and supplied prompt coach"})
    write_json(root / "learner-plugin/.claude-plugin/plugin.json", {
        "name": "my-team", "version": "0.1.0", "description": "Skills created by the workshop participant"})
    (root / "learner-plugin/skills").mkdir(exist_ok=True)
    shutil.copytree(KIT / "materials/inputs", root / "inputs")
    if lab == "lab1":
        shutil.copytree(KIT / "materials/starters", root / "materials/starters")
    if lab == "lab2":
        shutil.copyfile(KIT / "docs/API.md", root / "API.md")
    if lab == "lab3":
        shutil.copytree(KIT / "materials/inspection-target", root / "inspection-target")
        shutil.copyfile(KIT / "materials/original-prompt.txt", root / "inputs/original-prompt.txt")
    shutil.copyfile(KIT / "docs/worksheets" / f"{lab}.md", root / "worksheet.md")
    shutil.copyfile(KIT / "docs/labs" / f"{lab}.md", root / "README.md")
    shutil.copyfile(KIT / "coach/CLAUDE.md", root / "CLAUDE.md")
    write_json(root / ".workshop/config.json", {
        "lab": lab, "api_base": api_base, "python": sys.executable,
        "launcher": "claude", "version": "2.0.0", "kit_directory": str(KIT)})
    write_json(root / ".claude/settings.json", {
        "permissions": {"deny": ["Read(.env*)"]}})
    (root / ".gitignore").write_text(
        ".workshop/\n.env*\n.claude/settings.local.json\nartifacts/\nmeasurements/\n"
        "__pycache__/\n.venv/\n", encoding="utf-8")
    (root / "artifacts").mkdir()
    (root / "tools").mkdir()
    (root / "tools/check.py").write_text(tool_wrapper("checks"), encoding="utf-8")
    if lab == "lab2":
        (root / "tools/api.py").write_text(tool_wrapper("client"), encoding="utf-8")
    if lab == "lab3":
        (root / "tools/compare.py").write_text(tool_wrapper("measure"), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=Workshop",
                    "-c", "user.email=workshop@example.invalid",
                    "commit", "-qm", "lab: provided materials; learner skills start empty"], check=True)
    return {"workspace": str(root), "lab": lab, "title": LABS[lab],
            "first_prompt": f"/workshop:workshop-coach {lab}",
            "next": shlex.join([sys.executable, str(KIT / "workshop.py"), "run", "--workspace", str(root)])}


def configure(root, token, api_base=None):
    root = Path(root).resolve()
    path = root / ".workshop/config.json"
    config = json.loads(path.read_text())
    if config["lab"] != "lab2":
        raise ValueError("API 설정은 lab2에만 필요합니다.")
    if not token or any(c in token for c in "\r\n") or not 8 <= len(token) <= 200:
        raise ValueError("유효한 실습 토큰을 입력하세요.")
    if api_base:
        config["api_base"] = api_base
    token_file = root / ".env.local"
    if token_file.is_symlink():
        raise ValueError("토큰 파일의 심볼릭 링크는 덮어쓰지 않습니다.")
    fd = os.open(token_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w") as f:
        f.write("LAB_TOKEN=" + token + "\n")
    os.chmod(token_file, 0o600)
    write_json(path, config)
    return {"configured": True, "api_base": config["api_base"], "token": "stored locally; not displayed"}


def run(root, command, extra):
    root = Path(root).resolve()
    config_path = root / ".workshop/config.json"
    config = json.loads(config_path.read_text())
    config["launcher"] = command
    write_json(config_path, config)
    args = ["--plugin-dir", str(root / ".workshop/support-plugin"),
            "--plugin-dir", str(root / "learner-plugin"), *extra]
    env = os.environ.copy()
    env["PATH"] = str(Path(config["python"]).parent) + os.pathsep + env.get("PATH", "")
    return subprocess.call(launcher(command, args), cwd=root, env=env)
