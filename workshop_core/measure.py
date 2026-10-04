"""Compare two read-only document prompts using observed Claude CLI results."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
import uuid

from .workspace import launcher, write_json


def parse_stream(text):
    records, replies, tools = [], [], []
    decoder = json.JSONDecoder()
    for line in text.splitlines():
        start = line.find("{")
        if start < 0:
            continue
        try:
            value, _ = decoder.raw_decode(line[start:])
        except ValueError:
            continue
        if not isinstance(value, dict):
            continue
        records.append(value)
        if value.get("type") == "assistant":
            for part in value.get("message", {}).get("content", []):
                if part.get("type") == "text":
                    replies.append(part["text"])
                if part.get("type") == "tool_use":
                    tools.append({"name": part["name"], "input": part.get("input", {})})
    result = next((v for v in reversed(records) if v.get("type") == "result"), {})
    init = next((v for v in records if v.get("type") == "system" and v.get("subtype") == "init"), {})
    return {"result": result, "init": init, "text": "\n\n".join(replies), "tools": tools}


def input_fingerprint(directory):
    entries = {}
    for p in sorted(directory.rglob("*")):
        if p.is_symlink():
            raise ValueError("비교 입력은 로컬 일반 파일이어야 합니다.")
        if p.is_file():
            entries[str(p.relative_to(directory))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def trial(root, variant, prompt, command, model, out, timeout, effort="medium"):
    destination = out / variant
    destination.mkdir()
    shutil.copytree(root / "inputs", destination / "inputs")
    before = input_fingerprint(destination / "inputs")
    args = ["--print", "--verbose", "--output-format", "stream-json", "--no-session-persistence",
            "--setting-sources", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--disable-slash-commands", "--permission-mode", "dontAsk",
            "--tools", "Read,Glob,Grep", "--allowedTools", "Read,Glob,Grep",
            "--effort", effort, "--max-budget-usd", "3"]
    if model:
        args.extend(["--model", model])
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)  # Explicit independent headless trial, not a resumed parent session.
    start = time.monotonic()
    proc = subprocess.Popen(launcher(command, args), cwd=destination, env=env,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            stdout, stderr = proc.communicate()
    parsed = parse_stream(stdout)
    result = parsed["result"]
    usage = result.get("usage") or {}
    models = sorted((result.get("modelUsage") or {}).keys())
    if not models and parsed["init"].get("model"):
        models = [parsed["init"]["model"]]
    (destination / "stdout.jsonl").write_text(stdout, encoding="utf-8")
    (destination / "stderr.txt").write_text(stderr, encoding="utf-8")
    (destination / "response.md").write_text(parsed["text"], encoding="utf-8")
    (destination / "prompt.txt").write_text(prompt, encoding="utf-8")
    summary = {
        "variant": variant, "run_id": out.name, "models": models,
        "effort": effort,
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "inputs_sha256": before,
        "input_files_unchanged": before == input_fingerprint(destination / "inputs"),
        "completed": proc.returncode == 0 and not timed_out and result.get("is_error") is False,
        "exit_code": proc.returncode, "timed_out": timed_out,
        "duration_seconds": round(time.monotonic() - start, 3),
        "cli_estimated_cost_usd": result.get("total_cost_usd"),
        "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "response": str((destination / "response.md").relative_to(root)),
        "response_sha256": hashlib.sha256((destination / "response.md").read_bytes()).hexdigest(),
    }
    write_json(destination / "summary.json", summary)
    return summary


def compare(root, original, improved, *, command=None, model=None, timeout=180, effort="medium"):
    root = Path(root).resolve()
    config = json.loads((root / ".workshop/config.json").read_text())
    original_path, improved_path = (root / original).resolve(), (root / improved).resolve()
    if not original_path.is_relative_to(root) or not improved_path.is_relative_to(root):
        raise ValueError("프롬프트 파일은 현재 작업 공간 안에 두세요.")
    original_text, improved_text = original_path.read_text(), improved_path.read_text()
    if not original_text.strip() or not improved_text.strip():
        raise ValueError("비교할 두 프롬프트를 작성하세요.")
    out = root / "measurements" / uuid.uuid4().hex
    out.mkdir(parents=True)
    results = [trial(root, name, prompt, command or config["launcher"], model, out, timeout, effort)
               for name, prompt in [("original", original_text), ("improved", improved_text)]]
    comparable = (all(r["completed"] and r["input_files_unchanged"] and r["models"] for r in results)
                  and results[0]["models"] == results[1]["models"]
                  and results[0]["inputs_sha256"] == results[1]["inputs_sha256"])
    report = {"runs": results, "comparable": bool(comparable),
              "original_file": str(original_path.relative_to(root)),
              "improved_file": str(improved_path.relative_to(root)),
              "coach_cost_usd": None, "coach_cost_status": "not_measured_separately",
              "quality_status": "participant_review_required",
              "scope": "read-only document task; no file edits, API writes, MCP or user skills",
              "interpretation": "단일 쌍의 관측입니다. 캐시 차이를 함께 보세요. CLI 추정 비용은 실제 청구액이 아닙니다."}
    write_json(out / "comparison.json", report)
    write_json(root / "measurements/comparison.json", report)
    fields = ["run_id", "variant", "models", "effort", "duration_seconds", "cli_estimated_cost_usd",
              "input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens",
              "completed", "prompt_sha256", "inputs_sha256"]
    with (out / "usage.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in results:
            writer.writerow({k: item.get(k) for k in fields})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True)
    parser.add_argument("--improved", required=True)
    parser.add_argument("--command")
    parser.add_argument("--model")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--effort", choices=["low", "medium", "high"], default="medium")
    args = parser.parse_args(argv)
    try:
        report = compare(Path.cwd(), args.original, args.improved,
                         command=args.command, model=args.model, timeout=args.timeout, effort=args.effort)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["comparable"] else 2
    except (OSError, ValueError) as exc:
        print("Compare error: " + str(exc))
        return 2
