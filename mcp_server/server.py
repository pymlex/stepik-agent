import asyncio
import json
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from stepik_agent.config import load_settings
from stepik_agent.db.preferences import PreferencesStore
from stepik_agent.db.search_log import SearchLogStore
from stepik_agent.stepik.api import search_courses


server = Server("stepik-agent")
settings = load_settings()
prefs_store = PreferencesStore(settings.data_dir / "preferences.db")
search_store = SearchLogStore(settings.data_dir / "search_log.db")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="stepik_search",
            description="Search Stepik courses by query string",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_preferences",
            description="Read stored user preferences from SQLite",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="list_search_log",
            description="List logged Stepik search queries",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "stepik_search":
        query = arguments["query"]
        limit = int(arguments.get("limit", 5))
        cards = search_courses(query, limit=limit, token=settings.stepik_token)
        return [TextContent(type="text", text=json.dumps(cards, ensure_ascii=False))]

    if name == "get_preferences":
        data = prefs_store.list_preferences()
        return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False))]

    if name == "list_search_log":
        session_id = arguments.get("session_id")
        if session_id:
            queries = search_store.queries_for_session(session_id)
            payload = {"session_id": session_id, "queries": queries}
        else:
            payload = search_store.all_queries()
        return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
