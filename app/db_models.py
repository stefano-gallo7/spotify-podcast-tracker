from sqlalchemy import (
    Column, String, Integer, SmallInteger, Boolean, DateTime, Date,
    ForeignKey, Text, Table, CheckConstraint, func, select
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from app.db import Base


show_tags = Table(
    "show_tags",
    Base.metadata,
    Column("show_id", Integer, ForeignKey("shows.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)

    shows = relationship("Show", secondary=show_tags, back_populates="tags")


class Show(Base):
    __tablename__ = "shows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)             # always set on import
    name_from_export = Column(String, nullable=True)
    uri = Column(String, unique=True, nullable=True)
    description = Column(Text, nullable=True)
    total_episodes = Column(Integer, nullable=True)
    has_new_episodes = Column(Boolean, default=False, nullable=False)
    image_url_big = Column(String, nullable=True)
    image_url_medium = Column(String, nullable=True)
    image_url_small = Column(String, nullable=True)
    languages = Column(String, nullable=True)  # comma-separated
    explicit = Column(Boolean, nullable=True)
    spotify_url = Column(String, nullable=True)
    media_type = Column(String, nullable=True)

    # User interaction
    status = Column(String, default="active", index=True)  # active / finished / dropped / paused / backlog
    status_changed_at = Column(DateTime, nullable=True)
    is_favorite = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    api_status = Column(String, default="pending")  # pending / fetched / unavailable
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    episodes = relationship(
        "Episode", back_populates="show", cascade="all, delete-orphan"
    )
    tags = relationship("Tag", secondary=show_tags, back_populates="shows")

    @hybrid_property
    def listened_count(self) -> int:
        return sum(1 for e in self.episodes if e.is_fully_played)

    @listened_count.expression
    def listened_count(cls):
        return (
            select(func.count(Episode.uri))
            .where(Episode.show_id == cls.id, Episode.is_fully_played.is_(True))
            .scalar_subquery()
        )

    @hybrid_property
    def has_more_episodes(self) -> bool:
        return (self.total_episodes or 0) > self.listened_count

    @has_more_episodes.expression
    def has_more_episodes(cls):
        return cls.total_episodes > cls.listened_count


class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
    )

    uri = Column(String, primary_key=True)
    show_id = Column(
        Integer, ForeignKey("shows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String, nullable=False)

    # Fallback name from the export
    name_from_export = Column(String, nullable=True)

    # Fields populated by API
    description = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    release_date = Column(Date, nullable=True)
    languages = Column(String, nullable=True)
    image_url_big = Column(String, nullable=True)
    image_url_medium = Column(String, nullable=True)
    image_url_small = Column(String, nullable=True)
    explicit = Column(Boolean, nullable=True)
    spotify_url = Column(String, nullable=True)
    is_playable = Column(Boolean, nullable=True)

    # Listening info (combined from export + API)
    is_fully_played = Column(Boolean, default=False)
    resume_position_ms = Column(Integer, nullable=True)
    last_played_at = Column(DateTime, nullable=True, index=True)
    ms_played = Column(Integer, nullable=True)  # total time across all plays
    play_count = Column(Integer, nullable=True)
    connection_country = Column(String, nullable=True)
    discovered_via = Column(String)  # export / api

    # User interaction
    rating = Column(SmallInteger, nullable=True)  # 1-5
    is_favorite = Column(Boolean, default=False)
    rated_at = Column(DateTime, nullable=True)
    is_archived = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    api_status = Column(String, default="pending")  # pending / fetched / unavailable
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    show = relationship("Show", back_populates="episodes")
