import asyncio
from typing import Any, Dict, List, Optional

import httpx


SERPAPI_URL = "https://serpapi.com/search"


class SerpApiError(RuntimeError):
    """Raised when SerpAPI returns an error payload."""


class SerpClient:
    def __init__(
        self,
        api_key: str,
        *,
        engine: str = "google",
        location: str = "United States",
        language: str = "en",
        num_results: int = 8,
        timeout: float = 15.0,
        retries: int = 3,
        logger=None,
    ):
        self.api_key = api_key
        self.engine = engine
        self.location = location
        self.language = language
        self.num_results = num_results
        self.timeout = timeout
        self.retries = retries
        self.logger = logger

    async def fetch_context(
        self,
        *,
        topic: str,
        keywords: Optional[List[str]] = None,
        link: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = self._build_query(topic, keywords, link)
        params = {
            "engine": self.engine,
            "api_key": self.api_key,
            "q": query,
            "num": self.num_results,
            "location": self.location,
            "hl": self.language,
        }
        payload = await self._request_with_retry(params)
        return self._normalize_results(payload, query)

    def _build_query(
        self, topic: str, keywords: Optional[List[str]], link: Optional[str]
    ) -> str:
        keyword_fragment = " ".join(keywords or [])
        link_fragment = f" site:{link}" if link else ""
        base = topic.strip()
        query = " ".join(fragment for fragment in [base, keyword_fragment] if fragment)
        return f"{query}{link_fragment}".strip()

    async def _request_with_retry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        delay = 1.0
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                return await self._perform_request(params)
            except Exception as exc:  # pragma: no cover
                last_error = exc
                if self.logger:
                    self.logger.warning(
                        "SerpAPI request failed (attempt %s/%s): %s",
                        attempt,
                        self.retries,
                        exc,
                    )
                await asyncio.sleep(delay)
                delay *= 2
        raise SerpApiError(f"SerpAPI request failed after {self.retries} attempts") from last_error

    async def _perform_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(SERPAPI_URL, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("error"):
                raise SerpApiError(data["error"])
            return data

    def _normalize_results(
        self, payload: Dict[str, Any], query: str
    ) -> List[Dict[str, Any]]:
        organic = payload.get("organic_results", [])
        news = payload.get("news_results", [])
        people_also_ask = payload.get("related_questions", [])
        combined: List[Dict[str, Any]] = []

        def _push(item: Dict[str, Any], source: str):
            snippet = {
                "title": item.get("title") or item.get("question") or "Untitled",
                "link": item.get("link") or item.get("source"),
                "snippet": item.get("snippet")
                or item.get("answer")
                or item.get("description")
                or "",
                "source": source,
            }
            combined.append(snippet)

        for entry in organic[: self.num_results]:
            _push(entry, entry.get("source") or "organic")
        for entry in news[: self.num_results]:
            _push(entry, entry.get("source") or "news")
        for entry in people_also_ask[:2]:
            _push(entry, "related_question")

        if not combined:
            combined.append(
                {
                    "title": f"No public snippets for {query}",
                    "link": "",
                    "snippet": "SerpAPI returned no organic results.",
                    "source": "serpapi",
                }
            )
        return combined[: self.num_results]

