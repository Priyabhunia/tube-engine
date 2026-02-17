"""
Civitai indexer - indexes Stable Diffusion models and AI art.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import logging

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)


class CivitaiIndexer(BaseIndexer):
    """Indexer for Civitai models."""

    platform_id = "civitai"
    platform_name = "Civitai"

    def __init__(self, db, api_token: Optional[str] = None):
        super().__init__(db)
        self.api_token = api_token
        self.base_url = "https://civitai.com/api/v1"

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch models from Civitai."""
        items = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                params = {
                    "limit": limit,
                    "sort": "Newest",
                }

                response = await client.get(f"{self.base_url}/models", params=params)

                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                else:
                    logger.warning(f"Civitai returned status {response.status_code}")

            except Exception as e:
                logger.error(f"Error fetching from Civitai: {e}")

        return items

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse Civitai model data."""
        if not raw_data:
            return None

        model_id = raw_data.get("id", 0)
        name = raw_data.get("name", "Unknown Model")
        creator = raw_data.get("creator", {}).get("username", "unknown")

        # Build URL
        url = f"https://civitai.com/models/{model_id}"

        # Get description
        description = (
            raw_data.get("description", "")[:500]
            if raw_data.get("description")
            else f"AI model by {creator}"
        )

        # Extract tags
        tags = raw_data.get("tags", [])[:10]
        model_type = raw_data.get("type", "Checkpoint")

        # Determine content type based on model type
        content_type = "artwork"  # Default for image models
        if model_type == "Checkpoint":
            tags.insert(0, "checkpoint")
        elif model_type == "LORA":
            tags.insert(0, "lora")

        return ContentCreate(
            agent_id_external=f"civitai:{creator}",
            content_type=content_type,
            title=name,
            description=description,
            content_url=url,
            source_platform="civitai",
            source_url=url,
            tags=tags,
            categories=[model_type.lower()],
            license=raw_data.get("allowCommercialUse", "Unknown"),
        )
