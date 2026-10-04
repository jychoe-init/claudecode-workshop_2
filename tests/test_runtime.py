import asyncio
import concurrent.futures
import csv
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from workshop_lab.cli import hook, initialize, stage_standup
from workshop_lab.store import Store
from workshop_lab.telemetry import ingest

ROOT = Path(__file__).resolve().parents[1]


def request(service, path, data=None, *, token="test-token"):
    req = urllib.request.Request(service.base_url + path,
        data=None if data is None else json.dumps(data).encode(),
        headers={"Content-Type": "application/json", "X-Superlab-Token": token})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if body.startswith("{") else body
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def test_local_server_denies_untrusted_requests(service):
    assert request(service, "/api/hr/balance", token="bad")[0] == 401
    assert request(service, "/hooks/stop", {}, token="bad")[0] == 401


def test_standup_requires_explicit_matching_outbox_and_deduplicates(service):
    event = {"hook_event_name": "Stop", "session_id": "s", "prompt_id": "p",
             "last_assistant_message": "Do NOT send this unrelated text"}
    assert request(service, "/hooks/stop", event) == (200, {})
    assert not any(x["kind"] == "mock_slack_received" for x in service.store.rows("events"))
    status, row = request(service, "/outbox", {"session_id": "s", "prompt_id": "p", "text": "Final standup"})
    assert status == 200
    assert request(service, "/hooks/stop", {**event, "prompt_id": "other"}) == (200, {})
    assert request(service, "/hooks/stop", {**event, "agent_id": "background"}) == (200, {})
    assert not any(x["kind"] == "mock_slack_received" for x in service.store.rows("events"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: request(service, "/hooks/stop", event), range(6)))
    assert all(status == 200 for status, _ in results)
    sent = [x for x in service.store.rows("events") if x["kind"] == "mock_slack_received"]
    assert len(sent) == 1
    assert json.loads(sent[0]["payload"])["text"] == "Final standup"
    assert service.store.rows("outbox")[0]["state"] == "sent"
    assert request(service, "/outbox", {"session_id": "s", "prompt_id": "p", "text": "changed"})[0] == 400


def test_delivery_failure_is_recorded_without_automatic_resend(service):
    service.slack_url = service.base_url + "/mock/slack?mode=fail"
    request(service, "/outbox", {"session_id": "s", "prompt_id": "p", "text": "standup"})
    event = {"hook_event_name": "Stop", "session_id": "s", "prompt_id": "p"}
    status, result = request(service, "/hooks/stop", event)
    assert status == 200 and "failed" in result["systemMessage"]
    assert service.store.rows("outbox")[0]["state"] == "failed"
    request(service, "/hooks/stop", event)
    assert len([x for x in service.store.rows("events") if x["kind"] == "standup_delivery"]) == 1


def test_unknown_delivery_outcome_is_not_retried(service, monkeypatch):
    monkeypatch.setattr("workshop_lab.server.deliver", lambda *a, **k: ("uncertain", "timeout"))
    request(service, "/outbox", {"session_id": "s", "prompt_id": "p", "text": "standup"})
    event = {"hook_event_name": "Stop", "session_id": "s", "prompt_id": "p"}
    request(service, "/hooks/stop", event)
    request(service, "/hooks/stop", event)
    assert service.store.rows("outbox")[0]["state"] == "uncertain"
    assert len([x for x in service.store.rows("events") if x["kind"] == "standup_delivery"]) == 1


def test_hr_validation_state_and_idempotency(service):
    assert request(service, "/api/hr/balance")[1]["available_days"] == 12
    body = {"start_date": "2030-04-05", "days": 1.5, "request_key": "r1"}
    status, row = request(service, "/api/hr/requests", body)
    assert status == 200 and row["status"] == "pending" and row["created_now"]
    assert request(service, "/api/hr/balance")[1]["available_days"] == 10.5
    assert request(service, "/api/hr/requests", body)[1]["created_now"] is False
    assert request(service, "/api/hr/requests", {**body, "request_key": "r2"})[1]["id"] == row["id"]
    assert request(service, "/api/hr/requests", {**body, "days": 2})[0] == 400
    for value in [0, -1, True, "nan", 0.3, 99]:
        assert request(service, "/api/hr/requests", {**body, "days": value, "request_key": "bad"})[0] == 400
    assert len(service.store.rows("requests")) == 1


