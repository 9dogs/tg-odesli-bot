"""Odesli API schemas."""
from marshmallow import Schema, fields


class SongSchema(Schema):
    """Platform song schema."""

    #: Identifier
    id = fields.Str(required=True, data_key='id')
    #: Platform
    platform = fields.Str(required=True, data_key='apiProvider')
    #: Artist (can be missing)
    artist = fields.Str(data_key='artistName', missing='<Unknown>')
    #: Title
    title = fields.Str(data_key='title')
    #: Thumbnail URL
    thumbnail_url = fields.Str(data_key='thumbnailUrl')


class PlatformLink(Schema):
    """Platform link schema."""

    #: Identifier
    id = fields.Str(required=True, data_key='entityUniqueId')
    #: URL
    url = fields.URL(required=True)


class ApiResponseSchema(Schema):
    """Odesli API response schema."""

    #: Dictionary of entity_id -> SongSchema
    songs = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(SongSchema, unknown='EXCLUDE'),
        data_key='entitiesByUniqueId',
        required=True,
    )
    #: Dictionary of platform -> LinkSchema
    links = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(PlatformLink, unknown='EXCLUDE'),
        data_key='linksByPlatform',
        required=True,
    )
