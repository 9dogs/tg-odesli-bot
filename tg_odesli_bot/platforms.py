"""Supported platforms."""
import re
from abc import ABC
from typing import Pattern, Union

#: Supported platforms registry
PLATFORMS = {}


class PlatformABC(ABC):
    """Platform data ABC."""

    # Platform's Odesli name
    key: str
    # RegEx to find platform's URL in a message text
    url_re: Union[str, Pattern]
    # Human readable name which will appear in a bot's message
    name: str
    # Order of platform's link in a bot's message
    order: int

    def __init_subclass__(cls, **kwargs):
        """Compile regex and add platform to `PLATFORM` registry."""
        super().__init_subclass__(**kwargs)
        cls.url_re = re.compile(cls.url_re)
        PLATFORMS[cls.key] = cls()


class DeezerPlatform(PlatformABC):
    """Deezer platform."""

    key = 'deezer'
    url_re = (
        r'(https?://([a-zA-Z\d-]+\.)*deezer\.com(/\w\w)?/'
        r'(album|track)/[^\s.,]*)'
        r'|(https?://deezer\.page\.link/[^\s.,]*)'
    )
    name = 'Deezer'
    order = 0


class SoundCloudPlatform(PlatformABC):
    """SoundCloud platform."""

    key = 'soundcloud'
    url_re = (
        r'https?://([a-zA-Z\d-]+\.)*soundcloud\.(com|app\.goo\.gl)/[^\s.,]*'
    )
    name = 'SoundCloud'
    order = 1


class YandexMusicPlatform(PlatformABC):
    """Yandex Music platform."""

    key = 'yandex'
    url_re = (
        r'https?://([a-zA-Z\d-]+\.)*music\.yandex\.(com|ru|by)/(album|track)/'
        r'[^\s.,]*'
    )
    name = 'Yandex Music'
    order = 2


class SpotifyPlatform(PlatformABC):
    """Spotify platform."""

    key = 'spotify'
    url_re = (
        r'https?://([a-zA-Z\d-]+\.)*((spotify\.com/(album|track)/[^\s.,]*)'
        r'|(tospotify\.com/[^\s.,]*))'
    )
    name = 'Spotify'
    order = 3


class YouTubeMusicPlatform(PlatformABC):
    """YouTube Music platform."""

    key = 'youtubeMusic'
    url_re = (
        r'(https?://([a-zA-Z\d-]+\.)*music\.youtube\.com/(watch|playlist)\?'
        r'(v|list)=[^\s.,]*)'
    )
    name = 'YouTube Music'
    order = 4


class YouTubePlatform(PlatformABC):
    """YouTube platform."""

    key = 'youtube'
    url_re = (
        r'https?://(((www\.)?youtube\.com/(watch|playlist)\?(v|list)=[^\s,]*)'
        r'|(youtu\.be/[^\s.,]*))'
    )
    name = 'YouTube'
    order = 5


class AppleMusicPlatform(PlatformABC):
    """Apple Music platform."""

    key = 'appleMusic'
    url_re = r'https?://([a-zA-Z\d-]+\.)*music\.apple\.com/.*?/album/[^\s,.]*'
    name = 'Apple Music'
    order = 6


class TidalPlatform(PlatformABC):
    """Tidal platform."""

    key = 'tidal'
    url_re = (
        r'https?://(www\.|listen\.)?tidal\.com(/browse)?/(track|album)/\d+'
    )
    name = 'Tidal'
    order = 7


class BandcampPlatform(PlatformABC):
    """Bandcamp platform."""

    key = 'bandcamp'
    url_re = r'https?://[^\s.,]*\.bandcamp\.com/(album|track)/[^\s.,]*'
    name = 'Bandcamp'
    order = 8
