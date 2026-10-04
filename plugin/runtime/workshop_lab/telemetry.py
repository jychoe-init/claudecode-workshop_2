"""OTLP HTTP JSON/protobuf log ingestion. Only an allowlist of usage fields is persisted."""
from .store import canonical, finite_number, identity


def val(v):
    if not isinstance(v, dict):
        return v
    for key in ("stringValue", "intValue", "doubleValue", "boolValue",
                "string_value", "int_value", "double_value", "bool_value"):
        if key in v:
            return v[key]
    return None


def attrs(items):
    return {x.get("key"): val(x.get("value", {})) for x in items or [] if "key" in x}


def parse_otlp(body, content_type):
    if "protobuf" in content_type:
        from google.protobuf.json_format import MessageToDict
        from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
        request = ExportLogsServiceRequest()
        try:
            request.ParseFromString(body)
        except Exception as exc:
            raise ValueError("Invalid OTLP protobuf") from exc
        return MessageToDict(request)
    import json
    return json.loads(body)


def ingest(store, envelope):
    accepted = ignored = 0
    for resource in envelope.get("resourceLogs", []):
        common = attrs(resource.get("resource", {}).get("attributes"))
        for scope in resource.get("scopeLogs", []):
            for record in scope.get("logRecords", []):
                a = {**common, **attrs(record.get("attributes"))}
                name = record.get("eventName") or a.get("event.name") or val(record.get("body", {}))
                if name not in ("claude_code.api_request", "api_request"):
                    ignored += 1
                    continue
                row = {
                    "kind": "api_request", "session": str(a.get("session.id", "unknown")),
                    "prompt": str(a.get("prompt.id", "")),
                    "run_id": str(a.get("run.id", "")),
                    "module": str(a.get("module.id", "")),
                    "model": str(a.get("model", a.get("model.id", "unknown"))),
                    "timestamp": str(record.get("timeUnixNano", record.get("observedTimeUnixNano", ""))),
                    "input_tokens": finite_number(a.get("input_tokens"), integer=True),
                    "output_tokens": finite_number(a.get("output_tokens"), integer=True),
                    "cache_read_tokens": finite_number(a.get("cache_read_tokens", a.get("cache_read_input_tokens")), integer=True),
                    "cache_write_tokens": finite_number(a.get("cache_creation_tokens", a.get("cache_creation_input_tokens")), integer=True),
                    "cost_usd": finite_number(a.get("cost_usd")),
                    "duration_ms": finite_number(a.get("duration_ms")),
                }
                # No prompt/body text, secret headers or arbitrary resource attributes are retained.
                row["data"] = canonical({"event_sequence": a.get("event.sequence"),
                                         "trace_id": record.get("traceId", "")})
                row["id"] = identity(row)
                accepted += int(store.record_api(row))
    return {"accepted": accepted, "ignored": ignored}
