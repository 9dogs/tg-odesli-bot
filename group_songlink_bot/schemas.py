"""Songlink API schemas."""
from marshmallow import Schema, fields


class SongSchema(Schema):
    """Platform song schema."""

    #: Identifier
    id = fields.Str(required=True, data_key='id')
    #: Platform
    platform = fields.Str(required=True, data_key='apiProvider')
    #: Artist
    artist = fields.Str(data_key='artistName')
    #: Title
    title = fields.Str(data_key='title')


class PlatformLink(Schema):
    """Platform URL schema."""

    #: Identifier
    id = fields.Str(required=True, data_key='entityUniqueId')
    #: URL
    url = fields.URL(required=True)


class SongLinkResponseSchema(Schema):
    """SongLink API response schema."""

    #: Dictionary of entity_id -> SongSchema
    songs = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(SongSchema, unknown='EXCLUDE'),
        data_key='entitiesByUniqueId',
    )
    #: Dictionary of platform -> LinkSchema
    links = fields.Dict(
        keys=fields.Str(),
        values=fields.Nested(PlatformLink, unknown='EXCLUDE'),
        data_key='linksByPlatform',
    )