def test_hr_concurrent_requests_do_not_overbook(service):
    def run(index):
        return request(service, "/api/hr/requests",
                       {"start_date": f"2030-05-{index+1:02d}", "days": 8, "request_key": str(index)})
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, [0, 1]))
    assert sorted(x[0] for x in results) == [200, 400]
    assert request(service, "/api/hr/balance")[1]["available_days"] == 4


def api_envelope(sequence="1", input_tokens=100, cost="0.01"):
    values = {"session.id": "s", "prompt.id": "p", "event.sequence": sequence,
              "input_tokens": input_tokens, "output_tokens": 20,
              "cache_read_tokens": 30, "cache_creation_tokens": 10, "model": "lab-model",
              "cost_usd": cost, "duration_ms": 100,
              "user_prompt": "PRIVATE PROMPT MUST NOT BE STORED"}
    attributes = [{"key": k, "value": {"intValue" if isinstance(v, int) else "stringValue": v}}
                  for k, v in values.items()]
    return {"resourceLogs": [{"scopeLogs": [{"logRecords": [{
        "timeUnixNano": "1000000", "body": {"stringValue": "claude_code.api_request"},
        "attributes": attributes}]}]}]}


def test_otlp_dedup_redaction_and_snapshot_non_additivity(service, tmp_path):
    event = api_envelope()
    assert request(service, "/v1/logs", event)[0] == 200
    assert request(service, "/v1/logs", event)[0] == 200
    assert len(service.store.rows("telemetry")) == 1
    assert "PRIVATE" not in json.dumps(service.store.rows("telemetry"))
    ignored = api_envelope()
    ignored["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]["body"]["stringValue"] = "claude_code.agent.completed"
    assert ingest(service.store, ignored)["ignored"] == 1
    for cost in (0.02, 0.03, 0.03):
        request(service, "/status", {
            "session_id": "s", "model": {"id": "lab-model"},
            "context_window": {"total_input_tokens": 999999, "current_usage": {
                "input_tokens": 10, "cache_read_input_tokens": 5, "cache_creation_input_tokens": 4},
                "used_percentage": 1, "context_window_size": 200000},
            "cost": {"total_cost_usd": cost}})
    assert len(service.store.rows("snapshots")) == 2
    assert service.store.rows("snapshots")[0]["context_tokens"] == 19
    service.store.export(tmp_path / "csv")
    with (tmp_path / "csv/sessions.csv").open(encoding="utf-8-sig") as f:
        row = next(csv.DictReader(f))
    assert row["observed_api_requests"] == "1"
    assert float(row["observed_api_cost_usd"]) == 0.01


def test_otlp_protobuf_actual_http(service):
    from google.protobuf.json_format import ParseDict
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
    message = ParseDict(api_envelope(), ExportLogsServiceRequest())
    req = urllib.request.Request(service.base_url + "/v1/logs", data=message.SerializeToString(),
        headers={"Content-Type": "application/x-protobuf", "X-Superlab-Token": "test-token"})
    with urllib.request.urlopen(req) as response:
        assert response.status == 200 and response.read() == b""
    assert len(service.store.rows("telemetry")) == 1


def test_workspaces_are_portable_and_existing_work_is_not_overwritten(tmp_path, service):
    target = tmp_path / "folder with spaces"
    initialize(target, "S1", "complete", service.base_url, "test-token")
    with pytest.raises(ValueError):
        initialize(target, "S1", "complete", service.base_url, "test-token")
    hook("record-prompt", {"hook_event_name": "UserPromptSubmit", "session_id": "s", "prompt_id": "p",
                          "prompt": "Do not persist this"}, cwd=target)
    active = (target / ".superlab/active.json").read_text()
    assert "Do not persist" not in active
    report = target / "artifacts/standup.md"
    report.write_text("### 어제\n작업\n### 오늘\n미정\n### 확인 필요\n미확인\n")
    assert stage_standup(target, "artifacts/standup.md")["state"] == "pending"
    with pytest.raises(ValueError):
        stage_standup(target, "../outside.md")
    script = target / ".superlab/plugin/skills/standup/scripts/stage.py"
    run = subprocess.run([sys.executable, str(script), "artifacts/standup.md"],
                         cwd=target, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert subprocess.run(["npm", "test"], cwd=target, capture_output=True).returncode == 0


def test_init_rejects_external_receiver_without_creating_workspace(tmp_path):
    with pytest.raises(ValueError):
        initialize(tmp_path / "external", "S1", "complete", "https://example.com", "test")
    assert not (tmp_path / "external").exists()


def test_malformed_otlp_is_rejected(service):
    req = urllib.request.Request(service.base_url + "/v1/logs", data=b"not-protobuf",
        headers={"Content-Type": "application/x-protobuf", "X-Superlab-Token": "test-token"})
    with pytest.raises(urllib.error.HTTPError) as caught:
        urllib.request.urlopen(req)
    assert caught.value.code == 400


def test_diff_scope_and_empty_case(tmp_path):
    initialize(tmp_path / "repo", "S3", "complete", "http://127.0.0.1:8765", "test")
    root = tmp_path / "repo"
    script = root / ".superlab/plugin/skills/pr-desc/scripts/diff.py"
    result = json.loads(subprocess.check_output([sys.executable, str(script)], cwd=root))
    assert result["status"] == "ok" and "getUserLabel" in result["diff"]
    (root / "untracked.txt").write_text("must not be in staged diff")
    assert "untracked.txt" not in result["diff"]
    subprocess.run(["git", "reset", "-q", "HEAD"], cwd=root, check=True)
    assert json.loads(subprocess.check_output([sys.executable, str(script)], cwd=root))["status"] == "empty"


def test_profiles_are_cli_presets_and_do_not_claim_managed_policy(tmp_path):
    root = tmp_path / "repo"
    initialize(root, "S5", "complete", "http://127.0.0.1:8765", "test")
    base = json.loads((root / ".claude/settings.json").read_text())["permissions"]
    assert "mcp__hr__request_leave" not in base.get("ask", [])
    profiles = root / ".superlab/profiles"
    assert "mcp__hr__request_leave" in json.loads((profiles / "read-only.json").read_text())["permissions"]["deny"]
    assert "mcp__hr__request_leave" in json.loads((profiles / "assisted.json").read_text())["permissions"]["ask"]
    assert "mcp__hr__request_leave" in json.loads((profiles / "lab-automation.json").read_text())["permissions"]["allow"]


def test_real_mcp_stdio_transport_and_http_backend(service):
    def payload(result):
        if result.structuredContent is not None:
            return result.structuredContent
        return json.loads(next(item.text for item in result.content if item.type == "text"))

    async def exercise():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        params = StdioServerParameters(command=sys.executable,
            args=[str(ROOT / "plugin/runtime/mcp_entry.py")],
            env={**os.environ, "SUPERLAB_API_URL": service.base_url, "SUPERLAB_TOKEN": "test-token"})
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                assert names == {"get_leave_balance", "request_leave"}
                balance = await session.call_tool("get_leave_balance", {})
                assert not balance.isError and payload(balance)["available_days"] == 12
                missing = await session.call_tool("request_leave", {"days": 1})
                assert missing.isError and service.store.rows("requests") == []
                result = await session.call_tool("request_leave", {
                    "start_date": "2030-06-01", "days": 1, "request_key": "mcp-1"})
                assert not result.isError and payload(result)["status"] == "pending"
    asyncio.run(exercise())
    assert len(service.store.rows("requests")) == 1
