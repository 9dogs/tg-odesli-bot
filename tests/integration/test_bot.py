"""Integration tests for Odesli bot."""
import asyncio
from http import HTTPStatus
from unittest import mock

from aiogram import types
from aiogram.types import Chat, ChatType, ContentType, Message, User
from aiogram.utils.exceptions import MessageCantBeDeleted, NetworkError
from aiohttp import ClientConnectionError
from aioresponses import aioresponses
from pytest import mark

from tests.conftest import TEST_RESPONSE
from tg_odesli_bot.bot import SongInfo


def make_mock_message(
    text: str, method_mocks: dict = None, chat_type: ChatType = ChatType.GROUP
) -> mock.Mock:
    """Make a mock message with given text.

    :param text: text of the message
    :param method_mocks: dict of message's method mocks if needed
        {'reply': reply_mock, 'delete': delete_mock, ...}
    :param chat_type: chat type.  See `aiogram.types.ChatType` enum
    :return: mock message
    """
    message = mock.Mock(spec=Message)
    message.content_type = ContentType.TEXT
    message.text = text
    message.from_user = mock.Mock(spec=User)
    message.from_user.username = 'test_user'
    message.chat = mock.Mock(spec=Chat)
    message.chat.type = chat_type
    types.User.set_current(message.from_user)
    types.Chat.set_current(message.chat)
    if method_mocks:
        for method_name, callback in method_mocks.items():
            setattr(message, method_name, callback)
    return message


def make_reply_mock(expected_text=None):
    """Make `Message.reply` method mock with expected text."""

    async def reply_mock_fn(text, parse_mode, reply):
        """Reply mock."""
        assert parse_mode == 'HTML'
        assert not reply
        if expected_text is not None:
            assert text == expected_text

    reply_mock = mock.Mock(side_effect=reply_mock_fn)
    return reply_mock


def make_delete_mock():
    """Make `Message.delete` method mock."""

    async def delete_mock_fn():
        """Delete mock."""
        pass

    delete_mock = mock.Mock(side_effect=delete_mock_fn)
    return delete_mock


