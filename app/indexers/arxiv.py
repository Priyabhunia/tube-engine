"""
arXiv indexer - indexes AI research papers.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import xml.etree.ElementTree as ET
import logging

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)

# AI categories on arXiv
AI_CATEGORIES = [
    "cs.AI",  # Artificial Intelligence
    "cs.CL",  # Computation and Language
    "cs.LG",  # Machine Learning
    "cs.NE",  # Neural and Evolutionary Computing
    "cs.RO",  # Robotics
]


class ArxivIndexer(BaseIndexer):
    """Indexer for arXiv papers."""

    platform_id = "arxiv"
    platform_name = "arXiv"

    def __init__(self, db):
        super().__init__(db)
        self.base_url = "http://export.arxiv.org/api/query"

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch AI papers from arXiv."""
        items = []

        # Build search query
        query = "cat:" + " OR cat:".join(AI_CATEGORIES)

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                params = {
                    "search_query": query,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                    "max_results": limit,
                }

                response = await client.get(self.base_url, params=params)

                if response.status_code == 200:
                    root = ET.fromstring(response.text)

                    # Define namespace
                    ns = {"atom": "http://www.w3.org/2005/Atom"}

                    for entry in root.findall("atom:entry", ns):
                        item = {}

                        title_elem = entry.find("atom:title", ns)
                        item["title"] = (
                            title_elem.text if title_elem is not None else ""
                        )

                        summary_elem = entry.find("atom:summary", ns)
                        item["summary"] = (
                            summary_elem.text.strip()
                            if summary_elem is not None
                            else ""
                        )

                        # Get authors
                        authors = []
                        for author in entry.findall("atom:author", ns):
                            name_elem = author.find("atom:name", ns)
                            if name_elem is not None:
                                authors.append(name_elem.text)
                        item["authors"] = authors

                        # Get ID
                        id_elem = entry.find("atom:id", ns)
                        item["id"] = id_elem.text if id_elem is not None else ""

                        # Get published date
                        published_elem = entry.find("atom:published", ns)
                        item["published"] = (
                            published_elem.text if published_elem is not None else ""
                        )

                        # Get categories
                        categories = []
                        for cat in entry.findall("atom:category", ns):
                            term = cat.get("term")
                            if term:
                                categories.append(term)
                        item["categories"] = categories

                        items.append(item)

            except Exception as e:
                logger.error(f"Error fetching from arXiv: {e}")

        return items

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse arXiv paper data."""
        if not raw_data or not raw_data.get("id"):
            return None

        paper_id = raw_data["id"].split("/")[-1]
        url = f"https://arxiv.org/abs/{paper_id}"

        title = raw_data.get("title", "Untitled Paper").replace("\n", " ").strip()
        authors = raw_data.get("authors", ["Unknown"])

        # Filter for AI-agent related papers
        ai_agent_keywords = [
            "agent",
            "autonomous",
            "llm",
            "gpt",
            "language model",
            "multi-agent",
            "reasoning",
            "planning",
        ]
        content_lower = (title + " " + raw_data.get("summary", "")).lower()

        # Skip papers not related to AI agents
        if not any(kw in content_lower for kw in ai_agent_keywords):
            return None

        tags = raw_data.get("categories", ["research"])[:5]
        tags.append("paper")

        return ContentCreate(
            agent_id_external=f"arxiv:{authors[0] if authors else 'unknown'}",
            content_type="research",
            title=title,
            description=raw_data.get("summary", "")[:500],
            content_url=url,
            source_platform="arxiv",
            source_url=url,
            tags=tags,
            categories=raw_data.get("categories", [])[:3],
        )
