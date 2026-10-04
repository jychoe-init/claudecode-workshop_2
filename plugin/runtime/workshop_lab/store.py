from __future__ import annotations

import csv
import hashlib
import json
import math
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def identity(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def finite_number(value, *, integer=False):
    if value is None or isinstance(value, bool):
        return None
    try:
        n = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(n) or n < 0 or (integer and not n.is_integer()):
        return None
    return int(n) if integer else n


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY, employee TEXT, start_date TEXT, days REAL,
                    request_key TEXT UNIQUE, status TEXT, created REAL,
                    UNIQUE(employee, start_date, days)
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    id TEXT PRIMARY KEY, session TEXT, prompt TEXT, text TEXT,
                    state TEXT, detail TEXT, created REAL, updated REAL,
                    UNIQUE(session, prompt)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY, kind TEXT, payload TEXT, created REAL
                );
                CREATE TABLE IF NOT EXISTS telemetry (
                    id TEXT PRIMARY KEY, kind TEXT, session TEXT, prompt TEXT,
                    run_id TEXT, module TEXT, model TEXT, timestamp TEXT,
                    input_tokens INTEGER, output_tokens INTEGER,
                    cache_read_tokens INTEGER, cache_write_tokens INTEGER,
                    cost_usd REAL, duration_ms REAL, data TEXT
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY, session TEXT, timestamp REAL,
                    context_tokens INTEGER, context_capacity INTEGER,
                    context_pct REAL, session_cost_usd REAL, model TEXT
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def event(self, kind, payload):
        with self.connect() as db:
            db.execute("INSERT INTO events(kind,payload,created) VALUES(?,?,?)",
                       (kind, canonical(payload), time.time()))

    def balance(self, employee):
        if employee != "demo-user":
            raise ValueError("Unknown demo employee")
        with self.connect() as db:
            reserved = db.execute(
                "SELECT COALESCE(SUM(days),0) FROM requests WHERE employee=? AND status='pending'",
                (employee,)).fetchone()[0]
        return {"employee_id": employee, "annual_balance_days": 12,
                "pending_reserved_days": reserved, "available_days": 12 - reserved,
                "policy": "Lab-only: pending requests reserve availability; no approval tool is provided."}

    def request_leave(self, employee, start, days, key):
        self.balance(employee)
        if not isinstance(start, str):
            raise ValueError("start_date must be an ISO date")
        date.fromisoformat(start)
        number = finite_number(days)
        if number is None or number == 0 or number * 2 != int(number * 2):
            raise ValueError("days must be a positive multiple of 0.5")
        if not isinstance(key, str) or not 1 <= len(key) <= 100:
            raise ValueError("request_key is required (1–100 characters)")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            same_key = db.execute("SELECT * FROM requests WHERE request_key=?", (key,)).fetchone()
            if same_key:
                if (same_key["employee"], same_key["start_date"], same_key["days"]) != (employee, start, number):
                    raise ValueError("request_key was already used with different arguments")
                return {**dict(same_key), "created_now": False}
            previous = db.execute(
                "SELECT * FROM requests WHERE employee=? AND start_date=? AND days=?",
                (employee, start, number)).fetchone()
            if previous:
                return {**dict(previous), "created_now": False}
            reserved = db.execute("SELECT COALESCE(SUM(days),0) FROM requests").fetchone()[0]
            if number > 12 - reserved:
                raise ValueError("Insufficient available days")
            request_id = "LEAVE-" + uuid.uuid4().hex[:10]
            db.execute("INSERT INTO requests VALUES(?,?,?,?,?,?,?)",
                       (request_id, employee, start, number, key, "pending", time.time()))
            row = db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            return {**dict(row), "created_now": True}

    def stage(self, session, prompt, text):
        if not all(isinstance(v, str) and v.strip() for v in (session, prompt, text)):
            raise ValueError("session_id, prompt_id and text are required")
        if len(text.encode()) > 16000:
            raise ValueError("standup payload exceeds 16 KB")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT * FROM outbox WHERE session=? AND prompt=?",
                             (session, prompt)).fetchone()
            if old:
                if old["text"] != text:
                    raise ValueError("A result is already staged for this prompt; use a new prompt")
                return dict(old)
            rid = uuid.uuid4().hex
            now = time.time()
            db.execute("INSERT INTO outbox VALUES(?,?,?,?,?,?,?,?)",
                       (rid, session, prompt, text, "pending", "", now, now))
            return dict(db.execute("SELECT * FROM outbox WHERE id=?", (rid,)).fetchone())

    def claim(self, session, prompt):
        """Only pending entries can start delivery. Unknown outcomes never auto-retry."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM outbox WHERE session=? AND prompt=?",
                             (session, prompt)).fetchone()
            if not row or row["state"] != "pending":
                return None
            db.execute("UPDATE outbox SET state='sending',updated=? WHERE id=?",
                       (time.time(), row["id"]))
            return dict(row)

    def finish(self, rid, state, detail=""):
        if state not in {"sent", "failed", "uncertain"}:
            raise ValueError("Invalid delivery state")
        with self.connect() as db:
            db.execute("UPDATE outbox SET state=?,detail=?,updated=? WHERE id=?",
                       (state, detail[:500], time.time(), rid))

    def rows(self, table):
        if table not in {"requests", "outbox", "events", "telemetry", "snapshots"}:
            raise ValueError("Unknown table")
        with self.connect() as db:
            return [dict(row) for row in db.execute(f"SELECT * FROM {table}")]

    def record_api(self, row):
        fields = ("id", "kind", "session", "prompt", "run_id", "module", "model",
                  "timestamp", "input_tokens", "output_tokens", "cache_read_tokens",
                  "cache_write_tokens", "cost_usd", "duration_ms", "data")
        with self.connect() as db:
            cursor = db.execute(
                "INSERT OR IGNORE INTO telemetry VALUES(" + ",".join("?" for _ in fields) + ")",
                tuple(row.get(k) for k in fields))
            return bool(cursor.rowcount)

    def record_snapshot(self, data):
        context = data.get("context_window") or {}
        usage = context.get("current_usage") or {}
        values = [finite_number(usage.get(k), integer=True)
                  for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")]
        context_tokens = sum(v or 0 for v in values) if any(v is not None for v in values) else None
        row = {
            "session": data.get("session_id", "unknown"),
            "timestamp": time.time(),
            "context_tokens": context_tokens,
            "context_capacity": finite_number(context.get("context_window_size"), integer=True),
            "context_pct": finite_number(context.get("used_percentage")),
            "session_cost_usd": finite_number((data.get("cost") or {}).get("total_cost_usd")),
            "model": (data.get("model") or {}).get("id", "unknown")
        }
        # Exclude timestamp from identity: status line may emit the same snapshot repeatedly.
        rid = identity({k: v for k, v in row.items() if k != "timestamp"})
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO snapshots VALUES(?,?,?,?,?,?,?,?)",
                       (rid, *row.values()))
        return row

    def export(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        summary = {}
        api_rows = self.rows("telemetry")
        for row in api_rows:
            if row["kind"] != "api_request":
                continue
            s = summary.setdefault(row["session"], {
                "session": row["session"], "observed_api_requests": 0,
                "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
                "cache_write_tokens": 0, "observed_api_cost_usd": 0.0,
                "requests_missing_cost": 0, "requests_missing_usage": 0,
                "coverage": "observed events only; not provider billing"})
            s["observed_api_requests"] += 1
            token_keys = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")
            for k in token_keys:
                s[k] += row[k] or 0
            if any(row[k] is None for k in token_keys[:2]):
                s["requests_missing_usage"] += 1
            if row["cost_usd"] is None:
                s["requests_missing_cost"] += 1
            else:
                s["observed_api_cost_usd"] += row["cost_usd"]
        tables = {"api_requests": api_rows, "status_snapshots": self.rows("snapshots"),
                  "sessions": list(summary.values())}
        for name, rows in tables.items():
            with (directory / f"{name}.csv").open("w", encoding="utf-8-sig", newline="") as f:
                keys = list(rows[0]) if rows else ["no_observations"]
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(rows)
        (directory / "coverage.json").write_text(canonical({
            "api_events": len(api_rows), "sessions": len(summary),
            "snapshots": len(tables["status_snapshots"]),
            "notes": ["Snapshots are NOT summed.", "Agent final-request tokens are NOT run totals.",
                      "Missing observations are not zero-cost proof."]}) + "\n")
        return {name: len(rows) for name, rows in tables.items()}
