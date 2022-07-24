"""Unit tests for Odesli bot."""
from pytest import mark

from tg_odesli_bot.bot import OdesliBot, SongInfo


@mark.usefixtures('event_loop')
class TestOdesliBot:
    """Unit tests for Odesli bot."""

    async def test_extracts_urls(self, bot: OdesliBot):
        """Extract platform URLs from message text."""
        text = (
            '1 https://www.deezer.com/track/568497412,\n'
            '2 https://soundcloud.com/worakls/nto-trauma-worakls-remix \n'
            '3 https://music.yandex.com/album/50197/track/120711 no_link\n'
            '4 https://music.yandex.ru/album/6004920/track/44769475\n'
            '5 https://open.spotify.com/track/1gfzgfcrmkn2yTWuVGhCgh\n'
            '6 https://music.youtube.com/watch?v=eVTXPUF4Oz4\n'
            '7 https://www.youtube.com/watch?v=eVTXPUF4Oz4\n'
            '8 https://music.apple.com/se/album/'
            'raindrops-feat-j3po/1450701158\n '
            '9 https://tidal.com/track/139494756\n'
            '10 https://deezer.page.link/aXUq1xjzF8s2AZje9\n'
            '11 https://music.yandex.by/album/6004920/track/44769475\n'
            '12 https://www.deezer.com/ru/track/568497412,\n'
            '13 https://link.tospotify.com/pfc3erwl2ab\n'
            '14 https://music.youtube.com/playlist?list='
            'OLAK5uy_l2F5ezYgFM0mQ3tg2-vK900BTgr8zXMW0\n'
            '15 https://www.youtube.com/playlist?list='
            'OLAK5uy_n64ojqXEYWqrvO5GAWU1Ik040wTIzBdbQ\n'
            '16 https://gunnarspardel.bandcamp.com/album/simplicity-in-a-'
            'complex-world\n'
            '17 https://carbonbasedlifeforms.bandcamp.com/track/6equj5\n'
            '18 https://youtu.be/ugYB3VxpivU'
        )
        urls = bot.extract_song_urls(text)
        assert len(urls) == 18
        deezer_url = urls[0]
        assert deezer_url.platform_key == 'deezer'
        assert deezer_url.url == 'https://www.deezer.com/track/568497412'
        deezer_new = urls[1]
        assert deezer_new.platform_key == 'deezer'
        assert deezer_new.url == 'https://deezer.page.link/aXUq1xjzF8s2AZje9'
        deezer_ru = urls[2]
        assert deezer_ru.platform_key == 'deezer'
        assert deezer_ru.url == 'https://www.deezer.com/ru/track/568497412'
        soundcloud_url = urls[3]
        assert soundcloud_url.platform_key == 'soundcloud'
        assert soundcloud_url.url == (
            'https://soundcloud.com/worakls/nto-trauma-worakls-remix'
        )
        yandex_com = urls[4]
        assert yandex_com.platform_key == 'yandex'
        assert yandex_com.url == (
            'https://music.yandex.com/album/50197/track/120711'
        )
        yandex_ru = urls[5]
        assert yandex_ru.platform_key == 'yandex'
        assert yandex_ru.url == (
            'https://music.yandex.ru/album/6004920/track/44769475'
        )
        yandex_by = urls[6]
        assert yandex_by.platform_key == 'yandex'
        assert yandex_by.url == (
            'https://music.yandex.by/album/6004920/track/44769475'
        )
        spotify = urls[7]
        assert spotify.platform_key == 'spotify'
        assert spotify.url == (
            'https://open.spotify.com/track/1gfzgfcrmkn2yTWuVGhCgh'
        )
        spotify = urls[8]
        assert spotify.platform_key == 'spotify'
        assert spotify.url == 'https://link.tospotify.com/pfc3erwl2ab'
        youtube_music = urls[9]
        assert youtube_music.platform_key == 'youtubeMusic'
        assert youtube_music.url == (
            'https://music.youtube.com/watch?v=eVTXPUF4Oz4'
        )
        youtube_music_album = urls[10]
        assert youtube_music_album.platform_key == 'youtubeMusic'
        assert youtube_music_album.url == (
            'https://music.youtube.com/playlist?list='
            'OLAK5uy_l2F5ezYgFM0mQ3tg2-vK900BTgr8zXMW0'
        )
        youtube = urls[11]
        assert youtube.platform_key == 'youtube'
        assert youtube.url == 'https://www.youtube.com/watch?v=eVTXPUF4Oz4'
        youtube_album = urls[12]
        assert youtube_album.platform_key == 'youtube'
        assert youtube_album.url == (
            'https://www.youtube.com/playlist?list='
            'OLAK5uy_n64ojqXEYWqrvO5GAWU1Ik040wTIzBdbQ'
        )
        youtube_short = urls[13]
        assert youtube_short.platform_key == 'youtube'
        assert youtube_short.url == 'https://youtu.be/ugYB3VxpivU'
        apple_music = urls[14]
        assert apple_music.platform_key == 'appleMusic'
        assert apple_music.url == (
            'https://music.apple.com/se/album/raindrops-feat-j3po/1450701158'
        )
        tidal = urls[15]
        assert tidal.platform_key == 'tidal'
        assert tidal.url == 'https://tidal.com/track/139494756'
        bandcamp_album = urls[16]
        assert bandcamp_album.platform_key == 'bandcamp'
        assert bandcamp_album.url == (
            'https://gunnarspardel.bandcamp.com/album/simplicity-in-a-'
            'complex-world'
        )
        bandcamp_track = urls[17]
        assert bandcamp_track.platform_key == 'bandcamp'
        assert bandcamp_track.url == (
            'https://carbonbasedlifeforms.bandcamp.com/track/6equj5'
        )

    @mark.parametrize(
        'url',
        [
            'https://open.spotify.com/user/spotify/playlist/INVALID',
            'https://open.spotify.com/playlist/INVALID',
            'https://open.spotify.com/artist/INVALID',
            'https://www.spotify.com/us/purchase/products/?country=RU',
            'https://spotify.com/family-plan/redeem/?token=INVALID',
            'https://open.spotify.com/episode/INVALID',
            'https://support.spotify.com/ru-ru/article/INVALID/',
            'https://www.youtube.com/channel/INVALID',
            'https://music.youtube.com/transfer',
            'https://music.apple.com/ru/artist/INVALID',
            'https://music.apple.com/en/playlist/INVALID',
            'https://music.yandex.ru/users/INVALID',
            'https://www.deezer.com/playlist/INVALID',
            'https://bandcamp.com/?from=menubar_logo_logged_out',
            'https://daily.bandcamp.com/',
        ],
    )
    async def test_skips_incorrect_urls(self, bot, url):
        """Skip messages with invalid URLs."""
        assert not bot.extract_song_urls(url)

    async def test_merges_urls_for_same_song(self, bot: OdesliBot):
        """Merge SongInfo objects if they point to the same song."""
        song_infos = (
            SongInfo(
                ids={'id1', 'id2'},
                title='Test title',
                artist='Test artist',
                thumbnail_url='url1',
                urls={'deezer': 'http://test_deezer_url'},
                urls_in_text={'http://test_deezer_url'},
            ),
            SongInfo(
                ids={'id2', 'id3'},
                title='Test title',
                artist='Test artist',
                thumbnail_url='url2',
                urls={'google': 'http://test_google_url'},
                urls_in_text={'http://test_google_url'},
            ),
            SongInfo(
                ids={'id3', 'id4'},
                title='Test title',
                artist='Test artist',
                thumbnail_url='url3',
                urls={'soundcloud': 'http://test_soundcloud_url'},
                urls_in_text={'http://test_soundcloud_url'},
            ),
            SongInfo(
                ids={'id5'},
                title='Not merged',
                artist='Not merged',
                thumbnail_url='url4',
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
        assert song_info.thumbnail_url
        assert set(song_info.urls_in_text) == {
            'http://test_deezer_url',
            'http://test_google_url',
            'http://test_soundcloud_url',
        }
        assert len(song_info.urls_in_text) == 3
