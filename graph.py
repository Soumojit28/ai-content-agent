from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from agents.copywriter import CopywritingAgent
from agents.hashtags import HashtagAgent
from agents.research import ResearchAgent
from state import State
from tools.serp_client import SerpClient
from tools.masumi_image_client import (
    MasumiImageClientError,
    generate_image_with_masumi,
)


class ContentGraph:
    """LangGraph workflow for research → copy → image → hashtags."""

    def __init__(
        self,
        *,
        serp_client: SerpClient,
        research_agent: ResearchAgent,
        copy_agent: CopywritingAgent,
        hashtag_agent: HashtagAgent,
        logger=None,
    ):
        self.serp_client = serp_client
        self.research_agent = research_agent
        self.copy_agent = copy_agent
        self.hashtag_agent = hashtag_agent
        self.logger = logger
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(State)
        graph.add_node("fetch_snippets", self._fetch_snippets)
        graph.add_node("synthesize_research", self._synthesize_research)
        graph.add_node("generate_copy", self._generate_copy)
        graph.add_node("generate_image", self._generate_image)
        graph.add_node("generate_hashtags", self._generate_hashtags)
        graph.add_edge(START, "fetch_snippets")
        graph.add_edge("fetch_snippets", "synthesize_research")
        graph.add_edge("synthesize_research", "generate_copy")
        # Ensure image generation happens after copywriter so it can use post.image_prompt
        graph.add_edge("generate_copy", "generate_image")
        graph.add_edge("generate_image", "generate_hashtags")
        graph.add_edge("generate_hashtags", END)
        return graph.compile()

    async def invoke(self, state: State) -> State:
        result = await self.graph.ainvoke(state)
        # Ensure return type is State
        return State(**result)

    async def _fetch_snippets(self, state: State) -> Dict[str, Any]:
        snippets = await self.serp_client.fetch_context(
            topic=state.get("topic", ""),
            keywords=state.get("keywords"),
            link=state.get("link"),
        )
        if self.logger:
            self.logger.info("Fetched %s snippets from SerpAPI", len(snippets))
        metadata = dict(state.get("metadata", {}))
        metadata["serp_snippet_count"] = len(snippets)
        return {"context_snippets": snippets, "metadata": metadata}

    async def _synthesize_research(self, state: State) -> Dict[str, Any]:
        snippets = state.get("context_snippets", [])
        summary = await self.research_agent.summarize(state, snippets)
        metadata = dict(state.get("metadata", {}))
        metadata["research_summary"] = summary.get("summary", "")
        return {
            "insights": summary.get("insights", []),
            "research_summary": summary.get("summary", ""),
            "metadata": metadata,
        }

    async def _generate_copy(self, state: State) -> Dict[str, Any]:
        insights = state.get("insights", [])
        post = await self.copy_agent.generate_post(state, insights)
        return {"post": post}

    async def _generate_image(self, state: State) -> Dict[str, Any]:
        """Generate image via Masumi image agent using the copywriter's image_prompt."""
        post = state.get("post") or {}
        image_prompt = post.get("image_prompt")

        if not image_prompt:
            if self.logger:
                self.logger.info("No image_prompt in post; skipping image generation")
            return {}

        try:
            if self.logger:
                self.logger.info("Starting Masumi image generation from graph node")
            image_result = await generate_image_with_masumi(
                prompt=image_prompt,
                logger=self.logger,
            )
            metadata = dict(state.get("metadata", {}))
            metadata["image"] = {
                "job_id": image_result.get("job_id"),
                "ipfs_hash": image_result.get("ipfs_hash"),
                "image_ipfs_url": image_result.get("image_ipfs_url"),
                "raw_status": image_result.get("raw_status"),
            }
            return {
                "metadata": metadata,
                "image_ipfs_hash": image_result.get("ipfs_hash"),
                "image_ipfs_url": image_result.get("image_ipfs_url"),
                "image_job": {
                    "job_id": image_result.get("job_id"),
                    "raw_status": image_result.get("raw_status"),
                },
            }
        except MasumiImageClientError as e:
            if self.logger:
                self.logger.error(
                    "Masumi image generation failed in graph node: %s",
                    e,
                    exc_info=True,
                )
            metadata = dict(state.get("metadata", {}))
            metadata["image_error"] = str(e)
            return {"metadata": metadata, "image_error": str(e)}
        except Exception as e:
            if self.logger:
                self.logger.error(
                    "Unexpected error during Masumi image generation in graph node: %s",
                    e,
                    exc_info=True,
                )
            metadata = dict(state.get("metadata", {}))
            metadata["image_error"] = f"Unexpected image error: {e}"
            return {"metadata": metadata, "image_error": str(e)}

    async def _generate_hashtags(self, state: State) -> Dict[str, Any]:
        package = await self.hashtag_agent.generate_hashtags(state)
        return {"hashtag_package": package}


# Instantiate the graph for LangGraph server
import logging
from langchain_openai import ChatOpenAI
from config.content_agent import load_content_agent_config

_logger = logging.getLogger(__name__)
_config = load_content_agent_config()
_llm = ChatOpenAI(
    temperature=_config.temperature,
    model=_config.model
)
_serp_client = SerpClient(
    api_key=_config.serpapi_key,
    engine=_config.serpapi_engine,
    location=_config.serpapi_location,
    language=_config.serpapi_language,
    num_results=_config.serpapi_num_results,
    logger=_logger,
)
_research_agent = ResearchAgent(_llm, _config.prompts.research, logger=_logger)
_copy_agent = CopywritingAgent(_llm, _config.prompts.copywriter, logger=_logger)
_hashtag_agent = HashtagAgent(_llm, _config.prompts.hashtags, logger=_logger)

content_graph_builder = ContentGraph(
    serp_client=_serp_client,
    research_agent=_research_agent,
    copy_agent=_copy_agent,
    hashtag_agent=_hashtag_agent,
    logger=_logger,
)
content_graph = content_graph_builder.graph
