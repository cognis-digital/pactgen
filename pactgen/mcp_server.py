"""PACTGEN MCP server — exposes build() as an MCP tool for Cognis.Studio."""
from __future__ import annotations
import json
import sys
from pactgen.core import parse_proposal_file, proposal_to_dict


def serve() -> int:
    """Start an MCP stdio server. Requires the optional 'mcp' extra:
        pip install "cognis-pactgen[mcp]"
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print("Install the MCP extra: pip install 'cognis-pactgen[mcp]'", file=sys.stderr)
        return 1
    app = FastMCP("pactgen")

    @app.tool()
    def pactgen_build(spec_path: str) -> str:
        """Parse a YAML proposal spec and validate line-item math. Returns JSON findings."""
        try:
            proposal = parse_proposal_file(spec_path)
        except (FileNotFoundError, PermissionError, ValueError) as exc:
            return json.dumps({"error": str(exc)})
        return json.dumps(proposal_to_dict(proposal))

    app.run()
    return 0
