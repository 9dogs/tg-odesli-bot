"""Unit tests for Odesli bot."""
from pytest import mark

from tg_odesli_bot.bot import OdesliBot, SongInfo


@mark.usefixtures('loop')
class TestOdesliBot:
    """Unit tests for Odesli bot."""

    async def test_extracts_urls(self, bot: OdesliBot):
        """Extract platform URLs from message text."""
        text = (
            '1 https://www.deezer.com/track/568497412,\n'
            '2 https://play.google.com/music/m/Tdyd5oxivy52cpw4b2qqbgewdwu.\n'
            '3 https://soundcloud.com/worakls/nto-trauma-worakls-remix \n'
            '4 https://music.yandex.com/album/50197/track/120711 no_link\n'
            '5 https://music.yandex.ru/album/6004920/track/44769475\n'
            '6 https://open.spotify.com/track/1gfzgfcrmkn2yTWuVGhCgh\n'
            '7 https://music.youtube.com/watch?v=eVTXPUF4Oz4\n'
            '8 https://www.youtube.com/watch?v=eVTXPUF4Oz4'
        )
        urls = bot.extract_song_urls(text)
        assert len(urls) == 8
        deezer_url = urls[0]
        assert deezer_url.platform_key == 'deezer'
        assert deezer_url.url == 'https://www.deezer.com/track/568497412'
        google_url = urls[1]
        assert google_url.platform_key == 'google'
        assert google_url.url == (
            'https://play.google.com/music/m/Tdyd5oxivy52cpw4b2qqbgewdwu'
        )
        soundcloud_url = urls[2]
        assert soundcloud_url.platform_key == 'soundcloud'
        assert soundcloud_url.url == (
            'https://soundcloud.com/worakls/nto-trauma-worakls-remix'
        )
        yandex_com = urls[3]
        assert yandex_com.platform_key == 'yandex'
        assert yandex_com.url == (
            'https://music.yandex.com/album/50197/track/120711'
        )
        yandex_ru = urls[4]
        assert yandex_ru.platform_key == 'yandex'
        assert yandex_ru.url == (
            'https://music.yandex.ru/album/6004920/track/44769475'
        )
        spotify = urls[5]
        assert spotify.platform_key == 'spotify'
        assert spotify.url == (
            'https://open.spotify.com/track/1gfzgfcrmkn2yTWuVGhCgh'
        )
        youtube_music = urls[6]
        assert youtube_music.platform_key == 'youtubeMusic'
        assert youtube_music.url == (
            'https://music.youtube.com/watch?v=eVTXPUF4Oz4'
        )
        youtube = urls[7]
        assert youtube.platform_key == 'youtube'
        assert youtube.url == (
            'https://www.youtube.com/watch?v=eVTXPUF4Oz4'
        )

    async def test_merges_urls_for_same_song(self, bot: OdesliBot):
        """Merge SongInfo objects if they point to the same song."""
        song_infos = (
            SongInfo(
                ids={'id1', 'id2'},
                title='Test title',
                artist='Test artist',
                urls={'deezer': 'http://test_deezer_url'},
                urls_in_text={'http://test_deezer_url'},
            ),
            SongInfo(
                ids={'id2', 'id3'},
                title='Test title',
                artist='Test artist',
                urls={'google': 'http://test_google_url'},
                urls_in_text={'http://test_google_url'},
            ),
            SongInfo(
                ids={'id3', 'id4'},
                title='Test title',
                artist='Test artist',
                urls={'soundcloud': 'http://test_soundcloud_url'},
                urls_in_text={'http://test_soundcloud_url'},
            ),
            SongInfo(
                ids={'id5'},
                title='Not merged',
                artist='Not merged',
                urls={'not_merged': 'http://not_merged'},
                urls_in_text={'http://not_merged'},
            ),
        )
        song_infos_merged = bot._merge_same_songs(song_infos)
        assert len(song_infos_merged) == 2
        song_info = song_infos_merged[0]
        assert song_info.ids == {'id1', 'id2', 'id3', 'id4'}
        assert song_info.urls == {
            'deezer': 'http://test_deezer_url',
            'google': 'http://test_google_url',
            'soundcloud': 'http://test_soundcloud_url',
        }
        assert set(song_info.urls_in_text) == {
            'http://test_deezer_url',
            'http://test_google_url',
            'http://test_soundcloud_url',
        }
        assert len(song_info.urls_in_text) == 3
