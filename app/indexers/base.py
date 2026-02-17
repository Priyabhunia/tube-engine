"""
Base indexer class for all platform indexers.
Each platform has its own indexer that fetches and indexes AI-generated content.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.entity import Agent, AgentContent
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)


class BaseIndexer(ABC):
    """Base class for all content indexers."""

    platform_id: str = ""
    platform_name: str = ""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.stats = {"indexed": 0, "skipped": 0, "errors": 0}

    @abstractmethod
    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch content from the platform.

        Args:
            since: Only fetch content newer than this timestamp
            limit: Maximum number of items to fetch

        Returns:
            List of raw content data from the platform
        """
        pass

    @abstractmethod
    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """
        Parse raw platform data into ContentCreate schema.

        Args:
            raw_data: Raw data from the platform API/scraper

        Returns:
            ContentCreate object or None if invalid
        """
        pass

    async def get_or_create_agent(self, agent_id: str, name: str, **kwargs) -> Agent:
        """Get existing agent or create a new one."""
        stmt = select(Agent).where(Agent.agent_id == agent_id)
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if agent:
            return agent

        agent = Agent(agent_id=agent_id, name=name, **kwargs)
        self.db.add(agent)
        await self.db.flush()
        return agent

    async def content_exists(self, source_url: str) -> bool:
        """Check if content already exists in database."""
        stmt = select(AgentContent).where(AgentContent.source_url == source_url)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def index_content(self, content: ContentCreate) -> Optional[AgentContent]:
        """Index a single content item."""
        try:
            # Check for duplicates
            if content.source_url and await self.content_exists(content.source_url):
                self.stats["skipped"] += 1
                return None

            # Get or create agent
            agent = await self.get_or_create_agent(
                agent_id=content.agent_id_external, name=content.agent_id_external
            )

            # Create content
            content_data = content.model_dump(exclude={"agent_id_external"})
            content_data["agent_id"] = agent.id

            db_content = AgentContent(**content_data)
            self.db.add(db_content)

            # Update agent's creation count
            agent.total_creations = (agent.total_creations or 0) + 1

            self.stats["indexed"] += 1
            return db_content

        except Exception as e:
            logger.error(f"Error indexing content: {e}")
            self.stats["errors"] += 1
            return None

    async def run(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> Dict[str, int]:
        """
        Run the indexer.

        Args:
            since: Only fetch content newer than this
            limit: Maximum items to fetch

        Returns:
            Statistics about the indexing run
        """
        logger.info(f"Starting indexer for {self.platform_name}")

        try:
            raw_items = await self.fetch_content(since=since, limit=limit)
            logger.info(f"Fetched {len(raw_items)} items from {self.platform_name}")

            for raw_item in raw_items:
                try:
                    content = self.parse_content(raw_item)
                    if content:
                        await self.index_content(content)
                except Exception as e:
                    logger.error(f"Error parsing item: {e}")
                    self.stats["errors"] += 1

            await self.db.commit()

        except Exception as e:
            logger.error(f"Indexer error for {self.platform_name}: {e}")
            await self.db.rollback()

        logger.info(f"Indexer finished: {self.stats}")
        return self.stats
