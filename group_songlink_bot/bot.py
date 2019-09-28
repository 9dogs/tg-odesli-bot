import html
import os
import re
from dataclasses import dataclass
from urllib.parse import urlencode

import aiohttp
import structlog
from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv

# Load env
load_dotenv()
# Configure logging
logger = structlog.get_logger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=os.environ['BOT_API_TOKEN'])
dp = Dispatcher(bot)

#: SongLink API URL template
SONGLINK_API_URL = 'https://api.song.link/v1-alpha.1/links?{params}'
#: If this string is in an incoming message, the message will be skipped
#: by the bot
SKIP_MARK = '!skip'


@dataclass
class Platform:
    """Platform data holder."""

    songlink_key: str
    url_re: re.Pattern
    name: str
    order: int


deezer_platform = Platform(
    songlink_key='deezer',
    url_re=re.compile(r'https?://([a-zA-Z\d-]+\.)*deezer\.com/[\S]*'),
    name='Deezer',
    order=0,
)

google_music_platform = Platform(
    songlink_key='google',
    url_re=re.compile(
        r'https?://([a-zA-Z\d-]+\.)*play\.google\.com/music/[\S]*'
    ),
    name='Google Music',
    order=1,
)

soundcloud_platform = Platform(
    songlink_key='soundcloud',
    url_re=re.compile(r'https?://([a-zA-Z\d-]+\.)*soundcloud\.com/[\S]*'),
    name='SoundCloud',
    order=2,
)

PLATFORMS_LIST = [deezer_platform, google_music_platform, soundcloud_platform]

# Supported platforms
PLATFORMS = {platform.songlink_key: platform for platform in PLATFORMS_LIST}


def extract_song_info(data: dict, index: int) -> str:
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


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """

    :param message:
    :return:
    """
    _logger = logger.bind(
        from_=message.from_user.username, message_id=message.message_id
    )
    _logger.debug('Sending a welcome message')
    welcome_msg = (
        'Hi!\n'
        'I\'m a simple SongLink Bot. If you invite me to a group and promote '
        'to an admin (for me to be able to read messages) I will replace '
        'any message containing links to Deezer, Google Music or SoundCloud '
        'songs with all-services-in-one message!\n'
        'Powered by <a href="https://song.link/">SongLink</a>.'
    )
    await message.reply(welcome_msg, parse_mode='HTML')


@dp.message_handler()
async def echo(message: types.Message):
    _logger = logger.bind(
        from_=message.from_user.username, message_id=message.message_id
    )
    # Check if message should be handled
    text = message.text
    if SKIP_MARK in text:
        _logger.debug('Message is skipped due to SKIP_MARK')
        return
    songs = []
    idx = 1
    for platform in PLATFORMS.values():
        for match in platform.url_re.finditer(text):
            text = platform.url_re.sub(html.escape(f'[{idx}]'), text)
            url = match.group(0)
            # Do SongLink API request
            params = urlencode({'url': url, 'userCountry': 'RU'})
            async with aiohttp.ClientSession() as client:
                url = SONGLINK_API_URL.format(params=params)
                async with client.get(url) as resp:
                    assert resp.status == 200
                    response = await resp.json()
                    _logger.debug(
                        'Got SongLink API response', response=response
                    )
            song_info = extract_song_info(response, index=idx)
            songs.append(song_info)
            idx += 1
    reply = [f'{message.from_user.first_name} wrote:\n{text}\n']
    if songs:
        reply_msg = '\n'.join(reply + songs)
        _logger.debug('Reply', reply=reply_msg)
        await message.reply(reply_msg, reply=False, parse_mode='HTML')
        await message.delete()
    else:
        _logger.debug('No songs found in message')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
