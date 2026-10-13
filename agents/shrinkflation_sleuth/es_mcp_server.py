"""
es_mcp_server.py — Stdio MCP server wrapping the Elasticsearch Python client.

Implements the same 5 read-only tools as docker.elastic.co/mcp/elasticsearch:
  list_indices, get_mappings, search, esql, get_shards

agent.py spawns this over stdio for local development when ELASTIC_MCP_URL
is not set, so the agent runs without Docker. Reads ES_URL and ES_API_KEY
from the environment (loaded via python-dotenv).
"""

import json
import os
from functools import lru_cache

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from mcp.server.fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("elasticsearch")


@lru_cache(maxsize=1)
def get_client() -> Elasticsearch:
    """Create the client on first use so a missing config fails with a clear message."""
    url, api_key = os.environ.get("ES_URL"), os.environ.get("ES_API_KEY")
    if not url or not api_key:
        raise RuntimeError("ES_URL and ES_API_KEY must be set (see .env.example)")
    return Elasticsearch(url, api_key=api_key)


@mcp.tool()
def list_indices() -> str:
    """List all Elasticsearch indices with basic stats."""
    resp = get_client().cat.indices(format="json", h="index,health,status,docs.count,store.size")
    return json.dumps(resp.body)


@mcp.tool()
def get_mappings(index: str) -> str:
    """Return field mappings for the given index."""
    resp = get_client().indices.get_mapping(index=index)
    return json.dumps(resp.body)


@mcp.tool()
def search(index: str, body: dict) -> str:
    """Search an index using Elasticsearch query DSL. Pass the full request body as `body`."""
    resp = get_client().search(index=index, body=body)
    return json.dumps(resp.body)


@mcp.tool()
def esql(query: str) -> str:
    """Run an ES|QL query string and return results."""
    resp = get_client().esql.query(body={"query": query})
    return json.dumps(resp.body)


@mcp.tool()
def get_shards(index: str = "") -> str:
    """Get shard info. Pass an index name to filter, or omit for all shards."""
    kwargs = {"format": "json"}
    if index:
        kwargs["index"] = index
    resp = get_client().cat.shards(**kwargs)
    return json.dumps(resp.body)


if __name__ == "__main__":
    mcp.run(transport="stdio")
