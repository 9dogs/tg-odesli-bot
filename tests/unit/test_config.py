"""Tests for configuration."""
from tg_odesli_bot.settings import TestSettings


class TestConfiguration:
    """Tests for configuration."""

    def test_loads_settings(self):
        """Load config."""
        config = TestSettings.load()
        assert config
