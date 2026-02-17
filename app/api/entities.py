from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.database import get_db
from app.schemas.entity import (
    ContentCreate,
    ContentResponse,
    SearchResult,
    SearchQuery,
    StatsResponse,
    AgentResponse,
)
from app.services.search import SearchService
from app.services.scheduler import scheduler

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/search", response_model=SearchResult)
async def search(
    query: str = Query(..., min_length=1),
    content_type: Optional[str] = None,
    agent_type: Optional[str] = None,
    source_platform: Optional[str] = None,
    tags: Optional[str] = None,
    sort_by: str = Query("relevance", pattern="^(relevance|recent|popular|liked)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = SearchService(db)

    tag_list = tags.split(",") if tags else []

    search_query = SearchQuery(
        query=query,
        content_type=content_type,
        agent_type=agent_type,
        source_platform=source_platform,
        tags=tag_list,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    results, total = await service.search_content(search_query)

    return SearchResult(
        results=[ContentResponse.model_validate(r) for r in results],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size if total > 0 else 0,
        query=query,
    )


@router.get("/content/{content_id}", response_model=ContentResponse)
async def get_content(content_id: int, db: AsyncSession = Depends(get_db)):
    service = SearchService(db)
    content = await service.get_content_by_id(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/content", response_model=ContentResponse)
async def create_content(content: ContentCreate, db: AsyncSession = Depends(get_db)):
    service = SearchService(db)
    return await service.create_content(content)


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    service = SearchService(db)
    return await service.get_stats()


@router.get("/content-types", response_model=List[str])
async def get_content_types(db: AsyncSession = Depends(get_db)):
    service = SearchService(db)
    return await service.get_content_types()


@router.get("/platforms", response_model=List[str])
async def get_platforms(db: AsyncSession = Depends(get_db)):
    service = SearchService(db)
    return await service.get_platforms()


@router.get("/tags", response_model=List[str])
async def get_tags(db: AsyncSession = Depends(get_db)):
    service = SearchService(db)
    return await service.get_tags()


@router.get("/agent-types", response_model=List[str])
async def get_agent_types(db: AsyncSession = Depends(get_db)):
    service = SearchService(db)
    return await service.get_agent_types()


@router.get("/featured", response_model=List[ContentResponse])
async def get_featured(
    limit: int = Query(6, ge=1, le=20), db: AsyncSession = Depends(get_db)
):
    service = SearchService(db)
    return await service.get_featured_content(limit)


@router.get("/recent", response_model=List[ContentResponse])
async def get_recent(
    limit: int = Query(12, ge=1, le=50), db: AsyncSession = Depends(get_db)
):
    service = SearchService(db)
    return await service.get_recent_content(limit)


# Admin endpoints for indexing
@router.post("/admin/index/{platform}")
async def trigger_index(
    platform: str,
    limit: int = Query(50, ge=1, le=200),
    background_tasks: BackgroundTasks = None,
):
    """Manually trigger indexing for a specific platform."""
    valid_platforms = [
        "websearch",  # Dynamic web search (DuckDuckGo, feeds)
        "dynamic",  # HackerNews, Dev.to, Medium
        "moltbook",  # Agent posting platforms
        "github",  # AI repositories
        "huggingface",  # Models and datasets
        "civitai",  # AI art models
        "reddit",  # AI discussions
        "arxiv",  # Research papers
        "youtube",  # AI videos
    ]
    if platform not in valid_platforms:
        raise HTTPException(
            status_code=400, detail=f"Invalid platform. Choose from: {valid_platforms}"
        )

    # Run in background
    import asyncio

    result = await scheduler.run_indexer(platform, limit=limit)
    return {"platform": platform, "status": "completed", "result": result}


@router.post("/admin/index-all")
async def trigger_index_all(limit: int = Query(30, ge=1, le=100)):
    """Manually trigger indexing for all platforms."""
    result = await scheduler.run_all_indexers(limit=limit)
    return {"status": "completed", "results": result}


@router.get("/admin/schedule")
async def get_schedule():
    """Get scheduled indexing jobs."""
    return {"jobs": scheduler.get_jobs()}


@router.get("/platforms/available")
async def get_available_platforms():
    """Get list of available platforms for indexing."""
    from app.platforms.registry import PLATFORMS

    return [
        {
            "id": p.id,
            "name": p.name,
            "type": p.type.value,
            "has_api": p.has_api,
            "icon": p.icon,
        }
        for p in PLATFORMS.values()
    ]
