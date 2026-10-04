"""Thin DynamoDB/Lambda adapter; build_template embeds the shared API contract."""
import base64
from decimal import Decimal
import json
import os
import time

import boto3
from botocore.exceptions import ClientError

from workshop_core.api import ApiError, handle


def plain(value):
    if isinstance(value, Decimal):
        return int(value)
    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [plain(v) for v in value]
    return value


class DynamoStore:
    def __init__(self, table):
        self.table = table

    def authenticate(self, hashed):
        item = self.table.get_item(Key={"pk": "TOKEN#" + hashed}, ConsistentRead=True).get("Item", {})
        return item.get("participant") if item.get("active") is True else None

    def rate_limit(self, hashed, now=None):
        timestamp = int(time.time() if now is None else now)
        try:
            self.table.update_item(
                Key={"pk": f"RATE#{hashed}#{timestamp // 60}"},
                UpdateExpression="SET expires = :expires ADD #n :one",
                ConditionExpression="attribute_not_exists(#n) OR #n < :limit",
                ExpressionAttributeNames={"#n": "count"},
                ExpressionAttributeValues={":expires": timestamp + 120, ":one": 1, ":limit": 60})
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ApiError(429, "rate_limited", "토큰당 분당 60회 제한입니다.", retry_after=60)
            raise

    def read(self, participant):
        item = self.table.get_item(Key={"pk": "PARTICIPANT#" + participant}, ConsistentRead=True).get("Item")
        if not item:
            raise ApiError(404, "not_found", "실습 계정이 준비되지 않았습니다.")
        return plain(item["data"])

    def mutate(self, participant, operation):
        for _ in range(8):
            previous = self.read(participant)
            next_state, payload, status = operation(previous)
            if next_state == previous:
                return status, payload
            try:
                self.table.put_item(
                    Item={"pk": "PARTICIPANT#" + participant, "data": next_state},
                    ConditionExpression="#d.#r = :revision",
                    ExpressionAttributeNames={"#d": "data", "#r": "revision"},
                    ExpressionAttributeValues={":revision": previous["revision"]})
                return status, payload
            except ClientError as exc:
                if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
                    raise
        raise ApiError(409, "concurrent_update", "다른 요청 처리와 겹쳤습니다. 현재 상태를 먼저 조회하세요.")


_store = None


def handler(event, context):
    global _store
    if _store is None:
        _store = DynamoStore(boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"]))
    try:
        method = event["requestContext"]["http"]["method"]
        path = event.get("rawPath", "/")
        if event.get("rawQueryString"):
            path += "?" + event["rawQueryString"]
        raw = event.get("body") or ""
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw)
        if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > 8192:
            raise ApiError(413, "body_too_large", "최대 8192 bytes입니다.")
        body = None
        headers = event.get("headers") or {}
        if method == "POST":
            if not next((v for k, v in headers.items() if k.lower() == "content-type"), "").startswith("application/json"):
                raise ApiError(415, "json_required", "Content-Type: application/json이 필요합니다.")
            try:
                body = json.loads(raw)
            except (ValueError, UnicodeError):
                raise ApiError(400, "invalid_json", "유효한 JSON 본문이 필요합니다.")
        status, payload = handle(_store, method, path, headers, body)
    except ApiError as exc:
        status, payload = exc.status, exc.payload
    response_headers = {"content-type": "application/json", "cache-control": "no-store"}
    if status == 429:
        response_headers["retry-after"] = "60"
    return {"statusCode": status, "headers": response_headers,
            "body": json.dumps(payload, ensure_ascii=False)}
