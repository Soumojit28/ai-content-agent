from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from agents.utils import extract_json
from state import State


class CopywritingAgent:
    """LLM-powered generator for LinkedIn/X copy."""

    def __init__(self, llm: Runnable, prompt_template: str, logger=None):
        self.llm = llm
        self.prompt_template = prompt_template
        self.logger = logger

    async def generate_post(
        self,
        state: State,
        insights: List[str],
    ) -> Dict[str, str]:
        keywords = ", ".join(state.get("keywords", [])) or "None"
        link = state.get("link") or "None"
        use_emojis = state.get("use_emojis", True)
        prompt = self.prompt_template.format(
            topic=state.get("topic", ""),
            tone=state.get("tone", ""),
            platform=state.get("platform", "linkedin"),
            keywords=keywords
        )
        
        emoji_instruction = "\nIMPORTANT: Use emojis in the content." if use_emojis else "\nIMPORTANT: Do NOT use emojis in the content."
        insight_block = "\n".join(f"- {point}" for point in insights) or "No insights provided."
        messages = [
            SystemMessage(
                content=(
                    "You return pure JSON for social copy requests with the keys: "
                    "post_body, headline, rationale, call_to_action, image_prompt."
                )
            ),
            HumanMessage(
                content=(
                    f"{prompt}\n\nTopic: {state.get('topic', '')}\n"
                    f"Tone: {state.get('tone', '')}\n"
                    f"Platform: {state.get('platform', 'linkedin')}\n"
                    f"Keywords: {keywords}\n"
                    f"Link: {link}\n"
                    f"Audience: {state.get('audience') or 'General'}\n"
                    f"Insights:\n{insight_block}{emoji_instruction}"
                )
            ),
        ]
        response = await self.llm.ainvoke(messages)
        default = {
            "post_body": "",
            "headline": "",
            "rationale": "",
            "call_to_action": "",
            "image_prompt": "",
        }
        data = extract_json(response.content, default)
        if self.logger:
            self.logger.debug("Copywriter output: %s", data)
        return data

