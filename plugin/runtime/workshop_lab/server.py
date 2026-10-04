from __future__ import annotations

import hmac
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .store import Store
from .telemetry import ingest, parse_otlp


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def deliver(url, text, timeout=5):
    req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=timeout) as response:
            body = response.read(4096).decode(errors="replace").strip()
            if 200 <= response.status < 300 and body == "ok":
                return "sent", "Slack-compatible receiver acknowledged"
            return "failed", f"unexpected receiver response: HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return "failed", f"receiver HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError):
        # A timeout may occur AFTER the external service accepted the message.
        return "uncertain", "Delivery outcome unknown; reconcile before any manual resend."


class LabServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, token, slack_url=None):
        self.store = store
        self.token = token
        self.slack_url = slack_url
        super().__init__(address, Handler)

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server_port}"


class Handler(BaseHTTPRequestHandler):
    server: LabServer

    def log_message(self, *_):
        pass  # Do not put secrets or payloads into access logs.

    def respond(self, status, value=None, *, plain=False):
        body = (str(value).encode() if plain else json.dumps(value or {}, ensure_ascii=False).encode())
        self.send_response(status)
        self.send_header("Content-Type", "text/plain" if plain else "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        value = self.headers.get("X-Superlab-Token", "")
        return hmac.compare_digest(value, self.server.token)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path)
        if path.path == "/health":
            return self.respond(200, {"status": "ok", "mode": "slack" if self.server.slack_url else "mock"})
        if not self.authorized():
            return self.respond(401, {"error": "lab token required"})
        try:
            if path.path == "/api/hr/balance":
                employee = urllib.parse.parse_qs(path.query).get("employee_id", ["demo-user"])[0]
                return self.respond(200, self.server.store.balance(employee))
            tables = {"/api/hr/requests": "requests", "/outbox": "outbox", "/events": "events"}
            if path.path in tables:
                return self.respond(200, {"items": self.server.store.rows(tables[path.path])})
            return self.respond(404, {"error": "not found"})
        except ValueError as exc:
            return self.respond(400, {"error": str(exc)})

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path)
        if path.path != "/mock/slack" and not self.authorized():
            return self.respond(401, {"error": "lab token required"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 2_000_000:
                return self.respond(413, {"error": "body size must be 1..2000000 bytes"})
            raw = self.rfile.read(length)
            if path.path == "/v1/logs":
                result = ingest(self.server.store, parse_otlp(raw, self.headers.get("Content-Type", "")))
                if "protobuf" in self.headers.get("Content-Type", ""):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-protobuf")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                return self.respond(200, {})
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("JSON object required")
            if path.path == "/mock/slack":
                if urllib.parse.parse_qs(path.query).get("mode") == ["fail"]:
                    return self.respond(503, "simulated_failure", plain=True)
                if not isinstance(data.get("text"), str) or not data["text"].strip():
                    return self.respond(400, "no_text", plain=True)
                self.server.store.event("mock_slack_received", {"text": data["text"]})
                return self.respond(200, "ok", plain=True)
            if path.path == "/api/hr/requests":
                result = self.server.store.request_leave(data.get("employee_id", "demo-user"),
                    data.get("start_date"), data.get("days"), data.get("request_key"))
                self.server.store.event("hr_request", {"id": result["id"], "created_now": result["created_now"]})
                return self.respond(200, result)
            if path.path == "/outbox":
                return self.respond(200, self.server.store.stage(
                    data.get("session_id"), data.get("prompt_id"), data.get("text")))
            if path.path == "/status":
                return self.respond(200, self.server.store.record_snapshot(data))
            if path.path == "/hooks/stop":
                if data.get("hook_event_name") != "Stop" or data.get("agent_id"):
                    return self.respond(200, {})
                session, prompt = data.get("session_id"), data.get("prompt_id")
                if not session or not prompt:
                    return self.respond(200, {})
                entry = self.server.store.claim(session, prompt)
                if not entry:
                    self.server.store.event("hook_ignored", {"session_id": session, "prompt_id": prompt,
                                                             "reason": "unarmed_or_already_consumed"})
                    return self.respond(200, {})
                target = self.server.slack_url or self.server.base_url + "/mock/slack"
                state, detail = deliver(target, entry["text"])
                self.server.store.finish(entry["id"], state, detail)
                self.server.store.event("standup_delivery", {"outbox_id": entry["id"], "state": state})
                if state == "sent":
                    return self.respond(200, {})
                return self.respond(200, {"systemMessage": f"Standup delivery {state}: {detail}"})
            return self.respond(404, {"error": "not found"})
        except (ValueError, TypeError, KeyError) as exc:
            self.respond(400, {"error": str(exc)[:300]})
        except ImportError:
            self.respond(415, {"error": "Install pinned requirements to receive OTLP protobuf."})
