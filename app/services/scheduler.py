"""
Indexing scheduler - runs indexers on schedule.
"""

from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import async_session_maker
from app.indexers.github import GitHubIndexer
from app.indexers.huggingface import HuggingFaceIndexer
from app.indexers.civitai import CivitaiIndexer
from app.indexers.youtube import YouTubeIndexer
from app.indexers.reddit import RedditIndexer
from app.indexers.arxiv import ArxivIndexer
from app.indexers.dynamic import DynamicWebIndexer
from app.indexers.moltbook import MoltbookIndexer
from app.indexers.websearch import WebSearchIndexer

logger = logging.getLogger(__name__)


class IndexingScheduler:
    """Manages scheduled indexing jobs."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.indexers = {}
        self.last_run: Dict[str, datetime] = {}
        self.running = False

    def get_indexer(self, platform: str, db: AsyncSession):
        """Get indexer instance for a platform."""
        indexers = {
            "github": lambda: GitHubIndexer(
                db, api_token=os.environ.get("GITHUB_TOKEN")
            ),
            "huggingface": lambda: HuggingFaceIndexer(
                db, api_token=os.environ.get("HF_TOKEN")
            ),
            "civitai": lambda: CivitaiIndexer(
                db, api_token=os.environ.get("CIVITAI_TOKEN")
            ),
            "youtube": lambda: YouTubeIndexer(
                db, api_key=os.environ.get("YOUTUBE_API_KEY")
            ),
            "reddit": lambda: RedditIndexer(
                db,
                client_id=os.environ.get("REDDIT_CLIENT_ID"),
                client_secret=os.environ.get("REDDIT_CLIENT_SECRET"),
            ),
            "arxiv": lambda: ArxivIndexer(db),
            "dynamic": lambda: DynamicWebIndexer(db),
            "moltbook": lambda: MoltbookIndexer(db),
            "websearch": lambda: WebSearchIndexer(db),
        }
        return indexers.get(platform, lambda: None)()

    async def run_indexer(self, platform: str, limit: int = 100) -> Dict[str, Any]:
        """Run a single indexer."""
        logger.info(f"Running indexer for {platform}")

        async with async_session_maker() as db:
            indexer = self.get_indexer(platform, db)
            if not indexer:
                return {"error": f"Unknown platform: {platform}"}

            try:
                since = self.last_run.get(platform)
                stats = await indexer.run(since=since, limit=limit)
                self.last_run[platform] = datetime.utcnow()
                return stats
            except Exception as e:
                logger.error(f"Indexer {platform} failed: {e}")
                return {"error": str(e)}

    async def run_all_indexers(self, limit: int = 50) -> Dict[str, Any]:
        """Run all indexers."""
        platforms = [
            "websearch",
            "dynamic",
            "github",
            "huggingface",
            "civitai",
            "reddit",
            "arxiv",
        ]
        results = {}

        for platform in platforms:
            try:
                results[platform] = await self.run_indexer(platform, limit=limit)
                await asyncio.sleep(2)
            except Exception as e:
                results[platform] = {"error": str(e)}

        return results

    def schedule_jobs(self):
        """Set up scheduled indexing jobs."""
        # Dynamic web search - every 2 hours
        self.scheduler.add_job(
            self.run_indexer,
            IntervalTrigger(hours=2),
            id="websearch_indexer",
            args=["websearch", 30],
            replace_existing=True,
        )

        # Dynamic indexer (HackerNews, Dev.to, Medium) - every 3 hours
        self.scheduler.add_job(
            self.run_indexer,
            IntervalTrigger(hours=3),
            id="dynamic_indexer",
            args=["dynamic", 50],
            replace_existing=True,
        )

        # Moltbook - every 4 hours
        self.scheduler.add_job(
            self.run_indexer,
            IntervalTrigger(hours=4),
            id="moltbook_indexer",
            args=["moltbook", 30],
            replace_existing=True,
        )

        # GitHub - every 6 hours
        self.scheduler.add_job(
            self.run_indexer,
            IntervalTrigger(hours=6),
            id="github_indexer",
            args=["github", 50],
            replace_existing=True,
        )

        # HuggingFace - every 6 hours
        self.scheduler.add_job(
            self.run_indexer,
            IntervalTrigger(hours=6),
            id="huggingface_indexer",
            args=["huggingface", 50],
            replace_existing=True,
        )

        # Civitai - every 12 hours
        self.scheduler.add_job(
            self.run_indexer,
            IntervalTrigger(hours=12),
            id="civitai_indexer",
            args=["civitai", 50],
            replace_existing=True,
        )

        # Reddit - every 4 hours
        self.scheduler.add_job(
            self.run_indexer,
            IntervalTrigger(hours=4),
            id="reddit_indexer",
            args=["reddit", 30],
            replace_existing=True,
        )

        # arXiv - daily at 2 AM
        self.scheduler.add_job(
            self.run_indexer,
            CronTrigger(hour=2, minute=0),
            id="arxiv_indexer",
            args=["arxiv", 100],
            replace_existing=True,
        )

        logger.info("Scheduled indexing jobs configured")

    def start(self):
        """Start the scheduler."""
        if not self.running:
            self.schedule_jobs()
            self.scheduler.start()
            self.running = True
            logger.info("Indexing scheduler started")

    def stop(self):
        """Stop the scheduler."""
        if self.running:
            self.scheduler.shutdown()
            self.running = False
            logger.info("Indexing scheduler stopped")

    def get_jobs(self) -> list:
        """Get list of scheduled jobs."""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "next_run": str(job.next_run_time) if job.next_run_time else None,
                    "trigger": str(job.trigger),
                }
            )
        return jobs


# Global scheduler instance
scheduler = IndexingScheduler()
