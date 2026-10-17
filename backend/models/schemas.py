from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


InteractionStatus = Literal["to_explore", "implemented", "not_interested", "all"]


class ReelWebhookRequest(BaseModel):
    url: HttpUrl
    secret: str


class ToolExtraction(BaseModel):
    name: str
    functionality: str
    problem_solved: str
    tags: list[str] = Field(default_factory=list)


class ToolInteractionPatch(BaseModel):
    status: Literal["to_explore", "implemented", "not_interested"]
    notes: str | None = None


class ToolResponse(BaseModel):
    id: str
    name: str
    functionality: str | None = None
    problem_solved: str | None = None
    tags: list[str] = Field(default_factory=list)
    first_seen_date: date | None = None
    source_video_ids: list[str] = Field(default_factory=list)
    status: Literal["to_explore", "implemented", "not_interested"] = "to_explore"
    notes: str | None = None
    updated_at: datetime | None = None


class VideoListResponse(BaseModel):
    id: str
    instagram_url: str
    video_created_at: date | None = None
    processed_at: datetime | None = None
    tool_names: list[str] = Field(default_factory=list)


class VideoDetailResponse(BaseModel):
    id: str
    instagram_url: str
    video_created_at: date | None = None
    processed_at: datetime | None = None
    transcript: str | None = None
    caption: str | None = None
    raw_extraction: Any | None = None
    tools: list[ToolResponse] = Field(default_factory=list)


class RepositoryRef(BaseModel):
    name: str
    url: str | None = None  # only set when the source actually provides one
    description: str | None = None


class KnowledgeExtraction(BaseModel):
    """General knowledge extracted from a Reel. Every list may be empty; `tools` stays the legacy tool model."""

    title: str
    summary: str
    key_ideas: list[str] = Field(default_factory=list)
    tools: list[ToolExtraction] = Field(default_factory=list)
    repositories: list[RepositoryRef] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
