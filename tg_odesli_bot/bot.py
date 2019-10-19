"""Odesli bot."""
import asyncio
import contextvars
import signal
from collections import Counter
from dataclasses import dataclass
from http import HTTPStatus
from typing import Dict, List, Optional, Set, Tuple

import aiohttp
import structlog
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ChatType
from aiogram.utils.exceptions import MessageCantBeDeleted, NetworkError
from aiohttp import ClientConnectionError
from marshmallow import ValidationError

from tg_odesli_bot.config import Config
from tg_odesli_bot.platforms import PLATFORMS
from tg_odesli_bot.schemas import ApiResponseSchema


class BotException(Exception):
    """Odesli Bot exception."""


@dataclass
class SongUrl:
    """Song URL found in text."""

    #: Platform key
    platform_key: str
    #: Platform name (human-readable)
    platform_name: str
    #: URL
    url: str


@dataclass
class SongInfo:
    """Song metadata."""

    #: Ids
    ids: set
    #: Title
    title: Optional[str]
    #: Artist
    artist: Optional[str]
    #: Platform URLs
    urls: Optional[Dict[str, str]]
    #: URLs in text
    urls_in_text: List[str]


class LoggingMiddleware(BaseMiddleware):
    """Middleware to bind incoming message metadata to a logger."""

    def __init__(self, logger_var):
        """Init middleware."""
        self.logger_var = logger_var
        super().__init__()

    async def on_pre_process_message(self, message: types.Message, data: dict):
        """Bind message metadata to a logger.

        :param message: incoming message
        :param data: data
        """
        logger = self.logger_var.get()
        _logger = logger.bind(
            from_username=message.from_user.username,
            chat_id=message.chat.id,
            message_id=message.message_id,
        )
        self.logger_var.set(_logger)


