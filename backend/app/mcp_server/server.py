"""
MCP Server — Standalone mode (port 8001).
For development/testing without starting FastAPI.
All tools and resources are defined in setup.py.

Usage:
    cd C:\\chatbot\\backend
    python app/mcp_server/server.py

MCP Inspector: Transport=SSE, URL=http://127.0.0.1:8001/sse
"""

import sys
import os

_this_file = os.path.abspath(__file__)
_backend_root = os.path.dirname(os.path.dirname(os.path.dirname(_this_file)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

import logging

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)

from app.mcp_server.setup import mcp

if __name__ == "__main__":
    print("MCP Server starting at http://127.0.0.1:8001", file=sys.stderr)
    print("MCP Inspector: Transport=SSE, URL=http://127.0.0.1:8001/sse", file=sys.stderr)
    mcp.run(transport="sse", host="127.0.0.1", port=8001)




