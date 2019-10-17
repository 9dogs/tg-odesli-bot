"""Helpers and fixtures for pytest."""
import re
from functools import partial
from pathlib import Path
from unittest import mock

import dotenv
from aioresponses import aioresponses
from pytest import fixture

from tg_odesli_bot.bot import OdesliBot
from tg_odesli_bot.config import TestConfig

#: Tests base dir
BASE_DIR = Path(__file__).resolve().parent
#: Odesli API test response
TEST_RESPONSE = {
    'entityUniqueId': 'GOOGLE_SONG::G1',
    'userCountry': 'US',
    'entitiesByUniqueId': {
        'DEEZER_SONG::D1': {
            'id': 'D1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'deezer',
        },
        'ITUNES_SONG::IT1': {
            'id': 'IT1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'itunes',
        },
        'SPOTIFY_SONG::S1': {
            'id': 'S1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'spotify',
        },
        'GOOGLE_SONG::G1': {
            'id': 'G1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'google',
        },
        'AMAZON_SONG::A1': {
            'id': 'A1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'amazon',
        },
        'TIDAL_SONG::T1': {
            'id': 'T1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'tidal',
        },
        'NAPSTER_SONG::N1': {
            'id': 'N1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'napster',
        },
        'YANDEX_SONG::Y1': {
            'id': 'Y1',
            'title': 'Test Title',
            'artistName': 'Test Artist',
            'apiProvider': 'yandex',
        },
    },
    'linksByPlatform': {
        'deezer': {
            'url': 'https://www.test.com/d',
            'entityUniqueId': 'DEEZER_SONG::D1',
        },
        'appleMusic': {
            'url': 'https://www.test.com/am',
            'entityUniqueId': 'ITUNES_SONG::AM1',
        },
        'spotify': {
            'url': 'https://www.test.com/s',
            'entityUniqueId': 'SPOTIFY_SONG::S1',
        },
        'youtube': {
            'url': 'https://www.test.com/y',
            'entityUniqueId': 'YOUTUBE_VIDEO::Y1',
        },
        'youtubeMusic': {
            'url': 'https://www.test.com/ym',
            'entityUniqueId': 'YOUTUBE_VIDEO::YM1',
        },
        'google': {
            'url': 'https://www.test.com/g',
            'entityUniqueId': 'GOOGLE_SONG::G1',
        },
        'amazonMusic': {
            'url': 'https://www.test.com/a',
            'entityUniqueId': 'AMAZON_SONG::A1',
        },
        'tidal': {
            'url': 'https://www.test.com/t',
            'entityUniqueId': 'TIDAL_SONG::T1',
        },
        'napster': {
            'url': 'https://www.test.com/n',
            'entityUniqueId': 'NAPSTER_SONG::N1',
        },
        'yandex': {
            'url': 'https://www.test.com/yn',
            'entityUniqueId': 'YANDEX_SONG::YN1',
        },
        'itunes': {
            'url': 'https://www.test.com/it',
            'entityUniqueId': 'ITUNES_SONG::IT1',
        },
        'googleStore': {
            'url': 'https://www.test.com/gs',
            'entityUniqueId': 'GOOGLE_SONG::GS1',
        },
        'amazonStore': {
            'url': 'https://www.test.com/az',
            'entityUniqueId': 'AMAZON_SONG::AZ1',
        },
    },
}


@fixture
def test_dotenv():
    """Load test .env file."""
    load_test_dotenv = partial(
        dotenv.load_dotenv,
        dotenv_path=BASE_DIR / 'test_env',
        verbose=True,
        override=True,
    )
    with mock.patch(
        'tg_odesli_bot.config.dotenv.load_dotenv', load_test_dotenv
    ):
        yield


@fixture
def test_config():
    """Test config fixture."""
    config = TestConfig.load_config()
    return config


@fixture
async def bot(test_config):
    """Bot fixture."""

    def mock_check_token(token):
        return True

    with mock.patch('aiogram.bot.api.check_token', mock_check_token):
        bot = OdesliBot(config=test_config)
        yield bot
    await bot.stop()


@fixture
async def odesli_api(test_config):
    """Odesli API mock."""
    pattern = re.compile(rf'^{re.escape(test_config.ODESLI_API_URL)}.*$')
    with aioresponses() as m:
        m.get(pattern, status=200, payload=TEST_RESPONSE)
        yield m
