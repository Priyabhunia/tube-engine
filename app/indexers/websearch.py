"""
Web Search Indexer - searches the web like Google and indexes AI-related content.
Uses DuckDuckGo and other search APIs to find content dynamically.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import asyncio
import logging
import urllib.parse

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)

# Search queries that find AI agent content
SEARCH_QUERIES = [
    "AI agent autonomous",
    "GPT agent framework",
    "LLM agent tutorial",
    "AI coding assistant",
    "autonomous AI bot",
    "AI generated content",
    "agent workflow automation",
]


class WebSearchIndexer(BaseIndexer):
    """
    Searches the web dynamically for AI agent content.
    Like Google - finds and indexes relevant content in real-time.
    """

    platform_id = "websearch"
    platform_name = "Web Search"

    def __init__(self, db):
        super().__init__(db)

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search the web for AI-related content.
        Uses multiple search APIs to find relevant content.
        """
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Use DuckDuckGo Instant Answer API (free, no auth)
            for query in SEARCH_QUERIES[:5]:
                try:
                    search_items = await self._search_duckduckgo(
                        client, query, limit // 5
                    )
                    items.extend(search_items)
                    await asyncio.sleep(0.5)  # Rate limiting
                except Exception as e:
                    logger.error(f"Search error for '{query}': {e}")

        # Also fetch from discovery APIs
        try:
            discovery_items = await self._fetch_discovery_feeds(client, limit // 2)
            items.extend(discovery_items)
        except Exception as e:
            logger.debug(f"Discovery fetch error: {e}")

        return items[:limit]

    async def _search_duckduckgo(
        self, client: httpx.AsyncClient, query: str, limit: int
    ) -> List[Dict]:
        """
        Search using DuckDuckGo Instant Answer API.
        Free and requires no authentication.
        """
        items = []

        try:
            # DuckDuckGo Instant Answer API
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )

            if response.status_code == 200:
                data = response.json()

                # Related topics
                for topic in data.get("RelatedTopics", [])[:limit]:
                    if isinstance(topic, dict) and topic.get("FirstURL"):
                        items.append(
                            {
                                "title": topic.get("Text", "")[:200],
                                "url": topic.get("FirstURL", ""),
                                "description": topic.get("Text", ""),
                                "_source": "duckduckgo",
                                "_query": query,
                            }
                        )

                # Abstract
                if data.get("Abstract"):
                    items.append(
                        {
                            "title": data.get("Heading", query),
                            "url": data.get("AbstractURL", ""),
                            "description": data.get("Abstract", ""),
                            "_source": "duckduckgo",
                            "_query": query,
                        }
                    )
        except Exception as e:
            logger.debug(f"DuckDuckGo search error: {e}")

        return items

    async def _fetch_discovery_feeds(
        self, client: httpx.AsyncClient, limit: int
    ) -> List[Dict]:
        """Fetch from discovery/feed APIs."""
        items = []

        # Fetch from AI-related RSS/API feeds
        feeds = [
            ("https://r.jina.ai/http://feeds.feedburner.com/oreilly/radar", "oreilly"),
            ("https://r.jina.ai/http://feeds.arxiv.org/arxiv/cs.AI", "arxiv-rss"),
            (
                "https://r.jina.ai/https://www.artificialintelligence-news.com/feed/",
                "ai-news",
            ),
        ]

        for feed_url, source in feeds[:2]:
            try:
                # Use Jina AI reader API to get clean content
                response = await client.get(feed_url)

                if response.status_code == 200:
                    # Parse the simplified content
                    content = response.text

                    # Extract articles (simplified parsing)
                    lines = content.split("\n")
                    current_item = {}

                    for line in lines:
                        if line.startswith("Title:"):
                            if current_item.get("title"):
                                current_item["_source"] = source
                                items.append(current_item)
                            current_item = {"title": line[6:].strip()}
                        elif line.startswith("URL:"):
                            current_item["url"] = line[4:].strip()
                        elif current_item.get("title") and not current_item.get(
                            "description"
                        ):
                            current_item["description"] = line[:500]

                    if current_item.get("title"):
                        current_item["_source"] = source
                        items.append(current_item)

            except Exception as e:
                logger.debug(f"Feed fetch error for {source}: {e}")

        return items[:limit]

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse search results into content."""
        if not raw_data:
            return None

        source = raw_data.get("_source", "web")
        title = raw_data.get("title", "")
        url = raw_data.get("url", "")
        description = raw_data.get("description", "")
        query = raw_data.get("_query", "ai")

        if not url or not title:
            return None

        # Determine content type from URL
        content_type = "post"
        if "youtube.com" in url or "vimeo.com" in url:
            content_type = "video"
        elif "github.com" in url:
            content_type = "code"
        elif "arxiv.org" in url:
            content_type = "research"
        elif "medium.com" in url or "blog" in url:
            content_type = "document"

        # Extract domain for platform
        try:
            domain = urllib.parse.urlparse(url).netloc.replace("www.", "")
        except:
            domain = source

        return ContentCreate(
            agent_id_external=f"web:{domain}",
            content_type=content_type,
            title=title,
            description=description[:500]
            if description
            else f"Found via search: {query}",
            content_url=url,
            source_platform=domain[:50],
            source_url=url,
            tags=[query, source, content_type],
        )
