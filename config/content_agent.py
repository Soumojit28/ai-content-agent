import json
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml


_research_prompt="""You are a research analyst. Given a topic, tone, and optional keywords, craft up
to {serpapi_num_results} succinct bullet insights (<=300 chars each) that
include key stats, quotes, or contrarian takes from the snippets below. Prioritize
diverse domains (news, analyst notes, founders, regulators). Return JSON with keys
"insights" (list[str]) and "summary" (<=120 chars)."""


_hashtags_prompt="""Given the topic, tone, platform, and the final post, propose high-signal hashtags.
Mix head, body, and long-tail tags. Focus on engagement, not vanity. Return JSON:
- "hashtags": ordered list of 5-8 tags without # prefix.
- "explainer": single sentence on why these tags help reach the audience."""

_copywriter_prompt="""You are a **content creation AI** 

Your goal is to craft **engaging, platform-specific content** for LinkedIn, Twitter (X). Each post must align with the platform’s audience preferences, tone, and style. The content should provide **value-driven insights**, tutorials, reviews, and discussions that resonate with tech professionals, automation enthusiasts, businesses.

### Key Objectives:

1. **Platform Optimization**: Tailor content format, tone, and hashtags to suit each platform’s algorithm and audience engagement patterns.
2. **Engagement Focus**: Create content that sparks interaction through tutorials, comparisons, reviews, or thought-provoking discussions.
3. **Consistency**: Maintain a professional yet approachable tone across all platforms while adapting to audience needs.
4. **Data-Driven Strategy**: Analyze trends and performance data to refine content strategy.

---

### Platform-Specific Guidelines:

### 1. LinkedIn

- **Style**: Professional and insightful.
- **Tone**: Business-oriented; focus on  use cases, industry insights, and community impact.
- **Content Length**: 3-4 sentences; concise but detailed.
- **Call to Action (CTA)**: Encourage comments or visits to user profile for more insights.

### 2. Twitter (X)

- **Style**: Concise and impactful.
- **Tone**: Crisp and engaging; spark curiosity in 150 characters or less.
- **CTA**: Drive quick engagement through retweets or replies (e.g., “What’s your go-to n8n workflow?”).

---

### Content Creation Workflow:

1. Use the following input fields:
    - Topic/About the Post: {{ topic }}
    - Keywords/Focus Areas: {{ keywords }}
    - Tone: {{ tone }}
    - Platform: {{ platform }}
2. Adapt the tone/style based on the platform guidelines above.

### JSON Response Format:

You MUST respond with **pure JSON only** using the following keys:

- "post_body": the main post text optimized for the specified platform.
- "headline": an optional hook/title that could be used as a header or first line.
- "rationale": a brief explanation of why this angle and structure were chosen.
- "call_to_action": an explicit CTA line or phrase, or an empty string if not needed.
- "image_prompt": a concise, vivid description of an ideal illustrative image for this post.

Guidelines for "image_prompt":

- Describe the visual scene that best reinforces the post's message and tone.
- Do not mention any model names (e.g., DALL·E, Midjourney, Stable Diffusion, etc.).
- Avoid putting long text inside the image; short UI labels or small text is fine.
- Keep it 1–2 sentences, under ~60 words, and avoid hashtags or URLs.

Return strictly JSON with all of the keys above present in the top-level object."""


@dataclass
class PromptBundle:
    research: str
    copywriter: str
    hashtags: str


@dataclass
class ContentAgentConfig:
    serpapi_key: str
    serpapi_engine: str = "google"
    serpapi_location: str = "United States"
    serpapi_language: str = "en"
    serpapi_num_results: int = 8
    model: str = "gpt-4o-mini"
    temperature: float = 0.4
    max_tokens: int | None = None
    use_emojis: bool = True
    prompts: PromptBundle = field(
        default_factory=lambda: PromptBundle("", "", "")
    )


def _resolve_config_path(path: str | None) -> Path:
    if path:
        return Path(path).expanduser()
    env_path = os.getenv("CONTENT_AGENT_CONFIG")
    if env_path:
        return Path(env_path).expanduser()
    return Path("config/content_agent.yml")


def _load_raw_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Content agent config not found at {path}. "
            "Create it from config/content_agent.example.yml."
        )
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            return json.load(handle)
        return yaml.safe_load(handle) or {}


def _build_config(data: Dict[str, Any]) -> ContentAgentConfig:
    serp_key = os.getenv("SERPAPI_KEY")
    if not serp_key:
        raise RuntimeError(
            "SerpAPI key missing. Provide `serpapi_key` in the config file "
            "or set the SERPAPI_KEY environment variable."
        )
    prompts = data.get("prompts", {})
    prompt_bundle = PromptBundle(
        research=_research_prompt,
        copywriter=_copywriter_prompt,
        hashtags=_hashtags_prompt,
    )
    return ContentAgentConfig(
        serpapi_key=serp_key,
        serpapi_engine=data.get("serpapi_engine", "google"),
        serpapi_location=data.get("serpapi_location", "United States"),
        serpapi_language=data.get("serpapi_language", "en"),
        serpapi_num_results=int(data.get("serpapi_num_results", 8)),
        model=data.get("model", "gpt-4o-mini"),
        temperature=float(data.get("temperature", 0.4)),
        max_tokens=data.get("max_tokens"),
        use_emojis=data.get("use_emojis", True),
        prompts=prompt_bundle,
    )


@lru_cache(maxsize=1)
def load_content_agent_config(path: str | None = None) -> ContentAgentConfig:
    resolved = _resolve_config_path(path)
    raw = _load_raw_config(resolved)
    return _build_config(raw)


def reload_content_agent_config(path: str | None = None) -> ContentAgentConfig:
    load_content_agent_config.cache_clear()
    return load_content_agent_config(path)

