"""Unit tests for Songlink bot."""
from pytest import mark

from group_songlink_bot.bot import SongInfo, SonglinkBot


@mark.usefixtures('loop')
class TestSonglinkBot:
    """Unit tests for Songlink bot."""

    async def test_extracts_urls(self, bot: SonglinkBot):
        """Extract platform URLs and positions from message text."""
        text = (
            'Check this out: https://www.deezer.com/track/568497412,\n'
            'Check this out: https://play.google.com/music/m/Tdyd5oxivy52cpw'
            '4b2qqbgewdwu.\n'
            'Check this out: https://soundcloud.com/worakls/nto-trauma-worakls'
            '-remix Great songs!'
        )
        urls = bot.extract_song_urls(text)
        assert len(urls) == 3
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

    async def test_merges_urls_for_same_song(self, bot: SonglinkBot):
        """Merge SongInfo objects if they point to the same song."""
        song_infos = (
            SongInfo(
                ids={'id1', 'id2'},
                title='Test title',
                artist='Test artist',
                urls={'deezer': 'http://test_deezer_url'},
                urls_in_text=['http://test_deezer_url'],
            ),
            SongInfo(
                ids={'id2', 'id3'},
                title='Test title',
                artist='Test artist',
                urls={'google': 'http://test_google_url'},
                urls_in_text=['http://test_google_url'],
            ),
            SongInfo(
                ids={'id3', 'id4'},
                title='Test title',
                artist='Test artist',
                urls={'soundcloud': 'http://test_soundcloud_url'},
                urls_in_text=['http://test_soundcloud_url'],
            ),
            SongInfo(
                ids={'id5'},
                title='Not merged',
                artist='Not merged',
                urls={'not_merged': 'http://not_merged'},
                urls_in_text=['http://not_merged'],
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
