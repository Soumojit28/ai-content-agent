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
        return {
            "post_body": "Body",
            "headline": "HL",
            "rationale": "Because",
            "image_prompt": "an image prompt from copywriter",
        }


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


@pytest.mark.asyncio
async def test_langgraph_service_image_fields_present(monkeypatch):
    """Sanity check that image fields are exposed on the result payload."""
    from langgraph_service import LangGraphService

    # Patch the graph's image node helper so we don't hit real HTTP.
    async def fake_generate_image_with_masumi(*args, **kwargs):
        return {
            "job_id": "fake-job",
            "ipfs_hash": "QmFakeHash",
            "image_ipfs_url": "https://ipfs.io/ipfs/QmFakeHash",
            "raw_status": {"status": "completed", "result": "QmFakeHash"},
        }

    monkeypatch.setattr(
        "graph.generate_image_with_masumi",
        fake_generate_image_with_masumi,
    )

    service = LangGraphService()

    input_data = {
        "topic": "Graph test",
        "tone": "bold",
        "platform": "linkedin",
        "keywords": ["test"],
    }

    result = await service.execute_task(input_data)
    assert result.json_dict["image_ipfs_hash"] == "QmFakeHash"
    assert result.json_dict["image_ipfs_url"].endswith("/QmFakeHash")
    assert result.json_dict["image_job"]["job_id"] == "fake-job"


@pytest.mark.asyncio
async def test_langgraph_service_image_error_is_non_fatal(monkeypatch):
    """If image generation fails, text payload should still succeed with image_error set."""
    from langgraph_service import LangGraphService
    from tools.masumi_image_client import MasumiImageClientError

    async def failing_generate_image_with_masumi(*args, **kwargs):
        raise MasumiImageClientError("boom")

    monkeypatch.setattr(
        "graph.generate_image_with_masumi",
        failing_generate_image_with_masumi,
    )

    service = LangGraphService()

    input_data = {
        "topic": "Graph test",
        "tone": "bold",
        "platform": "linkedin",
        "keywords": ["test"],
    }

    result = await service.execute_task(input_data)
    assert result.raw != ""
    assert "image_error" in result.json_dict

