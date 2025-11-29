from typing import Dict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from agents.utils import extract_json
from state import State


class HashtagAgent:
    """Produces high-signal hashtags tailored to the generated copy."""

    def __init__(self, llm: Runnable, prompt_template: str, logger=None):
        self.llm = llm
        self.prompt_template = prompt_template
        self.logger = logger

    async def generate_hashtags(self, state: State) -> Dict[str, str]:
        prompt = self.prompt_template.format(
            platform=state.get("platform", "linkedin"),
            tone=state.get("tone", ""),
        )
        messages = [
            SystemMessage(content="Always respond with JSON containing hashtags + explainer."),
            HumanMessage(
                content=(
                    f"{prompt}\n\nPost:\n{state.get('post', {}).get('post_body', '')}\n"
                    f"Topic: {state.get('topic', '')}\nTone: {state.get('tone', '')}\n"
                    f"Audience: {state.get('audience') or 'General'}"
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        default = {"hashtags": [], "explainer": ""}
        data = extract_json(response.content, default)
        if isinstance(data.get("hashtags"), str):
            data["hashtags"] = [tag.strip("# ").strip() for tag in data["hashtags"].split(",")]
        if self.logger:
            self.logger.debug("Hashtag output: %s", data)
        return data

