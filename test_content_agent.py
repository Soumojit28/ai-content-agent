import pytest

from graph import ContentGraph
from state import State


class DummySerpClient:
    async def fetch_context(self, **kwargs):
        return [{"title": "Result", "snippet": "Insightful note", "link": "https://example.com", "source": "test"}]


class DummyResearchAgent:
    async def summarize(self, state, snippets):
        return {"insights": ["Insight A"], "summary": "Summary"}


class DummyCopywritingAgent:
    async def generate_post(self, state, insights):
        return {"post_body": "Body", "headline": "HL", "rationale": "Because"}


class DummyHashtagAgent:
    async def generate_hashtags(self, state):
        return {"hashtags": ["AI"], "explainer": "test"}


@pytest.mark.asyncio
async def test_content_graph_pipeline():
    graph = ContentGraph(
        serp_client=DummySerpClient(),
        research_agent=DummyResearchAgent(),
        copy_agent=DummyCopywritingAgent(),
        hashtag_agent=DummyHashtagAgent(),
    )
    state: State = {
        "topic": "Graph test",
        "tone": "bold",
        "platform": "linkedin",
        "keywords": ["test"],
    }
    result = await graph.invoke(state)
    assert result["post"]["post_body"] == "Body"
    assert result["hashtag_package"]["hashtags"] == ["AI"]
    assert result["research_summary"] == "Summary"

