"""pactgen — part of the Cognis Neural Suite."""
from pactgen.core import (  # noqa: F401
    TOOL_NAME,
    TOOL_VERSION,
    parse_yaml,
    parse_proposal,
    parse_proposal_file,
    compute_totals,
    check_math,
    proposal_to_dict,
    render_html,
    LineItem,
    MathIssue,
    Proposal,
)

__version__ = TOOL_VERSION
