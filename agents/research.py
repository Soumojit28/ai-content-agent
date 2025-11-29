from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from agents.utils import extract_json
from state import ResearchSnippet, State


class ResearchAgent:
    """Turns raw SerpAPI snippets into ranked insights."""

    def __init__(self, llm: Runnable, prompt_template: str, logger=None):
        self.llm = llm
        self.prompt_template = prompt_template
        self.logger = logger

    async def summarize(self, state: State, snippets: List[ResearchSnippet]) -> Dict[str, List[str]]:
        prompt = self.prompt_template.format(
            topic=state.get("topic", ""),
            tone=state.get("tone", ""),
            serpapi_num_results=len(snippets),
        )
        snippet_text = "\n".join(
            f"- {item.get('title','Untitled')} ({item.get('source','unknown')}): "
            f"{item.get('snippet','')[:400]}"
            for item in snippets
        )
        messages = [
            SystemMessage(
                content="You convert SERP snippets into JSON with 'insights' and 'summary'."
            ),
            HumanMessage(content=f"{prompt}\n\nSnippets:\n{snippet_text}"),
        ]
        response = await self.llm.ainvoke(messages)
        data = extract_json(response.content, {"insights": [], "summary": ""})
        if self.logger:
            self.logger.debug("Research agent output: %s", data)
        return {
            "insights": data.get("insights", []),
            "summary": data.get("summary", ""),
        }