class OdesliBot:
    """Odesli Telegram bot."""

    #: If this string is in an incoming message, the message will be skipped
    #: by the bot
    SKIP_MARK = '!skip'
    #: Time to wait before retrying and API call if 429 code was returned
    API_RETRY_TIME = 5
    #: Max retries count
    API_MAX_RETRIES = 5
    #: Telegram API retry time
    TG_RETRY_TIME = 1
    #: Max reties count in case of Telegram API connection error (None is
    #: unlimited)
    TG_MAX_RETRIES = None

    def __init__(self, config: Config = None, *, loop=None):
        """Initialize the bot.

        :param config: configuration
        :param loop: event loop
        """
        # Config
        self.config = config or Config.load()
        # Logger
        self.logger = structlog.get_logger('tg_odesli_bot')
        self.logger_var = contextvars.ContextVar('logger', default=self.logger)
        self._loop = loop or asyncio.get_event_loop()
        # HTTP session
        self.session = aiohttp.ClientSession()
        try:
            self._loop.add_signal_handler(signal.SIGINT, self.stop)
        except NotImplementedError:  # Windows
            pass
        # Bot and dispatcher
        self.bot = Bot(token=self.config.TG_API_TOKEN)
        self.dispatcher = Dispatcher(self.bot)
        # API ready event (used for requests throttling)
        self._api_ready = asyncio.Event()
        self._api_ready.set()
        # Setup logging middleware
        self._logging_middleware = LoggingMiddleware(self.logger_var)
        self.dispatcher.middleware.setup(self._logging_middleware)
        # Add handlers
        self._add_handlers()

    def _add_handlers(self):
        """Add messages and commands handlers."""
        self.dispatcher.message_handler(commands=['start', 'help'])(
            self.send_welcome
        )
        self.dispatcher.message_handler()(self.handle_message)

    async def send_welcome(self, message: types.Message):
        """Send a welcome message.

        :param message: incoming message
        """
        _logger = self.logger_var.get()
        _logger.debug('Sending a welcome message')
        welcome_msg_template = (
            'Hi!\n'
            "I'm a Odesli Bot. You can message me a link to a supported "
            'music streaming platform and I will respond with links from all '
            'the platforms. If you invite me to a group chat I will do the '
            'same as well as trying to delete original message (you must '
            'promote me to admin to enable this behavior).\n'
            '<b>Supported platforms:</b> {supported_platforms}.\n'
            'Powered by great <a href="https://odesli.co/">Odesli</a> '
            '(thank you guys!).'
        )
        supported_platforms = []
        for platform in PLATFORMS.values():
            supported_platforms.append(platform.name)
        welcome_msg = welcome_msg_template.format(
            supported_platforms=' | '.join(supported_platforms)
        )
        await message.reply(text=welcome_msg, parse_mode='HTML', reply=False)

    def _replace_urls_with_footnotes(
        self, message: str, song_infos: Tuple[SongInfo, ...]
    ) -> str:
        """Replace song URLs in message with footnotes.

        :param message: original message text
        :param song_infos: list of SongInfo objects
        :return: transformed message
        """
        for index, song_info in enumerate(song_infos, start=1):
            for url in song_info.urls_in_text:
                message = message.replace(url, f'[{index}]')
        return message

    def extract_song_urls(self, text: str) -> List[SongUrl]:
        """Extract song URLs and its positions from text.

        :param text: message text
        :return: list of platform URLs
        """
        urls = []
        for platform_key, platform in PLATFORMS.items():
            for match in platform.url_re.finditer(text):
                platform_url = SongUrl(
                    platform_key=platform_key,
                    platform_name=platform.name,
                    url=match.group(0),
                )
                urls.append(platform_url)
        return urls

    def _merge_same_songs(
        self, song_infos: Tuple[SongInfo, ...]
    ) -> Tuple[SongInfo, ...]:
        """Merge SongInfo objects if two or more links point to the same
        song.

        :param song_infos: songs found in a message
        """
        merged_song_info_indexes: Set[int] = set()
        for idx1, song_info1 in enumerate(song_infos):
            # Skip empty SongInfos
            if not song_info1.ids:
                continue
            if idx1 in merged_song_info_indexes:
                continue
            ids1 = song_info1.ids
            for idx2, song_info2 in enumerate(song_infos):
                if (
                    song_info2 is song_info1
                    or idx2 in merged_song_info_indexes
                    or not song_info2.ids
                ):
                    continue
                ids2 = song_info2.ids
                if ids1 & ids2:
                    song_info1.ids = ids1 | ids2
                    if song_info1.urls and song_info2.urls:
                        song_info1.urls = {
                            **song_info1.urls,
                            **song_info2.urls,
                        }
                    song_info1.urls_in_text = (
                        song_info1.urls_in_text + song_info2.urls_in_text
                    )
                    merged_song_info_indexes.add(idx2)
        merged_song_infos = tuple(
            song_info
            for idx, song_info in enumerate(song_infos)
            if idx not in merged_song_info_indexes
        )
        return merged_song_infos

    async def handle_message(self, message: types.Message):
        """Handle incoming message.

        :param message: incoming message
        """
        logger = self.logger_var.get()
        # Check if message should be handled
        if self.SKIP_MARK in message.text:
            logger.debug('Message is skipped due to skip mark')
            return
        # Extract song URLs from the message
        song_urls = self.extract_song_urls(message.text)
        if not song_urls:
            logger.debug('No songs found in message')
            return
        # Get songs information by its URLs via Odesli service API
        song_infos = await asyncio.gather(
            *[self.find_song_by_url(song_url) for song_url in song_urls]
        )
        # Do not reply to the message if all song infos are empty
        if all(not song_info.ids for song_info in song_infos):
            logger.error('API returned errors for all URLs')
            return
        # Combine song infos if different platform links point to the same song
        song_infos = self._merge_same_songs(song_infos)
        # Replace original URLs in message with footnotes (like [1], [2] etc)
        text = self._replace_urls_with_footnotes(message.text, song_infos)
        # Form a reply text.  In group chats quote the original message
        if message.chat.type != ChatType.PRIVATE:
            reply_list = [
                f'<b>@{message.from_user.username} wrote:</b> {text}\n'
            ]
        else:
            reply_list = []
        for index, song_info in enumerate(song_infos, start=1):
            if not song_info.ids:
                reply_list.append(f'{index}. {song_info.urls_in_text[0]}')
                continue
            reply_list.append(
                f'{index}. {song_info.artist} - {song_info.title}'
            )
            platform_urls = []
            for platform_name, url in song_info.urls.items():
                platform_urls.append(f'<a href="{url}">{platform_name}</a>')
            reply_list.append(' | '.join(platform_urls))
        reply_text = '\n'.join(reply_list)
        await message.reply(text=reply_text, parse_mode='HTML', reply=False)
        # Try to delete original message if in group chat
        if message.chat.type != ChatType.PRIVATE:
            try:
                await message.delete()
            except MessageCantBeDeleted as exc:
                logger.warning('Cannot delete message', exc_info=exc)

    async def find_song_by_url(self, song_url: SongUrl):
        """Make an API call to Odesli service and return song data for
        supported services.

        :param str song_url: URL of a song in any supported platform
        :return: Odesli response
        """
        logger = self.logger_var.get()
        params = {'url': song_url.url}
        if self.config.ODESLI_API_KEY:
            params['api_key'] = self.config.ODESLI_API_KEY
        logger = logger.bind(url=self.config.ODESLI_API_URL, params=params)
        # Create empty SongInfo in case of API error
        song_info = SongInfo(set(), None, None, None, [song_url.url])
        _retries = 0
        while _retries < self.API_MAX_RETRIES:
            try:
                # Wait if requests are being throttled
                if not self._api_ready.is_set():
                    logger.info('Waiting for the API')
                    await self._api_ready.wait()
                async with self.session.get(
                    self.config.ODESLI_API_URL, params=params
                ) as resp:
                    if resp.status != HTTPStatus.OK:
                        # Throttle requests and retry
                        if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
                            logger.warning(
                                'Too many requests, retrying in %d sec',
                                self.API_RETRY_TIME,
                            )
                            # Stop all requests and wait before retry
                            self._api_ready.clear()
                            await asyncio.sleep(self.API_RETRY_TIME)
                            self._api_ready.set()
                            continue
                        # Return empty response if API error
                        else:
                            logger.error('API error', status_code=resp.status)
                            break
                    response = await resp.json()
                    logger.debug('Got Odesli API response', response=response)
                    schema = ApiResponseSchema(unknown='EXCLUDE')
                    try:
                        data = schema.load(response)
                    except ValidationError as exc:
                        logger.error('Invalid response data', exc_info=exc)
                    else:
                        song_info = self.process_api_response(
                            data, song_url.url
                        )
                    finally:
                        break
            except ClientConnectionError as exc:
                _retries += 1
                logger.error(
                    'Connection error, retrying in %d sec',
                    self.API_RETRY_TIME,
                    exc_info=exc,
                    retries=_retries,
                )
                await asyncio.sleep(self.API_RETRY_TIME)
        return song_info

    def _filter_platform_urls(self, platform_urls: dict) -> dict:
        """Filter and reorder platform URLs.

        :param platform_urls: dictionary of platform URLs
        :return: dictionary of filtered platform URLs in order
        """
        logger = self.logger_var.get()
        logger = logger.bind(data=platform_urls)
        urls = []
        for platform_key, platform in PLATFORMS.items():
            if platform_key not in platform_urls:
                logger.info(
                    'No URL for platform in data', platform_key=platform_key
                )
                continue
            urls.append(
                (platform.order, platform.name, platform_urls[platform_key])
            )
        # Reorder platforms URL
        platform_urls = {
            name: url for order, name, url in sorted(urls, key=lambda x: x[0])
        }
        return platform_urls

    def process_api_response(self, data: dict, url: str) -> SongInfo:
        """Extract a song info from Odesli API info.

        :param data: deserialized JSON Odesli data
        :param url: URL in message text
        :return: song info object
        """
        ids = set()
        titles, artists = [], []
        for song_entity in data['songs'].values():
            ids.add(song_entity['id'])
            titles.append(song_entity['title'])
            artists.append(song_entity['artist'])
        platform_urls = {}
        for platform_key, link_entity in data['links'].items():
            platform_urls[platform_key] = link_entity['url']
        platform_urls = self._filter_platform_urls(platform_urls)
        # Pick most common title and artist
        titles_counter = Counter(titles)
        title = titles_counter.most_common(1)[0][0]
        artist_counter = Counter(artists)
        artist = artist_counter.most_common(1)[0][0]
        song_info = SongInfo(
            ids=ids,
            title=title,
            artist=artist,
            urls=platform_urls,
            urls_in_text=[url],
        )
        return song_info

    async def _start(self):
        """Start polling.  Retry if cannot connect to Telegram servers."""
        _retries = 0
        try:
            await self.dispatcher.skip_updates()
            self._loop.create_task(self.dispatcher.start_polling())
        except (
            ConnectionResetError,
            NetworkError,
            ClientConnectionError,
        ) as exc:
            _retries += 1
            self.logger.info(
                'Connection error, retrying in %d sec',
                self.TG_RETRY_TIME,
                exc_info=exc,
                retries=_retries,
            )
            if self.TG_MAX_RETRIES is None or _retries < self.TG_MAX_RETRIES:
                await asyncio.sleep(self.TG_RETRY_TIME)
                asyncio.create_task(self._start())
            else:
                self.logger.info('Max retries count reached, exiting')
                await self.stop()
                self._loop.stop()
        else:
            self.logger.info('Bot started')

    def start(self):
        """Start the bot."""
        self.logger.info('Starting polling...')
        self._loop.create_task(self._start())
        try:
            self._loop.run_forever()
        except KeyboardInterrupt:
            self._loop.create_task(self.stop())

    async def stop(self):
        """Stop the bot."""
        self.logger.info('Stopping...')
        await self.session.close()
        await self.bot.close()


if __name__ == '__main__':
    bot = OdesliBot()
    bot.start()
