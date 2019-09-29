import contextvars
import html
from urllib.parse import urlencode

import aiohttp
import structlog
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.middlewares import BaseMiddleware

from group_songlink_bot.config import Config
from group_songlink_bot.platforms import PLATFORMS


class LoggingMiddleware(BaseMiddleware):
    """Middleware to bind incoming message meta data to a logger."""

    def __init__(self, logger_var):
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
    """SongLink Telegram Bot."""

    # If this string is in an incoming message, the message will be skipped
    # by the bot
    SKIP_MARK = '!skip'

    def __init__(self):
        """Initialize the bot."""
        # Load config
        self._config = Config.load_config()
        # Create a logger
        self.logger_var = contextvars.ContextVar('logger')
        self.logger = structlog.get_logger(self.__class__.__name__)
        self.logger_var.set(self.logger)
        # Initialize the bot and a dispatcher
        self._bot = Bot(token=self._config.BOT_API_TOKEN)
        self._dp = Dispatcher(self._bot)
        # Setup logging middleware
        logging_middleware = LoggingMiddleware(self.logger_var)
        self._dp.middleware.setup(logging_middleware)
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
        welcome_msg = (
            'Hi!\n'
            "I'm a simple SongLink Bot. If you invite me to a group and "
            'promote to an admin (for me to be able to read messages) I will '
            'replace any message containing links to Deezer, Google Music or '
            'SoundCloud songs with all-services-in-one message!\n'
            'Powered by <a href="https://song.link/">SongLink</a>.'
        )
        await message.reply(welcome_msg, parse_mode='HTML')

    async def handle_message(self, message: types.Message):
        """Handle incoming message.

        :param message: incoming message
        """
        logger = self.logger_var.get()
        # Check if message should be handled
        text = message.text
        if self.SKIP_MARK in text:
            logger.debug('Message is skipped due to SKIP_MARK')
            return
        songs = []
        idx = 1
        for platform in PLATFORMS.values():
            for match in platform.url_re.finditer(text):
                text = platform.url_re.sub(html.escape(f'[{idx}]'), text)
                url = match.group(0)
                # Do SongLink API request
                response = await self.find_song_by_url(url)
                song_info = self.extract_song_info(response, index=idx)
                songs.append(song_info)
                idx += 1
        reply = [f'@{message.from_user.username} wrote:\n{text}\n']
        if songs:
            reply_msg = '\n'.join(reply + songs)
            logger.debug('Reply', reply=reply_msg)
            await message.reply(reply_msg, reply=False, parse_mode='HTML')
            await message.delete()
        else:
            logger.debug('No songs found in message')

    def find_song_urls(self, message_text):
        """Find

        :param message_text:
        :return:
        """

    async def find_song_by_url(self, url, user_country='RU') -> dict:
        """Make an API call to SongLink service and return song data for
        supported services.

        :param url:
        :param user_country: user country (not sure if it matters)
        :return: SongLink response
        """
        logger = self.logger_var.get()
        params = urlencode({'url': url, 'userCountry': user_country})
        async with aiohttp.ClientSession() as client:
            url = f'{self._config.SONGLINK_API_URL}?{params}'
            async with client.get(url) as resp:
                assert resp.status == 200
                response = await resp.json()
                logger.debug('Got SongLink API response', response=response)
        return response

    def extract_song_info(self, data: dict, index: int) -> str:
        """Extract a song info from SongLink API info.

        :param data: JSON SongLink data
        :param index: index of a song in incoming message text
        :return: song info string like
            Whitewildbear, Ambyion - Rue
            <a href="...">Deezer</a>
            <a href="...">Google Music</a>
            <a href="...">SoundCloud</a>
        """
        entity_record = list(data['entitiesByUniqueId'].values())[0]
        artist = entity_record['artistName']
        title = entity_record['title']
        song_data = [f'{index}. {artist} - {title}']
        platform_links_order = []
        for platform_key, platform_data in data['linksByPlatform'].items():
            if platform_key in PLATFORMS:
                platform = PLATFORMS[platform_key]
                url = platform_data['url']
                platform_links_order.append(
                    (f'<a href="{url}">{platform.name}</a>', platform.order)
                )
        song_data += [
            el[0] for el in sorted(platform_links_order, key=lambda x: x[1])
        ]
        song_info = '\n'.join(song_data)
        return song_info

    def start(self):
        """Start the bot."""
        executor.start_polling(self._dp, skip_updates=True)


if __name__ == '__main__':
    bot = SonglinkBot()
    bot.start()
