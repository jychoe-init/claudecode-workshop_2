"""Shared business contract for the local server and Lambda adapter.

All records are fictional training data. This is not a company's leave policy.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import re
import secrets
from urllib.parse import parse_qs, urlsplit


class ApiError(Exception):
    def __init__(self, status, code, message, **details):
        super().__init__(message)
        self.status = status
        self.payload = {"error": code, "message": message, **details}


def initial_state():
    return {"annual_days": 12, "used_days": 0, "requests": [], "revision": 0}


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def balance(state):
    pending = sum(x["days"] for x in state["requests"] if x["status"] == "pending")
    return {"annual_days": state["annual_days"], "used_days": state["used_days"],
            "pending_days": pending,
            "available_days": state["annual_days"] - state["used_days"] - pending}


def normalize_request(body, today):
    if not isinstance(body, dict):
        raise ApiError(400, "invalid_body", "JSON object가 필요합니다.")
    fields = {"start_date", "end_date", "leave_type", "request_key", "note"}
    if set(body) - fields:
        raise ApiError(400, "unknown_fields", "명세에 없는 필드입니다.",
                       fields=sorted(set(body) - fields))
    if any(not isinstance(body.get(k), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", body[k])
           for k in ("start_date", "end_date")):
        raise ApiError(400, "invalid_date", "start_date와 end_date는 YYYY-MM-DD입니다.")
    try:
        start = date.fromisoformat(body["start_date"])
        end = date.fromisoformat(body["end_date"])
    except (ValueError, TypeError, KeyError):
        raise ApiError(400, "invalid_date", "start_date와 end_date는 YYYY-MM-DD입니다.")
    if start < today or end < start or (end - start).days > 31:
        raise ApiError(400, "invalid_range", "과거 날짜, 역순, 31일 초과 범위는 신청할 수 없습니다.")
    if start.weekday() >= 5 or end.weekday() >= 5:
        raise ApiError(400, "weekend_boundary", "실습에서는 시작일과 종료일을 평일로 지정하세요.")
    days = sum((start + timedelta(days=i)).weekday() < 5 for i in range((end - start).days + 1))
    if days > 5:
        raise ApiError(400, "request_limit", "실습 정책상 한 번에 최대 5 근무일입니다.")
    if body.get("leave_type") != "annual":
        raise ApiError(400, "invalid_type", "실습에서 지원하는 leave_type은 annual입니다.")
    key = body.get("request_key")
    if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", key):
        raise ApiError(400, "invalid_request_key", "8–80자의 영문·숫자·밑줄·하이픈 request_key가 필요합니다.")
    note = body.get("note", "")
    if not isinstance(note, str) or len(note) > 400:
        raise ApiError(400, "invalid_note", "note는 400자 이하 문자열입니다.")
    return {"start_date": start.isoformat(), "end_date": end.isoformat(),
            "leave_type": "annual", "request_key": key, "note": note, "days": days}


def submit(state, normalized):
    for previous in state["requests"]:
        if previous["request_key"] == normalized["request_key"]:
            if any(previous[k] != v for k, v in normalized.items()):
                raise ApiError(409, "request_key_conflict", "같은 request_key에 다른 내용을 제출했습니다.",
                               existing_request_id=previous["id"])
            return state, {"request": previous, "created": False, "balance": balance(state)}, 200
    for previous in state["requests"]:
        if previous["status"] in {"pending", "approved"} and (
            previous["start_date"] <= normalized["end_date"] and
            previous["end_date"] >= normalized["start_date"]
        ):
            raise ApiError(409, "overlapping_request", "해당 기간에 기존 신청이 있습니다.",
                           existing_request_id=previous["id"])
    if normalized["days"] > balance(state)["available_days"]:
        raise ApiError(409, "insufficient_balance", "가용 휴가가 부족합니다.", **balance(state))
    request = {**normalized, "id": "lr_" + secrets.token_hex(8), "status": "pending"}
    next_state = {**state, "requests": [*state["requests"], request],
                  "revision": state["revision"] + 1}
    return next_state, {"request": request, "created": True, "balance": balance(next_state)}, 201


def handle(store, method, raw_path, headers, body=None, *, today=None, now=None):
    today = today or datetime.now(timezone(timedelta(hours=9))).date()
    parts = urlsplit(raw_path)
    path = parts.path.rstrip("/") or "/"
    if method == "GET" and path == "/health":
        return 200, {"status": "ok", "service": "fictional-workshop-api", "version": "2.0.0"}
    normalized_headers = {str(k).lower(): v for k, v in headers.items()}
    auth = normalized_headers.get("authorization", "")
    if not isinstance(auth, str) or not auth.startswith("Bearer "):
        raise ApiError(401, "unauthorized", "실습 토큰이 필요합니다.")
    token = auth[7:]
    if not 8 <= len(token) <= 200:
        raise ApiError(401, "unauthorized", "유효한 실습 토큰이 필요합니다.")
    hashed = token_hash(token)
    participant = store.authenticate(hashed)
    if not participant:
        raise ApiError(401, "unauthorized", "등록된 실습 토큰이 아닙니다.")
    store.rate_limit(hashed, now=now)
    if method == "GET" and path == "/v1/me":
        return 200, {"participant_id": participant, "employee_id": "self",
                     "as_of": today.isoformat(), "data_kind": "fictional"}
    if method == "GET" and path == "/v1/leave/policy":
        return 200, {"as_of": today.isoformat(), "leave_types": ["annual"],
                     "max_days_per_request": 5, "unit": "whole_business_day",
                     "business_days": "Monday–Friday; no real holiday calendar",
                     "pending_reserves_balance": True,
                     "submission_status": "pending", "data_kind": "fictional"}
    if method == "GET" and path == "/v1/leave":
        return 200, balance(store.read(participant))
    if method == "GET" and path == "/v1/leave/requests":
        requests = store.read(participant)["requests"]
        query = parse_qs(parts.query, keep_blank_values=True)
        if set(query) - {"request_key"} or any(len(v) != 1 for v in query.values()):
            raise ApiError(400, "invalid_query", "request_key 하나로만 조회할 수 있습니다.")
        if "request_key" in query:
            if not re.fullmatch(r"[A-Za-z0-9_-]{8,80}", query["request_key"][0]):
                raise ApiError(400, "invalid_request_key", "조회할 request_key가 유효하지 않습니다.")
            requests = [r for r in requests if r["request_key"] == query["request_key"][0]]
        return 200, {"requests": requests}
    if method == "GET" and path.startswith("/v1/leave/requests/"):
        request_id = path.rsplit("/", 1)[-1]
        item = next((x for x in store.read(participant)["requests"] if x["id"] == request_id), None)
        if item is None:
            raise ApiError(404, "not_found", "이 실습 계정의 신청을 찾을 수 없습니다.")
        return 200, {"request": item}
    if method == "POST" and path == "/v1/leave/requests":
        normalized = normalize_request(body, today)
        return store.mutate(participant, lambda state: submit(state, normalized))
    raise ApiError(404, "not_found", "지원하지 않는 실습 API 경로입니다.")
