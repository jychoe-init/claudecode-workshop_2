#!/usr/bin/env python3
"""Issue isolated fictional accounts after an explicitly approved deployment."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

import boto3
from boto3.dynamodb.types import TypeSerializer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workshop_core.api import initial_state

EXPECTED_ACCOUNT = "135808921005"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="ap-northeast-2")
    parser.add_argument("--stack", default="claudecode-workshop-2")
    parser.add_argument("--count", type=int, default=80)
    parser.add_argument("--out", default=".local/tokens.csv")
    args = parser.parse_args()
    if not 1 <= args.count <= 100:
        raise ValueError("count must be 1–100")
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    if session.client("sts").get_caller_identity()["Account"] != EXPECTED_ACCOUNT:
        raise ValueError("Refusing to issue accounts outside the reviewed target account")
    stack = session.client("cloudformation").describe_stacks(StackName=args.stack)["Stacks"][0]
    outputs = {x["OutputKey"]: x["OutputValue"] for x in stack["Outputs"]}
    table = outputs["TableName"]
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Never overwrite the only record of an earlier token batch.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    client = session.client("dynamodb")
    serializer = TypeSerializer()
    batch = secrets.token_hex(4)
    issued = 0
    with os.fdopen(fd, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["participant_id", "lab_token", "api_base"])
        for i in range(args.count):
            participant = f"p-{batch}-{i + 1:03}"
            token = secrets.token_urlsafe(32)
            rows = [
                {"pk": "TOKEN#" + hashlib.sha256(token.encode()).hexdigest(),
                 "participant": participant, "active": True},
                {"pk": "PARTICIPANT#" + participant, "data": initial_state()},
            ]
            client.transact_write_items(TransactItems=[
                {"Put": {"TableName": table,
                         "Item": {k: serializer.serialize(v) for k, v in row.items()},
                         "ConditionExpression": "attribute_not_exists(pk)"}} for row in rows
            ])
            writer.writerow([participant, token, outputs["ApiBase"]])
            f.flush()
            os.fsync(f.fileno())
            issued += 1
    print(json.dumps({"issued": issued, "csv": str(destination.resolve()),
                      "api_base": outputs["ApiBase"], "tokens_printed": False}))


if __name__ == "__main__":
    main()