@mark.usefixtures('loop')
class TestOdesliBot:
    """Integration tests for Odesli bot."""

    @mark.parametrize('text', ['/start', '/help'])
    async def test_sends_welcome_message(self, bot, text):
        """Send a welcome message with supported platforms list in reply to
        /start or /help command.
        """
        reply_text = (
            'Hi!\n'
            "I'm a Odesli Bot. You can message me a link to a "
            'supported music streaming platform and I will respond with '
            'links from all the platforms. If you invite me to a group '
            'chat I will do the same as well as trying to delete original '
            'message (you must promote me to admin to enable this '
            'behavior).\n'
            '<b>Supported platforms:</b> Deezer | Google Music | '
            'SoundCloud | Yandex Music | Spotify.\n'
            'Powered by great <a href="https://odesli.co/">Odesli</a> '
            '(thank you guys!).'
        )
        reply_mock = make_reply_mock(reply_text)
        message = make_mock_message(
            text=text, method_mocks={'reply': reply_mock}
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert reply_mock.called

    async def test_replies_to_group_message(self, bot, odesli_api):
        """Send reply to a group message."""
        reply_text = (
            '<b>@test_user wrote:</b> check this one: [1]\n'
            '\n'
            '1. Test Artist - Test Title\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a>'
        )
        reply_mock = make_reply_mock(reply_text)
        delete_mock = make_delete_mock()
        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/65760860',
            method_mocks={'reply': reply_mock, 'delete': delete_mock},
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert reply_mock.called
        assert delete_mock.called

    async def test_returns_song_info_from_cache(self, bot, caplog, odesli_api):
        """Bot retrieves song info from cache."""
        url = 'https://www.deezer.com/track/1'
        song_info = SongInfo(
            ids={1},
            title='Cached',
            artist='Cached',
            urls={'soundcloud': 'test'},
            urls_in_text={url},
        )
        await bot.cache.set(url, song_info)
        reply_mock = make_reply_mock(
            expected_text=(
                '<b>@test_user wrote:</b> check this one: [1]\n'
                '\n'
                '1. Cached - Cached\n'
                '<a href="test">soundcloud</a>'
            )
        )
        delete_mock = make_delete_mock()
        message = make_mock_message(
            text=f'check this one: {url}',
            method_mocks={'reply': reply_mock, 'delete': delete_mock},
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert 'Returning data from cache' in caplog.text

    async def test_caches_song_info(self, bot, odesli_api):
        """Bot caches retrieved song info."""
        reply_mock = make_reply_mock()
        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/1',
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        await bot.dispatcher.message_handlers.notify(message)
        await bot.cache.get('https://www.deezer.com/track/1')

    async def test_replies_to_private_message(self, bot, odesli_api):
        """Send reply to a private message."""
        reply_text = (
            '1. Test Artist - Test Title\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a>'
        )
        reply_mock = make_reply_mock(reply_text)
        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/65760860',
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert reply_mock.called

    async def test_skips_message_with_skip_mark(self, caplog, bot):
        """Skip message if skip mark present."""
        message = make_mock_message(text=f'test message {bot.SKIP_MARK}')
        await bot.dispatcher.message_handlers.notify(message)
        assert 'Message is skipped due to skip mark' in caplog.text

    async def test_logs_if_no_song_links_in_message(self, caplog, bot):
        """Log and do not reply if message has no song links."""
        message = make_mock_message(text=f'test message without song links')
        await bot.dispatcher.message_handlers.notify(message)
        assert 'No songs found in message' in caplog.text

    async def test_logs_if_cannot_delete_message(
        self, caplog, bot, odesli_api
    ):
        """Log if cannot delete the message."""

        async def delete_mock_fn():
            """Message.delete method mock."""
            raise MessageCantBeDeleted(message='Test exception')

        reply_mock = make_reply_mock()
        delete_mock = mock.Mock(side_effect=delete_mock_fn)
        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/65760860',
            method_mocks={'reply': reply_mock, 'delete': delete_mock},
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert 'Cannot delete message' in caplog.text

    async def test_returns_original_url_if_one_song_404(self, bot):
        """Return original URL if one of the songs not found."""
        reply_text = (
            '<b>@test_user wrote:</b> check these: [1] and [2]\n'
            '\n'
            '1. https://deezer.com/track/1\n'
            '2. Test Artist - Test Title\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a>'
        )
        reply_mock = make_reply_mock(reply_text)
        delete_mock = make_delete_mock()
        url1 = 'https://deezer.com/track/1'
        url2 = 'https://deezer.com/track/2'
        message = make_mock_message(
            text=f'check these: {url1} and {url2}',
            method_mocks={'reply': reply_mock, 'delete': delete_mock},
            chat_type=ChatType.GROUP,
        )
        api_url1 = f'{bot.config.ODESLI_API_URL}?url={url1}'
        api_url2 = f'{bot.config.ODESLI_API_URL}?url={url2}'
        with aioresponses() as m:
            m.get(api_url1, status=HTTPStatus.NOT_FOUND)
            m.get(api_url2, status=HTTPStatus.OK, payload=TEST_RESPONSE)
            await bot.dispatcher.message_handlers.notify(message)
            assert reply_mock.called

    async def test_throttles_requests_if_429(self, caplog, bot):
        """Bot throttles requests if API returns 429 TOO_MANY_REQUESTS."""
        bot.API_RETRY_TIME = 1
        reply_text = (
            '1. Test Artist - Test Title\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a>'
        )
        reply_mock = make_reply_mock(reply_text)
        message1 = make_mock_message(
            text='check this one: https://deezer.com/track/1',
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        message2 = make_mock_message(
            text='check this one: https://deezer.com/track/2',
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        url1 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        url2 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/2'
        with aioresponses() as m:
            m.get(url1, status=HTTPStatus.TOO_MANY_REQUESTS)
            m.get(url1, status=HTTPStatus.OK, payload=TEST_RESPONSE)
            m.get(url2, status=HTTPStatus.OK, payload=TEST_RESPONSE)
            tasks = [
                asyncio.create_task(
                    bot.dispatcher.message_handlers.notify(message1)
                ),
                asyncio.create_task(
                    bot.dispatcher.message_handlers.notify(message2)
                ),
            ]
            await asyncio.sleep(1)
            assert 'Too many requests, retrying' in caplog.text
            assert 'Waiting for the API' in caplog.text
            await asyncio.gather(*tasks)
            assert reply_mock.called

    @mark.parametrize('error_code', [400, 500])
    async def test_do_not_reply_if_api_errors_for_all_songs(
        self, caplog, bot, error_code
    ):
        """Do not reply if API error returns for all songs."""
        reply_mock = make_reply_mock()
        message = make_mock_message(
            text=(
                'check this one: https://deezer.com/track/1, '
                'https://deezer.com/track/2'
            ),
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        url1 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        url2 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/2'
        with aioresponses() as m:
            m.get(url1, status=error_code, repeat=True)
            m.get(url2, status=error_code, repeat=True)
            await bot.dispatcher.message_handlers.notify(message)
            assert 'API returned errors for all URLs' in caplog.text
            assert not reply_mock.called

    async def test_do_not_reply_if_validation_error(self, caplog, bot):
        """Do not reply if API response validation error."""
        reply_mock = make_reply_mock()
        message = make_mock_message(
            text='check this one: https://deezer.com/track/1',
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        url1 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        with aioresponses() as m:
            m.get(url1, status=HTTPStatus.OK, payload={'invalid': 'invalid'})
            await bot.dispatcher.message_handlers.notify(message)
            assert 'Invalid response data' in caplog.text
            assert not reply_mock.called

    async def test_retries_if_api_connection_error(self, caplog, bot):
        """Bot retries to connect if API HTTP connection error."""
        bot.API_RETRY_TIME = 1
        bot.API_MAX_RETRIES = 1
        reply_mock = make_reply_mock()
        message = make_mock_message(
            text='check this one: https://deezer.com/track/1',
            method_mocks={'reply': reply_mock},
            chat_type=ChatType.PRIVATE,
        )
        bot.session.get = mock.MagicMock(side_effect=ClientConnectionError)
        await bot.dispatcher.message_handlers.notify(message)
        assert 'Connection error, retrying' in caplog.text

    @mock.patch(
        'aiogram.dispatcher.Dispatcher.skip_updates',
        mock.MagicMock(side_effect=NetworkError('Test error')),
    )
    def test_retries_if_telegram_connection_error(self, bot, caplog):
        """Bot retries to connect if Telegram API connection error."""
        bot.TG_RETRY_TIME = 1
        bot.TG_MAX_RETRIES = 1
        bot.start()
        assert 'Connection error, retrying' in caplog.text
