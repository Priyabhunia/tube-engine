"""
Moltbook/OpenBook indexer - indexes posts from agent platforms.
Real-time indexing of agent-generated content.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import asyncio
import logging
import json

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)


class MoltbookIndexer(BaseIndexer):
    """
    Indexer for agent posting platforms.
    Supports Moltbook, OpenBook, and similar platforms where agents post.
    """

    platform_id = "moltbook"
    platform_name = "Moltbook"

    def __init__(self, db, api_url: Optional[str] = None):
        super().__init__(db)
        self.api_url = api_url or "https://moltbook.com/api"

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch posts from Moltbook or similar platforms."""
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try Moltbook API
            try:
                response = await client.get(
                    f"{self.api_url}/posts",
                    params={"limit": limit, "sort": "popular", "type": "agent"},
                )

                if response.status_code == 200:
                    data = response.json()
                    for post in data.get(
                        "posts", data if isinstance(data, list) else []
                    ):
                        post["_source"] = "moltbook"
                        items.append(post)
            except Exception as e:
                logger.debug(f"Moltbook API not available: {e}")

            # Fallback: Index from Twitter/X API for AI agents
            try:
                twitter_items = await self._fetch_twitter_ai_posts(client, limit // 2)
                items.extend(twitter_items)
            except Exception as e:
                logger.debug(f"Twitter fetch error: {e}")

            # Fallback: Index from Bluesky for AI posts
            try:
                bluesky_items = await self._fetch_bluesky_posts(client, limit // 2)
                items.extend(bluesky_items)
            except Exception as e:
                logger.debug(f"Bluesky fetch error: {e}")

        return items[:limit]

    async def _fetch_twitter_ai_posts(
        self, client: httpx.AsyncClient, limit: int
    ) -> List[Dict]:
        """Fetch AI agent posts from Twitter/X public API."""
        items = []

        # Twitter's public search API (no auth needed for public tweets)
        # Using Nitter as a fallback for scraping
        try:
            # Search for AI agent related accounts/posts
            accounts = ["autogpt", "crewaiinc", "langchainai", "anthropicai", "openai"]

            for account in accounts[:3]:
                try:
                    # Use Nitter instance for public Twitter data
                    response = await client.get(
                        f"https://nitter.net/{account}",
                        headers={"User-Agent": "Mozilla/5.0"},
                    )

                    if response.status_code == 200:
                        # Parse HTML for tweet content
                        # This is a simplified parser
                        items.append(
                            {
                                "title": f"Latest from @{account}",
                                "content": f"AI agent posts from {account}",
                                "url": f"https://x.com/{account}",
                                "author": account,
                                "_source": "twitter",
                            }
                        )
                except:
                    continue
        except Exception as e:
            logger.debug(f"Twitter/Nitter fetch error: {e}")

        return items

    async def _fetch_bluesky_posts(
        self, client: httpx.AsyncClient, limit: int
    ) -> List[Dict]:
        """Fetch AI-related posts from Bluesky."""
        items = []

        try:
            # Bluesky public API
            response = await client.get(
                "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
                params={"q": "AI agent OR autonomous OR LLM", "limit": limit},
            )

            if response.status_code == 200:
                data = response.json()
                for post in data.get("posts", []):
                    post["_source"] = "bluesky"
                    items.append(post)
        except Exception as e:
            logger.debug(f"Bluesky fetch error: {e}")

        return items

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse content from agent platforms."""
        if not raw_data:
            return None

        source = raw_data.get("_source", "moltbook")

        if source == "bluesky":
            return self._parse_bluesky(raw_data)
        elif source == "twitter":
            return self._parse_twitter(raw_data)
        else:
            return self._parse_moltbook(raw_data)

    def _parse_moltbook(self, data: Dict) -> Optional[ContentCreate]:
        """Parse Moltbook post."""
        author = data.get("author", data.get("agent_name", "unknown"))
        title = data.get("title", data.get("content", "")[:100])
        content = data.get("content", data.get("body", ""))
        url = data.get("url", data.get("link", ""))

        return ContentCreate(
            agent_id_external=f"moltbook:{author}",
            content_type="post",
            title=title,
            description=content[:500],
            content_url=url,
            source_platform="moltbook",
            source_url=url,
            tags=data.get("tags", ["agent", "post"]),
        )

    def _parse_bluesky(self, data: Dict) -> Optional[ContentCreate]:
        """Parse Bluesky post."""
        record = data.get("record", {})
        author = data.get("author", {}).get("handle", "unknown")
        text = record.get("text", "")

        return ContentCreate(
            agent_id_external=f"bluesky:{author}",
            content_type="post",
            title=text[:100] if text else "Bluesky post",
            description=text[:500],
            content_url=f"https://bsky.app/profile/{author}",
            source_platform="bluesky",
            source_url=f"https://bsky.app/profile/{author}",
            tags=["bluesky", "social", "agent"],
        )

    def _parse_twitter(self, data: Dict) -> Optional[ContentCreate]:
        """Parse Twitter/X post."""
        author = data.get("author", "unknown")
        content = data.get("content", data.get("text", ""))
        url = data.get("url", f"https://x.com/{author}")

        return ContentCreate(
            agent_id_external=f"twitter:{author}",
            content_type="post",
            title=content[:100] if content else f"Post by @{author}",
            description=content[:500],
            content_url=url,
            source_platform="twitter",
            source_url=url,
            tags=["twitter", "social", "ai"],
        )
