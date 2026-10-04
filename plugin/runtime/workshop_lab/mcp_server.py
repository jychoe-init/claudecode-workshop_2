"""MCP SDK 1.26.0: real stdio transport wrapping the separate local HTTP API."""
import asyncio
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from .server import NoRedirect

mcp = FastMCP("hr", instructions="Lab HR API. Request submission is pending, not HR approval.")


def api(path, body=None):
    base = os.environ.get("SUPERLAB_API_URL", "http://127.0.0.1:8765")
    parsed = urllib.parse.urlsplit(base)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("This teaching wrapper only connects to the local lab API")
    token = os.environ.get("SUPERLAB_TOKEN", "")
    req = urllib.request.Request(base.rstrip("/") + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "X-Superlab-Token": token})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=5) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1000).decode(errors="replace")
        raise ValueError(f"Lab API rejected the operation ({exc.code}): {detail}") from None
    except urllib.error.URLError:
        raise ValueError("Lab API unavailable; no success can be confirmed") from None


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
async def get_leave_balance() -> dict:
    """Read demo-user's balance and pending reservations. No state changes."""
    return await asyncio.to_thread(api, "/api/hr/balance?employee_id=demo-user")


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                     idempotentHint=True, openWorldHint=False))
async def request_leave(start_date: str, days: float, request_key: str) -> dict:
    """Submit a PENDING request for demo-user. Confirm date/days with the user first.
    Reuse request_key for retries. This is not an approval operation.
    """
    return await asyncio.to_thread(api, "/api/hr/requests",
        {"employee_id": "demo-user", "start_date": start_date, "days": days, "request_key": request_key})


if __name__ == "__main__":
    mcp.run(transport="stdio")
