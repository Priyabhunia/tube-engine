from sqlalchemy import select, or_, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional, Tuple
from app.models.entity import Agent, AgentContent
from app.schemas.entity import SearchQuery, ContentCreate, AgentCreate


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_content(
        self, query: SearchQuery
    ) -> Tuple[List[AgentContent], int]:
        search_term = f"%{query.query}%"

        conditions = [
            or_(
                AgentContent.title.ilike(search_term),
                AgentContent.description.ilike(search_term),
                AgentContent.content.ilike(search_term),
                AgentContent.tags.contains([query.query.lower()]),
            )
        ]

        if query.content_type:
            conditions.append(AgentContent.content_type == query.content_type)

        if query.source_platform:
            conditions.append(
                AgentContent.source_platform.ilike(f"%{query.source_platform}%")
            )

        if query.tags:
            for tag in query.tags:
                conditions.append(AgentContent.tags.contains([tag]))

        if query.agent_type:
            conditions.append(Agent.agent_type == query.agent_type)

        sort_column = AgentContent.quality_score
        if query.sort_by == "recent":
            sort_column = AgentContent.indexed_at
        elif query.sort_by == "popular":
            sort_column = AgentContent.view_count
        elif query.sort_by == "liked":
            sort_column = AgentContent.like_count

        stmt = (
            select(AgentContent)
            .join(Agent)
            .options(selectinload(AgentContent.agent))
            .where(and_(*conditions))
            .order_by(desc(sort_column))
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await self.db.scalar(count_stmt) or 0

        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        result = await self.db.execute(stmt)

        return result.scalars().all(), total

    async def get_content_by_id(self, content_id: int) -> Optional[AgentContent]:
        stmt = (
            select(AgentContent)
            .options(selectinload(AgentContent.agent))
            .where(AgentContent.id == content_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_agent(self, agent: AgentCreate) -> Agent:
        db_agent = Agent(**agent.model_dump())
        self.db.add(db_agent)
        await self.db.commit()
        await self.db.refresh(db_agent)
        return db_agent

    async def get_or_create_agent(self, agent_id: str, name: str, **kwargs) -> Agent:
        stmt = select(Agent).where(Agent.agent_id == agent_id)
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if agent:
            return agent

        agent_data = {"agent_id": agent_id, "name": name, **kwargs}
        return await self.create_agent(AgentCreate(**agent_data))

    async def create_content(self, content: ContentCreate) -> AgentContent:
        stmt = select(Agent).where(Agent.agent_id == content.agent_id_external)
        result = await self.db.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            agent = await self.create_agent(
                AgentCreate(
                    agent_id=content.agent_id_external, name=content.agent_id_external
                )
            )

        content_data = content.model_dump(exclude={"agent_id_external"})
        content_data["agent_id"] = agent.id

        db_content = AgentContent(**content_data)
        self.db.add(db_content)

        agent.total_creations = (agent.total_creations or 0) + 1

        await self.db.commit()
        await self.db.refresh(db_content)

        return db_content

    async def get_stats(self) -> dict:
        total_agents = await self.db.scalar(select(func.count(Agent.id))) or 0
        total_contents = await self.db.scalar(select(func.count(AgentContent.id))) or 0

        content_type_counts = {}
        for ct in [
            "document",
            "video",
            "post",
            "code",
            "artwork",
            "music",
            "research",
            "conversation",
            "dataset",
            "simulation",
        ]:
            count = (
                await self.db.scalar(
                    select(func.count(AgentContent.id)).where(
                        AgentContent.content_type == ct
                    )
                )
                or 0
            )
            content_type_counts[ct] = count

        platform_stmt = (
            select(
                AgentContent.source_platform, func.count(AgentContent.id).label("count")
            )
            .where(AgentContent.source_platform.isnot(None))
            .group_by(AgentContent.source_platform)
            .order_by(desc("count"))
            .limit(10)
        )
        platform_result = await self.db.execute(platform_stmt)
        top_platforms = [{"platform": p, "count": c} for p, c in platform_result.all()]

        return {
            "total_agents": total_agents,
            "total_contents": total_contents,
            "total_documents": content_type_counts.get("document", 0),
            "total_videos": content_type_counts.get("video", 0),
            "total_posts": content_type_counts.get("post", 0),
            "total_code": content_type_counts.get("code", 0),
            "content_types": content_type_counts,
            "top_platforms": top_platforms,
            "recent_indexed": 0,
        }

    async def get_content_types(self) -> List[str]:
        result = await self.db.execute(
            select(AgentContent.content_type)
            .distinct()
            .where(AgentContent.content_type.isnot(None))
        )
        return [r for r in result.scalars().all() if r]

    async def get_platforms(self) -> List[str]:
        result = await self.db.execute(
            select(AgentContent.source_platform)
            .distinct()
            .where(AgentContent.source_platform.isnot(None))
        )
        return [r for r in result.scalars().all() if r]

    async def get_tags(self) -> List[str]:
        result = await self.db.execute(select(AgentContent.tags))
        all_tags = set()
        for row in result.scalars().all():
            if row:
                all_tags.update(row)
        return sorted(list(all_tags))

    async def get_agent_types(self) -> List[str]:
        result = await self.db.execute(
            select(Agent.agent_type).distinct().where(Agent.agent_type.isnot(None))
        )
        return [r for r in result.scalars().all() if r]

    async def get_featured_content(self, limit: int = 6) -> List[AgentContent]:
        stmt = (
            select(AgentContent)
            .options(selectinload(AgentContent.agent))
            .where(AgentContent.is_featured == True)
            .order_by(desc(AgentContent.quality_score))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent_content(self, limit: int = 12) -> List[AgentContent]:
        stmt = (
            select(AgentContent)
            .options(selectinload(AgentContent.agent))
            .order_by(desc(AgentContent.indexed_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
