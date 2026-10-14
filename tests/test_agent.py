"""Smoke tests for the agent wiring and the local MCP server (no network)."""

import json
from types import SimpleNamespace

import pytest


def test_root_agent_is_configured():
    from agents.shrinkflation_sleuth import agent

    assert agent.root_agent.name == "shrinkflation_sleuth"
    assert agent.root_agent.model == agent.GEMINI_MODEL
    assert set(agent.ELASTIC_MCP_TOOLS) == {"list_indices", "get_mappings", "search", "esql", "get_shards"}
    playbooks = [
        "PRODUCT LOOKUP",
        "BRAND INVESTIGATION",
        "CATEGORY ANALYSIS",
        "SHOPPING LIST AUDIT",
        "TREND DASHBOARD",
        "DATA DISCOVERY",
    ]
    for heading in playbooks:
        assert heading in agent.INSTRUCTION


def test_toolset_uses_http_when_mcp_url_set(monkeypatch):
    from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

    from agents.shrinkflation_sleuth import agent

    monkeypatch.setenv("ELASTIC_MCP_URL", "https://example.invalid/mcp")
    toolset = agent._elastic_mcp_toolset()
    assert isinstance(toolset._connection_params, StreamableHTTPConnectionParams)


class FakeES:
    """Records calls and returns canned bodies, mimicking elasticsearch.Elasticsearch."""

    def __init__(self):
        self.calls = []
        self.cat = SimpleNamespace(indices=self._rec("cat.indices"), shards=self._rec("cat.shards"))
        self.indices = SimpleNamespace(get_mapping=self._rec("indices.get_mapping"))
        self.esql = SimpleNamespace(query=self._rec("esql.query"))
        self.search = self._rec("search")

    def _rec(self, name):
        def call(**kwargs):
            self.calls.append((name, kwargs))
            return SimpleNamespace(body={"called": name})

        return call


@pytest.fixture
def server(monkeypatch):
    from agents.shrinkflation_sleuth import es_mcp_server

    fake = FakeES()
    monkeypatch.setattr(es_mcp_server, "get_client", lambda: fake)
    return es_mcp_server, fake


def test_mcp_tools_delegate_to_elasticsearch(server):
    mod, fake = server
    assert json.loads(mod.search("products", {"query": {"match_all": {}}})) == {"called": "search"}
    mod.esql("FROM products | LIMIT 1")
    mod.get_mappings("products")
    mod.list_indices()
    mod.get_shards()
    names = [c[0] for c in fake.calls]
    assert names == ["search", "esql.query", "indices.get_mapping", "cat.indices", "cat.shards"]
    assert fake.calls[1][1] == {"body": {"query": "FROM products | LIMIT 1"}}
    assert "index" not in fake.calls[-1][1]


def test_missing_credentials_raise_clear_error(monkeypatch):
    from agents.shrinkflation_sleuth import es_mcp_server

    monkeypatch.delenv("ES_URL", raising=False)
    es_mcp_server.get_client.cache_clear()
    with pytest.raises(RuntimeError, match="ES_URL and ES_API_KEY"):
        es_mcp_server.get_client()
    es_mcp_server.get_client.cache_clear()
