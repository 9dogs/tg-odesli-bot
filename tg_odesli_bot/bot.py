"""Telegram Odesli bot."""
import asyncio
import contextvars
import hashlib
from collections import Counter
from dataclasses import dataclass
from http import HTTPStatus
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import aiohttp
import structlog
from aiocache import caches
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import (
    ChatType,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Message,
)
from aiogram.utils.exceptions import MessageCantBeDeleted, NetworkError
from aiohttp import ClientConnectionError, TCPConnector
from marshmallow import ValidationError

from tg_odesli_bot.config import Config
from tg_odesli_bot.platforms import PLATFORMS
from tg_odesli_bot.schemas import ApiResponseSchema


class BotError(Exception):
    """Base bot error."""


class SongNotFoundError(BotError):
    """Song not found error."""


class APIError(Exception):
    """Odesli API error."""

    def __init__(
        self,
        status_code: Optional[HTTPStatus] = None,
        message: Optional[str] = None,
    ):
        """Init an error.

        :param status_code: response status code
        :param message: error message
        """
        super().__init__()
        self.status_code = status_code
        self.message = message


@dataclass(frozen=True)
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

    #: Odesli identifiers
    ids: set
    #: Title
    title: Optional[str]
    #: Artist
    artist: Optional[str]
    #: Platform URLs
    urls: Optional[Dict[str, str]]
    #: Thumbnail URL
    thumbnail_url: Optional[str]
    #: URLs in text
    urls_in_text: Set[str]

    def __bool__(self):
        """Return True if SongInfo is not empty."""
        return bool(self.ids)


class LoggingMiddleware(BaseMiddleware):
    """Middleware to bind incoming message metadata to a logger."""

    def __init__(self, logger_var):
        """Init middleware."""
        self.logger_var = logger_var
        super().__init__()

    async def on_pre_process_message(self, message: types.Message, *args):
        """Bind message metadata to a logger.

        :param message: incoming message
        :param * args: arguments
        """
        logger = self.logger_var.get()
        _logger = logger.bind(
            from_username=message.from_user.mention,
            chat_id=message.chat.id,
            message_id=message.message_id,
        )
        self.logger_var.set(_logger)


