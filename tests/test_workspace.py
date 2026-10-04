import json
from pathlib import Path
import subprocess
import sys

import pytest

from workshop_core import client
from workshop_core.checks import inspect_workspace
from workshop_core.measure import compare, parse_stream
from workshop_core.workspace import configure, initialize


@pytest.mark.parametrize("lab", ["lab1", "lab2", "lab3"])
def test_fresh_workspace_has_guidance_and_materials_not_finished_learner_skills(tmp_path, lab):
    root = tmp_path / "space in path" / lab
    initialize(root, lab)
    assert not list((root / "learner-plugin/skills").glob("*/SKILL.md"))
    support = root / ".workshop/support-plugin/skills"
    assert (support / "workshop-coach/SKILL.md").is_file()
    assert (support / "prompt-coach/SKILL.md").exists() == (lab == "lab3")
    assert not (root / ".mcp.json").exists()
    settings = json.loads((root / ".claude/settings.json").read_text())
    assert "hooks" not in settings and not (root / ".claude/profiles").exists()
    tracked = subprocess.check_output(["git", "ls-files"], cwd=root, text=True)
    assert ".workshop/" not in tracked
    with pytest.raises(ValueError):
        initialize(root, lab)
    result = subprocess.run([getattr(sys, "_base_executable", sys.executable), "tools/check.py"],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["api_write_performed"] is False


def test_api_client_uses_configured_token_without_printing_it(tmp_path, service, monkeypatch):
    root = tmp_path / "lab2"
    initialize(root, "lab2", service.base_url)
    monkeypatch.delenv("LAB_TOKEN", raising=False)
    configure(root, "participant-token-b")
    assert (root / ".env.local").stat().st_mode & 0o777 == 0o600
    result = subprocess.run([sys.executable, "tools/api.py", "get", "/v1/me"],
                            cwd=root, capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)["participant_id"] == "p002"
    assert "participant-token-b" not in result.stdout + result.stderr
    assert subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True) == ""


def test_post_timeout_is_not_automatically_retried(tmp_path, monkeypatch):
    root = tmp_path / "lab2"
    initialize(root, "lab2")
    configure(root, "a-local-test-token")
    calls = []
    def timeout(*args, **kwargs):
        calls.append(args)
        raise TimeoutError
    monkeypatch.setattr(client, "urlopen", timeout)
    status, body = client.request(root, "POST", "/v1/leave/requests", {"request_key": "same-key"})
    assert status == 0 and body["error"] == "outcome_unknown"
    assert len(calls) == 1
    with pytest.raises(ValueError):
        client.request(root, "GET", "https://outside.example/v1/me")


def fake_claude(tmp_path):
    path = tmp_path / "fake-claude"
    path.write_text("#!" + sys.executable + "\nimport json,sys\nsys.stdin.read()\n"
        "print(json.dumps({'type':'system','subtype':'init','model':'test-model'}))\n"
        "print(json.dumps({'type':'assistant','message':{'content':[{'type':'text','text':'Synthetic response'}]}}))\n"
        "print(json.dumps({'type':'result','is_error':False,'total_cost_usd':0.01,"
        "'usage':{'input_tokens':10,'output_tokens':20,'cache_read_input_tokens':30}}))\n")
    path.chmod(0o755)
    return path


def test_measurement_tracks_real_cli_fields_and_invalidates_changed_files(tmp_path):
    root = tmp_path / "lab3"
    initialize(root, "lab3")
    (root / "artifacts/improved.txt").write_text("Read inputs/meeting.txt and keep unknown owners unknown.")
    report = compare(root, "inputs/original-prompt.txt", "artifacts/improved.txt",
                     command=str(fake_claude(tmp_path)), timeout=10)
    assert report["comparable"] and report["coach_cost_usd"] is None
    assert report["runs"][0]["input_tokens"] == 10
    assert report["runs"][0]["cache_read_input_tokens"] == 30
    assert inspect_workspace(root)["comparison_valid"] is True
    (root / "artifacts/improved.txt").write_text("A different request")
    assert inspect_workspace(root)["comparison_valid"] is False


def test_stream_parser_handles_shell_prefix_and_no_measurement():
    parsed = parse_stream('\x1b]133;A\x07{"type":"result","is_error":false,"total_cost_usd":0.02}')
    assert parsed["result"]["total_cost_usd"] == 0.02
    assert parse_stream("authentication error")["result"] == {}


def test_token_registration_does_not_follow_symlink(tmp_path):
    root = tmp_path / "lab2"
    initialize(root, "lab2")
    outside = tmp_path / "existing.env"
    outside.write_text("KEEP=original\n")
    (root / ".env.local").symlink_to(outside)
    with pytest.raises(ValueError):
        configure(root, "new-training-token")
    assert outside.read_text() == "KEEP=original\n"
