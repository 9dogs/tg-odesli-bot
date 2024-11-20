"""Helpers and fixtures for pytest."""

import json
import re
import string
from http import HTTPStatus
from pathlib import Path
from unittest import mock
from unittest.mock import Mock

from aioresponses import aioresponses
from pytest import fixture

from tg_odesli_bot.bot import OdesliBot
from tg_odesli_bot.settings import TestSettings

#: Tests base dir
BASE_DIR = Path(__file__).resolve().parent
#: Odesli API test response template
TEST_RESPONSE_TEMPLATE = {
    'entityUniqueId': 'DEEZER_SONG::D${id}',
    'userCountry': 'US',
    'entitiesByUniqueId': {
        'DEEZER_SONG::D${id}': {
            'id': 'D${id}',
            'title': 'Test Title ${id}',
            'apiProvider': 'deezer',
            'thumbnailUrl': 'http://thumb1',
        },
        'ITUNES_SONG::IT${id}': {
            'id': 'IT${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'itunes',
        },
        'SPOTIFY_SONG::S${id}': {
            'id': 'S${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'spotify',
        },
        'AMAZON_SONG::A${id}': {
            'id': 'A${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'amazon',
        },
        'TIDAL_SONG::T${id}': {
            'id': 'T${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'tidal',
        },
        'NAPSTER_SONG::N${id}': {
            'id': 'N${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'napster',
        },
        'SOUNDCLOUD_SONG::SC${id}': {
            'id': 'SC${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'soundcloud',
        },
        'YANDEX_SONG::Y${id}': {
            'id': 'Y${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'yandex',
        },
        'BANDCAMP_SONG::B${id}': {
            'id': '${id}',
            'title': 'Test Title ${id}',
            'artistName': 'Test Artist ${id}',
            'apiProvider': 'bandcamp',
        },
    },
    'linksByPlatform': {
        'deezer': {
            'url': 'https://www.test.com/d',
            'entityUniqueId': 'DEEZER_SONG::D${id}',
        },
        'appleMusic': {
            'url': 'https://geo.www.test.com/am',
            'entityUniqueId': 'ITUNES_SONG::AM${id}',
        },
        'spotify': {
            'url': 'https://www.test.com/s',
            'entityUniqueId': 'SPOTIFY_SONG::S${id}',
        },
        'youtube': {
            'url': 'https://www.test.com/y',
            'entityUniqueId': 'YOUTUBE_VIDEO::Y${id}',
        },
        'youtubeMusic': {
            'url': 'https://www.test.com/ym',
            'entityUniqueId': 'YOUTUBE_VIDEO::YM${id}',
        },
        'amazonMusic': {
            'url': 'https://www.test.com/a',
            'entityUniqueId': 'AMAZON_SONG::A${id}',
        },
        'tidal': {
            'url': 'https://www.test.com/t',
            'entityUniqueId': 'TIDAL_SONG::T${id}',
        },
        'napster': {
            'url': 'https://www.test.com/n',
            'entityUniqueId': 'NAPSTER_SONG::N${id}',
        },
        'yandex': {
            'url': 'https://www.test.com/yn',
            'entityUniqueId': 'YANDEX_SONG::YN${id}',
        },
        'itunes': {
            'url': 'https://www.test.com/it',
            'entityUniqueId': 'ITUNES_SONG::IT${id}',
        },
        'amazonStore': {
            'url': 'https://www.test.com/az',
            'entityUniqueId': 'AMAZON_SONG::AZ${id}',
        },
        'soundcloud': {
            'url': 'https://www.test.com/sc',
            'entityUniqueId': 'SOUNDCLOUD_SONG::SC${id}',
        },
        'bandcamp': {
            'url': 'https://www.test.com/b',
            'entityUniqueId': 'BANDCAMP_SONG::B${id}',
        },
    },
}
#: Odesli API test response template with one URL
TEST_RESPONSE_WITH_ONE_URL_TEMPLATE = {
    'entityUniqueId': 'DEEZER_SONG::D${id}',
    'userCountry': 'US',
    'entitiesByUniqueId': {
        'DEEZER_SONG::D${id}': {
            'id': 'D${id}',
            'title': 'Test Title ${id}',
            'apiProvider': 'deezer',
            'thumbnailUrl': 'http://thumb1',
        },
    },
    'linksByPlatform': {
        'deezer': {
            'url': 'https://www.test.com/d',
            'entityUniqueId': 'DEEZER_SONG::D${id}',
        },
    },
}
#: Mock Spotify search response
MOCK_SPOTIFY_SEARCH_RESPONSE = {
    'tracks': {
        'items': [
            {
                'id': 'test_id',
                'name': 'test_name',
                'artists': [{'name': 'test_artist'}],
                'album': {'images': [{'url': 'http://thumb1'}]},
                'external_urls': {'spotify': 'test_url'},
            }
        ]
    }
}


def make_response(
    song_id: str | int = 1, template: dict = TEST_RESPONSE_TEMPLATE
) -> dict:
    """Prepare Odesli API test response with given song id.

    :param song_id: substitution for a song identifier
    :param template: response template
    :returns: response dict
    """
    response_template = string.Template(json.dumps(template))
    response = response_template.substitute(id=str(song_id))
    payload = json.loads(response)
    # Bandcamp song IDs are integers
    _key = f'BANDCAMP_SONG::B{song_id}'
    if _key in payload['entitiesByUniqueId']:
        payload['entitiesByUniqueId'][_key]['id'] = int(song_id)
    return payload


@fixture
def test_config():
    """Test config fixture."""
    config = TestSettings.load()
    return config


@fixture
async def bot(test_config):
    """Bot fixture."""

    def mock_check_token(token):
        return True

    with mock.patch('aiogram.bot.api.check_token', mock_check_token):
        bot = OdesliBot(config=test_config)
        await bot.init()
        bot.sp = Mock()
        bot.sp.search.return_value = MOCK_SPOTIFY_SEARCH_RESPONSE
        yield bot
    await bot.stop()


@fixture
async def odesli_api(test_config):
    """Odesli API mock."""
    pattern = re.compile(rf'^{re.escape(test_config.ODESLI_API_URL)}.*$')
    payload = make_response(song_id=1)
    with aioresponses() as m:
        m.get(pattern, status=HTTPStatus.OK, payload=payload)
        yield m
