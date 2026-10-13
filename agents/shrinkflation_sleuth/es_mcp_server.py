"""
es_mcp_server.py — Stdio MCP server wrapping the Elasticsearch Python client.

Implements the same 5 read-only tools as docker.elastic.co/mcp/elasticsearch:
  list_indices, get_mappings, search, esql, get_shards

Used by agent.py when Docker is not available (local dev without Docker).
Reads ES_URL and ES_API_KEY from the environment (loaded via python-dotenv).
"""

import json
import os
import sys

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from mcp.server.fastmcp import FastMCP

load_dotenv()

es = Elasticsearch(os.environ["ES_URL"], api_key=os.environ["ES_API_KEY"])
mcp = FastMCP("elasticsearch")


@mcp.tool()
def list_indices() -> str:
    """List all Elasticsearch indices with basic stats."""
    resp = es.cat.indices(format="json", h="index,health,status,docs.count,store.size")
    return json.dumps(resp.body)


@mcp.tool()
def get_mappings(index: str) -> str:
    """Return field mappings for the given index."""
    resp = es.indices.get_mapping(index=index)
    return json.dumps(resp.body)


@mcp.tool()
def search(index: str, body: dict) -> str:
    """Search an index using Elasticsearch query DSL. Pass the full request body as `body`."""
    resp = es.search(index=index, body=body)
    return json.dumps(resp.body)


@mcp.tool()
def esql(query: str) -> str:
    """Run an ES|QL query string and return results."""
    resp = es.esql.query(body={"query": query})
    return json.dumps(resp.body)


@mcp.tool()
def get_shards(index: str = "") -> str:
    """Get shard info. Pass an index name to filter, or omit for all shards."""
    kwargs = {"format": "json"}
    if index:
        kwargs["index"] = index
    resp = es.cat.shards(**kwargs)
    return json.dumps(resp.body)


if __name__ == "__main__":
    mcp.run(transport="stdio")
