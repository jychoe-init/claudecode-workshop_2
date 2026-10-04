"""Read-only structural checks. These do not grade a learner's business judgment."""
import json
import hashlib
from pathlib import Path
import subprocess

import yaml


def inspect_workspace(root):
    root = Path(root).resolve()
    config = json.loads((root / ".workshop/config.json").read_text())
    findings, skills = [], []
    for path in (root / "learner-plugin/skills").glob("*/SKILL.md"):
        item = {"file": str(path.relative_to(root)), "valid": False}
        try:
            text = path.read_text()
            front, body = text.removeprefix("---\n").split("\n---\n", 1)
            meta = yaml.safe_load(front)
            if not text.startswith("---\n") or not isinstance(meta, dict):
                raise ValueError("YAML frontmatter required")
            if not meta.get("name") or not meta.get("description") or not body.strip():
                raise ValueError("name, description and body required")
            item.update(valid=True, name=meta["name"])
        except (ValueError, yaml.YAMLError) as exc:
            item["problem"] = str(exc)
        skills.append(item)
    if not skills and config["lab"] != "lab3":
        findings.append("학습자가 만들 스킬이 아직 없습니다. 시작·힌트 단계에서는 정상입니다.")
    tracked = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
    leaked = [p for p in tracked if p.startswith((".env", ".workshop/", "artifacts/", "measurements/"))
              or p.endswith("settings.local.json")]
    if leaked:
        findings.append("공유 대상에서 제외할 로컬 파일: " + ", ".join(leaked))
    measurement = root / "measurements/comparison.json"
    comparison = json.loads(measurement.read_text()) if measurement.is_file() else None
    current_comparison = None
    if comparison:
        from .measure import input_fingerprint
        try:
            current_comparison = bool(comparison["comparable"])
            for label, item in zip(("original_file", "improved_file"), comparison["runs"]):
                prompt_path = (root / comparison[label]).resolve()
                response_path = (root / item["response"]).resolve()
                current_comparison = current_comparison and (
                    prompt_path.is_relative_to(root) and response_path.is_relative_to(root)
                    and hashlib.sha256(prompt_path.read_bytes()).hexdigest() == item["prompt_sha256"]
                    and hashlib.sha256(response_path.read_bytes()).hexdigest() == item["response_sha256"]
                    and input_fingerprint(root / "inputs") == item["inputs_sha256"])
        except (OSError, KeyError, ValueError):
            current_comparison = False
        if not current_comparison:
            findings.append("현재 파일에 유효한 비교 결과가 아닙니다. 입력·출력·모델 조건을 확인하세요.")
    return {"lab": config["lab"], "skills": skills, "findings": findings,
            "comparison_available": bool(comparison),
            "comparison_valid": current_comparison,
            "api_write_performed": False,
            "remaining_human_review": [
                "워크시트의 기준·예측과 실제 결과를 비교하세요.",
                "스킬 호출 출처와 현재 파일 버전을 확인하세요.",
                "이 검사는 업무 품질이나 학습 완료를 자동 판정하지 않습니다."]}


def main(argv=None):
    print(json.dumps(inspect_workspace(Path.cwd()), ensure_ascii=False, indent=2))
    return 0
