"""
YouTube indexer - indexes AI-generated videos.
Uses RSS feeds for channels and search.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import feedparser
import logging
import re

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)

# AI video channels/topics to index
AI_CHANNELS = [
    "UCmHOwcofUXmYlhjf4sYvA1w",  # AI explained channels
]
AI_SEARCH_TERMS = [
    "AI generated video",
    "autonomous AI agent",
    "AI art timelapse",
    "GPT-4 demo",
    "Claude AI",
    "AI music generation",
]


class YouTubeIndexer(BaseIndexer):
    """Indexer for YouTube videos."""

    platform_id = "youtube"
    platform_name = "YouTube"

    def __init__(self, db, api_key: Optional[str] = None):
        super().__init__(db)
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch AI-related videos from YouTube."""
        items = []

        if not self.api_key:
            # Use RSS feeds as fallback
            return await self._fetch_via_rss(limit)

        async with httpx.AsyncClient() as client:
            for query in AI_SEARCH_TERMS[:5]:
                try:
                    params = {
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "order": "date",
                        "maxResults": min(limit // len(AI_SEARCH_TERMS[:5]), 20),
                        "key": self.api_key,
                    }

                    response = await client.get(
                        f"{self.base_url}/search", params=params
                    )

                    if response.status_code == 200:
                        data = response.json()
                        for item in data.get("items", []):
                            item["_query"] = query
                            items.append(item)
                    elif response.status_code == 403:
                        logger.warning("YouTube API quota exceeded")
                        break

                except Exception as e:
                    logger.error(f"Error fetching from YouTube: {e}")

        return items[:limit]

    async def _fetch_via_rss(self, limit: int) -> List[Dict[str, Any]]:
        """Fetch videos via RSS feeds as fallback."""
        items = []

        async with httpx.AsyncClient() as client:
            for query in AI_SEARCH_TERMS[:5]:
                try:
                    # YouTube RSS search
                    rss_url = f"https://www.youtube.com/rss/search/{query}/videos"
                    response = await client.get(rss_url)

                    if response.status_code == 200:
                        feed = feedparser.parse(response.text)
                        for entry in feed.entries[: limit // 5]:
                            items.append(
                                {
                                    "id": {
                                        "videoId": self._extract_video_id(entry.link)
                                    },
                                    "snippet": {
                                        "title": entry.title,
                                        "description": entry.get(
                                            "description", entry.get("summary", "")
                                        ),
                                        "channelTitle": entry.get("author", "Unknown"),
                                        "publishedAt": entry.get("published", ""),
                                        "thumbnails": {},
                                    },
                                    "_query": query,
                                }
                            )
                except Exception as e:
                    logger.error(f"Error fetching YouTube RSS: {e}")

        return items

    def _extract_video_id(self, url: str) -> str:
        """Extract video ID from YouTube URL."""
        match = re.search(r"(?:v=|/v/|youtu\.be/)([^&\?/]+)", url)
        return match.group(1) if match else ""

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse YouTube video data."""
        if not raw_data:
            return None

        snippet = raw_data.get("snippet", {})
        video_id = raw_data.get("id", {}).get("videoId", "")

        if not video_id:
            return None

        title = snippet.get("title", "Untitled Video")
        channel = snippet.get("channelTitle", "Unknown Channel")
        description = snippet.get("description", "")[:500]

        url = f"https://www.youtube.com/watch?v={video_id}"

        # Determine tags from query
        query = raw_data.get("_query", "")
        tags = ["video", "ai"]
        if query:
            tags.extend(query.lower().split()[:3])

        return ContentCreate(
            agent_id_external=f"youtube:{channel}",
            content_type="video",
            title=title,
            description=description or f"Video by {channel}",
            content_url=url,
            thumbnail_url=snippet.get("thumbnails", {}).get("high", {}).get("url"),
            source_platform="youtube",
            source_url=url,
            tags=tags[:10],
        )
