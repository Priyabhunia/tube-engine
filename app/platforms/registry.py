"""
Platform registry for content sources.
Each platform has an indexer that fetches AI-generated content.
"""

from enum import Enum
from typing import Dict, Type, Optional
from dataclasses import dataclass


class PlatformType(str, Enum):
    VIDEO = "video"
    CODE = "code"
    DOCUMENT = "document"
    POST = "post"
    ART = "art"
    MUSIC = "music"
    RESEARCH = "research"
    MODEL = "model"


@dataclass
class Platform:
    id: str
    name: str
    url: str
    type: PlatformType
    description: str
    icon: str
    has_api: bool
    api_url: Optional[str] = None
    indexer_class: Optional[str] = None


# Real platforms where AI agents create content
PLATFORMS: Dict[str, Platform] = {
    # Video Platforms
    "youtube": Platform(
        id="youtube",
        name="YouTube",
        url="https://youtube.com",
        type=PlatformType.VIDEO,
        description="AI-generated videos, animations, documentaries",
        icon="▶️",
        has_api=True,
        api_url="https://www.googleapis.com/youtube/v3",
        indexer_class="YouTubeIndexer",
    ),
    "tiktok": Platform(
        id="tiktok",
        name="TikTok",
        url="https://tiktok.com",
        type=PlatformType.VIDEO,
        description="Short AI-generated video content",
        icon="📱",
        has_api=False,
        indexer_class="TikTokIndexer",
    ),
    # Code Platforms
    "github": Platform(
        id="github",
        name="GitHub",
        url="https://github.com",
        type=PlatformType.CODE,
        description="AI-generated code repositories and projects",
        icon="🐙",
        has_api=True,
        api_url="https://api.github.com",
        indexer_class="GitHubIndexer",
    ),
    "huggingface": Platform(
        id="huggingface",
        name="Hugging Face",
        url="https://huggingface.co",
        type=PlatformType.MODEL,
        description="AI models, datasets, and spaces created by agents",
        icon="🤗",
        has_api=True,
        api_url="https://huggingface.co/api",
        indexer_class="HuggingFaceIndexer",
    ),
    # Post/Social Platforms
    "reddit": Platform(
        id="reddit",
        name="Reddit",
        url="https://reddit.com",
        type=PlatformType.POST,
        description="AI agent discussions and posts",
        icon="🔴",
        has_api=True,
        api_url="https://www.reddit.com/api",
        indexer_class="RedditIndexer",
    ),
    "twitter": Platform(
        id="twitter",
        name="X (Twitter)",
        url="https://x.com",
        type=PlatformType.POST,
        description="AI agent tweets and threads",
        icon="🐦",
        has_api=True,
        api_url="https://api.twitter.com/2",
        indexer_class="TwitterIndexer",
    ),
    "medium": Platform(
        id="medium",
        name="Medium",
        url="https://medium.com",
        type=PlatformType.DOCUMENT,
        description="AI-written articles and blog posts",
        icon="📝",
        has_api=False,
        indexer_class="MediumIndexer",
    ),
    # Art Platforms
    "artstation": Platform(
        id="artstation",
        name="ArtStation",
        url="https://artstation.com",
        type=PlatformType.ART,
        description="AI-generated digital artwork",
        icon="🎨",
        has_api=False,
        indexer_class="ArtStationIndexer",
    ),
    "deviantart": Platform(
        id="deviantart",
        name="DeviantArt",
        url="https://deviantart.com",
        type=PlatformType.ART,
        description="AI-generated art and illustrations",
        icon="🖌️",
        has_api=True,
        api_url="https://www.deviantart.com/api/v1/oauth2",
        indexer_class="DeviantArtIndexer",
    ),
    "civitai": Platform(
        id="civitai",
        name="Civitai",
        url="https://civitai.com",
        type=PlatformType.MODEL,
        description="Stable Diffusion models and AI art",
        icon="🖼️",
        has_api=True,
        api_url="https://civitai.com/api/v1",
        indexer_class="CivitaiIndexer",
    ),
    # Music Platforms
    "soundcloud": Platform(
        id="soundcloud",
        name="SoundCloud",
        url="https://soundcloud.com",
        type=PlatformType.MUSIC,
        description="AI-composed music tracks",
        icon="🎵",
        has_api=True,
        api_url="https://api.soundcloud.com",
        indexer_class="SoundCloudIndexer",
    ),
    "bandcamp": Platform(
        id="bandcamp",
        name="Bandcamp",
        url="https://bandcamp.com",
        type=PlatformType.MUSIC,
        description="AI-generated music albums",
        icon="💿",
        has_api=False,
        indexer_class="BandcampIndexer",
    ),
    # Research Platforms
    "arxiv": Platform(
        id="arxiv",
        name="arXiv",
        url="https://arxiv.org",
        type=PlatformType.RESEARCH,
        description="AI-written research papers",
        icon="📚",
        has_api=True,
        api_url="http://export.arxiv.org/api/query",
        indexer_class="ArxivIndexer",
    ),
    "paperswithcode": Platform(
        id="paperswithcode",
        name="Papers With Code",
        url="https://paperswithcode.com",
        type=PlatformType.RESEARCH,
        description="AI research with code implementations",
        icon="📄",
        has_api=True,
        api_url="https://paperswithcode.com/api/v1",
        indexer_class="PapersWithCodeIndexer",
    ),
    # General/Collections
    "producthunt": Platform(
        id="producthunt",
        name="Product Hunt",
        url="https://producthunt.com",
        type=PlatformType.POST,
        description="AI agent products and tools",
        icon="🚀",
        has_api=True,
        api_url="https://api.producthunt.com/v2",
        indexer_class="ProductHuntIndexer",
    ),
}


def get_platform(platform_id: str) -> Optional[Platform]:
    return PLATFORMS.get(platform_id)


def get_all_platforms() -> Dict[str, Platform]:
    return PLATFORMS


def get_platforms_by_type(platform_type: PlatformType) -> list[Platform]:
    return [p for p in PLATFORMS.values() if p.type == platform_type]
