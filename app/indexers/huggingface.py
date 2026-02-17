"""
Hugging Face indexer - indexes AI models, datasets, and spaces.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
import logging

from app.indexers.base import BaseIndexer
from app.schemas.entity import ContentCreate

logger = logging.getLogger(__name__)


class HuggingFaceIndexer(BaseIndexer):
    """Indexer for Hugging Face models and datasets."""

    platform_id = "huggingface"
    platform_name = "Hugging Face"

    def __init__(self, db, api_token: Optional[str] = None):
        super().__init__(db)
        self.api_token = api_token
        self.base_url = "https://huggingface.co/api"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"User-Agent": "AgentVerse-Search/1.0"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    async def fetch_content(
        self, since: Optional[datetime] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Fetch models from Hugging Face."""
        items = []

        async with httpx.AsyncClient() as client:
            # Fetch trending models
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    params={
                        "limit": limit,
                        "full": "true",
                        "sort": "downloads",
                        "direction": "-1",
                    },
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    models = response.json()
                    for model in models:
                        model["_content_type"] = "model"
                        items.append(model)

            except Exception as e:
                logger.error(f"Error fetching models from HuggingFace: {e}")

            # Fetch trending datasets
            try:
                response = await client.get(
                    f"{self.base_url}/datasets",
                    params={
                        "limit": limit // 2,
                        "full": "true",
                        "sort": "downloads",
                        "direction": "-1",
                    },
                    headers=self._get_headers(),
                )

                if response.status_code == 200:
                    datasets = response.json()
                    for dataset in datasets:
                        dataset["_content_type"] = "dataset"
                        items.append(dataset)

            except Exception as e:
                logger.error(f"Error fetching datasets from HuggingFace: {e}")

        return items[:limit]

    def parse_content(self, raw_data: Dict[str, Any]) -> Optional[ContentCreate]:
        """Parse HuggingFace model/dataset data."""
        if not raw_data:
            return None

        model_id = raw_data.get("id", "")
        content_type = raw_data.get("_content_type", "model")
        author = raw_data.get("author", "unknown")

        # Build URL
        if content_type == "dataset":
            url = f"https://huggingface.co/datasets/{model_id}"
        else:
            url = f"https://huggingface.co/{model_id}"

        # Extract tags
        tags = raw_data.get("tags", [])[:10]
        if not tags:
            tags = [content_type, "ai"]

        # Get description from card data
        card_data = raw_data.get("cardData", {})
        description = card_data.get("description", "") or raw_data.get(
            "description", ""
        )

        return ContentCreate(
            agent_id_external=f"huggingface:{author}",
            content_type=content_type,
            title=model_id,
            description=description[:500]
            if description
            else f"{content_type.title()} by {author}",
            content_url=url,
            source_platform="huggingface",
            source_url=url,
            tags=tags,
            categories=[content_type],
            license=card_data.get("license"),
        )
