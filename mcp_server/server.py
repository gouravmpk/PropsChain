"""
Indian Property Registry — MCP Server
--------------------------------------
Exposes the generic national property registry as Model Context Protocol tools.
Any MCP-compatible client (Claude Desktop, Claude Code, etc.) can query
property records without needing to call the REST API directly.

Tools:
  registry_lookup            - Look up a property by survey / registration number
  registry_verify_owner      - Check if a claimed owner matches registry records
  registry_encumbrances      - Check for active mortgages, liens, court orders
  registry_ownership_history - Full chain of title
  registry_search_by_owner   - Find all properties under an owner's name
  registry_stats             - Registry coverage statistics

Usage (stdio transport):
  python server.py

Usage (from Claude Code):
  Add to ~/.claude/mcp_servers.json or run directly.
"""

import asyncio
import json
import os
import sys

# Allow importing from the backend directory
_BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, _BACKEND)

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from services.registry_service import (
    check_encumbrances,
    get_ownership_history,
    get_registry_stats,
    lookup_by_registration,
    lookup_by_survey,
    search_by_owner,
    verify_owner,
)

server = Server("indian-property-registry")


# ─── Tool definitions ─────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="registry_lookup",
            description=(
                "Look up a property in the national Indian property registry by survey number "
                "or registration number. Returns owner details, address, land type, area, "
                "encumbrance status, and market value. "
                "Use this first when verifying any property document."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "survey_number": {
                        "type": "string",
                        "description": "Survey / plot / khasra number (e.g. '123/4A', 'Plot-7A', 'Gata-445/2')",
                    },
                    "registration_number": {
                        "type": "string",
                        "description": "Document registration number from SRO (e.g. 'REG-BLR-2024-9876')",
                    },
                    "state": {
                        "type": "string",
                        "description": "Optional: state name to narrow results (e.g. 'Karnataka', 'Maharashtra')",
                    },
                },
            },
        ),
        Tool(
            name="registry_verify_owner",
            description=(
                "Verify whether the owner name on a document matches the officially "
                "registered owner in the national registry. "
                "Detects ownership fraud, impersonation, and benami transactions. "
                "Returns owner_match (bool), registered_owner name, and a fraud_flag."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner_name": {
                        "type": "string",
                        "description": "Owner name exactly as it appears in the document",
                    },
                    "survey_number": {"type": "string"},
                    "registration_number": {"type": "string"},
                    "state": {"type": "string"},
                },
                "required": ["owner_name"],
            },
        ),
        Tool(
            name="registry_encumbrances",
            description=(
                "Check encumbrances (mortgages, bank liens, court orders) on a property. "
                "An active encumbrance means the property is pledged to a lender or under legal hold — "
                "the seller cannot legally transfer ownership without clearing it first. "
                "Returns encumbrance_status, property_status, and full encumbrance list."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "survey_number": {"type": "string"},
                    "registration_number": {"type": "string"},
                    "state": {"type": "string"},
                },
            },
        ),
        Tool(
            name="registry_ownership_history",
            description=(
                "Retrieve the complete chain of title (ownership history) for a property. "
                "Shows all past owners with transfer dates, sale values, and SRO office. "
                "Useful for detecting suspicious rapid transfers, inflated valuations, "
                "or gaps in the ownership chain."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "survey_number": {"type": "string"},
                    "registration_number": {"type": "string"},
                    "state": {"type": "string"},
                },
            },
        ),
        Tool(
            name="registry_search_by_owner",
            description=(
                "Find all properties — current or historical — associated with an owner's name. "
                "Supports partial / fuzzy name matching. "
                "Useful for detecting undisclosed property holdings or benami transactions "
                "where one person holds many properties under slight name variations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "owner_name": {
                        "type": "string",
                        "description": "Full or partial owner name",
                    },
                    "state": {
                        "type": "string",
                        "description": "Optional: limit search to a specific state",
                    },
                },
                "required": ["owner_name"],
            },
        ),
        Tool(
            name="registry_stats",
            description=(
                "Return registry coverage statistics: total properties, states covered, "
                "breakdown by state and by property status (Clear / Encumbered / Disputed)."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


# ─── Tool dispatch ────────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    args = arguments or {}

    if name == "registry_lookup":
        if args.get("registration_number"):
            result = lookup_by_registration(args["registration_number"])
        elif args.get("survey_number"):
            result = lookup_by_survey(args["survey_number"], args.get("state"))
        else:
            result = {"error": "Provide survey_number or registration_number"}

    elif name == "registry_verify_owner":
        result = verify_owner(
            args.get("owner_name", ""),
            args.get("survey_number"),
            args.get("registration_number"),
            args.get("state"),
        )

    elif name == "registry_encumbrances":
        result = check_encumbrances(
            args.get("survey_number"),
            args.get("registration_number"),
            args.get("state"),
        )

    elif name == "registry_ownership_history":
        result = get_ownership_history(
            args.get("survey_number"),
            args.get("registration_number"),
            args.get("state"),
        )

    elif name == "registry_search_by_owner":
        result = search_by_owner(args.get("owner_name", ""), args.get("state"))

    elif name == "registry_stats":
        result = get_registry_stats()

    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]


# ─── Entry point ──────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
