from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    Boolean,
    JSON,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


class ContentType(enum.Enum):
    DOCUMENT = "document"
    VIDEO = "video"
    POST = "post"
    CODE = "code"
    ARTWORK = "artwork"
    MUSIC = "music"
    RESEARCH = "research"
    CONVERSATION = "conversation"
    DATASET = "dataset"
    SIMULATION = "simulation"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    agent_type = Column(String(100), nullable=True, index=True)
    framework = Column(String(100), nullable=True)
    capabilities = Column(JSON, nullable=True)
    creator = Column(String(255), nullable=True)
    creator_url = Column(String(500), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    reputation_score = Column(Float, default=0.0)
    total_creations = Column(Integer, default=0)
    extra_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    contents = relationship("AgentContent", back_populates="agent", lazy="dynamic")


class AgentContent(Base):
    __tablename__ = "agent_contents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    content_type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    content_url = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    source_platform = Column(String(100), nullable=True, index=True)
    source_url = Column(String(1000), nullable=True)
    tags = Column(JSON, nullable=True)
    categories = Column(JSON, nullable=True)
    language = Column(String(50), nullable=True)
    license = Column(String(100), nullable=True)
    quality_score = Column(Float, default=0.0)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    extra_data = Column(JSON, nullable=True)
    indexed_at = Column(DateTime, server_default=func.now())
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    agent = relationship("Agent", back_populates="contents")
