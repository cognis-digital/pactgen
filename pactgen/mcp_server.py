"""PACTGEN MCP server — exposes scan() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
from pactgen.core import scan, to_json

def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-pactgen[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-pactgen[mcp]'")
        return 1
    app = FastMCP("pactgen")

    @app.tool()
    def pactgen_scan(target: str) -> str:
        """Generate branded sales proposals and SOWs from a YAML scope file + pricing table into PDF/HTML, with a deterministic line-item math check.. Returns JSON findings."""
        return to_json(scan(target))

    app.run()
    return 0
