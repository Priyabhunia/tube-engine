"""
GitHub indexer - indexes AI-generated repositories and projects.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import logging

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)

# AI agent keywords to search for
AI_KEYWORDS = [
    "ai-agent",
    "autonomous-agent",
    "llm-agent",
    "gpt-agent",
    "auto-gpt",
    "babyagi",
    "langchain",
    "crewai",
    "autogen",
    "llamaindex",
    "agent-framework",
    "ai-assistant",
    "ai-generated",
    "auto-generated",
    "llm-generated",
]


class GitHubIndexer(BaseIndexer):
    """Indexer for GitHub repositories."""

    platform_id = "github"
    platform_name = "GitHub"

    def __init__(self, db, api_token: Optional[str] = None):
        super().__init__(db)
        self.api_token = api_token
        self.base_url = "https://api.github.com"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AgentVerse-Search/1.0",
        }
        if self.api_token:
            headers["Authorization"] = f"token {self.api_token}"
        return headers

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch AI-related repositories from GitHub."""
        items = []

        async with httpx.AsyncClient() as client:
            for keyword in AI_KEYWORDS[:5]:  # Limit keywords to avoid rate limiting
                try:
                    params = {
                        "q": f"{keyword} in:name,description,topics",
                        "sort": "updated",
                        "order": "desc",
                        "per_page": min(limit // len(AI_KEYWORDS[:5]), 30),
                    }

                    if since:
                        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
                        params["q"] += f" pushed:>{since_str}"

                    response = await client.get(
                        f"{self.base_url}/search/repositories",
                        params=params,
                        headers=self._get_headers(),
                    )

                    if response.status_code == 200:
                        data = response.json()
                        items.extend(data.get("items", []))
                    elif response.status_code == 403:
                        logger.warning("GitHub rate limit reached")
                        break

                except Exception as e:
                    logger.error(f"Error fetching from GitHub: {e}")

        return items[:limit]

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse GitHub repository data."""
        if not raw_data:
            return None

        repo_url = raw_data.get("html_url", "")
        owner = raw_data.get("owner", {}).get("login", "unknown")
        name = raw_data.get("name", "unknown")

        # Determine if this is likely AI-generated based on topics/description
        topics = raw_data.get("topics", [])
        description = raw_data.get("description", "") or ""

        # Extract tags from topics
        tags = [t for t in topics if t]
        if not tags:
            tags = ["code", "repository"]

        return ContentCreate(
            agent_id_external=f"github:{owner}",
            content_type="code",
            title=raw_data.get("full_name", name),
            description=description[:500] if description else f"Repository by {owner}",
            content_url=repo_url,
            source_platform="github",
            source_url=repo_url,
            tags=tags[:10],
            categories=["open-source"] if not raw_data.get("private") else [],
            language=raw_data.get("language"),
            license=raw_data.get("license", {}).get("spdx_id")
            if raw_data.get("license")
            else None,
        )
