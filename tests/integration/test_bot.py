"""Integration tests for Odesli bot."""
import asyncio
from http import HTTPStatus
from unittest import mock

from aiogram import types
from aiogram.types import (
    Chat,
    ChatType,
    ContentType,
    InlineQuery,
    Message,
    User,
)
from aiogram.utils.exceptions import MessageCantBeDeleted, NetworkError
from aiohttp import ClientConnectionError
from aioresponses import aioresponses
from pytest import mark

from tests.conftest import make_response
from tg_odesli_bot.bot import SongInfo


def make_mock_message(
    text: str,
    chat_type: ChatType = ChatType.GROUP,
    raise_on_delete: bool = False,
    inline: bool = False,
    is_reply: bool = False,
) -> mock.Mock:
    """Make a mock message with given text.

    :param text: text of the message
    :param chat_type: chat type.  See `aiogram.types.ChatType` enum
    :param raise_on_delete: raise exception on message delete
    :param inline: message is an inline query
    :param is_reply: message is a reply
    :return: mock message
    """
    spec = InlineQuery if inline else Message
    message = mock.Mock(spec=spec)
    message.content_type = ContentType.TEXT
    if inline:
        message.query = text
        message.message_id = 'id'
    else:
        message.text = text
    message.from_user = mock.Mock(spec=User)
    message.from_user.username = 'test_user'
    message.chat = mock.Mock(spec=Chat)
    message.chat.type = chat_type
    types.User.set_current(message.from_user)
    types.Chat.set_current(message.chat)

    async def reply_mock_fn(text, parse_mode, reply=True):
        """Reply mock."""
        assert parse_mode == 'HTML'
        assert reply == is_reply
        # Save text argument for assertion
        reply_mock.called_with_text = text

    reply_mock = mock.Mock(side_effect=reply_mock_fn)
    message.reply = reply_mock

    async def delete_mock_fn():
        """Delete mock."""
        if raise_on_delete:
            raise MessageCantBeDeleted(message='Test exception')

    delete_mock = mock.Mock(side_effect=delete_mock_fn)
    message.delete = delete_mock
    return message


