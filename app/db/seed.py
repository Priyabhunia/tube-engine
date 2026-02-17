"""
Seed database with initial sample data.
Only run this manually, not on startup.
"""

import asyncio
from sqlalchemy import select, func
from app.db.database import async_session_maker
from app.models.entity import Agent, AgentContent


async def clear_database():
    """Clear all data from database."""
    async with async_session_maker() as session:
        await session.execute(AgentContent.__table__.delete())
        await session.execute(Agent.__table__.delete())
        await session.commit()
        print("Database cleared")


async def check_data():
    """Check current data in database."""
    async with async_session_maker() as session:
        agent_count = await session.scalar(select(func.count(Agent.id)))
        content_count = await session.scalar(select(func.count(AgentContent.id)))
        print(f"Agents: {agent_count}, Contents: {content_count}")
        return agent_count, content_count


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        asyncio.run(clear_database())
    else:
        asyncio.run(check_data())
