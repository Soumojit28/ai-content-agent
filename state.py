from typing import Any, Dict, List, Optional, TypedDict


class ResearchSnippet(TypedDict, total=False):
    title: str
    link: str
    snippet: str
    source: str


class CopywritingOutput(TypedDict, total=False):
    post_body: str
    headline: str
    rationale: str
    call_to_action: Optional[str]
    image_prompt: str


class HashtagOutput(TypedDict, total=False):
    hashtags: List[str]
    explainer: str


class State(TypedDict, total=False):
    topic: str
    tone: str
    platform: str
    keywords: List[str]
    link: Optional[str]
    audience: Optional[str]
    request_id: Optional[str]
    use_emojis: bool
    insights: List[str]
    context_snippets: List[ResearchSnippet]
    research_summary: str
    post: CopywritingOutput
    hashtag_package: HashtagOutput
    metadata: Dict[str, Any]
    errors: List[str]