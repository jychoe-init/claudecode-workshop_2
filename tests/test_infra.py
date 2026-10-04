import importlib.util
from pathlib import Path


def test_review_template_embeds_same_domain_and_scoped_permissions():
    path = Path(__file__).resolve().parents[1] / "infra/build_template.py"
    spec = importlib.util.spec_from_file_location("build_template", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    template = module.build()
    resources = template["Resources"]
    code = resources["Function"]["Properties"]["Code"]["ZipFile"]
    compile(code, "index.py", "exec")
    assert "def normalize_request" in code and "def submit" in code
    assert resources["Function"]["Properties"]["Environment"]["Variables"] == {"TABLE_NAME": {"Ref": "Data"}}
    statements = resources["Role"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    assert all(s["Resource"] != "*" for s in statements)
    assert all("slack" not in name.lower() for name in resources)
    assert resources["Data"]["Properties"]["BillingMode"] == "PAY_PER_REQUEST"


def test_lambda_gateway_payload_uses_the_shared_business_contract(service):
    import base64
    import json
    from infra import lambda_handler
    lambda_handler._store = service.store
    body = {"start_date": "2030-04-08", "end_date": "2030-04-09",
            "leave_type": "annual", "request_key": "gateway-payload", "note": "가상 신청"}
    event = {"requestContext": {"http": {"method": "POST"}},
             "rawPath": "/v1/leave/requests", "rawQueryString": "",
             "headers": {"authorization": "Bearer participant-token-a", "content-type": "application/json"},
             "isBase64Encoded": True,
             "body": base64.b64encode(json.dumps(body, ensure_ascii=False).encode()).decode()}
    result = lambda_handler.handler(event, None)
    assert result["statusCode"] == 201
    record = json.loads(result["body"])["request"]
    assert record["note"] == "가상 신청" and record["status"] == "pending"
    assert service.store.read("p001")["requests"][0]["id"] == record["id"]
