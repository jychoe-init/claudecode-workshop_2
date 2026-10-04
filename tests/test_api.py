import concurrent.futures
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from workshop_core.api import ApiError, handle, token_hash


def call(server, method, path, body=None, token="participant-token-a"):
    req = Request(server.base_url + path, method=method,
                  data=None if body is None else json.dumps(body).encode(),
                  headers={"Content-Type": "application/json", "Authorization": "Bearer " + token})
    try:
        with urlopen(req, timeout=5) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def submission(key="first-request", start="2030-04-08", end="2030-04-09"):
    return {"start_date": start, "end_date": end, "leave_type": "annual", "request_key": key}


def test_actual_http_full_workflow_and_replay(service):
    assert call(service, "GET", "/v1/me")[1]["participant_id"] == "p001"
    assert call(service, "GET", "/v1/leave")[1]["available_days"] == 12
    code, result = call(service, "POST", "/v1/leave/requests", submission())
    assert code == 201 and result["request"]["status"] == "pending"
    request_id = result["request"]["id"]
    assert result["balance"]["pending_days"] == 2 and result["balance"]["used_days"] == 0
    assert call(service, "GET", "/v1/leave/requests/" + request_id)[1]["request"] == result["request"]
    replay = call(service, "POST", "/v1/leave/requests", submission())
    assert replay[0] == 200 and replay[1]["created"] is False
    assert call(service, "GET", "/v1/leave")[1]["available_days"] == 10
    assert len(call(service, "GET", "/v1/leave/requests?request_key=first-request")[1]["requests"]) == 1


def test_isolation_and_registered_tokens(service):
    assert call(service, "GET", "/v1/me", token="valid-looking-but-not-issued")[0] == 401
    request_id = call(service, "POST", "/v1/leave/requests", submission())[1]["request"]["id"]
    assert call(service, "GET", "/v1/leave/requests/" + request_id, token="participant-token-b")[0] == 404
    assert call(service, "GET", "/v1/leave", token="participant-token-b")[1]["available_days"] == 12
    assert "participant-token-a" not in service.store.path.read_bytes().decode(errors="ignore")


@pytest.mark.parametrize("change", [
    {"start_date": "invalid"}, {"start_date": "2020-01-01"}, {"end_date": "2030-04-07"},
    {"start_date": "2030-04-06"}, {"end_date": "2030-04-19"},
    {"leave_type": "approve"}, {"request_key": "x"}, {"employee_id": "other"},
])
def test_invalid_submissions_do_not_change_state(service, change):
    assert call(service, "POST", "/v1/leave/requests", {**submission(), **change})[0] == 400
    assert call(service, "GET", "/v1/leave/requests")[1]["requests"] == []


def test_overlap_key_conflict_and_concurrency(service):
    first = call(service, "POST", "/v1/leave/requests", submission())
    assert first[0] == 201
    assert call(service, "POST", "/v1/leave/requests", submission("different-key"))[1]["error"] == "overlapping_request"
    assert call(service, "POST", "/v1/leave/requests", {**submission(), "note": "changed"})[1]["error"] == "request_key_conflict"
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        result = list(pool.map(lambda _: call(service, "POST", "/v1/leave/requests", submission()), range(6)))
    assert all(r[0] == 200 and not r[1]["created"] for r in result)
    assert len(call(service, "GET", "/v1/leave/requests")[1]["requests"]) == 1


def test_concurrent_different_requests_cannot_overbook(service):
    bodies = [submission("request-week-" + str(i), start, end) for i, (start, end) in enumerate([
        ("2030-05-06", "2030-05-10"), ("2030-05-13", "2030-05-17"), ("2030-05-20", "2030-05-24")
    ])]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda body: call(service, "POST", "/v1/leave/requests", body), bodies))
    assert sorted(code for code, _ in results) == [201, 201, 409]
    assert call(service, "GET", "/v1/leave")[1]["available_days"] == 2


def test_rate_limit_and_next_window(service):
    headers = {"Authorization": "Bearer participant-token-a"}
    for _ in range(60):
        assert handle(service.store, "GET", "/v1/me", headers, now=600)[0] == 200
    with pytest.raises(ApiError) as caught:
        handle(service.store, "GET", "/v1/me", headers, now=600)
    assert caught.value.status == 429
    assert handle(service.store, "GET", "/v1/me", headers, now=660)[0] == 200


def test_empty_key_lookup_and_compact_dates_are_rejected(service):
    assert call(service, "GET", "/v1/leave/requests?request_key=")[0] == 400
    assert call(service, "POST", "/v1/leave/requests", {**submission(), "start_date": "20300408"})[0] == 400
