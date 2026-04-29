"""
MCP Server Setup — shared between standalone (server.py) and integrated (main.py) modes.
Creates the FastMCP instance and registers all tools + resources.
Import `mcp` from this module; never call mcp.run() here.
"""

import sys
import os

_this_file = os.path.abspath(__file__)
_backend_root = os.path.dirname(os.path.dirname(os.path.dirname(_this_file)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from fastmcp import FastMCP

mcp = FastMCP(
    name="chatbot-mcp-server",
    instructions=(
        "This server exposes your chatbot platform — FAQs, workflows, "
        "and chatbot config — as MCP tools and resources."
    ),
)


# ── Ping ─────────────────────────────────────────────────────────────────────
@mcp.tool()
def ping() -> str:
    """Check if the MCP server is running and reachable."""
    return "MCP server is running. Chatbot platform is ready."


# ── Tools ─────────────────────────────────────────────────────────────────────
from app.mcp_server.tools.chatbot import register_chatbot_tools
from app.mcp_server.tools.faq import register_faq_tools
from app.mcp_server.tools.workflow import register_workflow_tools

register_chatbot_tools(mcp)
register_faq_tools(mcp)
register_workflow_tools(mcp)

# Uncomment when Milvus is running:
# from app.mcp_server.tools.knowledge import register_knowledge_tools
# register_knowledge_tools(mcp)

# ── Resources ─────────────────────────────────────────────────────────────────
from app.mcp_server.resources.chatbot_resources import register_chatbot_resources

register_chatbot_resources(mcp)
