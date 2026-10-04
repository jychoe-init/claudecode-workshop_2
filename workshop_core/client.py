"""Authentication + one HTTP request only. No pre-built leave workflow or POST retries."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import uuid
from http.client import HTTPException
from urllib.request import HTTPRedirectHandler, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


urlopen = build_opener(NoRedirect()).open


def settings(workspace):
    root = Path(workspace).resolve()
    config = json.loads((root / ".workshop/config.json").read_text())
    token = os.environ.get("LAB_TOKEN")
    token_file = root / ".env.local"
    if token is None and token_file.is_file():
        for line in token_file.read_text().splitlines():
            if line.startswith("LAB_TOKEN="):
                token = line.partition("=")[2].strip()
                break
    base = os.environ.get("LAB_API_BASE") or config["api_base"]
    parts = urlsplit(base)
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("API base must not include credentials, query or fragment")
    if parts.scheme != "https" and not (parts.scheme == "http" and parts.hostname in {"localhost", "127.0.0.1"}):
        raise ValueError("Use HTTPS, or HTTP on localhost")
    if not token:
        raise ValueError("LAB_TOKEN is missing. Register it with workshop.py configure; do not paste it into Claude.")
    return base.rstrip("/"), token


def request(workspace, method, path, body=None, *, timeout=15):
    if not path.startswith("/v1/") or urlsplit(path).netloc or any(c in path for c in "\r\n"):
        raise ValueError("Use a relative /v1/ API path")
    base, token = settings(workspace)
    req = Request(base + path, method=method, data=None if body is None else json.dumps(body).encode(),
                  headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=timeout) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read())
        except (ValueError, UnicodeError):
            payload = {"error": "http_error", "message": "API가 JSON 오류 응답을 반환하지 않았습니다."}
        return exc.code, payload
    except (TimeoutError, URLError, OSError, ValueError, HTTPException):
        # A timed-out POST may have succeeded. Only the learner's workflow decides
        # what to do next, using GET .../requests?request_key=... as evidence.
        return 0, {"error": "outcome_unknown" if method == "POST" else "connection_failed",
                   "message": "응답을 확인하지 못했습니다. POST를 자동 재시도하지 않았습니다."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", choices=["get", "post", "key"])
    parser.add_argument("path", nargs="?")
    parser.add_argument("--json-file")
    args = parser.parse_args(argv)
    try:
        if args.method == "key":
            print(uuid.uuid4().hex)
            return 0
        if not args.path:
            raise ValueError("API path required")
        if args.method == "post" and not args.json_file:
            raise ValueError("POST requires --json-file")
        body = json.loads(Path(args.json_file).read_text()) if args.json_file else None
        status, payload = request(Path.cwd(), args.method.upper(), args.path, body)
        print(json.dumps({"http_status": status, **payload}, ensure_ascii=False, indent=2))
        return 0 if 200 <= status < 300 else 2
    except (OSError, ValueError) as exc:
        print("Client error: " + str(exc), file=sys.stderr)
        return 2
