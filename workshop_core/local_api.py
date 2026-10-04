from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import time

from .api import ApiError, handle, initial_state, token_hash


class LocalStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tokens (hash TEXT PRIMARY KEY, participant TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS participants (id TEXT PRIMARY KEY, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, count INTEGER NOT NULL);
            """)

    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def register(self, token, participant):
        with self.connect() as db:
            db.execute("INSERT INTO tokens VALUES (?, ?)", (token_hash(token), participant))
            db.execute("INSERT OR IGNORE INTO participants VALUES (?, ?)",
                       (participant, json.dumps(initial_state())))

    def authenticate(self, hashed):
        with self.connect() as db:
            row = db.execute("SELECT participant FROM tokens WHERE hash=?", (hashed,)).fetchone()
            return row[0] if row else None

    def rate_limit(self, hashed, now=None):
        minute = int((time.time() if now is None else now) // 60)
        key = f"{hashed}:{minute}"
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT count FROM limits WHERE key=?", (key,)).fetchone()
            if row and row[0] >= 60:
                raise ApiError(429, "rate_limited", "토큰당 분당 60회 제한입니다.", retry_after=60)
            db.execute("INSERT INTO limits VALUES (?, 1) ON CONFLICT(key) DO UPDATE SET count=count+1", (key,))
            db.execute("DELETE FROM limits WHERE key NOT LIKE ? AND key LIKE ?", (f"%:{minute}", f"{hashed}:%"))

    def read(self, participant):
        with self.connect() as db:
            row = db.execute("SELECT data FROM participants WHERE id=?", (participant,)).fetchone()
            if row is None:
                raise ApiError(404, "not_found", "실습 계정이 준비되지 않았습니다.")
            return json.loads(row[0])

    def mutate(self, participant, operation):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM participants WHERE id=?", (participant,)).fetchone()
            state, payload, status = operation(json.loads(row[0]))
            db.execute("UPDATE participants SET data=? WHERE id=?", (json.dumps(state), participant))
            return status, payload


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass  # No headers, query strings, tokens, prompts or employee records in access logs.

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def dispatch(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 8192:
                raise ApiError(413, "body_too_large", "최대 8192 bytes입니다.")
            body = None
            if self.command == "POST":
                if not self.headers.get("Content-Type", "").startswith("application/json"):
                    raise ApiError(415, "json_required", "Content-Type: application/json이 필요합니다.")
                try:
                    body = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeError):
                    raise ApiError(400, "invalid_json", "유효한 JSON 본문이 필요합니다.")
            status, payload = handle(self.server.store, self.command, self.path, dict(self.headers), body)
        except ApiError as exc:
            status, payload = exc.status, exc.payload
        except ValueError:
            status, payload = 400, {"error": "invalid_request", "message": "요청 형식이 잘못됐습니다."}
        encoded = (json.dumps(payload, ensure_ascii=False) + "\n").encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        if status == 429:
            self.send_header("Retry-After", "60")
        self.end_headers()
        self.wfile.write(encoded)


class LabServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store):
        super().__init__(address, Handler)
        self.store = store

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.server_port}"
