"""Songlink bot."""
import asyncio
import contextvars
from collections import Counter
from dataclasses import dataclass
from http import HTTPStatus
from typing import Dict, List, Set, Tuple
from urllib.parse import urlencode

import aiohttp
import structlog
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ChatType
from aiogram.utils.exceptions import MessageCantBeDeleted
from marshmallow import ValidationError

from group_songlink_bot.config import Config
from group_songlink_bot.platforms import PLATFORMS
from group_songlink_bot.schemas import SongLinkResponseSchema


class BotException(Exception):
    """Songlink Bot exception."""


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
    title: str
    #: Artist
    artist: str
    #: Platform URLs
    urls: Dict[str, str]
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


class SonglinkBot:
    """Songlink Telegram bot."""

    #: If this string is in an incoming message, the message will be skipped
    #: by the bot
    SKIP_MARK = '!skip'
    #: Time to wait before retrying and API call if 429 code was returned
    RETRY_WAIT_TIME = 5

    def __init__(self, config: Config = None):
        """Initialize the bot.

        :param config: configuration
        """
        # Load config
        self._config = config or Config.load_config()
        # Create a logger
        self.logger = structlog.get_logger('group_songlink_bot')
        self.logger_var = contextvars.ContextVar('logger', default=self.logger)
        # Initialize the bot and a dispatcher
        self._bot = Bot(token=self._config.BOT_API_TOKEN)
        self._dp = Dispatcher(self._bot)
        # Setup logging middleware
        self._logging_middleware = LoggingMiddleware(self.logger_var)
        self._dp.middleware.setup(self._logging_middleware)
        # Add handlers
        self._add_handlers()

    def _add_handlers(self):
        """Add messages and commands handlers."""
        self._dp.message_handler(commands=['start', 'help'])(self.send_welcome)
        self._dp.message_handler()(self.handle_message)

    async def send_welcome(self, message: types.Message):
        """Send a welcome message.

        :param message: incoming message
        """
        _logger = self.logger_var.get()
        _logger.debug('Sending a welcome message')
        welcome_msg_template = (
            'Hi!\n'
            "I'm a SongLink Bot. You can message me a link to a supported "
            'music streaming platform and I will respond with links from all '
            'the platforms. If you invite me to a group chat I will do the '
            'same as well as trying to delete original message (you must '
            'promote me to admin to enable this behavior).\n'
            'Supported platforms: {supported_platforms}.\n'
            'Powered by great <a href="https://song.link/">SongLink</a> '
            '(thank you guys!).'
        )
        supported_platforms = []
        for platform in PLATFORMS.values():
            supported_platforms.append(platform.name)
        welcome_msg = welcome_msg_template.format(
            supported_platforms=' | '.join(supported_platforms)
        )
        await message.reply(text=welcome_msg, parse_mode='HTML')

    def _make_query(self, song_url: str, user_country: str = 'RU') -> str:
        """Make an Songlink API query URL for a given song.

        :param str song_url: song URL in any platform
        :param user_country: user country (not sure if it matters)
        :return: Songlink API
        """
        params = {'url': song_url, 'userCountry': user_country}
        if self._config.SONGLINK_API_KEY:
            params['api_key'] = self._config.SONGLINK_API_KEY
        url_params = urlencode(params)
        url = f'{self._config.SONGLINK_API_URL}?{url_params}'
        return url

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
            if idx1 in merged_song_info_indexes:
                continue
            ids1 = song_info1.ids
            for idx2, song_info2 in enumerate(song_infos):
                if (
                    song_info2 is song_info1
                    or idx2 in merged_song_info_indexes
                ):
                    continue
                if ids1 & song_info2.ids:
                    song_info1.ids = ids1 | song_info2.ids
                    song_info1.urls = {**song_info1.urls, **song_info2.urls}
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
        # Get songs information by its URLs via Songlink service API
        song_infos = await asyncio.gather(
            *[self.find_song_by_url(song_url) for song_url in song_urls]
        )
        # Combine song infos if different platform links point to
        # the same song
        song_infos = self._merge_same_songs(song_infos)
        # Replace original URLs in message with footnotes (like [1], [2] etc)
        text = self._replace_urls_with_footnotes(message.text, song_infos)
        # Form reply text.  In group chats quote original message
        if message.chat.type != ChatType.PRIVATE:
            reply_list = [f'@{message.from_user.username} wrote: {text}\n']
        else:
            reply_list = []
        for index, song_info in enumerate(song_infos, start=1):
            reply_list.append(
                f'{index}. {song_info.artist} - {song_info.title}'
            )
            platform_urls = []
            for platform_name, url in song_info.urls.items():
                platform_urls.append(f'<a href="{url}">{platform_name}</a>')
            reply_list.append(' | '.join(platform_urls))
        reply_text = '\n'.join(reply_list)
        await message.reply(text=reply_text, parse_mode='HTML')
        # Try to delete original message if in group chat
        if message.chat.type != ChatType.PRIVATE:
            try:
                await message.delete()
            except MessageCantBeDeleted as exc:
                logger.warning('Cannot delete message', exc_info=exc)

    async def find_song_by_url(self, song_url: SongUrl) -> SongInfo:
        """Make an API call to SongLink service and return song data for
        supported services.

        :param str song_url: URL of a song in any supported platform
        :return: SongLink response
        """
        logger = self.logger_var.get()
        url = self._make_query(song_url.url)
        async with aiohttp.ClientSession() as client:
            async with client.get(url) as resp:
                if resp.status != HTTPStatus.OK:
                    if resp.status == HTTPStatus.TOO_MANY_REQUESTS:
                        logger.warning(
                            'Too many requests',
                            status_code=resp.status,
                            response=resp.content,
                        )
                        await asyncio.sleep(self.RETRY_WAIT_TIME)
                    else:
                        logger.error(
                            'SongLink API error',
                            status_code=resp.status,
                            response=resp.content,
                        )
                response = await resp.json()
                logger.debug('Got SongLink API response', response=response)
                schema = SongLinkResponseSchema()
                try:
                    data = schema.load(response)
                except ValidationError as exc:
                    logger.error('Invalid response data', exc_info=exc)
                else:
                    song_info = self.process_songlink_response(
                        data, song_url.url
                    )
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

    def process_songlink_response(self, data: dict, url: str) -> SongInfo:
        """Extract a song info from SongLink API info.

        :param data: deserialized JSON SongLink data
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

    def start(self):
        """Start the bot."""
        self.logger.info('Starting polling...')
        executor.start_polling(self._dp, skip_updates=True)

    async def stop(self):
        """Stop the bot."""
        await self._bot.close()


if __name__ == '__main__':
    bot = SonglinkBot()
    bot.start()