@mark.usefixtures('loop')
class TestOdesliBot:
    """Integration tests for Odesli bot."""

    @mark.parametrize('text', ['/start', '/help'])
    async def test_sends_welcome_message(self, bot, text):
        """Send a welcome message with supported platforms list in reply to
        /start or /help command.
        """
        supported_platforms = (
            'Deezer | Google Music | SoundCloud | Yandex Music | Spotify | '
            'YouTube Music | YouTube | Apple Music | Tidal'
        )
        message = make_mock_message(text=text)
        reply_text = bot.WELCOME_MSG_TEMPLATE.format(
            supported_platforms=supported_platforms
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert message.reply.called
        assert message.reply.called_with_text == reply_text

    async def test_replies_to_group_message(self, bot, odesli_api):
        """Send reply to a group message."""
        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/1'
        )
        reply_text = (
            '<b>@test_user wrote:</b> check this one: [1]\n'
            '\n'
            '1. Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert message.reply.called
        assert message.delete.called
        assert message.reply.called_with_text == reply_text

    async def test_replies_to_inline_query(self, bot, odesli_api, monkeypatch):
        """Send reply to an inline query."""
        inline_query = make_mock_message(
            'https://www.deezer.com/track/1', inline=True
        )
        reply_text = (
            'Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )

        async def mock_answer_inline_query(inline_query_id, results):
            """Mock inline query answer."""
            assert len(results) == 1
            result = results[0]
            assert result.title == 'Test Artist 1 - Test Title 1'
            assert result.input_message_content.message_text == reply_text
            assert result.input_message_content.parse_mode == 'HTML'
            assert result.thumb_url == 'http://thumb1'
            assert result.description == (
                'Deezer | Google Music | SoundCloud | Yandex Music | Spotify '
                '| YouTube Music | YouTube | Apple Music | Tidal'
            )

        monkeypatch.setattr(
            bot.bot, 'answer_inline_query', mock_answer_inline_query
        )
        await bot.dispatcher.inline_query_handlers.notify(inline_query)

    @mark.parametrize('query', ['not a URL', ''])
    async def test_not_replies_to_inline_query_if_no_url(
        self, bot, odesli_api, monkeypatch, query
    ):
        """Do not reply to an inline query if not URL in query."""
        inline_query = make_mock_message(query, inline=True)

        async def mock_answer_inline_query(inline_query_id, results):
            """Mock an inline query answer."""
            assert not results

        monkeypatch.setattr(
            bot.bot, 'answer_inline_query', mock_answer_inline_query
        )
        await bot.dispatcher.inline_query_handlers.notify(inline_query)

    @mark.parametrize(
        'error_code',
        [HTTPStatus.BAD_REQUEST, HTTPStatus.INTERNAL_SERVER_ERROR],
    )
    async def test_not_replies_to_inline_query_if_api_errors(
        self, caplog, bot, error_code, monkeypatch
    ):
        """Do not reply to an inline query if API error returns for all
        songs.
        """
        message = make_mock_message(
            text='https://deezer.com/track/1', inline=True,
        )

        async def mock_answer_inline_query(inline_query_id, results):
            """Mock an inline query answer."""
            assert not results

        monkeypatch.setattr(
            bot.bot, 'answer_inline_query', mock_answer_inline_query
        )

        url = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        with aioresponses() as m:
            m.get(url, status=error_code, repeat=True)
            await bot.dispatcher.inline_query_handlers.notify(message)
            assert 'API error' in caplog.text

    async def test_replies_to_inline_query_if_404(
        self, caplog, bot, monkeypatch
    ):
        """Reply to an inline query if API error returns 404 for all songs."""
        message = make_mock_message(
            text='https://deezer.com/track/1', inline=True,
        )

        async def mock_answer_inline_query(inline_query_id, results):
            """Mock an inline query answer."""
            assert len(results) == 1
            result = results[0]
            assert result.title == 'Not found'
            assert result.input_message_content.message_text == (
                "Sorry, Odesli couldn't find that song"
            )
            assert result.input_message_content.parse_mode == 'HTML'
            assert not result.thumb_url
            assert not result.description

        monkeypatch.setattr(
            bot.bot, 'answer_inline_query', mock_answer_inline_query
        )

        url = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        with aioresponses() as m:
            m.get(url, status=HTTPStatus.NOT_FOUND, repeat=True)
            await bot.dispatcher.inline_query_handlers.notify(message)
            assert 'API error' in caplog.text

    async def test_returns_song_info_from_cache(self, bot, caplog, odesli_api):
        """Bot retrieves song info from cache."""
        url = 'https://www.deezer.com/track/1'
        song_info = SongInfo(
            ids={1},
            title='Cached',
            artist='Cached',
            thumbnail_url='cached',
            urls={'soundcloud': 'test'},
            urls_in_text={url},
        )
        await bot.cache.set(url, song_info)
        message = make_mock_message(text=f'check this one: {url}')
        reply_text = (
            '<b>@test_user wrote:</b> check this one: [1]\n'
            '\n'
            '1. Cached - Cached\n'
            '<a href="test">soundcloud</a>'
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert 'Returning data from cache' in caplog.text
        assert message.reply.called_with_text == reply_text

    async def test_caches_song_info(self, bot, odesli_api):
        """Bot caches retrieved song info."""
        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/1',
            chat_type=ChatType.PRIVATE,
        )
        await bot.dispatcher.message_handlers.notify(message)
        await bot.cache.get('https://www.deezer.com/track/1')

    async def test_replies_to_private_message(self, bot, odesli_api):
        """Send reply to a private message."""
        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/1',
            chat_type=ChatType.PRIVATE,
        )
        reply_text = (
            'check this one: [1]\n'
            '\n'
            '1. Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert message.reply.called
        assert message.reply.called_with_text == reply_text

    async def test_replies_to_private_for_single_url(self, bot, odesli_api):
        """Send reply to a private message without an index number if incoming
        message consists only of one URL.
        """
        message = make_mock_message(
            text='https://www.deezer.com/track/1', chat_type=ChatType.PRIVATE,
        )
        reply_text = (
            'Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert message.reply.called
        assert message.reply.called_with_text == reply_text

    async def test_replies_if_some_urls_not_found(self, bot):
        """Send reply to a private message if song not found in some
        platforms.
        """
        url = 'https://www.deezer.com/track/1'
        message = make_mock_message(
            text=f'check this one: {url}', chat_type=ChatType.PRIVATE
        )
        reply_text = (
            'check this one: [1]\n'
            '\n'
            '1. Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        api_url = f'{bot.config.ODESLI_API_URL}?url={url}'
        payload = make_response(song_id=1)
        # Remove Deezer data from the payload
        del payload['linksByPlatform']['deezer']
        with aioresponses() as m:
            m.get(api_url, status=HTTPStatus.OK, payload=payload)
            await bot.dispatcher.message_handlers.notify(message)
            assert message.reply.called
            assert message.reply.called_with_text == reply_text

    async def test_replies_to_private_message_if_only_urls(self, bot):
        """Send reply to a private message without text if message consists of
        song URLs only.
        """
        url1 = 'https://www.deezer.com/track/1'
        url2 = 'https://soundcloud.com/2'
        message = make_mock_message(
            text=f'{url1}\n{url2}', chat_type=ChatType.PRIVATE
        )
        reply_text = (
            '1. Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>\n'
            '2. Test Artist 2 - Test Title 2\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        api_url1 = f'{bot.config.ODESLI_API_URL}?url={url1}'
        api_url2 = f'{bot.config.ODESLI_API_URL}?url={url2}'
        payload1 = make_response(song_id=1)
        payload2 = make_response(song_id=2)
        with aioresponses() as m:
            m.get(api_url1, status=HTTPStatus.OK, payload=payload1)
            m.get(api_url2, status=HTTPStatus.OK, payload=payload2)
            await bot.dispatcher.message_handlers.notify(message)
            assert message.reply.called
            assert message.reply.called_with_text == reply_text

    async def test_replies_to_private_message_for_single_url(self, bot):
        """Send reply to a private message without an index number if incoming
        message consists only of one URL.
        """
        url = 'https://www.deezer.com/track/1'
        message = make_mock_message(text=url, chat_type=ChatType.PRIVATE)
        reply_text = (
            'Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        api_url = f'{bot.config.ODESLI_API_URL}?url={url}'
        payload = make_response(song_id=1)
        with aioresponses() as m:
            m.get(api_url, status=HTTPStatus.OK, payload=payload)
            await bot.dispatcher.message_handlers.notify(message)
            assert message.reply.called
            assert message.reply.called_with_text == reply_text

    async def test_skips_message_with_skip_mark(self, caplog, bot):
        """Skip message if skip mark present."""
        message = make_mock_message(text=f'test message {bot.SKIP_MARK}')
        await bot.dispatcher.message_handlers.notify(message)
        assert 'Message is skipped due to skip mark' in caplog.text

    async def test_logs_if_cannot_delete_message(
        self, caplog, bot, odesli_api
    ):
        """Log if cannot delete the message."""

        message = make_mock_message(
            text='check this one: https://www.deezer.com/track/1',
            raise_on_delete=True,
        )
        await bot.dispatcher.message_handlers.notify(message)
        assert 'Cannot delete message' in caplog.text

    async def test_returns_original_url_if_one_song_404(self, bot):
        """Return original URL if one of the songs not found."""
        url1 = 'https://deezer.com/track/1'
        url2 = 'https://deezer.com/track/2'
        message = make_mock_message(
            text=f'check these: {url1} and {url2}', chat_type=ChatType.GROUP
        )
        reply_text = (
            '<b>@test_user wrote:</b> check these: [1] and [2]\n'
            '\n'
            '1. https://deezer.com/track/1\n'
            '2. Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        api_url1 = f'{bot.config.ODESLI_API_URL}?url={url1}'
        api_url2 = f'{bot.config.ODESLI_API_URL}?url={url2}'
        payload = make_response()
        with aioresponses() as m:
            m.get(api_url1, status=HTTPStatus.NOT_FOUND)
            m.get(api_url2, status=HTTPStatus.OK, payload=payload)
            await bot.dispatcher.message_handlers.notify(message)
            assert message.reply.called
            assert message.reply.called_with_text == reply_text

    async def test_throttles_requests_if_429(self, caplog, bot):
        """Bot throttles requests if API returns 429 TOO_MANY_REQUESTS."""
        bot.API_RETRY_TIME = 1
        message1 = make_mock_message(
            text='check this one: https://deezer.com/track/1',
            chat_type=ChatType.PRIVATE,
        )
        message2 = make_mock_message(
            text='check this one: https://deezer.com/track/2',
            chat_type=ChatType.PRIVATE,
        )
        reply_text = (
            'check this one: [1]\n'
            '\n'
            '1. Test Artist 1 - Test Title 1\n'
            '<a href="https://www.test.com/d">Deezer</a> | '
            '<a href="https://www.test.com/g">Google Music</a> | '
            '<a href="https://www.test.com/sc">SoundCloud</a> | '
            '<a href="https://www.test.com/yn">Yandex Music</a> | '
            '<a href="https://www.test.com/s">Spotify</a> | '
            '<a href="https://www.test.com/ym">YouTube Music</a> | '
            '<a href="https://www.test.com/y">YouTube</a> | '
            '<a href="https://www.test.com/am">Apple Music</a> | '
            '<a href="https://www.test.com/t">Tidal</a>'
        )
        url1 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        url2 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/2'
        payload = make_response()
        with aioresponses() as m:
            m.get(url1, status=HTTPStatus.TOO_MANY_REQUESTS)
            m.get(url1, status=HTTPStatus.OK, payload=payload)
            m.get(url2, status=HTTPStatus.OK, payload=payload)
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
            assert message1.reply.called
            assert message1.reply.called_with_text == reply_text
            assert message2.reply.called
            assert message2.reply.called_with_text == reply_text

    @mark.parametrize(
        'error_code',
        [HTTPStatus.BAD_REQUEST, HTTPStatus.INTERNAL_SERVER_ERROR],
    )
    async def test_not_replies_if_api_errors_for_all_songs(
        self, caplog, bot, error_code
    ):
        """Do not reply if API error returns for all songs."""
        message = make_mock_message(
            text=(
                'check this one: https://deezer.com/track/1, '
                'https://deezer.com/track/2'
            ),
            chat_type=ChatType.PRIVATE,
        )
        url1 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        url2 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/2'
        with aioresponses() as m:
            m.get(url1, status=error_code, repeat=True)
            m.get(url2, status=error_code, repeat=True)
            await bot.dispatcher.message_handlers.notify(message)
            assert 'API error' in caplog.text
            assert not message.reply.called

    async def test_replies_if_404(self, caplog, bot):
        """Reply if API error returned 404 for a song URL."""
        message = make_mock_message(
            text='https://deezer.com/track/1',
            chat_type=ChatType.PRIVATE,
            is_reply=True,
        )
        url1 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        with aioresponses() as m:
            m.get(url1, status=HTTPStatus.NOT_FOUND, repeat=True)
            await bot.dispatcher.message_handlers.notify(message)
            assert 'API error' in caplog.text
            assert message.reply.called
            assert message.reply.called_with_text == (
                "Sorry, Odesli couldn't find that song"
            )

    async def test_not_replies_if_validation_error(self, caplog, bot):
        """Do not reply if API response validation error."""
        message = make_mock_message(
            text='check this one: https://deezer.com/track/1',
            chat_type=ChatType.PRIVATE,
        )
        url1 = f'{bot.config.ODESLI_API_URL}?url=https://deezer.com/track/1'
        with aioresponses() as m:
            m.get(url1, status=HTTPStatus.OK, payload={'invalid': 'invalid'})
            await bot.dispatcher.message_handlers.notify(message)
            assert 'Invalid response data' in caplog.text
            assert not message.reply.called

    async def test_retries_if_api_connection_error(self, caplog, bot):
        """Bot retries to connect if API HTTP connection error."""
        bot.API_RETRY_TIME = 1
        bot.API_MAX_RETRIES = 1
        message = make_mock_message(
            text='check this one: https://deezer.com/track/1',
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
