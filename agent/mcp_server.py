# agent/mcp_server.py
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from agent.data_sources.bcrd import BCRDClient
from agent.data_sources.superbancos import SuperbancosClient
from agent.data_sources.imf import IMFClient
from agent.data_sources.worldbank import WorldBankClient
from agent.data_sources.hacienda import HaciendaClient

server = Server("bancario-rd")
_bcrd = BCRDClient()
_sb = SuperbancosClient()
_imf = IMFClient()
_wb = WorldBankClient()
_hacienda = HaciendaClient()


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="get_bcrd_indicators",
            description="Fetches BCRD macro and banking rate indicators (TPM, tasas activas/pasivas, IMAE, inflacion, tipo de cambio, reservas)",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_sb_banking_data",
            description="Fetches Superintendencia de Bancos system and entity rankings (cartera growth, NPL)",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_imf_data",
            description="Fetches IMF Financial Soundness Indicators for Dominican Republic",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_worldbank_data",
            description="Fetches World Bank financial development indicators for Dominican Republic",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="get_hacienda_data",
            description="Fetches Ministerio de Hacienda fiscal summary (debt/GDP, budget execution)",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    dispatch = {
        "get_bcrd_indicators": _bcrd.get_all,
        "get_sb_banking_data": _sb.get_all,
        "get_imf_data": _imf.get_all,
        "get_worldbank_data": _wb.get_all,
        "get_hacienda_data": _hacienda.get_all,
    }
    if name not in dispatch:
        raise ValueError(f"Unknown tool: {name}")
    data = dispatch[name]()
    return [types.TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
