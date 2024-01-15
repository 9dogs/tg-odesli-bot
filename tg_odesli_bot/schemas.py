"""Odesli API schemas."""
from pydantic import BaseModel, Field


class SongSchema(BaseModel):
    """Platform song schema."""

    #: Identifier
    id: str | int
    #: Platform
    platform: str = Field(..., validation_alias='apiProvider')
    #: Artist (can be missing)
    artist: str = Field('<Unknown>', validation_alias='artistName')
    #: Title
    title: str | None = None
    #: Thumbnail URL
    thumbnail_url: str | None = Field(None, validation_alias='thumbnailUrl')


class PlatformLink(BaseModel):
    """Platform link schema."""

    #: Identifier
    id: str | int = Field(..., validation_alias='entityUniqueId')
    #: URL
    url: str


class ApiResponseSchema(BaseModel):
    """Odesli API response schema."""

    #: Dictionary of entity_id -> SongSchema
    songs: dict[str, SongSchema] = Field(
        ..., validation_alias='entitiesByUniqueId'
    )
    #: Dictionary of platform -> LinkSchema
    links: dict[str, PlatformLink] = Field(
        ..., validation_alias='linksByPlatform'
    )