class OdesliBot:
    """Odesli Telegram bot."""

    #: If this string is in an incoming message, the message won't be processed
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
    #: Welcome message template
    WELCOME_MSG_TEMPLATE = (
        "I'm an (unofficial) Odesli Bot. You can send me a link to a song on "
        'any supported music streaming platform and I will reply with links '
        'from all the other platforms. I work in group chats as well. In a '
        'group chat I will also try to delete original message so that the '
        'chat remains tidy (you must promote me to admin to enable this).\n'
        '\n'
        '<b>Supported platforms:</b> {supported_platforms}.\n'
        '\n'
        'The bot is open source. Your feedback, suggestions and PRs are '
        'welcome: <a href="https://github.com/9dogs/tg-odesli-bot">GitHub</a>.'
        '\n'
        'Powered by a great <a href="https://odesli.co/">Odesli</a> service.'
    )

    def __init__(self, config: Optional[Config] = None, *, loop=None):
        """Initialize the bot.

        :param config: configuration
        :param loop: event loop
        """
        # Configuration
        self.config = config or Config.load()
        # Logger
        self.logger = structlog.get_logger('tg_odesli_bot')
        self.logger_var = contextvars.ContextVar('logger', default=self.logger)
        # Event loop
        self._loop = loop or asyncio.get_event_loop()
        # Cache
        self.cache = caches.get('default')
        # Telegram connection retries count
        self._tg_retries = 0

    async def init(self):
        """Initialize the bot (async part)."""
        # HTTP session
        self.session = aiohttp.ClientSession(connector=TCPConnector(limit=10))
        # Aiogram bot instance
        self.bot = Bot(token=self.config.TG_API_TOKEN)
        # Bot's dispatcher
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
        self.dispatcher.inline_handler()(self.handle_inline_query)

    async def send_welcome(self, message: types.Message):
        """Send a welcome message.

        :param message: incoming message
        """
        _logger = self.logger_var.get()
        _logger.debug('Sending a welcome message')
        supported_platforms = []
        for platform in PLATFORMS.values():
            supported_platforms.append(platform.name)
        welcome_msg = self.WELCOME_MSG_TEMPLATE.format(
            supported_platforms=' | '.join(supported_platforms)
        )
        await message.reply(text=welcome_msg, parse_mode='HTML', reply=False)

    def _replace_urls_with_footnotes(
        self, message: str, song_infos: Tuple[SongInfo, ...]
    ) -> str:
        """Replace song URLs in message with footnotes.

        E.g. "this song is awesome <link>" will be transformed to "this song
        is awesome [1]".

        :param message: original message text
        :param song_infos: list of SongInfo metadata objects
        :returns: transformed message
        """
        # Check if message consists only of a song URL and return empty string
        # if so
        _test_message = message
        for song_info in song_infos:
            for url in song_info.urls_in_text:
                _test_message = _test_message.replace(url, '')
        if not _test_message.strip():
            return ''
        # Else replace song URLs with [1], [2] etc
        for index, song_info in enumerate(song_infos, start=1):
            for url in song_info.urls_in_text:
                message = message.replace(url, f'[{index}]')
        return message

    def extract_song_urls(
        self, text: str, skip_youtube: bool = False
    ) -> List[SongUrl]:
        """Extract song URLs from text for each registered platform.

        :param text: message text
        :param skip_youtube: skip YouTube platform (used for group messages)
        :returns: list of SongURLs
        """
        urls = []
        for platform_key, platform in PLATFORMS.items():
            if skip_youtube and platform_key == 'youtube':
                continue
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
        """Merge SongInfo objects if different links point to the same song.

        Use identifiers provided by Odesli API to find identical song linked
        from different platforms.

        :param song_infos: tuple of SongInfo objects found in a message
        :returns: tuple of merged SongInfo objects
        """
        merged_song_info_indexes: Set[int] = set()
        for idx1, song_info1 in enumerate(song_infos):
            # Skip empty SongInfos
            if not song_info1:
                continue
            if idx1 in merged_song_info_indexes:
                continue
            ids1 = song_info1.ids
            for idx2, song_info2 in enumerate(song_infos):
                if (
                    song_info2 is song_info1
                    or idx2 in merged_song_info_indexes
                    or not song_info2
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
                        song_info1.urls_in_text | song_info2.urls_in_text
                    )
                    merged_song_info_indexes.add(idx2)
        merged_song_infos = tuple(
            song_info
            for idx, song_info in enumerate(song_infos)
            if idx not in merged_song_info_indexes
        )
        return merged_song_infos

    async def _find_songs(
        self, text: str, group_message: bool
    ) -> Tuple[SongInfo, ...]:
        """Find song info based on given text.

        :param text: message text
        :param group_message: text is from a group message
        :returns: tuple of SongInfo instances
        :raise SongNotFoundError: if Odesli couldn't find any song
        """
        # Extract song URLs from the message
        song_urls = self.extract_song_urls(text, skip_youtube=group_message)
        if not song_urls:
            return ()
        # Get songs information by its URLs via Odesli service API
        tasks = [self.find_song_by_url(song_url) for song_url in song_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        song_infos, exceptions = [], []
        for item, song_url in zip(results, song_urls):
            if isinstance(item, SongInfo):
                song_infos.append(item)
            else:
                # Append an empty SongInfo
                song_infos.append(
                    SongInfo(set(), None, None, None, None, {song_url.url})
                )
                exceptions.append(item)
        # Raise an exception if API returned 404 for all songs
        if not any(song_infos) and all(
            exc.status_code == HTTPStatus.NOT_FOUND for exc in exceptions
        ):
            raise SongNotFoundError
        # Merge song infos if different platform links point to the same song
        merged_song_infos = self._merge_same_songs(tuple(song_infos))
        return merged_song_infos

    def _format_urls(
        self, song_info: SongInfo, separator: str = ' | '
    ) -> Tuple[str, str]:
        """Format platform URLs into a single HTML string.

        :param song_info: SongInfo metadata
        :param separator: separator for platform URLs
        :returns: HTML string e.g.
            <a href="1">Deezer</a> | <a href="2">SoundCloud</a> ...
        """
        platform_urls = song_info.urls or {}
        reply_urls, platform_names = [], []
        for platform_name, url in platform_urls.items():
            reply_urls.append(f'<a href="{url}">{platform_name}</a>')
            platform_names.append(platform_name)
        formatted_urls = separator.join(reply_urls)
        formatted_platforms = separator.join(platform_names)
        return formatted_urls, formatted_platforms

    def _compose_reply(
        self,
        song_infos: Tuple[SongInfo, ...],
        message_text: str,
        message: Message,
        append_index: bool,
    ) -> str:
        """Compose a reply.

        For group chats original message is included in
        reply with song URLs replaces with its indexes.  If original message
        consists only of a single link the index is omitted.

        <b>@test_user wrote:</b> check this one [1]
        1. Artist - Song
        <a href="url1">Deezer</a>
        ...

        :param song_infos: list of songs metadata
        :param message: incoming message
        :param message_text: incoming message text with song URLs replaced
            with its indexes
        :param append_index: append index
        :returns: reply text
        """
        # Quote the original message for group chats
        if message.chat.type != ChatType.PRIVATE:
            if message.from_user.username:
                mention = message.from_user.mention
            else:
                mention = message.from_user.get_mention(as_html=True)
            reply_list = [f'<b>{mention} wrote:</b> {message_text}']
        else:
            reply_list = [message_text]
        for index, song_info in enumerate(song_infos, start=1):
            # Use original URL if we failed to find that song via Odesli API
            if not song_info:
                urls_in_text = song_info.urls_in_text.pop()
                reply_list.append(f'{index}. {urls_in_text}')
                continue
            if append_index:
                reply_list.append(
                    f'{index}. {song_info.artist} - {song_info.title}'
                )
            else:
                reply_list.append(f'{song_info.artist} - {song_info.title}')
            platform_urls, __ = self._format_urls(song_info)
            reply_list.append(platform_urls)
        reply = '\n'.join(reply_list).strip()
        return reply

    async def handle_inline_query(self, inline_query: InlineQuery):
        """Handle inline query.

        :param inline_query: query
        """
        logger = self.logger_var.get()
        query = inline_query.query
        logger.info('Inline request', query=query)
        if not query:
            await self.bot.answer_inline_query(inline_query.id, results=[])
            return
        try:
            song_infos = await self._find_songs(query, group_message=False)
        except SongNotFoundError:
            reply = InputTextMessageContent(
                "Sorry, Odesli couldn't find that song", parse_mode='HTML'
            )
            article = InlineQueryResultArticle(
                id=hashlib.md5(query.encode()).hexdigest(),
                title='Not found',
                input_message_content=reply,
            )
            await self.bot.answer_inline_query(
                inline_query.id, results=[article]
            )
            return
        articles = []
        for song_info in song_infos:
            if not song_info:
                continue
            # Use hashed concatenated IDs as a result id
            id_ = ''.join(song_info.ids)
            result_id = hashlib.md5(id_.encode()).hexdigest()
            title = f'{song_info.artist} - {song_info.title}'
            platform_urls, platform_names = self._format_urls(song_info)
            reply_text = f'{title}\n{platform_urls}'
            reply = InputTextMessageContent(reply_text, parse_mode='HTML')
            article = InlineQueryResultArticle(
                id=result_id,
                title=title,
                input_message_content=reply,
                thumb_url=song_info.thumbnail_url,
                description=platform_names,
            )
            articles.append(article)
        await self.bot.answer_inline_query(inline_query.id, results=articles)

    async def handle_message(self, message: types.Message):
        """Handle incoming message.

        :param message: incoming message
        """
        logger = self.logger_var.get()
        # Check if message should be processed
        if self.SKIP_MARK in message.text:
            logger.debug('Message is skipped due to skip mark')
            return
        group_message = message.chat.type in (
            ChatType.GROUP,
            ChatType.SUPERGROUP,
        )
        try:
            song_infos = await self._find_songs(
                message.text, group_message=group_message
            )
        except SongNotFoundError:
            await message.reply(
                text="Sorry, Odesli couldn't find that song",
                parse_mode='HTML',
            )
            return
        # Do not reply if no songs have been found in message or song info has
        # only one URL (which will be the same URL as in the original message)
        if not any(song_infos) or all(
            len(song_info.urls) == 1
            for song_info in song_infos
            if song_info.urls
        ):
            return
        # Replace original URLs in message with footnotes (e.g. [1], [2], ...)
        prepared_message_text = self._replace_urls_with_footnotes(
            message.text, song_infos
        )
        if prepared_message_text:
            prepared_message_text += '\n'
        # Compose reply text
        append_index = bool(len(song_infos) > 1 or prepared_message_text)
        reply_text = self._compose_reply(
            song_infos=song_infos,
            message_text=prepared_message_text,
            message=message,
            append_index=append_index,
        )
        await message.reply(text=reply_text, parse_mode='HTML', reply=False)
        # In group chat try to delete original message
        if message.chat.type != ChatType.PRIVATE:
            try:
                await message.delete()
            except MessageCantBeDeleted as exc:
                logger.warning('Cannot delete message', exc_info=exc)

    @staticmethod
    def normalize_url(url):
        """Strip "utm_" parameters from URL.

        Used in caching to increase cache density.

        :param url: url
        :returns: normalized URL
        """
        parsed = urlparse(url)
        query_dict = parse_qs(parsed.query, keep_blank_values=True)
        filtered_params = {
            k: v for k, v in query_dict.items() if not k.startswith('utm_')
        }
        normalized_url = urlunparse(
            [
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(filtered_params, doseq=True),
                parsed.fragment,
            ]
        )
        return normalized_url

    async def find_song_by_url(self, song_url: SongUrl) -> SongInfo:
        """Find song info by its URL.

        Make an API call to Odesli service and return song data for
        supported services.

        :param song_url: SongURL object
        :returns: SongInfo instance for given URL
        :raises APIError: if Odesli API returned an error
        """
        logger = self.logger_var.get()
        # Normalize URL to use as a consistent cache key
        normalized_url = self.normalize_url(song_url.url)
        params = {'url': normalized_url}
        if self.config.ODESLI_API_KEY:
            params['api_key'] = self.config.ODESLI_API_KEY
        logger = logger.bind(url=self.config.ODESLI_API_URL, params=params)
        _retries = 0
        while _retries < self.API_MAX_RETRIES:
            # Try to get data from cache.  Should be inside `while` loop in
            # case other task retrieves the data and sets cache
            cached = await self.cache.get(normalized_url)
            if cached:
                logger.debug('Returning data from cache')
                song_info = SongInfo(
                    ids=cached.ids,
                    title=cached.title,
                    artist=cached.artist,
                    thumbnail_url=cached.thumbnail_url,
                    urls=cached.urls,
                    urls_in_text={song_url.url},
                )
                return song_info
            try:
                # Wait for ready event in case requests are being throttled
                if not self._api_ready.is_set():
                    logger.info('Waiting for the API')
                    await self._api_ready.wait()
                # Query the API
                async with self.session.get(
                    self.config.ODESLI_API_URL, params=params
                ) as resp:
                    if resp.status != HTTPStatus.OK:
                        # Throttle requests and retry if 429
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
                        # Else log and raise an error
                        text = await resp.text()
                        logger.error(
                            'API error', status_code=resp.status, message=text
                        )
                        raise APIError(status_code=resp.status, message=text)
                    response = await resp.json()
                    logger.debug('Got Odesli API response', response=response)
                    schema = ApiResponseSchema(unknown='EXCLUDE')
                    try:
                        data = schema.load(response)
                    except ValidationError as exc:
                        logger.error('Invalid response data', exc_info=exc)
                        raise APIError(
                            status_code=None, message='Invalid data'
                        )
                    else:
                        song_info = self.process_api_response(
                            data, song_url.url
                        )
                        # Cache processed data
                        await self.cache.set(normalized_url, song_info)
                        return song_info
            except ClientConnectionError as exc:
                _retries += 1
                logger.error(
                    'Connection error, retrying in %d sec',
                    self.API_RETRY_TIME,
                    exc_info=exc,
                    retries=_retries,
                )
                await asyncio.sleep(self.API_RETRY_TIME)
        raise APIError(status_code=None, message='Connection error')

    def _filter_platform_urls(self, platform_urls: dict) -> dict:
        """Filter and reorder platform URLs according to `PLATFORMS` registry.

        :param platform_urls: dictionary of {platform_key: platform_urls}
        :returns: dictionary of filtered and ordered platform URLs
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
        # Reorder platform URLs
        platform_urls = {
            name: url for order, name, url in sorted(urls, key=lambda x: x[0])
        }
        return platform_urls

    def process_api_response(self, data: dict, url: str) -> SongInfo:
        """Process Odesli API data creating SongInfo metadata object.

        :param data: deserialized Odesli data
        :param url: original URL in message text
        :returns: song info object
        """
        # Set of song identifiers
        ids = set()
        titles, artists = [], []
        thumbnail_url = None
        for song_entity in data['songs'].values():
            ids.add(song_entity['id'])
            titles.append(song_entity['title'])
            artists.append(song_entity['artist'])
            # Pick the first thumbnail URL
            if song_entity.get('thumbnail_url') and not thumbnail_url:
                thumbnail_url = song_entity['thumbnail_url']
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
            thumbnail_url=thumbnail_url,
            urls=platform_urls,
            urls_in_text={url},
        )
        return song_info

    async def _start(self):
        """Start polling.  Retry if cannot connect to Telegram servers.

        Mimics `aiogram.executor.start_polling` functionality.
        """
        await self.init()
        try:
            await self.dispatcher.skip_updates()
            self._loop.create_task(self.dispatcher.start_polling())
        except (
            ConnectionResetError,
            NetworkError,
            ClientConnectionError,
        ) as exc:
            self.logger.info(
                'Connection error, retrying in %d sec',
                self.TG_RETRY_TIME,
                exc_info=exc,
                retries=self._tg_retries,
            )
            if (
                self.TG_MAX_RETRIES is None
                or self._tg_retries < self.TG_MAX_RETRIES
            ):
                self._tg_retries += 1
                await asyncio.sleep(self.TG_RETRY_TIME)
                asyncio.create_task(self._start())
            else:
                self.logger.info('Max retries count reached, exiting')
                await self.stop()
                self._loop.stop()
        else:
            self.logger.info('Bot started')  # pragma: no cover

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
        await self.cache.clear()
        await self.session.close()
        await self.bot.close()


def main():
    """Run the bot."""
    bot = OdesliBot()  # pragma: no cover
    bot.start()  # pragma: no cover


if __name__ == '__main__':
    main()  # pragma: no cover
