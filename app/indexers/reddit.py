"""
Reddit indexer - indexes AI agent discussions and posts.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import logging

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)

# AI-related subreddits
AI_SUBREDDITS = [
    "LocalLLaMA",
    "ChatGPT",
    "artificial",
    "MachineLearning",
    "OpenAI",
    "AnthropicAI",
    "AutoGPT",
    "LangChain",
    "StableDiffusion",
    "SillyTavernAI",
]


class RedditIndexer(BaseIndexer):
    """Indexer for Reddit posts."""

    platform_id = "reddit"
    platform_name = "Reddit"

    def __init__(
        self, db, client_id: Optional[str] = None, client_secret: Optional[str] = None
    ):
        super().__init__(db)
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://www.reddit.com"

    def _get_headers(self) -> Dict[str, str]:
        return {"User-Agent": "AgentVerse-Search/1.0"}

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch posts from AI subreddits."""
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for subreddit in AI_SUBREDDITS[:5]:
                try:
                    response = await client.get(
                        f"{self.base_url}/r/{subreddit}/hot.json",
                        params={"limit": limit // len(AI_SUBREDDITS[:5])},
                        headers=self._get_headers(),
                    )

                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get("data", {}).get("children", [])
                        for post in posts:
                            post_data = post.get("data", {})
                            post_data["_subreddit"] = subreddit
                            items.append(post_data)
                    elif response.status_code == 429:
                        logger.warning("Reddit rate limited")
                        break

                except Exception as e:
                    logger.error(f"Error fetching from Reddit r/{subreddit}: {e}")

        return items[:limit]

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse Reddit post data."""
        if not raw_data:
            return None

        # Filter: only AI-generated content or agent discussions
        title = raw_data.get("title", "")
        self_text = raw_data.get("selftext", "")
        subreddit = raw_data.get("_subreddit", "unknown")

        # Skip if not relevant
        ai_keywords = ["ai", "agent", "gpt", "llm", "autonomous", "generated", "bot"]
        content_lower = (title + " " + self_text).lower()
        if not any(kw in content_lower for kw in ai_keywords):
            return None

        author = raw_data.get("author", "unknown")
        post_id = raw_data.get("id", "")
        url = f"https://reddit.com{raw_data.get('permalink', '')}"

        # Determine if it's a link post or text post
        is_link = bool(raw_data.get("url") and not raw_data.get("is_self"))

        tags = ["reddit", subreddit.lower()]
        if raw_data.get("link_flair_text"):
            tags.append(raw_data["link_flair_text"].lower())

        return ContentCreate(
            agent_id_external=f"reddit:{author}",
            content_type="post",
            title=title,
            description=self_text[:500] if self_text else f"Post in r/{subreddit}",
            content=raw_data.get("url") if is_link else None,
            content_url=url,
            source_platform="reddit",
            source_url=url,
            tags=tags[:10],
        )
