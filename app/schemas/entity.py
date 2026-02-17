from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


class AgentBase(BaseModel):
    agent_id: str
    name: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    agent_type: Optional[str] = None
    framework: Optional[str] = None
    capabilities: Optional[List[str]] = []
    creator: Optional[str] = None
    creator_url: Optional[str] = None


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    id: int
    is_verified: bool
    is_active: bool
    reputation_score: float
    total_creations: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ContentBase(BaseModel):
    content_type: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    content_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    tags: Optional[List[str]] = []
    categories: Optional[List[str]] = []
    language: Optional[str] = None
    license: Optional[str] = None


class ContentCreate(ContentBase):
    agent_id_external: str


class ContentResponse(ContentBase):
    id: int
    agent_id: int
    quality_score: float
    view_count: int
    like_count: int
    share_count: int
    download_count: int
    is_public: bool
    is_featured: bool
    indexed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    agent: Optional[AgentResponse] = None

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    results: List[ContentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    query: str


class SearchQuery(BaseModel):
    query: str = Field(..., min_length=1)
    content_type: Optional[str] = None
    agent_type: Optional[str] = None
    source_platform: Optional[str] = None
    tags: Optional[List[str]] = []
    sort_by: str = "relevance"
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class StatsResponse(BaseModel):
    total_agents: int
    total_contents: int
    total_documents: int
    total_videos: int
    total_posts: int
    total_code: int
    content_types: dict
    top_platforms: List[dict]
    recent_indexed: int
