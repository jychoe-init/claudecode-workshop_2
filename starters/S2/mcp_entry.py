"""S2 start: one working read tool. Add request_leave using the complete runtime as reference."""
from mcp.server.fastmcp import FastMCP
from workshop_lab.mcp_server import api
import asyncio

mcp = FastMCP("hr")


@mcp.tool()
async def get_leave_balance() -> dict:
    """Read demo-user's current balance without changing it."""
    return await asyncio.to_thread(api, "/api/hr/balance?employee_id=demo-user")


# Learner: add a request_leave(start_date, days, request_key) tool.
# It must POST to /api/hr/requests and return the actual server result.
# Do not print diagnostics on stdout; it is reserved for MCP transport.

if __name__ == "__main__":
    mcp.run(transport="stdio")
