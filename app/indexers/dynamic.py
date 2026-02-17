"""
Dynamic indexer that searches and indexes content in real-time.
Like Google - searches multiple platforms and indexes what's popular.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import asyncio
import logging
import re

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)

# Dynamic search terms - these update based on what's trending
TRENDING_AI_TOPICS = [
    "AI agent",
    "autonomous agent",
    "GPT-4",
    "Claude",
    "LLM",
    "LangChain",
    "AutoGPT",
    "CrewAI",
    "RAG",
    "vector database",
    "AI coding",
    "AI music",
    "AI art",
    "Stable Diffusion",
    "AI video",
]


class DynamicWebIndexer(BaseIndexer):
    """
    Dynamic indexer that searches the web for AI-related content.
    Uses multiple sources and APIs to find trending content.
    """

    platform_id = "dynamic"
    platform_name = "Dynamic Web"

    def __init__(self, db):
        super().__init__(db)
        self.sources = []

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch content from multiple dynamic sources."""
        items = []

        # Fetch from multiple sources in parallel
        tasks = [
            self._fetch_hackernews(limit // 4),
            self._fetch_devto(limit // 4),
            self._fetch_producthunt(limit // 4),
            self._fetch_medium(limit // 4),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                items.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Error fetching: {result}")

        return items[:limit]

    async def _fetch_hackernews(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch AI posts from Hacker News."""
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get top stories
                response = await client.get(
                    "https://hacker-news.firebaseio.com/v0/topstories.json"
                )
                story_ids = response.json()[: limit * 2]

                for story_id in story_ids[:limit]:
                    try:
                        story_resp = await client.get(
                            f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                        )
                        story = story_resp.json()

                        if story and story.get("url") and story.get("title"):
                            # Filter for AI-related content
                            title = story.get("title", "").lower()
                            if any(
                                topic.lower() in title for topic in TRENDING_AI_TOPICS
                            ):
                                story["_source"] = "hackernews"
                                items.append(story)
                    except Exception as e:
                        continue

            except Exception as e:
                logger.error(f"HackerNews fetch error: {e}")

        return items

    async def _fetch_devto(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch AI articles from Dev.to."""
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            for tag in ["ai", "machinelearning", "llm", "chatgpt"][:2]:
                try:
                    response = await client.get(
                        "https://dev.to/api/articles",
                        params={"tag": tag, "per_page": limit // 2, "top": 7},
                    )

                    if response.status_code == 200:
                        articles = response.json()
                        for article in articles:
                            article["_source"] = "devto"
                            items.append(article)
                except Exception as e:
                    logger.error(f"Dev.to fetch error: {e}")

        return items

    async def _fetch_producthunt(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch AI products from Product Hunt via scraping."""
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Product Hunt API alternative - scraping
                response = await client.get(
                    "https://www.producthunt.com/v1/posts/all",
                    params={"per_page": limit},
                    headers={"Accept": "application/json"},
                )

                # Fallback: use their public RSS-style feed
                if response.status_code != 200:
                    response = await client.get(
                        "https://www.producthunt.com/feed",
                        headers={"Accept": "application/xml"},
                    )
            except Exception as e:
                logger.debug(f"Product Hunt not accessible: {e}")

        return items

    async def _fetch_medium(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch AI articles from Medium via RSS."""
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            publications = [
                "towards-data-science",
                "the-generator",
                "artificial-intelligence-news",
            ]

            for pub in publications[:2]:
                try:
                    # Medium's public RSS feed
                    response = await client.get(f"https://medium.com/feed/{pub}")

                    if response.status_code == 200:
                        import xml.etree.ElementTree as ET

                        root = ET.fromstring(response.text)

                        ns = {"atom": "http://www.w3.org/2005/Atom"}

                        for item in root.findall(".//item")[: limit // 2]:
                            try:
                                entry = {
                                    "title": item.findtext("title", ""),
                                    "link": item.findtext("link", ""),
                                    "description": item.findtext("description", ""),
                                    "pubDate": item.findtext("pubDate", ""),
                                    "_source": "medium",
                                }

                                # Filter for AI content
                                desc = entry.get("description", "").lower()
                                title = entry.get("title", "").lower()
                                if any(
                                    t in title or t in desc
                                    for t in [
                                        "ai",
                                        "llm",
                                        "gpt",
                                        "agent",
                                        "machine learning",
                                    ]
                                ):
                                    items.append(entry)
                            except:
                                continue
                except Exception as e:
                    logger.debug(f"Medium fetch error for {pub}: {e}")

        return items

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse content from various sources."""
        if not raw_data:
            return None

        source = raw_data.get("_source", "unknown")

        if source == "hackernews":
            return self._parse_hackernews(raw_data)
        elif source == "devto":
            return self._parse_devto(raw_data)
        elif source == "medium":
            return self._parse_medium(raw_data)

        return None

    def _parse_hackernews(self, data: Dict) -> Optional[ContentCreate]:
        """Parse Hacker News story."""
        title = data.get("title", "")
        url = data.get("url", "")
        by = data.get("by", "unknown")
        score = data.get("score", 0)

        if not url:
            url = f"https://news.ycombinator.com/item?id={data.get('id')}"

        return ContentCreate(
            agent_id_external=f"hackernews:{by}",
            content_type="post",
            title=title,
            description=f"Hacker News post with {score} points. {data.get('text', '')[:200] if data.get('text') else ''}",
            content_url=url,
            source_platform="hackernews",
            source_url=url,
            tags=["hackernews", "community", "tech"],
        )

    def _parse_devto(self, data: Dict) -> Optional[ContentCreate]:
        """Parse Dev.to article."""
        title = data.get("title", "")
        url = data.get("url", "")
        user = data.get("user", {}).get("username", "unknown")
        desc = data.get("description", "") or data.get("body_markdown", "")[:500]
        tags = data.get("tag_list", ["dev"])

        return ContentCreate(
            agent_id_external=f"devto:{user}",
            content_type="document",
            title=title,
            description=desc,
            content_url=url,
            source_platform="devto",
            source_url=url,
            tags=tags[:10] if tags else ["dev"],
        )

    def _parse_medium(self, data: Dict) -> Optional[ContentCreate]:
        """Parse Medium article."""
        title = data.get("title", "")
        url = data.get("link", "")
        desc = data.get("description", "")[:500]

        return ContentCreate(
            agent_id_external="medium:author",
            content_type="document",
            title=title,
            description=desc,
            content_url=url,
            source_platform="medium",
            source_url=url,
            tags=["medium", "article", "ai"],
        )
