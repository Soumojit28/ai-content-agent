from typing import Any, Dict

from langchain_openai import ChatOpenAI

from agentic_service import ServiceResult
from agents.copywriter import CopywritingAgent
from agents.hashtags import HashtagAgent
from agents.research import ResearchAgent
from config.content_agent import load_content_agent_config
from graph import ContentGraph
from state import State
from tools.serp_client import SerpClient


class LangGraphService:
    """Multi-agent workflow orchestrating research, copy, and hashtags."""
    
    def __init__(self, logger=None):
        self.logger = logger
        self.config = load_content_agent_config()
        self.llm = ChatOpenAI(
            temperature=self.config.temperature,
            model=self.config.model
        )
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> ContentGraph:
        serp_client = SerpClient(
            api_key=self.config.serpapi_key,
            engine=self.config.serpapi_engine,
            location=self.config.serpapi_location,
            language=self.config.serpapi_language,
            num_results=self.config.serpapi_num_results,
            logger=self.logger,
        )
        research_agent = ResearchAgent(self.llm, self.config.prompts.research, logger=self.logger)
        copy_agent = CopywritingAgent(self.llm, self.config.prompts.copywriter, logger=self.logger)
        hashtag_agent = HashtagAgent(self.llm, self.config.prompts.hashtags, logger=self.logger)
        return ContentGraph(
            serp_client=serp_client,
            research_agent=research_agent,
            copy_agent=copy_agent,
            hashtag_agent=hashtag_agent,
            logger=self.logger,
        )

    async def execute_task(self, input_data: Dict[str, Any]) -> ServiceResult:
        print(f"Input data: {input_data}")
        state = self._build_initial_state(input_data)
        final_state = await self.workflow.invoke(state)
        payload = {
            "topic": final_state.get("topic"),
            "tone": final_state.get("tone"),
            "platform": final_state.get("platform"),
            "post": final_state.get("post", {}),
            "hashtags": final_state.get("hashtag_package", {}).get("hashtags", []),
            "hashtag_explainer": final_state.get("hashtag_package", {}).get("explainer", ""),
            "insights": final_state.get("insights", []),
            "research_summary": final_state.get("research_summary", ""),
            "metadata": final_state.get("metadata", {}),
        }
        return ServiceResult(
            raw=final_state.get("post", {}).get("post_body", ""),
            json_dict=payload,
            original_text=state.get("topic", ""),
            extras={"state": final_state},
        )

    def _build_initial_state(self, input_data: Dict[str, Any]) -> State:
        keywords = input_data.get("keywords") or []
        if isinstance(keywords, str):
            keywords = [part.strip() for part in keywords.split(",") if part.strip()]
        platform = (input_data.get("platform") or "linkedin").lower()
        state: State = {
            "topic": input_data.get("topic", ""),
            "tone": input_data.get("tone", "insightful"),
            "platform": platform,
            "keywords": keywords,
            "link": input_data.get("link"),
            "audience": input_data.get("audience"),
            "request_id": input_data.get("request_id"),
            "use_emojis": input_data.get("use_emojis", self.config.use_emojis),
            "metadata": {},
            "errors": [],
        }
        return state